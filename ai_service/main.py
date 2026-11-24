# -*- coding: utf-8 -*-
"""
Microservice FastAPI : point d'entrée du service IA OdooCopilot.
Fournit les endpoints /health, /chat, /approve et /reject
avec authentification par clé API.
Phase 3 : ajout du mécanisme de brouillon, approbation/rejet et journalisation.
"""

import json
import logging
import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis .env
load_dotenv()

from agents.router import run_graph
from tools.odoo_client import odoo_client

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
    version="2.0.0",
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
# Dictionnaire { draft_id: DraftEntry } — remplacé par une base persistante en Phase 4+.
_drafts: dict[str, dict] = {}


def verify_api_key(key: str = Security(api_key_header)) -> str:
    """Vérifie que la clé API fournie dans l'en-tête X-API-Key est valide.

    Args:
        key: Clé API extraite de l'en-tête HTTP.

    Returns:
        La clé API si elle est valide.

    Raises:
        HTTPException 403: Si la clé est absente ou incorrecte.
    """
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
    status: str          # "ok" | "draft" | "error"
    draft_id: str | None = None
    draft_payload: dict | None = None


class ActionResponse(BaseModel):
    """Corps de la réponse POST /approve ou /reject."""

    draft_id: str
    action: str          # "approved" | "rejected"
    message: str
    log_id: int | None = None


# ──────────────────────────── Endpoints ────────────────────────────────────

@app.get("/health", tags=["Santé"])
def health_check() -> dict[str, str]:
    """Vérifie que le service est opérationnel.

    Returns:
        Dictionnaire indiquant le statut et la version du service.
    """
    return {"status": "ok", "version": "2.0.0"}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(
    request: ChatRequest,
    _api_key: str = Depends(verify_api_key),
) -> ChatResponse:
    """Reçoit une question et retourne la réponse de l'agent IA approprié.
    Si l'agent produit un brouillon d'action, celui-ci est stocké et un draft_id est retourné.

    Args:
        request: Corps de la requête avec la question et l'identifiant utilisateur.
        _api_key: Clé API validée (injectée par FastAPI).

    Returns:
        Réponse structurée de l'agent IA.
    """
    logger.info("Requête /chat reçue : user_id=%d, question=%s", request.user_id, request.question[:80])
    result: dict[str, Any] = run_graph(question=request.question, user_id=request.user_id)

    draft_id: str | None = None
    draft_payload = result.get("draft_payload")

    # Si un brouillon existe, l'enregistrer et journaliser dans Odoo
    if draft_payload:
        draft_id = str(uuid.uuid4())
        _drafts[draft_id] = {
            "question": request.question,
            "user_id": request.user_id,
            "agent": result.get("agent", "routeur"),
            "answer": result.get("answer", ""),
            "draft_payload": draft_payload,
            "status": "draft",
        }
        _log_to_odoo(
            question=request.question,
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


@app.post("/approve/{draft_id}", response_model=ActionResponse, tags=["Validation"])
def approve_draft(
    draft_id: str,
    _api_key: str = Depends(verify_api_key),
) -> ActionResponse:
    """Approuve un brouillon d'action et l'exécute dans Odoo.

    Args:
        draft_id: Identifiant unique du brouillon à approuver.
        _api_key: Clé API validée (injectée par FastAPI).

    Returns:
        Confirmation de l'approbation avec le log_id Odoo créé.

    Raises:
        HTTPException 404: Si le brouillon n'existe pas.
        HTTPException 409: Si le brouillon a déjà été traité.
    """
    draft = _get_draft_or_404(draft_id)
    if draft["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail=f"Ce brouillon a déjà été traité (statut : {draft['status']}).",
        )

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
        message="Action approuvée et journalisée. L'exécution réelle nécessite une intégration Odoo complète (Phase 4).",
        log_id=log_id,
    )


@app.post("/reject/{draft_id}", response_model=ActionResponse, tags=["Validation"])
def reject_draft(
    draft_id: str,
    _api_key: str = Depends(verify_api_key),
) -> ActionResponse:
    """Rejette un brouillon d'action.

    Args:
        draft_id: Identifiant unique du brouillon à rejeter.
        _api_key: Clé API validée (injectée par FastAPI).

    Returns:
        Confirmation du rejet avec le log_id Odoo créé.

    Raises:
        HTTPException 404: Si le brouillon n'existe pas.
        HTTPException 409: Si le brouillon a déjà été traité.
    """
    draft = _get_draft_or_404(draft_id)
    if draft["status"] != "draft":
        raise HTTPException(
            status_code=409,
            detail=f"Ce brouillon a déjà été traité (statut : {draft['status']}).",
        )

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
    """Retourne la liste des brouillons en attente de validation.

    Returns:
        Dictionnaire listant les brouillons avec leur statut.
    """
    pending = {
        draft_id: {k: v for k, v in entry.items() if k != "draft_payload"}
        for draft_id, entry in _drafts.items()
        if entry["status"] == "draft"
    }
    return {"drafts": pending, "count": len(pending)}


# ──────────────────────────── Fonctions internes ────────────────────────────

def _get_draft_or_404(draft_id: str) -> dict:
    """Récupère un brouillon par son identifiant ou lève une HTTPException 404.

    Args:
        draft_id: Identifiant unique du brouillon.

    Returns:
        Entrée du brouillon.

    Raises:
        HTTPException 404: Si le brouillon n'existe pas.
    """
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
    """Enregistre une entrée dans le modèle Odoo ai.action.log.

    Args:
        question: Question posée par l'utilisateur.
        agent: Nom de l'agent IA ayant traité la demande.
        status: Statut de l'action ('draft', 'approved', 'rejected').
        draft_payload: Payload du brouillon (peut être None).
        response: Réponse complète de l'agent.
        user_id: Identifiant de l'utilisateur Odoo.

    Returns:
        Identifiant de l'enregistrement créé dans Odoo, ou None si échec.
    """
    try:
        summary = question[:100] if question else "Action IA"
        values = {
            "name": summary,
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
