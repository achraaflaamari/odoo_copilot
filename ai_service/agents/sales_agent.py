# -*- coding: utf-8 -*-
"""
Agent Ventes : répond aux questions sur les commandes de vente Odoo.
Utilise Groq (Llama 3.3 70B) et l'outil get_sales_orders.
"""

import os
import logging
from typing import Any

from langchain_groq import ChatGroq
from langchain.tools import tool

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
def get_sales_orders_tool(limit: int = 10) -> str:
    """Récupère les commandes de vente récentes depuis Odoo.

    Args:
        limit: Nombre maximum de commandes à retourner (défaut: 10).

    Returns:
        Chaîne JSON listant les commandes de vente.
    """
    import json
    try:
        orders = odoo_client.get_sales_orders(limit=limit)
        return json.dumps(orders, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("Erreur lors de la récupération des commandes : %s", exc)
        return f"Erreur : impossible de récupérer les commandes de vente. {exc}"


# Liste blanche des outils autorisés pour l'agent ventes
SALES_TOOLS = [get_sales_orders_tool]

# Prompt système de l'agent ventes
SALES_SYSTEM_PROMPT = """Tu es un assistant spécialisé dans les ventes d'une entreprise utilisant Odoo.
Tu as accès aux commandes de vente en lecture seule.
Réponds en français, de manière concise et structurée.
Ne propose jamais de modification sans mentionner qu'elle nécessite une validation humaine.
Si tu ne trouves pas l'information, dis-le clairement."""

def run_sales_agent(question: str, user_id: int = 1) -> dict[str, Any]:
    """Exécute l'agent ventes pour répondre à une question.

    Args:
        question: Question posée par l'utilisateur.
        user_id: Identifiant de l'utilisateur Odoo.

    Returns:
        Dictionnaire avec les clés 'answer', 'agent', 'status'.
    """
    return run_tool_agent(
        llm=llm,
        tools=SALES_TOOLS,
        system_prompt=SALES_SYSTEM_PROMPT,
        question=question,
        agent_name="ventes",
    )
