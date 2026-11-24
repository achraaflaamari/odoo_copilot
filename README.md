# OdooCopilot

Assistant IA multi-agents intégré à Odoo 20. Il comprend les données de l'ERP (ventes, achats, projets), répond aux questions en langage naturel et prépare des actions avec **validation humaine obligatoire** avant toute écriture.

---

## Présentation et objectif

OdooCopilot démontre l'intégration d'agents IA (LangGraph + LLM + RAG) dans un ERP Odoo. L'utilisateur pose une question depuis Odoo ; le microservice route la demande vers l'agent compétent, génère une réponse ou un brouillon d'action, et enregistre tout dans le journal `ai.action.log`.

**Principes fondamentaux :**
- Lecture seule par défaut — aucune écriture sans validation humaine
- Chaque décision est journalisée dans `ai.action.log`
- Agents spécialisés par domaine métier
- Pas de secret dans le code — tout passe par `.env`

---

## Architecture

```
Utilisateur Odoo
      │  (panneau de chat OWL — Phase 4)
      ▼
Module odoo_copilot  ──JSON/HTTP──►  Microservice FastAPI (port 8001)
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
CopilotOdoo/
├── addons/
│   └── odoo_copilot/          # Module Odoo
│       ├── __init__.py
│       ├── __manifest__.py
│       ├── models/
│       │   ├── ai_action_log.py   # Journal des actions
│       │   └── ai_config.py       # Configuration du microservice
│       ├── views/
│       │   ├── ai_action_log_views.xml
│       │   ├── ai_config_views.xml
│       │   └── menus.xml
│       ├── security/
│       │   └── ir.model.access.csv
│       └── data/
│           └── ai_config_data.xml
├── ai_service/                # Microservice FastAPI + LangGraph
│   ├── agents/
│   │   ├── router.py          # Graphe LangGraph et routeur
│   │   └── sales_agent.py     # Agent ventes
│   ├── tools/
│   │   └── odoo_client.py     # Client JSON-RPC Odoo
│   ├── rag/                   # Indexation et recherche (Phase 4)
│   ├── main.py                # Point d'entrée FastAPI
│   └── requirements.txt
├── docs/                      # Schémas et documentation détaillée
├── AGENT.md                   # Règles du projet (lire en premier)
├── CHANGELOG.md
├── README.md
├── .gitignore
└── .env.example
```

---

## Stack technique

| Couche | Outils |
|---|---|
| ERP | Odoo 20 (local), Python ORM, XML, OWL/JavaScript |
| Base de données | PostgreSQL |
| Microservice | FastAPI 0.115, Pydantic 2.9, Uvicorn |
| Agents | LangGraph 0.2, LangChain 0.3 |
| LLM | Groq — Llama 3.3 70B Versatile |
| RAG | Sentence-Transformers + Chroma (Phase 4) |
| Accès Odoo | JSON-RPC via `requests` |
| Versioning | Git |

---

## Prérequis

- **Odoo 20** installé localement dans `/home/achraf/odoo20/`
- **Python 3.11+** pour le microservice
- **PostgreSQL** avec la base `odoo`
- Un compte **Groq** avec une clé API (gratuit sur [console.groq.com](https://console.groq.com))

---

## Installation et configuration

### 1. Cloner le dépôt

```bash
git clone <url-du-depot> CopilotOdoo
cd CopilotOdoo
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos valeurs :
#   GROQ_API_KEY=gsk_...
#   ODOO_API_KEY=<clé API de l'utilisateur technique Odoo>
#   SERVICE_API_KEY=<secret partagé entre Odoo et le microservice>
```

### 3. Installer le microservice

```bash
cd ai_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Lancer le microservice

```bash
cd ai_service
source .venv/bin/activate
uvicorn main:app --reload --port 8001
# → http://localhost:8001
# → Documentation Swagger : http://localhost:8001/docs
```

### 5. Installer le module Odoo

Ajouter le chemin `addons/` à la configuration Odoo :

```ini
# ~/odoo20/odoo.conf
addons_path = /home/achraf/Documents/CopilotOdoo/addons,/home/achraf/odoo20/extracted/usr/lib/python3.14/site-packages/odoo/addons
```

Lancer Odoo et mettre à jour :

```bash
# Lancer Odoo
python /home/achraf/odoo20/extracted/usr/bin/odoo -c ~/odoo20/odoo.conf

# Mettre à jour le module (dans un autre terminal)
python /home/achraf/odoo20/extracted/usr/bin/odoo -c ~/odoo20/odoo.conf -u odoo_copilot -d odoo
```

Dans l'interface Odoo : **Applications → Rechercher "Odoo Copilot" → Installer**

### 6. Configurer la connexion dans Odoo

Dans Odoo : **Copilot IA → Configuration → Créer**
- URL du microservice : `http://localhost:8001`
- Clé API : valeur de `SERVICE_API_KEY` dans votre `.env`

---

## Utilisation

### Exemples de questions par agent

**Agent Ventes**
```
"Montre-moi les 5 dernières commandes de vente"
"Quel est le montant total des commandes confirmées ?"
"Liste les commandes du client Dupont"
```

**Agent Général**
```
"Comment fonctionne le module de vente d'Odoo ?"
"Explique-moi ce qu'est un bon de commande"
```

**Agent Achats** *(Phase 3)*
```
"Quels sont les bons de commande en attente ?"
"Quel fournisseur a le plus de commandes ce mois ?"
```

**Agent Projets** *(Phase 3)*
```
"Quels projets sont en retard ?"
"Montre-moi les tâches assignées à Jean"
```

### Appel direct à l'API (pour tests)

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_service_api_key" \
  -d '{"question": "Montre-moi les dernières commandes de vente", "user_id": 1}'
```

Réponse attendue :
```json
{
  "answer": "Voici les 10 dernières commandes de vente : ...",
  "agent": "ventes",
  "status": "ok",
  "draft_payload": null
}
```

---

## Validation humaine et journal

### Circuit de validation (Phase 3+)

```
Question utilisateur
       ↓
Agent IA génère un brouillon (status: "draft")
       ↓
Enregistrement dans ai.action.log
       ↓
Utilisateur : Approuver ──► Exécution (status: "executed")
           ou Rejeter  ──► Annulation (status: "rejected")
```

### Consulter le journal

Dans Odoo : **Copilot IA → Journal des actions**

Chaque entrée affiche :
- La question posée
- L'agent ayant répondu
- Le statut (brouillon / approuvé / rejeté / exécuté)
- La réponse complète et le payload JSON (si action d'écriture)

---

## Sécurité

| Mesure | Description |
|---|---|
| Authentification microservice | Clé API dans le header `X-API-Key` |
| Utilisateur technique Odoo | Droits limités, accès lecture seule |
| Lecture seule par défaut | Aucun outil d'écriture directe dans les agents |
| Validation humaine | Toute écriture passe par un brouillon approuvé |
| Liste blanche des outils | Chaque agent ne peut appeler que ses outils déclarés |
| Pas de secrets dans Git | `.env` ignoré, `.env.example` fourni |
| Filtrage des injections | Les données Odoo sont traitées comme données, jamais comme instructions (Phase 4) |

---

## Scénarios de vérification manuelle

### Scénario 1 : Vérifier que le microservice démarre

```bash
cd ai_service && source .venv/bin/activate
uvicorn main:app --port 8001
curl http://localhost:8001/health
# Attendu : {"status": "ok", "version": "1.0.0"}
```

### Scénario 2 : Tester le routage vers l'agent ventes

```bash
curl -X POST http://localhost:8001/chat \
  -H "X-API-Key: votre_cle" \
  -H "Content-Type: application/json" \
  -d '{"question": "Montre-moi les commandes de vente", "user_id": 1}'
# Attendu : agent == "ventes"
```

### Scénario 3 : Tester le routage général

```bash
curl -X POST http://localhost:8001/chat \
  -H "X-API-Key: votre_cle" \
  -H "Content-Type: application/json" \
  -d '{"question": "Bonjour, comment vas-tu ?", "user_id": 1}'
# Attendu : agent == "routeur", status == "ok"
```

### Scénario 4 : Tester l'authentification

```bash
curl -X POST http://localhost:8001/chat \
  -H "X-API-Key: mauvaise_cle" \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
# Attendu : HTTP 403
```

### Scénario 5 : Vérifier le module Odoo

1. Ouvrir Odoo → Applications → Rechercher "Copilot" → Installer
2. Vérifier que le menu **Copilot IA** apparaît dans la barre de navigation
3. Ouvrir **Copilot IA → Configuration** → Vérifier la config par défaut

### Scénario 6 : Vérifier le client JSON-RPC

```python
# Dans un shell Python avec le venv activé
import sys; sys.path.insert(0, "ai_service")
from tools.odoo_client import odoo_client
orders = odoo_client.get_sales_orders(limit=5)
print(orders)
```

---

## Limites connues

| Limite | Description |
|---|---|
| Agents Achats et Projets | Non implémentés — Phase 3 |
| Interface OWL | Pas encore de panneau de chat — Phase 4 |
| RAG | Pas encore d'indexation documentaire — Phase 4 |
| Brouillon d'écriture | Non implémenté — Phase 3 |
| Endpoints approuver/rejeter | Non implémentés — Phase 3 |
| Streaming | Non implémenté — Phase 4 |
| Filtrage injections de prompt | Non implémenté — Phase 4 |

---

## Perspectives

- **Phase 3** : Agents Achats et Projets, brouillons d'écriture, circuit d'approbation, journalisation complète
- **Phase 4** : Interface OWL, streaming, RAG sur la documentation Odoo, filtrage des injections
- **Phase 5** : Documentation complète, schémas d'architecture, guide d'installation, scénarios de vérification finaux
