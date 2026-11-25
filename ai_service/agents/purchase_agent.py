# -*- coding: utf-8 -*-
"""
Agent Achats : répond aux questions sur les bons de commande Odoo.
Utilise Groq (Llama 3.3 70B) et les outils d'accès aux achats.
En cas de demande d'écriture, prépare un brouillon sans exécuter directement.
"""

import json
import logging
import os
from typing import Any

from langchain.tools import tool
from langchain_groq import ChatGroq

from agents.tool_agent import run_tool_agent
from tools.odoo_client import odoo_client

logger = logging.getLogger(__name__)

# Initialisation du LLM Groq
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY", ""),
    temperature=0,
)


@tool
def get_purchase_orders_tool(limit: int = 10) -> str:
    """Récupère les bons de commande récents depuis Odoo.

    Args:
        limit: Nombre maximum de bons de commande à retourner (défaut: 10).

    Returns:
        Chaîne JSON listant les bons de commande.
    """
    try:
        orders = odoo_client.get_purchase_orders(limit=limit)
        return json.dumps(orders, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("Erreur lors de la récupération des achats : %s", exc)
        return f"Erreur : impossible de récupérer les bons de commande. {exc}"


@tool
def get_purchase_order_detail_tool(order_name: str) -> str:
    """Récupère le détail d'un bon de commande spécifique par son nom.

    Args:
        order_name: Nom du bon de commande (ex: 'PO/2024/0001').

    Returns:
        Chaîne JSON avec le détail du bon de commande.
    """
    try:
        orders = odoo_client.search_read(
            model="purchase.order",
            domain=[["name", "=", order_name]],
            fields=[
                "name", "partner_id", "amount_total", "state",
                "date_order", "date_planned", "currency_id", "notes",
            ],
            limit=1,
        )
        if not orders:
            return f"Aucun bon de commande trouvé avec le nom '{order_name}'."
        return json.dumps(orders[0], ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("Erreur lors de la récupération du détail achat : %s", exc)
        return f"Erreur : {exc}"


@tool
def propose_purchase_order_tool(
    partner_name: str,
    product_description: str,
    quantity: float,
    unit_price: float,
) -> str:
    """Prépare un brouillon de bon de commande à soumettre à validation humaine.
    NE crée PAS directement dans Odoo — retourne uniquement le payload brouillon.

    Args:
        partner_name: Nom du fournisseur.
        product_description: Description du produit à commander.
        quantity: Quantité commandée.
        unit_price: Prix unitaire estimé.

    Returns:
        Chaîne JSON décrivant le brouillon de commande.
    """
    draft = {
        "action": "create_purchase_order",
        "model": "purchase.order",
        "values": {
            "partner_name": partner_name,
            "product_description": product_description,
            "quantity": quantity,
            "unit_price": unit_price,
            "amount_total_estimate": quantity * unit_price,
        },
        "requires_approval": True,
    }
    return json.dumps(draft, ensure_ascii=False)


# Liste blanche des outils autorisés pour l'agent achats
PURCHASE_TOOLS = [
    get_purchase_orders_tool,
    get_purchase_order_detail_tool,
    propose_purchase_order_tool,
]

# Prompt système de l'agent achats
PURCHASE_SYSTEM_PROMPT = """Tu es un assistant spécialisé dans les achats d'une entreprise utilisant Odoo.
Tu as accès aux bons de commande en lecture seule.
Réponds en français, de manière concise et structurée.

Règles importantes :
- Tu ne modifies JAMAIS directement les données Odoo.
- Si l'utilisateur demande à créer ou modifier une commande, utilise l'outil propose_purchase_order_tool
  pour préparer un brouillon, puis indique clairement que cela nécessite une validation humaine.
- Si tu ne trouves pas l'information, dis-le clairement."""

def run_purchase_agent(question: str, user_id: int = 1) -> dict[str, Any]:
    """Exécute l'agent achats pour répondre à une question.

    Args:
        question: Question posée par l'utilisateur.
        user_id: Identifiant de l'utilisateur Odoo.

    Returns:
        Dictionnaire avec les clés 'answer', 'agent', 'status', 'draft_payload'.
    """
    return run_tool_agent(
        llm=llm,
        tools=PURCHASE_TOOLS,
        system_prompt=PURCHASE_SYSTEM_PROMPT,
        question=question,
        agent_name="achats",
        draft_tool_names=("propose_purchase_order_tool",),
    )
