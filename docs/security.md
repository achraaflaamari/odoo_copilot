# Sécurité

## Contrôles en place

| Couche | Contrôle |
|---|---|
| Réseau | Le navigateur passe par le contrôleur Odoo ; ne publiez pas directement le microservice |
| API | `X-API-Key` protège les routes de service ; `/health` est public |
| Session Odoo | Les routes du contrôleur utilisent `auth="user"` et la protection CSRF |
| Accès Odoo | L'API JSON-2 utilise une clé d'utilisateur technique à privilèges limités |
| Agents | Chaque agent reçoit uniquement les outils déclarés pour son domaine |
| Écritures | Les demandes d'achat nécessitent une approbation humaine explicite et restent en brouillon |
| Entrées | Filtrage anti-injection, troncature et suppression du HTML |
| Secrets | `.env` est ignoré par Git ; `.env.example` ne contient pas de secret |
| Audit | Les brouillons, approbations et rejets sont consignés dans `ai.action.log` |

Les données récupérées d'Odoo restent des données et ne doivent pas être
interprétées comme des instructions. Les filtres ne remplacent pas une revue
humaine ni les contrôles d'accès d'Odoo.

## Configuration de production

- Définir une valeur forte pour `SERVICE_API_KEY` et protéger la clé API Odoo.
- Limiter les droits de l'utilisateur technique au strict nécessaire.
- Restreindre les origines CORS et placer le service derrière un reverse proxy.
- Ne pas exposer les clés dans le navigateur, les journaux ou les captures.
- Vérifier les paramètres de devise et les droits avant d'approuver une action.

Voir aussi la [vue d'architecture](architecture.md) et le [guide d'installation](setup.md).
