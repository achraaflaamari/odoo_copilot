# -*- coding: utf-8 -*-
"""
Client JSON-RPC pour Odoo.
Permet d'authentifier un utilisateur et d'effectuer des opérations CRUD
sur les modèles Odoo depuis le microservice IA.
"""

import os
import json
import logging
from typing import Any

import requests
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

logger = logging.getLogger(__name__)

ODOO_URL: str = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB: str = os.getenv("ODOO_DB", "odoo")
ODOO_USER: str = os.getenv("ODOO_USER", "copilot_ai")
ODOO_API_KEY: str = os.getenv("ODOO_API_KEY", "")


class OdooClient:
    """Client JSON-RPC pour interagir avec Odoo via l'API clé."""

    def __init__(self) -> None:
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.user = ODOO_USER
        self.api_key = ODOO_API_KEY
        self._uid: int | None = None
        self._session = requests.Session()
        # Authentification par clé API dans l'en-tête HTTP
        self._session.headers.update({
            "Content-Type": "application/json",
        })

    def _call(self, endpoint: str, payload: dict) -> Any:
        """Envoie une requête JSON-RPC à Odoo.

        Args:
            endpoint: Chemin de l'endpoint (ex: '/web/dataset/call_kw').
            payload: Corps de la requête JSON-RPC.

        Returns:
            Résultat de l'appel JSON-RPC.

        Raises:
            RuntimeError: Si l'appel échoue ou retourne une erreur.
        """
        url = f"{self.url}{endpoint}"
        headers = {}
        if self.api_key:
            headers["X-Odoo-Api-Key"] = self.api_key
        try:
            response = self._session.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("Erreur HTTP lors de l'appel Odoo : %s", exc)
            raise RuntimeError(f"Erreur HTTP Odoo : {exc}") from exc

        if "error" in data:
            error_msg = data["error"].get("message", "Erreur inconnue")
            logger.error("Erreur JSON-RPC Odoo : %s", error_msg)
            raise RuntimeError(f"Erreur JSON-RPC Odoo : {error_msg}")

        return data.get("result")

    def authenticate(self) -> int:
        """Authentifie l'utilisateur et retourne son uid.

        Returns:
            Identifiant de l'utilisateur authentifié (uid).

        Raises:
            RuntimeError: Si l'authentification échoue.
        """
        if self._uid is not None:
            return self._uid

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "db": self.db,
                "login": self.user,
                "password": self.api_key,
            },
        }
        result = self._call("/web/session/authenticate", payload)
        uid = result.get("uid") if isinstance(result, dict) else None
        if not uid:
            raise RuntimeError("Authentification Odoo échouée. Vérifiez ODOO_USER et ODOO_API_KEY.")

        self._uid = uid
        logger.info("Authentifié sur Odoo avec uid=%d", uid)
        return uid

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 10,
    ) -> list[dict]:
        """Recherche et lit des enregistrements Odoo.

        Args:
            model: Nom du modèle Odoo (ex: 'sale.order').
            domain: Domaine de filtrage (ex: [['state', '=', 'sale']]).
            fields: Liste des champs à retourner.
            limit: Nombre maximum d'enregistrements.

        Returns:
            Liste de dictionnaires représentant les enregistrements.
        """
        uid = self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 2,
            "params": {
                "model": model,
                "method": "search_read",
                "args": [domain],
                "kwargs": {
                    "fields": fields,
                    "limit": limit,
                },
            },
        }
        result = self._call("/web/dataset/call_kw", payload)
        return result or []

    def create(self, model: str, values: dict) -> int:
        """Crée un enregistrement dans Odoo.

        Args:
            model: Nom du modèle Odoo.
            values: Dictionnaire des valeurs à créer.

        Returns:
            Identifiant du nouvel enregistrement.
        """
        uid = self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 3,
            "params": {
                "model": model,
                "method": "create",
                "args": [values],
                "kwargs": {},
            },
        }
        result = self._call("/web/dataset/call_kw", payload)
        return result

    def write(self, model: str, ids: list[int], values: dict) -> bool:
        """Modifie des enregistrements existants dans Odoo.

        Args:
            model: Nom du modèle Odoo.
            ids: Liste des identifiants à modifier.
            values: Dictionnaire des nouvelles valeurs.

        Returns:
            True si la modification a réussi.
        """
        uid = self.authenticate()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 4,
            "params": {
                "model": model,
                "method": "write",
                "args": [ids, values],
                "kwargs": {},
            },
        }
        result = self._call("/web/dataset/call_kw", payload)
        return result

    def get_sales_orders(self, limit: int = 10) -> list[dict]:
        """Retourne les commandes de vente récentes.

        Args:
            limit: Nombre maximum de commandes à retourner.

        Returns:
            Liste des commandes de vente avec leurs champs principaux.
        """
        return self.search_read(
            model="sale.order",
            domain=[],
            fields=["name", "partner_id", "amount_total", "state", "date_order"],
            limit=limit,
        )

    def get_purchase_orders(self, limit: int = 10) -> list[dict]:
        """Retourne les bons de commande récents.

        Args:
            limit: Nombre maximum de bons de commande à retourner.

        Returns:
            Liste des bons de commande avec leurs champs principaux.
        """
        return self.search_read(
            model="purchase.order",
            domain=[],
            fields=["name", "partner_id", "amount_total", "state", "date_order"],
            limit=limit,
        )

    def get_projects(self, limit: int = 10) -> list[dict]:
        """Retourne les projets récents.

        Args:
            limit: Nombre maximum de projets à retourner.

        Returns:
            Liste des projets avec leurs champs principaux.
        """
        return self.search_read(
            model="project.project",
            domain=[],
            fields=["name", "partner_id", "user_id", "date_start", "date"],
            limit=limit,
        )


# Instance partagée (singleton de session)
odoo_client = OdooClient()
