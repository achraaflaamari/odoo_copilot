# -*- coding: utf-8 -*-
"""
Module RAG (Retrieval-Augmented Generation) pour OdooCopilot.
Indexe des documents texte dans ChromaDB et expose un outil de recherche
utilisable par les agents LangGraph.
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Répertoire de stockage de la base vectorielle
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./rag/chroma_db")
COLLECTION_NAME: str = "odoo_copilot_docs"

# Importations optionnelles : RAG inactif si les packages sont absents
try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    _RAG_AVAILABLE = True
    logger.info("RAG disponible : ChromaDB + SentenceTransformers chargés.")
except ImportError:
    _RAG_AVAILABLE = False
    logger.warning(
        "RAG non disponible : installez chromadb et sentence-transformers. "
        "Le module fonctionnera sans RAG."
    )


class RagRetriever:
    """Interface de recherche documentaire via ChromaDB et Sentence-Transformers.

    La classe est en mode dégradé si les packages RAG ne sont pas installés.
    """

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._model = None
        self._ready = False

        if _RAG_AVAILABLE:
            self._init_chroma()

    def _init_chroma(self) -> None:
        """Initialise le client ChromaDB et le modèle d'embedding."""
        try:
            Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=CHROMA_PATH,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            # Modèle multilingue léger, bon pour le français
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            self._ready = True
            logger.info(
                "ChromaDB initialisé : collection '%s', %d documents.",
                COLLECTION_NAME,
                self._collection.count(),
            )
        except Exception as exc:
            logger.error("Erreur d'initialisation ChromaDB : %s", exc)
            self._ready = False

    # ─────────────────────────── Indexation ─────────────────────────────────

    def index_documents(self, documents: list[dict[str, Any]]) -> int:
        """Indexe une liste de documents dans ChromaDB.

        Args:
            documents: Liste de dicts avec les clés 'id', 'text', 'metadata'.
                - id (str)       : identifiant unique du document.
                - text (str)     : contenu textuel à indexer.
                - metadata (dict): métadonnées optionnelles (source, type, etc.).

        Returns:
            Nombre de documents indexés avec succès.
        """
        if not self._ready:
            logger.warning("RAG non disponible — indexation ignorée.")
            return 0

        indexed = 0
        for doc in documents:
            try:
                embedding = self._model.encode(doc["text"]).tolist()
                self._collection.upsert(
                    ids=[doc["id"]],
                    embeddings=[embedding],
                    documents=[doc["text"]],
                    metadatas=[doc.get("metadata", {})],
                )
                indexed += 1
            except Exception as exc:
                logger.error("Erreur d'indexation du document '%s' : %s", doc.get("id"), exc)

        logger.info("%d documents indexés dans ChromaDB.", indexed)
        return indexed

    def index_text_file(self, file_path: str, chunk_size: int = 500) -> int:
        """Découpe un fichier texte en morceaux et les indexe.

        Args:
            file_path: Chemin absolu ou relatif vers le fichier texte.
            chunk_size: Taille approximative de chaque morceau (en caractères).

        Returns:
            Nombre de morceaux indexés.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error("Fichier introuvable : %s", file_path)
            return 0

        text = path.read_text(encoding="utf-8", errors="ignore")
        # Découpage simple par paragraphes / chunks de taille fixe
        chunks = self._chunk_text(text, chunk_size)
        documents = [
            {
                "id": f"{path.stem}_{i}",
                "text": chunk,
                "metadata": {"source": str(path), "chunk": i},
            }
            for i, chunk in enumerate(chunks)
        ]
        return self.index_documents(documents)

    # ─────────────────────────── Recherche ──────────────────────────────────

    def search(self, query: str, n_results: int = 3) -> list[dict[str, Any]]:
        """Recherche les documents les plus pertinents pour une requête.

        Args:
            query: Texte de la requête utilisateur.
            n_results: Nombre de résultats à retourner.

        Returns:
            Liste de dicts {'text': str, 'metadata': dict, 'distance': float}.
            Retourne une liste vide si le RAG n'est pas disponible ou si la
            collection est vide.
        """
        if not self._ready:
            return []

        try:
            count = self._collection.count()
            if count == 0:
                return []

            n_results = min(n_results, count)
            embedding = self._model.encode(query).tolist()
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            output = []
            for text, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                output.append({"text": text, "metadata": meta, "distance": float(dist)})
            return output
        except Exception as exc:
            logger.error("Erreur de recherche RAG : %s", exc)
            return []

    def search_as_context(self, query: str, n_results: int = 3) -> str:
        """Retourne les résultats de recherche sous forme de texte pour le LLM.

        Args:
            query: Texte de la requête.
            n_results: Nombre de résultats.

        Returns:
            Contexte formaté à injecter dans le prompt, ou chaîne vide.
        """
        results = self.search(query, n_results)
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "document")
            parts.append(f"[Source {i} — {source}]\n{r['text']}")
        return "\n\n".join(parts)

    # ─────────────────────────── Utilitaires ────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int) -> list[str]:
        """Découpe un texte en morceaux de taille approximative.

        La coupure se fait de préférence à un saut de ligne ou une espace.

        Args:
            text: Texte à découper.
            chunk_size: Taille cible de chaque morceau.

        Returns:
            Liste de morceaux de texte.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
            # Chercher un saut de ligne ou une espace proches de la limite
            cut = text.rfind("\n", start, end)
            if cut == -1 or cut <= start:
                cut = text.rfind(" ", start, end)
            if cut == -1 or cut <= start:
                cut = end
            chunks.append(text[start:cut].strip())
            start = cut + 1
        return [c for c in chunks if c]

    @property
    def is_ready(self) -> bool:
        """Retourne True si le RAG est opérationnel."""
        return self._ready

    def document_count(self) -> int:
        """Retourne le nombre de documents indexés."""
        if not self._ready or self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0


# Instance partagée (singleton)
rag_retriever = RagRetriever()
