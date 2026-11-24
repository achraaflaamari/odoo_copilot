# -*- coding: utf-8 -*-
"""
Contrôleur HTTP Odoo : proxy entre le frontend OWL et le microservice FastAPI.
Expose les routes /copilot/chat, /copilot/approve, /copilot/reject.
"""

import json
import logging

import requests
from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)


def _get_config():
    """Récupère la configuration active du microservice.

    Returns:
        Tuple (service_url, service_api_key) ou (None, None) si absent.
    """
    config = request.env["ai.config"].sudo().search([("active", "=", True)], limit=1)
    if not config:
        return None, None
    return config.service_url, config.service_api_key


class CopilotController(http.Controller):
    """Contrôleur proxy : transfère les requêtes OWL vers le microservice FastAPI."""

    @http.route("/copilot/chat", type="json", auth="user", methods=["POST"], csrf=True)
    def chat(self, question: str = "", user_id: int = 1, **kwargs):
        """Transfère une question au microservice IA et retourne la réponse.

        Args:
            question: Question posée par l'utilisateur.
            user_id: Identifiant de l'utilisateur Odoo (injecté automatiquement).

        Returns:
            Dictionnaire JSON avec answer, agent, status, draft_id.
        """
        service_url, api_key = _get_config()
        if not service_url:
            return {"answer": "Le microservice IA n'est pas configuré.", "agent": "erreur", "status": "error"}

        # Utiliser l'uid réel de l'utilisateur connecté
        uid = request.env.uid
        payload = {
            "question": question,
            "user_id": uid,
            "session_id": str(request.session.sid),
        }
        try:
            resp = requests.post(
                f"{service_url}/chat",
                json=payload,
                headers={"X-API-Key": api_key or ""},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            logger.error("Timeout lors de l'appel au microservice IA.")
            return {"answer": "Le service IA ne répond pas (timeout). Réessayez.", "agent": "erreur", "status": "error"}
        except requests.RequestException as exc:
            logger.error("Erreur appel microservice : %s", exc)
            return {"answer": f"Erreur de connexion : {exc}", "agent": "erreur", "status": "error"}

    @http.route("/copilot/approve", type="json", auth="user", methods=["POST"], csrf=True)
    def approve(self, draft_id: str = "", **kwargs):
        """Approuve un brouillon d'action.

        Args:
            draft_id: Identifiant du brouillon à approuver.

        Returns:
            Dictionnaire JSON avec action et message.
        """
        service_url, api_key = _get_config()
        if not service_url:
            return {"action": "error", "message": "Microservice non configuré."}
        try:
            resp = requests.post(
                f"{service_url}/approve/{draft_id}",
                headers={"X-API-Key": api_key or ""},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("Erreur approbation brouillon : %s", exc)
            return {"action": "error", "message": str(exc)}

    @http.route("/copilot/reject", type="json", auth="user", methods=["POST"], csrf=True)
    def reject(self, draft_id: str = "", **kwargs):
        """Rejette un brouillon d'action.

        Args:
            draft_id: Identifiant du brouillon à rejeter.

        Returns:
            Dictionnaire JSON avec action et message.
        """
        service_url, api_key = _get_config()
        if not service_url:
            return {"action": "error", "message": "Microservice non configuré."}
        try:
            resp = requests.post(
                f"{service_url}/reject/{draft_id}",
                headers={"X-API-Key": api_key or ""},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("Erreur rejet brouillon : %s", exc)
            return {"action": "error", "message": str(exc)}
