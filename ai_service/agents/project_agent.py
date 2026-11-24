# -*- coding: utf-8 -*-
"""
Agent Projets : répond aux questions sur les projets et tâches Odoo.
Utilise Groq (Llama 3.3 70B) et les outils d'accès aux projets.
En cas de demande d'écriture, prépare un brouillon sans exécuter directement.
"""

import json
import logging
import os
from typing import Any

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from tools.odoo_client import odoo_client

logger = logging.getLogger(__name__)

# Initialisation du LLM Groq
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY", ""),
    temperature=0,
)


@tool
def get_projects_tool(limit: int = 10) -> str:
    """Récupère la liste des projets actifs depuis Odoo.

    Args:
        limit: Nombre maximum de projets à retourner (défaut: 10).

    Returns:
        Chaîne JSON listant les projets.
    """
    try:
        projects = odoo_client.get_projects(limit=limit)
        return json.dumps(projects, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("Erreur lors de la récupération des projets : %s", exc)
        return f"Erreur : impossible de récupérer les projets. {exc}"


@tool
def get_project_tasks_tool(project_name: str, limit: int = 20) -> str:
    """Récupère les tâches d'un projet spécifique.

    Args:
        project_name: Nom du projet (recherche partielle acceptée).
        limit: Nombre maximum de tâches à retourner (défaut: 20).

    Returns:
        Chaîne JSON listant les tâches du projet.
    """
    try:
        # Recherche d'abord le projet par nom
        projects = odoo_client.search_read(
            model="project.project",
            domain=[["name", "ilike", project_name]],
            fields=["id", "name"],
            limit=1,
        )
        if not projects:
            return f"Aucun projet trouvé avec le nom '{project_name}'."

        project_id = projects[0]["id"]
        tasks = odoo_client.search_read(
            model="project.task",
            domain=[["project_id", "=", project_id]],
            fields=["name", "user_ids", "stage_id", "date_deadline", "priority"],
            limit=limit,
        )
        return json.dumps(
            {"project": projects[0]["name"], "tasks": tasks},
            ensure_ascii=False,
            default=str,
        )
    except Exception as exc:
        logger.error("Erreur lors de la récupération des tâches : %s", exc)
        return f"Erreur : {exc}"


@tool
def propose_task_tool(
    project_name: str,
    task_name: str,
    description: str = "",
    assignee_name: str = "",
    deadline: str = "",
) -> str:
    """Prépare un brouillon de tâche à soumettre à validation humaine.
    NE crée PAS directement dans Odoo — retourne uniquement le payload brouillon.

    Args:
        project_name: Nom du projet cible.
        task_name: Titre de la tâche à créer.
        description: Description de la tâche (optionnel).
        assignee_name: Nom du responsable (optionnel).
        deadline: Date limite au format YYYY-MM-DD (optionnel).

    Returns:
        Chaîne JSON décrivant le brouillon de tâche.
    """
    draft = {
        "action": "create_task",
        "model": "project.task",
        "values": {
            "project_name": project_name,
            "task_name": task_name,
            "description": description,
            "assignee_name": assignee_name,
            "deadline": deadline,
        },
        "requires_approval": True,
    }
    return json.dumps(draft, ensure_ascii=False)


# Liste blanche des outils autorisés pour l'agent projets
PROJECT_TOOLS = [
    get_projects_tool,
    get_project_tasks_tool,
    propose_task_tool,
]

# Prompt système de l'agent projets
PROJECT_SYSTEM_PROMPT = """Tu es un assistant spécialisé dans la gestion de projets d'une entreprise utilisant Odoo.
Tu as accès aux projets et aux tâches en lecture seule.
Réponds en français, de manière concise et structurée.

Règles importantes :
- Tu ne modifies JAMAIS directement les données Odoo.
- Si l'utilisateur demande à créer une tâche ou modifier un projet, utilise l'outil propose_task_tool
  pour préparer un brouillon, puis indique clairement que cela nécessite une validation humaine.
- Si tu ne trouves pas l'information, dis-le clairement."""

prompt = ChatPromptTemplate.from_messages([
    ("system", PROJECT_SYSTEM_PROMPT),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


def run_project_agent(question: str, user_id: int = 1) -> dict[str, Any]:
    """Exécute l'agent projets pour répondre à une question.

    Args:
        question: Question posée par l'utilisateur.
        user_id: Identifiant de l'utilisateur Odoo.

    Returns:
        Dictionnaire avec les clés 'answer', 'agent', 'status', 'draft_payload'.
    """
    try:
        agent = create_tool_calling_agent(llm, PROJECT_TOOLS, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=PROJECT_TOOLS,
            verbose=False,
            max_iterations=5,
            return_intermediate_steps=True,
        )
        result = executor.invoke({"input": question})
        answer = result.get("output", "Aucune réponse générée.")

        # Détection d'un brouillon dans les étapes intermédiaires
        draft_payload: dict | None = None
        for action, observation in result.get("intermediate_steps", []):
            if hasattr(action, "tool") and action.tool == "propose_task_tool":
                try:
                    draft_payload = json.loads(observation)
                except (json.JSONDecodeError, TypeError):
                    pass

        status = "draft" if draft_payload else "ok"
        return {
            "answer": answer,
            "agent": "projets",
            "status": status,
            "draft_payload": draft_payload,
        }
    except Exception as exc:
        logger.error("Erreur dans l'agent projets : %s", exc)
        return {
            "answer": f"Erreur de l'agent projets : {exc}",
            "agent": "projets",
            "status": "error",
            "draft_payload": None,
        }
