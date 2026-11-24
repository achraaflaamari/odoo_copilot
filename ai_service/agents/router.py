# -*- coding: utf-8 -*-
"""
Graphe LangGraph principal : agent routeur + agents spécialisés.
Le routeur classifie la question et délègue à l'agent approprié.
"""

import os
import logging
from typing import Any

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from agents.sales_agent import run_sales_agent

logger = logging.getLogger(__name__)

# Initialisation du LLM Groq pour la classification
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY", ""),
    temperature=0,
)

# Catégories de classification supportées
CATEGORIES = ["ventes", "achats", "projets", "general"]

CLASSIFY_PROMPT = """Tu es un routeur d'agents IA pour un ERP Odoo.
Classe la question suivante dans UNE SEULE des catégories : ventes, achats, projets, general.
Réponds UNIQUEMENT avec le mot de la catégorie, sans explication.

Question : {question}
Catégorie :"""


class AgentState(TypedDict):
    """État partagé du graphe LangGraph."""

    question: str
    user_id: int
    agent: str
    answer: str
    status: str
    draft_payload: dict | None


def classify(state: AgentState) -> AgentState:
    """Nœud de classification : détermine l'agent compétent.

    Args:
        state: État courant du graphe.

    Returns:
        État mis à jour avec le champ 'agent' renseigné.
    """
    question = state["question"]
    prompt = CLASSIFY_PROMPT.format(question=question)
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        category = response.content.strip().lower()
        # Validation : si la catégorie n'est pas reconnue, on choisit 'general'
        if category not in CATEGORIES:
            logger.warning("Catégorie non reconnue '%s', utilisation de 'general'.", category)
            category = "general"
    except Exception as exc:
        logger.error("Erreur lors de la classification : %s", exc)
        category = "general"

    logger.info("Question classifiée : agent=%s", category)
    return {**state, "agent": category}


def route_to_agent(state: AgentState) -> str:
    """Fonction de routage conditionnel basée sur l'agent classifié.

    Args:
        state: État courant du graphe.

    Returns:
        Nom du nœud suivant à exécuter.
    """
    agent = state.get("agent", "general")
    if agent == "ventes":
        return "sales_agent"
    # Tous les autres cas vont vers le nœud général
    return "general"


def sales_agent_node(state: AgentState) -> AgentState:
    """Nœud agent ventes : délègue au sales_agent.

    Args:
        state: État courant du graphe.

    Returns:
        État mis à jour avec la réponse de l'agent ventes.
    """
    result = run_sales_agent(question=state["question"], user_id=state["user_id"])
    return {
        **state,
        "answer": result["answer"],
        "agent": result["agent"],
        "status": result["status"],
        "draft_payload": result.get("draft_payload"),
    }


def general_node(state: AgentState) -> AgentState:
    """Nœud général : répond directement avec le LLM sans outil.

    Args:
        state: État courant du graphe.

    Returns:
        État mis à jour avec la réponse directe du LLM.
    """
    question = state["question"]
    system = (
        "Tu es un assistant ERP utile. Réponds en français, de manière concise. "
        "Si la question porte sur des données Odoo spécifiques (ventes, achats, projets), "
        "indique que tu n'as pas accès aux données en temps réel pour cette catégorie."
    )
    try:
        response = llm.invoke([
            HumanMessage(content=f"[SYSTÈME] {system}\n\nQuestion : {question}"),
        ])
        answer = response.content
        status = "ok"
    except Exception as exc:
        logger.error("Erreur dans le nœud général : %s", exc)
        answer = f"Erreur lors de la génération de la réponse : {exc}"
        status = "error"

    return {
        **state,
        "answer": answer,
        "agent": "routeur",
        "status": status,
        "draft_payload": None,
    }


def build_graph() -> StateGraph:
    """Construit et compile le graphe LangGraph.

    Returns:
        Graphe compilé prêt à être invoqué.
    """
    builder = StateGraph(AgentState)

    # Ajout des nœuds
    builder.add_node("classify", classify)
    builder.add_node("sales_agent", sales_agent_node)
    builder.add_node("general", general_node)

    # Nœud de départ
    builder.set_entry_point("classify")

    # Routage conditionnel après classification
    builder.add_conditional_edges(
        "classify",
        route_to_agent,
        {
            "sales_agent": "sales_agent",
            "general": "general",
        },
    )

    # Les nœuds terminaux pointent vers END
    builder.add_edge("sales_agent", END)
    builder.add_edge("general", END)

    return builder.compile()


# Graphe compilé (singleton)
_graph = build_graph()


def run_graph(question: str, user_id: int = 1) -> dict[str, Any]:
    """Point d'entrée principal du graphe LangGraph.

    Args:
        question: Question posée par l'utilisateur.
        user_id: Identifiant de l'utilisateur Odoo.

    Returns:
        Dictionnaire avec 'answer', 'agent', 'status', 'draft_payload'.
    """
    initial_state: AgentState = {
        "question": question,
        "user_id": user_id,
        "agent": "",
        "answer": "",
        "status": "ok",
        "draft_payload": None,
    }
    try:
        final_state = _graph.invoke(initial_state)
        return {
            "answer": final_state.get("answer", ""),
            "agent": final_state.get("agent", "routeur"),
            "status": final_state.get("status", "ok"),
            "draft_payload": final_state.get("draft_payload"),
        }
    except Exception as exc:
        logger.error("Erreur lors de l'exécution du graphe : %s", exc)
        return {
            "answer": f"Erreur interne du graphe : {exc}",
            "agent": "routeur",
            "status": "error",
            "draft_payload": None,
        }
