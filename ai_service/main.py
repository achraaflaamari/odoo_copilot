# -*- coding: utf-8 -*-
"""
Microservice FastAPI — Phase 4 :
- Filtrage des injections de prompt sur /chat
- Endpoint /stream pour les réponses en Server-Sent Events (SSE)
- Endpoint /rag/index pour indexer des documents
- Endpoint /rag/search pour tester la recherche documentaire
- Intégration du contexte RAG dans les agents (via general_node)
"""

import json
import logging
import os
import uuid
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis .env
load_dotenv()

from agents.router import run_graph
from tools.odoo_client import odoo_client
from tools.prompt_filter import sanitize_question
from rag.retriever import rag_retriever

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
logger = logging.getLogger(__name__)

# Clé API du service (depuis les variables d'environnement)
SERVICE_API_KEY: str = os.getenv("SERVICE_API_KEY", "")

# Schéma de sécurité : clé API dans l'en-tête X-API-Key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

app = FastAPI(
    title="OdooCopilot IA Service",
    description="Microservice multi-agents LangGraph pour Odoo Copilot.",
    version="3.0.0",
)

# Middleware CORS : autorise les appels depuis Odoo (localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8069", "http://localhost:8001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────── Stockage en mémoire des brouillons ──────────────────
_drafts: dict[str, dict] = {}


def verify_api_key(key: str = Security(api_key_header)) -> str:
    """Vérifie que la clé API fournie dans l'en-tête X-API-Key est valide."""
    if not SERVICE_API_KEY:
        logger.warning("SERVICE_API_KEY non configurée — authentification désactivée en mode développement.")
        return key
    if key != SERVICE_API_KEY:
        logger.warning("Tentative d'accès avec une clé API invalide.")
        raise HTTPException(status_code=403, detail="Clé API invalide ou absente.")
    return key


# ─────────────────────────── Schémas Pydantic ───────────────────────────────

class ChatRequest(BaseModel):
    """Corps de la requête POST /chat."""
    question: str
    user_id: int = 1
    session_id: str = ""


class ChatResponse(BaseModel):
    """Corps de la réponse POST /chat."""
    answer: str
    agent: str
    status: str          # "ok" | "draft" | "error" | "blocked"
    draft_id: str | None = None
    draft_payload: dict | None = None


class ActionResponse(BaseModel):
    """Corps de la réponse POST /approve ou /reject."""
    draft_id: str
    action: str
    message: str
    log_id: int | None = None


class RagIndexRequest(BaseModel):
    """Corps de la requête POST /rag/index."""
    documents: list[dict]   # list of {id, text, metadata}


class RagSearchRequest(BaseModel):
    """Corps de la requête POST /rag/search."""
    query: str
    n_results: int = 3


# ──────────────────────────── Endpoints ────────────────────────────────────

@app.get("/health", tags=["Santé"])
def health_check() -> dict[str, Any]:
    """Vérifie que le service est opérationnel."""
    return {
        "status": "ok",
        "version": "3.0.0",
        "rag_ready": rag_retriever.is_ready,
        "rag_documents": rag_retriever.document_count(),
        "rag_backend": rag_retriever.embedding_backend,
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(
    request: ChatRequest,
    _api_key: str = Depends(verify_api_key),
) -> ChatResponse:
    """Reçoit une question, applique le filtrage d'injection, puis exécute le graphe LangGraph.
    Si un brouillon est produit, il est stocké avec un draft_id unique.
    """
    # ── 1. Filtrage anti-injection ──────────────────────────────────────────
    clean_question, injected = sanitize_question(request.question)
    if injected:
        logger.warning("Injection de prompt bloquée : user_id=%d", request.user_id)
        _log_to_odoo(
            question=request.question[:100],
            agent="routeur",
            status="rejected",
            draft_payload=None,
            response="[BLOQUÉ] Injection de prompt détectée.",
            user_id=request.user_id,
        )
        return ChatResponse(
            answer="⚠️ Votre message a été bloqué car il contient des instructions non autorisées.",
            agent="routeur",
            status="blocked",
        )

    logger.info("Requête /chat : user_id=%d, question=%s", request.user_id, clean_question[:80])

    # ── 2. Contexte RAG (si disponible) ────────────────────────────────────
    rag_context = rag_retriever.search_as_context(clean_question, n_results=2)
    if rag_context:
        logger.info("Contexte RAG injecté (%d chars).", len(rag_context))
        # Le contexte est préfixé à la question pour enrichir le LLM
        augmented_question = f"[Contexte documentaire]\n{rag_context}\n\n[Question]\n{clean_question}"
    else:
        augmented_question = clean_question

    # ── 3. Exécution du graphe LangGraph ───────────────────────────────────
    result: dict[str, Any] = run_graph(question=augmented_question, user_id=request.user_id)

    draft_id: str | None = None
    draft_payload = result.get("draft_payload")

    if draft_payload:
        draft_id = str(uuid.uuid4())
        _drafts[draft_id] = {
            "question": clean_question,
            "user_id": request.user_id,
            "agent": result.get("agent", "routeur"),
            "answer": result.get("answer", ""),
            "draft_payload": draft_payload,
            "status": "draft",
        }
        _log_to_odoo(
            question=clean_question,
            agent=result.get("agent", "routeur"),
            status="draft",
            draft_payload=draft_payload,
            response=result.get("answer", ""),
            user_id=request.user_id,
        )
        logger.info("Brouillon créé : draft_id=%s", draft_id)

    return ChatResponse(
        answer=result.get("answer", ""),
        agent=result.get("agent", "routeur"),
        status=result.get("status", "ok"),
        draft_id=draft_id,
        draft_payload=draft_payload,
    )


@app.get("/stream", tags=["Chat"])
async def stream_chat(
    question: str,
    user_id: int = 1,
    api_key: str = "",
) -> StreamingResponse:
    """Endpoint SSE : envoie la réponse token par token (Server-Sent Events).

    Le client consomme l'EventSource avec :
        const es = new EventSource('/stream?question=...&api_key=...');

    Format des événements :
        data: {"token": "...", "done": false}
        data: {"token": "", "done": true, "agent": "...", "status": "..."}
    """
    # Vérification de la clé API (GET — passée en query param)
    if SERVICE_API_KEY and api_key != SERVICE_API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide.")

    # Filtrage anti-injection
    clean_question, injected = sanitize_question(question)
    if injected:
        async def blocked_stream() -> AsyncGenerator[str, None]:
            payload = json.dumps({"token": "⚠️ Message bloqué : injection de prompt détectée.", "done": False})
            yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'token': '', 'done': True, 'agent': 'routeur', 'status': 'blocked'})}\n\n"
        return StreamingResponse(blocked_stream(), media_type="text/event-stream")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Génère les tokens SSE depuis le graphe LangGraph.

        Note : LangGraph/Groq ne supporte pas le streaming natif token par token
        dans cette configuration. On simule le streaming en envoyant d'abord un
        événement 'thinking' puis la réponse complète découpée en mots.
        Le vrai streaming par token nécessite langchain_groq avec streaming=True
        et un callback handler (prévu pour Phase 5+).
        """
        # Signal de début
        yield f"data: {json.dumps({'token': '', 'thinking': True})}\n\n"

        try:
            # Exécution synchrone dans l'event loop
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: run_graph(question=clean_question, user_id=user_id),
            )
            answer = result.get("answer", "")
            agent = result.get("agent", "routeur")
            status = result.get("status", "ok")

            # Envoi mot par mot pour simuler le streaming
            words = answer.split(" ")
            for i, word in enumerate(words):
                token = word + (" " if i < len(words) - 1 else "")
                payload = json.dumps({"token": token, "done": False}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0.03)   # délai simulé entre tokens

            # Événement de fin
            yield f"data: {json.dumps({'token': '', 'done': True, 'agent': agent, 'status': status})}\n\n"

        except Exception as exc:
            logger.error("Erreur dans le stream SSE : %s", exc)
            err = json.dumps({"token": f"Erreur : {exc}", "done": True, "agent": "routeur", "status": "error"})
            yield f"data: {err}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/approve/{draft_id}", response_model=ActionResponse, tags=["Validation"])
def approve_draft(
    draft_id: str,
    _api_key: str = Depends(verify_api_key),
) -> ActionResponse:
    """Approuve un brouillon et le journalise dans ai.action.log."""
    draft = _get_draft_or_404(draft_id)
    if draft["status"] != "draft":
        raise HTTPException(status_code=409, detail=f"Brouillon déjà traité : {draft['status']}.")
    draft["status"] = "approved"
    log_id = _log_to_odoo(
        question=draft["question"],
        agent=draft["agent"],
        status="approved",
        draft_payload=draft["draft_payload"],
        response=draft["answer"],
        user_id=draft["user_id"],
    )
    logger.info("Brouillon approuvé : draft_id=%s, log_id=%s", draft_id, log_id)
    return ActionResponse(
        draft_id=draft_id,
        action="approved",
        message="Action approuvée et journalisée.",
        log_id=log_id,
    )


@app.post("/reject/{draft_id}", response_model=ActionResponse, tags=["Validation"])
def reject_draft(
    draft_id: str,
    _api_key: str = Depends(verify_api_key),
) -> ActionResponse:
    """Rejette un brouillon et le journalise dans ai.action.log."""
    draft = _get_draft_or_404(draft_id)
    if draft["status"] != "draft":
        raise HTTPException(status_code=409, detail=f"Brouillon déjà traité : {draft['status']}.")
    draft["status"] = "rejected"
    log_id = _log_to_odoo(
        question=draft["question"],
        agent=draft["agent"],
        status="rejected",
        draft_payload=draft["draft_payload"],
        response=draft["answer"],
        user_id=draft["user_id"],
    )
    logger.info("Brouillon rejeté : draft_id=%s, log_id=%s", draft_id, log_id)
    return ActionResponse(
        draft_id=draft_id,
        action="rejected",
        message="Action rejetée et journalisée.",
        log_id=log_id,
    )


@app.get("/drafts", tags=["Validation"])
def list_drafts(_api_key: str = Depends(verify_api_key)) -> dict:
    """Retourne la liste des brouillons en attente."""
    pending = {
        did: {k: v for k, v in entry.items() if k != "draft_payload"}
        for did, entry in _drafts.items()
        if entry["status"] == "draft"
    }
    return {"drafts": pending, "count": len(pending)}


@app.post("/rag/index", tags=["RAG"])
def rag_index(
    request: RagIndexRequest,
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """Indexe des documents dans ChromaDB.

    Body : {"documents": [{"id": "...", "text": "...", "metadata": {...}}]}
    """
    if not rag_retriever.is_ready:
        raise HTTPException(
            status_code=503,
            detail="RAG non disponible. Installez le RAG optionnel : pip install -r requirements-rag.txt",
        )
    indexed = rag_retriever.index_documents(request.documents)
    return {"indexed": indexed, "total": rag_retriever.document_count()}


@app.post("/rag/search", tags=["RAG"])
def rag_search(
    request: RagSearchRequest,
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """Recherche des documents pertinents dans ChromaDB."""
    if not rag_retriever.is_ready:
        raise HTTPException(
            status_code=503,
            detail="RAG non disponible. Installez le RAG optionnel : pip install -r requirements-rag.txt",
        )
    results = rag_retriever.search(query=request.query, n_results=request.n_results)
    return {"query": request.query, "results": results}


# ──────────────────────────── Fonctions internes ────────────────────────────

def _get_draft_or_404(draft_id: str) -> dict:
    draft = _drafts.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Brouillon '{draft_id}' introuvable.")
    return draft


def _log_to_odoo(
    question: str,
    agent: str,
    status: str,
    draft_payload: dict | None,
    response: str,
    user_id: int,
) -> int | None:
    """Enregistre une entrée dans le modèle Odoo ai.action.log."""
    try:
        values = {
            "name": question[:100] if question else "Action IA",
            "question": question,
            "agent": agent,
            "status": status,
            "draft_payload": json.dumps(draft_payload, ensure_ascii=False) if draft_payload else False,
            "response": response,
            "user_id": user_id if user_id else False,
        }
        log_id = odoo_client.create(model="ai.action.log", values=values)
        logger.info("Journal Odoo créé : ai.action.log id=%s", log_id)
        return log_id
    except Exception as exc:
        logger.warning("Impossible de journaliser dans Odoo : %s", exc)
        return None
