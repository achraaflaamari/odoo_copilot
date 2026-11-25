# -*- coding: utf-8 -*-
"""
Script d'indexation initiale du RAG.
Lance ce script une fois pour indexer les documents de référence Odoo.

Usage :
    cd ai_service
    source .venv/bin/activate
    python rag/index_docs.py
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer rag.retriever
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import rag_retriever


def main() -> None:
    """Indexe les documents de démonstration et les fichiers du dossier docs/."""
    if not rag_retriever.is_ready:
        print("❌ RAG non disponible. Installez le RAG optionnel : pip install -r requirements-rag.txt")
        return

    # Documents de référence intégrés (documentation Odoo simplifiée)
    demo_docs = [
        {
            "id": "odoo_sale_intro",
            "text": (
                "Le module Ventes d'Odoo permet de gérer les devis et commandes clients. "
                "Un devis (quotation) peut être confirmé pour devenir une commande de vente (sale.order). "
                "Les états possibles sont : brouillon, envoyé, confirmé, annulé. "
                "Le champ amount_total représente le montant total TTC."
            ),
            "metadata": {"source": "odoo_docs", "module": "sale"},
        },
        {
            "id": "odoo_purchase_intro",
            "text": (
                "Le module Achats d'Odoo gère les bons de commande fournisseur (purchase.order). "
                "Un bon de commande passe par les états : brouillon, envoyé au fournisseur, confirmé, réceptionné. "
                "Le champ date_planned indique la date de livraison prévue. "
                "Les lignes de commande sont dans purchase.order.line."
            ),
            "metadata": {"source": "odoo_docs", "module": "purchase"},
        },
        {
            "id": "odoo_project_intro",
            "text": (
                "Le module Projets d'Odoo (project.project) permet de gérer des projets avec des tâches. "
                "Chaque tâche (project.task) est assignée à un ou plusieurs utilisateurs via user_ids. "
                "Les étapes (stages) définissent l'avancement : À faire, En cours, Terminé. "
                "La date_deadline indique l'échéance de la tâche."
            ),
            "metadata": {"source": "odoo_docs", "module": "project"},
        },
        {
            "id": "copilot_usage",
            "text": (
                "OdooCopilot est un assistant IA multi-agents pour Odoo 20. "
                "Il comprend trois agents spécialisés : Ventes, Achats et Projets. "
                "L'agent routeur classe automatiquement chaque question et délègue à l'agent compétent. "
                "Toute action d'écriture génère un brouillon qui nécessite une validation humaine avant exécution."
            ),
            "metadata": {"source": "copilot_docs", "type": "overview"},
        },
    ]

    print(f"📚 Indexation de {len(demo_docs)} documents de démonstration…")
    indexed = rag_retriever.index_documents(demo_docs)
    print(f"✅ {indexed} documents indexés. Total : {rag_retriever.document_count()}")

    # Indexer les fichiers texte du dossier docs/ (si présents)
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    if docs_dir.exists():
        txt_files = list(docs_dir.glob("*.txt")) + list(docs_dir.glob("*.md"))
        for f in txt_files:
            print(f"📄 Indexation de {f.name}…")
            n = rag_retriever.index_text_file(str(f))
            print(f"   → {n} morceaux indexés.")
    else:
        print("ℹ️  Aucun fichier dans docs/ — seuls les documents de démonstration ont été indexés.")


if __name__ == "__main__":
    main()
