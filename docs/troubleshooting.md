# Dépannage et limites

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Téléchargement de Triton en boucle | PyTorch CUDA sélectionné par `sentence-transformers` | Utiliser l'installation légère ; installer PyTorch CPU avant Sentence-Transformers |
| RAG indisponible | Dépendances RAG absentes | Installer `requirements-rag.txt`, puis redémarrer le service |
| `/rag/search` renvoie `[]` | Collection vide ou backend changé | Lancer `python rag/index_docs.py` ; réindexer après un changement de backend |
| HTTP 403 sur `/chat` | Clé absente ou incorrecte | Vérifier `SERVICE_API_KEY` et la configuration Odoo |
| Clé Groq invalide | `GROQ_API_KEY` absente ou expirée | Vérifier la clé configurée dans `.env` |
| Devise refusée à l'approbation | Devise désactivée ou inaccessible à l'utilisateur technique | Activer la devise et vérifier les droits, puis réessayer |
| Microservice non configuré dans Odoo | Aucune `ai.config` active | Créer ou activer une configuration dans **Copilot IA → Configuration** |
| Timeout du chat | Service arrêté ou URL incorrecte | Vérifier Uvicorn sur le port 8001 et l'URL dans Odoo |
| Module absent des applications | `addons_path` incorrect ou liste non actualisée | Corriger `odoo.conf`, redémarrer et mettre à jour la liste |
| `No module named 'odoo'` | Mauvais interpréteur Python pour lancer Odoo | Utiliser le Python de l'environnement Odoo (voir [Installation](setup.md)) |
| Erreur JSON-2 Odoo | Base, clé ou droits incorrects | Vérifier `ODOO_DB`, la clé Bearer et les groupes de l'utilisateur technique |
| Brouillons perdus après redémarrage | Stockage temporaire en mémoire | Comportement connu ; voir les limites ci-dessous |

## Limites connues

- Les brouillons sont stockés en mémoire et disparaissent au redémarrage.
- Les tâches de projet approuvées sont journalisées mais ne sont pas créées dans Odoo.
- L'agent Ventes est en lecture seule.
- Le streaming est simulé mot par mot, pas token par token.
- `session_id` n'active pas encore de mémoire conversationnelle.
- Le backend ONNX par défaut est moins adapté au français que
  Sentence-Transformers ; ce dernier demande une installation CPU plus lourde.
- Le service fonctionne sans RAG ; les dépendances correspondantes sont optionnelles.
- CORS est permissif pour le développement local et doit être restreint en production.
- La vérification repose actuellement sur des scénarios manuels.
- Une seule configuration `ai.config` active est utilisée à la fois.

## Pistes d'évolution

- Persister les brouillons et permettre leur reprise après redémarrage.
- Exécuter les tâches de projet approuvées.
- Ajouter un streaming natif et une mémoire conversationnelle.
- Respecter plus finement les droits de l'utilisateur connecté dans les outils.
- Renforcer le déploiement de production (CORS, limitation de débit, gestionnaire de secrets).
- Évaluer pgvector pour centraliser le stockage dans PostgreSQL.
