# CHANGELOG : OdooCopilot

Mis à jour à chaque tâche terminée. Entrée la plus récente en haut.

**Dernière phase : Phase 2 : Socle IA (terminée)**

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
**Statut** : à faire

### Tâches réalisées
- [ ] Panneau de chat OWL
- [ ] Réponses en streaming
- [ ] Boutons Approuver / Rejeter
- [ ] Lecture seule par défaut et liste blanche des outils
- [ ] Filtrage contre l'injection de prompt
- [ ] RAG (indexation et outil de recherche)

### Documentation
-

---

## Phase 3 : Agents spécialisés
**Statut** : à faire

### Tâches réalisées
- [ ] Agent Achats
- [ ] Agent Projets
- [ ] Mécanisme de brouillon
- [ ] Endpoints approuver / rejeter
- [ ] Journalisation dans `ai.action.log`

### Documentation
-

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
