# CHANGELOG : OdooCopilot

Mis à jour à chaque tâche terminée. Entrée la plus récente en haut.

**Dernière phase : Phase 5 : Finalisation (terminée)**

---

## Correctif Phase 4 : installation RAG allégée
**Statut** : terminé — 2026-11-25

### Tâches réalisées
- [x] Cause identifiée : `sentence-transformers` tirait PyTorch CUDA → `triton` (~285 Mo) + paquets `nvidia-*` (~2 Go), dont le téléchargement échouait en boucle pendant l'installation des phases 3-4
- [x] `requirements.txt` allégé : uniquement les dépendances cœur (plus de PyTorch / CUDA / triton)
- [x] Nouveau `requirements-rag.txt` : RAG optionnel via ChromaDB + embeddings ONNX (sans GPU)
- [x] `rag/retriever.py` : backend d'embeddings configurable (`RAG_EMBEDDING_BACKEND`, défaut `chroma-onnx`), repli automatique sur ONNX si Sentence-Transformers est absent
- [x] Indexation groupée des documents (un seul calcul d'embeddings par lot, repli document par document en cas d'erreur)
- [x] Endpoint `/health` : expose `rag_backend`
- [x] Messages d'erreur et script `rag/index_docs.py` mis à jour
- [x] `.env.example` : ajout de `RAG_EMBEDDING_BACKEND`

### Documentation
- [x] README : installation en deux étapes (cœur + RAG optionnel), procédure PyTorch CPU si Sentence-Transformers est vraiment nécessaire, stack et limites mises à jour
- [x] AGENT.md : stack RAG, commandes d'installation et variables d'environnement mises à jour
- [x] CHANGELOG mis à jour

---

## Phase 5 : Finalisation
**Statut** : terminée — 2026-11-25

### Tâches réalisées
- [x] README réécrit et complété : sommaire, présentation, architecture, stack, structure, prérequis, installation pas à pas, utilisation, référence API, validation/journal, sécurité, 13 scénarios, dépannage, limites, perspectives
- [x] Guide d'installation complet : utilisateur technique Odoo et clé API, installation/mise à jour du module (`-i` / `-u`), configuration `ai.config`
- [x] Scénarios de vérification renumérotés et complétés (rejet, `/drafts`, RAG, SSE, JSON-RPC)
- [x] Nouveau `docs/architecture.md` : diagrammes Mermaid (vue d'ensemble, graphe LangGraph, séquences chat et validation, flux RAG), modèle de données, défense en profondeur, variables d'environnement
- [x] Section Dépannage (triton/CUDA, 403, RAG, module absent, JSON-RPC, brouillons perdus)
- [x] `rag/retriever.py` : chargement de `.env` en exécution standalone (`index_docs.py`)
- [x] Migration des agents vers l'API LangChain 1.x (`create_agent`) : `AgentExecutor` n'existe plus dans LangChain 1.x installé ; détection des brouillons via les `ToolMessage`
- [x] `requirements.txt` borné : `langchain>=1.0,<2.0`, `langchain-groq>=1.0,<2.0`, `langgraph>=1.0,<2.0`
- [x] Droits `ai.action.log` durcis : les utilisateurs internes lisent et créent le journal, mais ne peuvent plus le modifier (audit intègre)
- [x] `.gitignore` : `**/rag/chroma_db/` — la base Chroma locale n'est plus proposée à Git
- [x] Correction du doublon « Scénario 6 » et du comptage des motifs d'injection (15)
- [x] CHANGELOG finalisé

### Vérifications
- [x] Compilation Python du microservice (`main.py`, `agents/*.py`, `rag/*.py`)
- [x] Démarrage FastAPI et endpoint `/health` via `TestClient`
- [x] Compilation Python et validation XML du module Odoo
- [x] Test RAG de bout en bout : backend ONNX, indexation et recherche de 2 documents (ChromaDB 1.5.9 / onnxruntime 1.32)

### Documentation
- [x] README, `docs/architecture.md`, AGENT.md (structure `docs/`) et CHANGELOG à jour

---

## Phase 4 : Interface et sécurité
**Statut** : terminée — 2026-11-24

### Tâches réalisées
- [x] Panneau de chat OWL (`addons/odoo_copilot/static/src/copilot_chat_panel.js/.xml/.css`) :
  - Composant OWL avec boucle de messages, bulles utilisateur/agent, badges d'agent colorés
  - Boutons Approuver / Rejeter sur les messages de type brouillon (status == "draft")
  - Champ de saisie avec envoi via Entrée, animation de chargement
- [x] Contrôleur HTTP Odoo (`controllers/copilot_controller.py`) :
  - Routes `/copilot/chat`, `/copilot/approve`, `/copilot/reject` (type JSON, auth utilisateur)
  - Proxy sécurisé vers le microservice FastAPI avec la clé API de la config active
- [x] Action client OWL enregistrée dans `views/copilot_chat_views.xml`
- [x] Menu "Chat IA" ajouté dans les menus Copilot IA
- [x] Filtrage anti-injection de prompt (`ai_service/tools/prompt_filter.py`) :
  - 15 patterns regex (FR + EN) couvrant les injections courantes
  - Troncature à 2000 caractères, suppression des balises HTML
  - Réponse "bloqué" + journalisation dans `ai.action.log`
- [x] RAG — Retrieval-Augmented Generation (`ai_service/rag/retriever.py`) :
  - ChromaDB (base vectorielle persistante) + SentenceTransformers (modèle multilingue)
  - Mode dégradé gracieux si packages absents
  - Méthodes : `index_documents()`, `index_text_file()`, `search()`, `search_as_context()`
- [x] Script d'indexation initiale (`ai_service/rag/index_docs.py`) avec 4 documents de démo
- [x] Endpoints RAG sur le microservice : `POST /rag/index`, `POST /rag/search`
- [x] Streaming SSE (`GET /stream`) : réponse mot par mot via Server-Sent Events
- [x] Contexte RAG injecté automatiquement dans les questions envoyées au LLM
- [x] Version microservice passée à `3.0.0`
- [x] `__manifest__.py` mis à jour : version `20.0.2.0.0`, assets OWL, dépendance `web`
- [x] `requirements.txt` mis à jour : `chromadb>=0.5.0`, `sentence-transformers>=3.0.0`

### Documentation
- [x] README mis à jour : nouvelle structure du dépôt, stack technique, 11 scénarios de vérification, limites mises à jour
- [x] CHANGELOG mis à jour

---

## Phase 3 : Agents spécialisés
**Statut** : terminée — 2026-11-24

### Tâches réalisées
- [x] Agent Achats (`ai_service/agents/purchase_agent.py`) :
  - Outils : `get_purchase_orders_tool`, `get_purchase_order_detail_tool`, `propose_purchase_order_tool`
  - Lecture seule par défaut ; création via brouillon uniquement
- [x] Agent Projets (`ai_service/agents/project_agent.py`) :
  - Outils : `get_projects_tool`, `get_project_tasks_tool`, `propose_task_tool`
  - Lecture seule par défaut ; création de tâches via brouillon uniquement
- [x] Mécanisme de brouillon dans `main.py` :
  - Stockage en mémoire des brouillons avec UUID unique (`draft_id`)
  - Détection automatique des brouillons dans les étapes intermédiaires LangGraph
- [x] Endpoint `POST /approve/{draft_id}` : approbation et journalisation dans `ai.action.log`
- [x] Endpoint `POST /reject/{draft_id}` : rejet et journalisation dans `ai.action.log`
- [x] Endpoint `GET /drafts` : liste des brouillons en attente
- [x] Journalisation dans Odoo `ai.action.log` à chaque étape (brouillon, approbation, rejet)
- [x] Routeur LangGraph mis à jour : routage vers `purchase_agent` et `project_agent`
- [x] Version microservice passée à `2.0.0`

### Documentation
- [x] README mis à jour : structure du dépôt, exemples de questions agents Achats/Projets, circuit de validation complet, 8 scénarios de vérification, limites mises à jour
- [x] CHANGELOG mis à jour

---

## Phase 2 : Socle IA
**Statut** : terminée — 2026-11-24

### Tâches réalisées
- [x] Microservice FastAPI (`ai_service/main.py`) avec endpoint `/chat` et `/health`
- [x] Authentification par clé API via header `X-API-Key` (dépendance FastAPI)
- [x] Middleware CORS configuré
- [x] Schémas Pydantic `ChatRequest` / `ChatResponse`
- [x] Graphe LangGraph (`ai_service/agents/router.py`) avec nœuds `classify`, `sales_agent`, `general`
- [x] Routage conditionnel basé sur la classification Groq (Llama 3.3 70B)
- [x] Agent Ventes (`ai_service/agents/sales_agent.py`) avec outil `get_sales_orders`
- [x] Fonction `run_graph(question, user_id)` exposée pour `main.py`
- [x] Fichiers `requirements.txt` avec toutes les dépendances

### Documentation
- [x] README mis à jour : section utilisation, exemples de questions, scénarios de vérification

---

## Phase 1 : Fondations
**Statut** : terminée — 2026-11-24

### Tâches réalisées
- [x] Structure du dépôt Git créée (`addons/`, `ai_service/`, `docs/`, etc.)
- [x] Fichier `.gitignore` (exclut `.env`, `*.pyc`, `__pycache__/`, `.venv/`, `*.log`, `rag/chroma_db/`)
- [x] Fichier `.env.example` avec toutes les variables requises
- [x] Module Odoo `odoo_copilot` créé :
  - `__manifest__.py` (version 20.0.1.0.0, dépend de `base` et `mail`)
  - Modèle `ai.action.log` : journal des actions IA avec validation humaine
  - Modèle `ai.config` : configuration du microservice FastAPI
  - Vues liste et formulaire pour les deux modèles
  - Menu principal "Copilot IA" avec sous-menus
  - Droits d'accès `ir.model.access.csv`
  - Données par défaut `ai_config_data.xml` (URL: http://localhost:8001)
- [x] Client JSON-RPC `ai_service/tools/odoo_client.py` :
  - `authenticate()`, `search_read()`, `create()`, `write()`
  - `get_sales_orders()`, `get_purchase_orders()`, `get_projects()`
  - Authentification par clé API Odoo (header `X-Odoo-Api-Key`)

### Documentation
- [x] README initial créé : présentation, architecture, stack, installation, utilisation, sécurité, scénarios de vérification, limites
