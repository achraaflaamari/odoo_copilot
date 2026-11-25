# -*- coding: utf-8 -*-
"""
Exécution commune des agents outillés.

S'appuie sur l'API LangChain 1.x (`create_agent`) : le graphe appelle les outils
en boucle jusqu'à obtenir une réponse finale. Les brouillons sont détectés dans
les messages `ToolMessage` renvoyés par les outils `propose_*`.
"""

import json
import logging
from typing import Any, Iterable, Sequence

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


def _content_to_text(content: Any) -> str:
    """Convertit le contenu d'un message IA en texte exploitable."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts).strip()
    return ""


def _extract_answer(messages: Sequence[Any]) -> str:
    """Retourne le contenu du dernier message IA texte."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _content_to_text(message.content)
            if text:
                return text
    return "Aucune réponse générée."


def _extract_draft(
    messages: Sequence[Any],
    draft_tool_names: Iterable[str],
) -> dict | None:
    """Retourne le dernier payload JSON produit par un outil de brouillon."""
    names = set(draft_tool_names)
    draft_payload: dict | None = None
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        if getattr(message, "name", None) not in names:
            continue
        try:
            payload = json.loads(message.content)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Payload de brouillon illisible pour l'outil %s.", message.name)
            continue
        if isinstance(payload, dict):
            draft_payload = payload
    return draft_payload


def run_tool_agent(
    *,
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
    question: str,
    agent_name: str,
    draft_tool_names: Iterable[str] = (),
) -> dict[str, Any]:
    """Exécute un agent outillé et normalise sa réponse.

    Args:
        llm: Modèle de chat compatible avec le tool calling.
        tools: Liste blanche des outils autorisés pour cet agent.
        system_prompt: Instructions système de l'agent.
        question: Question de l'utilisateur.
        agent_name: Nom retourné dans la réponse (`ventes`, `achats`, `projets`).
        draft_tool_names: Outils dont la sortie JSON devient un brouillon.

    Returns:
        Dictionnaire avec `answer`, `agent`, `status` et `draft_payload`.
    """
    try:
        agent = create_agent(model=llm, tools=list(tools), system_prompt=system_prompt)
        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        messages = result.get("messages", [])
        draft_payload = _extract_draft(messages, draft_tool_names)
        return {
            "answer": _extract_answer(messages),
            "agent": agent_name,
            "status": "draft" if draft_payload else "ok",
            "draft_payload": draft_payload,
        }
    except Exception as exc:
        logger.error("Erreur dans l'agent %s : %s", agent_name, exc)
        return {
            "answer": f"Erreur de l'agent {agent_name} : {exc}",
            "agent": agent_name,
            "status": "error",
            "draft_payload": None,
        }
