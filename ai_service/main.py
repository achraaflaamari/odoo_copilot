# -*- coding: utf-8 -*-
"""
Microservice FastAPI : point d'entrée du service IA OdooCopilot.
Fournit les endpoints /health et /chat avec authentification par clé API.
"""

import os
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis .env
load_dotenv()

from agents.router import run_graph

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
    version="1.0.0",
)

# Middleware CORS : autorise les appels depuis Odoo (localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8069", "http://localhost:8001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        # Si aucune clé n'est configurée, on avertit mais on laisse passer (dev)
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
    status: str  # "ok" | "draft" | "error"
    draft_payload: dict | None = None


# ──────────────────────────── Endpoints ────────────────────────────────────

@app.get("/health", tags=["Santé"])
def health_check() -> dict[str, str]:
    """Vérifie que le service est opérationnel.

    Returns:
        Dictionnaire indiquant le statut et la version du service.
    """
    return {"status": "ok", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(
    request: ChatRequest,
    _api_key: str = Depends(verify_api_key),
) -> ChatResponse:
    """Reçoit une question et retourne la réponse de l'agent IA approprié.

    Args:
        request: Corps de la requête avec la question et l'identifiant utilisateur.
        _api_key: Clé API validée (injectée par FastAPI).

    Returns:
        Réponse structurée de l'agent IA.
    """
    logger.info("Requête /chat reçue : user_id=%d, question=%s", request.user_id, request.question[:80])
    result: dict[str, Any] = run_graph(question=request.question, user_id=request.user_id)
    return ChatResponse(
        answer=result.get("answer", ""),
        agent=result.get("agent", "routeur"),
        status=result.get("status", "ok"),
        draft_payload=result.get("draft_payload"),
    )
