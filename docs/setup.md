# Installation et configuration

Guide d'installation locale d'OdooCopilot. Pour une présentation du projet,
consultez le [README](../README.md).

## Prérequis

- Odoo 20 et PostgreSQL
- Python 3.11+ pour le microservice
- Une clé API Groq ([console.groq.com](https://console.groq.com))
- Les modules Odoo Ventes, Achats et Projets installés pour les données de démo

## 1. Cloner le dépôt et configurer l'environnement

```bash
git clone <url-du-depot> CopilotOdoo
cd CopilotOdoo
cp .env.example .env
```

Renseignez les valeurs dans `.env` :

```ini
GROQ_API_KEY=gsk_...
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_API_KEY=<clé API de l'utilisateur technique Odoo>
SERVICE_API_KEY=<secret partagé entre Odoo et le microservice>
CHROMA_PATH=./rag/chroma_db
RAG_EMBEDDING_BACKEND=chroma-onnx
```

`.env` est ignoré par Git. Ne commitez jamais de clé réelle.

## 2. Installer le microservice

```bash
cd ai_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Cette installation n'inclut ni PyTorch, ni CUDA, ni Triton. Le RAG est
optionnel :

```bash
pip install -r requirements-rag.txt
```

ChromaDB et `onnxruntime` seront installés ; le modèle ONNX est téléchargé au
premier usage (~80 Mo).

> N'installez pas `sentence-transformers` directement dans un environnement
> propre : pip peut sélectionner PyTorch CUDA et télécharger Triton ainsi que
> plusieurs paquets NVIDIA. Pour utiliser les embeddings multilingues, installez
> d'abord PyTorch CPU :
>
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install 'sentence-transformers>=3.0.0'
> ```
>
> Puis définissez `RAG_EMBEDDING_BACKEND=sentence-transformers` et réindexez les
> documents. Les vecteurs des deux backends ne sont pas compatibles.

## 3. Configurer l'utilisateur technique Odoo

Dans **Paramètres → Utilisateurs et sociétés → Utilisateurs → Nouveau** :

1. Créez un utilisateur interne, par exemple `Copilot AI` (`copilot_ai`).
2. Accordez les droits de lecture nécessaires sur Ventes et Projets et le rôle
   **Achats / Utilisateur** pour créer des demandes de prix.
3. N'accordez pas les droits administrateur.
4. Depuis **Préférences → Sécurité du compte**, créez une clé API et renseignez-la
   dans `ODOO_API_KEY`.
5. Activez les devises nécessaires à vos tests et donnez à l'utilisateur
   technique les droits requis pour y accéder.

Le service utilise l'API JSON-2 avec cette clé. Il lit les données métier, crée
les entrées du journal `ai.action.log` et peut créer un brouillon de demande de
prix après approbation. Il ne confirme pas le bon d'achat.

## 4. Démarrer le microservice

```bash
cd ai_service
source .venv/bin/activate
uvicorn main:app --reload --port 8001
```

- Service : <http://localhost:8001>
- Documentation Swagger : <http://localhost:8001/docs>
- Vérification : `curl http://localhost:8001/health`

Redémarrez le service après chaque modification de `.env`.

## 5. Installer le module Odoo

Ajoutez le dossier `addons/` de ce dépôt à `addons_path` dans la configuration
Odoo :

```ini
addons_path = /chemin/vers/CopilotOdoo/addons,/chemin/vers/odoo/addons
```

Utilisez l'interpréteur Python de l'installation Odoo pour lancer le script
`odoo` :

```bash
export ODOO_PY=/chemin/vers/odoo/.venv/bin/python
export ODOO_BIN=/chemin/vers/odoo/odoo-bin
export ODOO_CONF=/chemin/vers/odoo.conf

# Première installation
"$ODOO_PY" "$ODOO_BIN" -c "$ODOO_CONF" -i odoo_copilot -d odoo

# Mise à jour après une modification
"$ODOO_PY" "$ODOO_BIN" -c "$ODOO_CONF" -u odoo_copilot -d odoo
```

Si le module n'apparaît pas, vérifiez `addons_path`, redémarrez Odoo et mettez
à jour la liste des applications. Lancer le script Odoo avec un Python qui ne
contient pas le paquet `odoo` provoque `ModuleNotFoundError: No module named
'odoo'`.

## 6. Relier Odoo au microservice

Le module crée une configuration par défaut dans **Copilot IA → Configuration** :

- **URL du microservice** : `http://localhost:8001`
- **Clé API du microservice** : la valeur de `SERVICE_API_KEY`
- **Actif** : coché

Une seule configuration active est utilisée. Seul un administrateur peut la
modifier.
