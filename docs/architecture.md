# Architecture OdooCopilot

Vue d'ensemble des composants, du routage des agents et du circuit
d'approbation. Pour installer et configurer le projet, consultez
[docs/setup.md](setup.md).

## Vue d'ensemble

```mermaid
flowchart LR
    U["Utilisateur Odoo"] -->|"Chat OWL"| ODOO["Module odoo_copilot<br/>contrôleur"]
    ODOO -->|"HTTP + X-API-Key"| API["Microservice FastAPI"]
    API --> GRAPH["Graphe LangGraph"]
    GRAPH --> ROUTER["Routeur LLM"]
    ROUTER --> SALES["Agent Ventes"]
    ROUTER --> PURCHASE["Agent Achats"]
    ROUTER --> PROJECT["Agent Projets"]
    ROUTER --> GENERAL["Réponse générale"]
    SALES --> TOOLS["Outils autorisés"]
    PURCHASE --> TOOLS
    PROJECT --> TOOLS
    TOOLS -->|"JSON-2 + clé Bearer"| ODOO_DB[("Odoo")]
    API --> RAG["RAG optionnel<br/>ChromaDB"]
    API -->|"Journalisation"| LOG[("ai.action.log")]
    LOG --> ODOO_DB
```

Le navigateur n'appelle pas directement le microservice. Le contrôleur Odoo
relaye les requêtes à l'aide de la clé stockée dans `ai.config`. Le microservice
interroge Odoo avec l'API JSON-2 et la clé Bearer de l'utilisateur technique.

## Composants

| Composant | Emplacement | Responsabilité |
|---|---|---|
| Panneau de chat OWL | `addons/odoo_copilot/static/src/` | Saisie, affichage, approbation et rejet |
| Contrôleur Odoo | `addons/odoo_copilot/controllers/copilot_controller.py` | Proxy authentifié vers le service |
| Configuration | `addons/odoo_copilot/models/ai_config.py` | URL et clé du service |
| Journal | `addons/odoo_copilot/models/ai_action_log.py` | Traçabilité des actions et réponses |
| API | `ai_service/main.py` | Routes FastAPI, brouillons et exécution après approbation |
| Graphe | `ai_service/agents/router.py` | Classification et routage |
| Agents | `ai_service/agents/` | Instructions, outils et brouillons métier |
| Client Odoo | `ai_service/tools/odoo_client.py` | Appels JSON-2 `search_read`, `create` et `write` |
| Filtre | `ai_service/tools/prompt_filter.py` | Filtrage d'entrées |
| RAG | `ai_service/rag/` | Indexation et recherche documentaire |

## Routage

```mermaid
stateDiagram-v2
    [*] --> classify
    classify --> sales_agent : ventes
    classify --> purchase_agent : achats
    classify --> project_agent : projets
    classify --> general : general ou erreur
    sales_agent --> [*]
    purchase_agent --> [*]
    project_agent --> [*]
    general --> [*]
```

Les agents métier n'obtiennent qu'une liste blanche d'outils liée à leur
domaine. Ventes et Projets lisent les données ; Achats peut également proposer
un bon d'achat. Une proposition n'effectue aucune écriture tant qu'elle n'a pas
été approuvée.

## Cycle d'une demande d'achat

```mermaid
sequenceDiagram
    autonumber
    participant U as Utilisateur
    participant O as Odoo (OWL + contrôleur)
    participant F as FastAPI
    participant M as Mémoire des brouillons
    participant D as Odoo JSON-2
    participant J as ai.action.log

    U->>O: Demande de création
    O->>F: POST /chat
    F->>M: Enregistre le brouillon
    F->>J: Journalise status=draft
    F-->>O: draft_id + détails du brouillon
    O-->>U: Boutons Approuver / Rejeter
    U->>O: Approuve
    O->>F: POST /approve/{draft_id}
    F->>F: Valide fournisseur, produit, quantité, prix et devise
    F->>D: Crée la demande de prix et ses lignes
    D-->>F: Identifiant de la RFQ
    F->>J: Journalise l'exécution
    F-->>O: Résultat de l'approbation
```

La RFQ créée reste en brouillon : la confirmation auprès du fournisseur est une
action Odoo distincte. Un échec de validation ou d'exécution est renvoyé au
client et laisse le brouillon réessayable après correction. La création utilise
l'identifiant du brouillon comme référence d'origine pour éviter une création
en double lors d'une nouvelle tentative.

Les brouillons de tâches projet sont approuvés et journalisés, mais leur
exécution métier n'est pas encore implémentée. Les brouillons sont conservés en
mémoire et disparaissent au redémarrage du service.

## RAG

```mermaid
flowchart LR
    DOCS["Documents et fichiers Markdown"] --> INDEX["rag/index_docs.py"]
    INDEX --> EMB["Embeddings"]
    EMB --> CHROMA[("ChromaDB")]
    Q["Question"] --> SEARCH["Recherche"]
    SEARCH --> CHROMA
    CHROMA --> CTX["Contexte documentaire"]
    CTX --> GRAPH["Graphe LangGraph"]
```

Le RAG est facultatif. `chroma-onnx` est le backend léger par défaut ;
`sentence-transformers` est une option CPU, plus lourde et généralement
meilleure pour le français. Les vecteurs ne sont pas interchangeables entre
backends : réindexez après un changement.

## Journal et configuration Odoo

`ai.config` stocke l'URL du microservice et la clé partagée ; une configuration
active est utilisée. `ai.action.log` conserve notamment la question, l'agent,
le statut, le payload proposé, la réponse, l'utilisateur et la date. Les
utilisateurs internes peuvent lire et créer les journaux ; l'administration
peut les modifier ou les supprimer.

Pour les détails des contrôles d'accès, consultez [docs/security.md](security.md).
