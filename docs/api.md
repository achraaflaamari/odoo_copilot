# API du microservice

Le microservice écoute par défaut sur `http://localhost:8001`. Toutes les routes
sauf `/health` exigent `X-API-Key`. Pour `/stream`, la clé peut aussi être passée
dans le paramètre `api_key`. Laisser `SERVICE_API_KEY` vide désactive
l'authentification : développement local uniquement.

## Routes

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/health` | État du service et disponibilité du RAG |
| `POST` | `/chat` | Réponse à une question, brouillon éventuel |
| `GET` | `/stream` | Réponse Server-Sent Events (SSE) |
| `POST` | `/approve/{draft_id}` | Approuve un brouillon ; une demande d'achat peut être créée comme RFQ |
| `POST` | `/reject/{draft_id}` | Rejette un brouillon |
| `GET` | `/drafts` | Brouillons en attente |
| `POST` | `/rag/index` | Indexe des documents |
| `POST` | `/rag/search` | Recherche documentaire |

## Conversation

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_service_api_key" \
  -d '{"question": "Montre-moi les dernières commandes de vente", "user_id": 1}'
```

Exemple de réponse :

```json
{
  "answer": "Voici les dernières commandes de vente...",
  "agent": "ventes",
  "status": "ok",
  "draft_id": null,
  "draft_payload": null
}
```

| Statut | Signification |
|---|---|
| `ok` | Réponse en lecture seule |
| `draft` | Action proposée ; `draft_id` fourni |
| `blocked` | Entrée bloquée par le filtre |
| `error` | Erreur technique ou LLM |

## Approuver ou rejeter un brouillon

Un brouillon d'achat approuvé est validé puis créé dans Odoo comme demande de
prix en brouillon. La confirmation auprès du fournisseur reste manuelle. Les
brouillons de tâches de projet ne sont pas encore exécutés.

```bash
curl -X POST http://localhost:8001/approve/<draft_id> \
  -H "X-API-Key: votre_service_api_key"

curl -X POST http://localhost:8001/reject/<draft_id> \
  -H "X-API-Key: votre_service_api_key"

curl http://localhost:8001/drafts \
  -H "X-API-Key: votre_service_api_key"
```

L'exécution d'achat vérifie les fournisseurs, produits, quantité, prix et
devise. Une validation échouée renvoie une erreur au client ; le brouillon
reste réessayable après correction de la configuration Odoo.

## RAG

```bash
curl -X POST http://localhost:8001/rag/index \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_service_api_key" \
  -d '{"documents":[{"id":"doc1","text":"Un devis confirmé devient une commande.","metadata":{"source":"manuel"}}]}'

curl -X POST http://localhost:8001/rag/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: votre_service_api_key" \
  -d '{"query":"commande de vente","n_results":2}'
```

Pour les scénarios de bout en bout, consultez le [guide de tests](testing.md).
