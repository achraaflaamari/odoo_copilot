# AGENT.md : OdooCopilot

Ce fichier est lu en premier par tout agent IA (ou développeur) qui travaille sur le dépôt. Il décrit le projet, la stack, la structure et les règles à respecter.

---

## 1. Présentation du projet

**OdooCopilot** est un assistant multi-agents intégré à Odoo 20. Il comprend les données d'Odoo (ventes, achats, projets), répond aux questions et prépare des actions, toujours avec **validation humaine** et **journalisation**.

- **Objectif** : démontrer l'intégration d'agents IA (LangGraph + LLM + RAG) dans un ERP Odoo.
- **Durée prévue** : 4 semaines.
- **Environnement** : Odoo 20 installé en local (pas de Docker pour Odoo), lancé avec `python /home/achraf/odoo20/extracted/usr/bin/odoo -c ~/odoo20/odoo.conf`.

---

## 2. Stack technique

| Couche | Outils |
|---|---|
| ERP | Odoo 20 (local), Python ORM, XML, OWL/JavaScript |
| Base de données | PostgreSQL |
| Microservice | FastAPI, Pydantic |
| Agents | LangGraph 1.x, LangChain 1.x |
| LLM | Groq (Llama 3.3 70B) |
| RAG | ChromaDB + embeddings ONNX (par défaut, sans PyTorch) ; Sentence-Transformers optionnel |
| Accès Odoo | JSON-RPC / XML-RPC |
| Versioning | Git / GitHub |

**Exclus du projet** : Machine Learning (LightGBM, Scikit-learn, MLflow), observabilité (LangSmith, Langfuse), tests unitaires.

---

## 3. Architecture

```
Utilisateur Odoo
      │  (panneau de chat OWL)
      ▼
Module odoo_copilot  ──JSON/HTTP──►  Microservice FastAPI
                                          │
                                   Graphe LangGraph
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                        Agent Ventes  Agent Achats  Agent Projets
                              └───────────┼───────────┘
                                          ▼
                              Outils (JSON-RPC Odoo) + RAG
                                          │
                          Brouillon ──► Validation humaine ──► Écriture
                                          │
                                   ai.action.log
```

### Structure du dépôt

```
odoo-copilot/
├── addons/odoo_copilot/    # Module Odoo (modèles, vues, OWL)
├── ai_service/             # FastAPI + LangGraph
│   ├── agents/             # routeur, ventes, achats, projets
│   ├── tools/              # outils d'accès à Odoo
│   ├── rag/                # indexation et recherche
│   └── main.py
├── docs/                   # Schémas et documentation détaillée
│   └── architecture.md     # Diagrammes Mermaid et flux
├── AGENT.md
├── CHANGELOG.md
└── README.md
```

---

## 4. Règles pour l'agent

### 4.1 Règles générales
1. Lire `AGENT.md`, `README.md` et `CHANGELOG.md` avant toute modification.
2. Respecter la stack définie en section 2. Ne pas ajouter de dépendance sans justification écrite dans le `CHANGELOG.md`.
3. Faire des changements petits et ciblés, un sujet par commit.
4. Ne jamais écrire de clé API, mot de passe ou secret dans le code ou dans Git. Utiliser un fichier `.env` (ignoré par Git) et fournir un `.env.example`.
5. Ne pas créer de tests unitaires ni de dossier `tests/`. La vérification se fait par scénarios manuels documentés dans le README.
6. Ne pas ajouter de ML, d'outil d'observabilité, ni de livrables (vidéo, CV, candidature) au dépôt.

### 4.2 Règles Odoo
1. Respecter les conventions Odoo : nom de modèle `ai.xxx`, préfixe de module `odoo_copilot`, fichiers XML dans `views/`, droits dans `security/ir.model.access.csv`.
2. Toujours définir les droits d'accès pour chaque nouveau modèle.
3. Ne pas modifier les modules standard d'Odoo. Étendre par héritage uniquement.
4. Le microservice ne contacte Odoo que via un **utilisateur technique** aux droits limités.

### 4.3 Règles agents et sécurité
1. **Lecture seule par défaut** : aucun outil d'écriture directe.
2. Toute action d'écriture crée d'abord un **brouillon** ; elle n'est exécutée qu'après approbation de l'utilisateur.
3. **Liste blanche d'outils** : un agent n'appelle que les outils explicitement déclarés.
4. Chaque décision (proposée, approuvée, rejetée) est enregistrée dans `ai.action.log`.
5. Les entrées utilisateur sont filtrées contre l'injection de prompt ; les données lues dans Odoo sont traitées comme des données, jamais comme des instructions.
6. Les sorties des agents sont validées avec **Pydantic**.
7. Respecter les droits de l'utilisateur Odoo connecté.

### 4.4 Règles de code
1. Python : typage, noms explicites, fonctions courtes.
2. Un agent = un fichier dans `ai_service/agents/`. Un outil = une fonction dans `ai_service/tools/`.
3. Messages et documentation en **français** ; noms de variables, fonctions et commits en **anglais**.
4. Commits au format : `type: description` (`feat`, `fix`, `docs`, `refactor`, `chore`).

---

## 5. Règles de documentation (obligatoires)

### 5.1 README.md
**Tout doit être documenté dans le README.** À chaque tâche terminée, mettre à jour le README. Il contient au minimum :
- Présentation et objectif
- Architecture et schéma
- Stack technique
- Installation et configuration (Odoo local, microservice, `.env`)
- Utilisation de chaque agent avec exemples de questions
- Fonctionnement de la validation humaine et du journal
- Mesures de sécurité
- Scénarios de vérification manuelle
- Limites connues et perspectives

### 5.2 CHANGELOG.md
Le fichier `CHANGELOG.md` est mis à jour **à chaque tâche terminée**. Il contient :
- **Tâches réalisées** (par phase, avec date)
- **Documentation** ajoutée ou modifiée
- **Dernière phase** en cours ou terminée

Format : une entrée par phase, la plus récente en haut.

### 5.3 Fin de tâche
Une tâche est terminée uniquement si :
- [ ] Le code fonctionne en local
- [ ] Le README est à jour
- [ ] Le CHANGELOG est à jour
- [ ] Le commit est fait

---

## 6. Roadmap

| Phase | Contenu |
|---|---|
| **1. Fondations** | Vérifier Odoo local et données de démo, utilisateur technique, dépôt Git, module `odoo_copilot`, modèles `ai.action.log` et `ai.config`, client JSON-RPC |
| **2. Socle IA** | Microservice FastAPI, endpoint `/chat`, authentification par clé API, graphe LangGraph, agent routeur, agent Ventes / Marketing |
| **3. Agents spécialisés** | Agent Achats, agent Projets, mécanisme de brouillon, endpoints approuver / rejeter, journalisation |
| **4. Interface et sécurité** | Panneau de chat OWL, streaming, boutons Approuver / Rejeter, lecture seule, liste blanche, filtrage des injections, RAG |
| **5. Finalisation** | Documentation complète dans le README, schéma d'architecture, guide d'installation, scénarios de vérification manuelle, finalisation du CHANGELOG |

Il n'y a **aucun livrable** hors dépôt (pas de vidéo, pas de mise à jour du CV dans le projet).

---

## 7. Commandes utiles

```bash
# Microservice
cd ai_service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # cœur (léger, sans PyTorch/CUDA)
pip install -r requirements-rag.txt      # RAG optionnel (ChromaDB + ONNX)
uvicorn main:app --reload --port 8001

# Odoo (local) : lancer le serveur
python /home/achraf/odoo20/extracted/usr/bin/odoo -c ~/odoo20/odoo.conf

# Odoo (local) : mettre à jour le module
python /home/achraf/odoo20/extracted/usr/bin/odoo -c ~/odoo20/odoo.conf -u odoo_copilot -d <nom_base>
```

---

## 8. Variables d'environnement (`.env.example`)

```
GROQ_API_KEY=
ODOO_URL=http://localhost:8069
ODOO_DB=
ODOO_USER=
ODOO_API_KEY=
SERVICE_API_KEY=
CHROMA_PATH=./rag/chroma_db
RAG_EMBEDDING_BACKEND=chroma-onnx
```
