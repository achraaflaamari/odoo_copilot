# CHANGELOG : OdooCopilot

Mis à jour à chaque tâche terminée. Entrée la plus récente en haut.

**Dernière phase : Phase 4 : Interface et sécurité (terminée)**

---

## Phase 5 : Finalisation
**Statut** : à faire

### Tâches réalisées
- [ ] Documentation complète dans le README
- [ ] Schéma d'architecture
- [ ] Guide d'installation
- [ ] Scénarios de vérification manuelle
- [ ] Finalisation du CHANGELOG

### Documentation
-

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
  - 14 patterns regex (FR + EN) couvrant les injections courantes
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
