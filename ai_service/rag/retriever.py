# -*- coding: utf-8 -*-
"""
Module RAG (Retrieval-Augmented Generation) pour OdooCopilot.
Indexe des documents texte dans ChromaDB et expose un outil de recherche
utilisable par les agents LangGraph.

Deux backends d'embeddings sont supportés (variable RAG_EMBEDDING_BACKEND) :
- "chroma-onnx" (défaut) : modèle ONNX MiniLM fourni par ChromaDB.
  Installation légère : aucun PyTorch / CUDA / triton à télécharger.
- "sentence-transformers" : modèle multilingue de meilleure qualité, mais
  nécessite PyTorch. Installer la roue CPU pour éviter triton et nvidia-*.
"""

import logging
import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# Charge .env (racine du dépôt ou ai_service/) même en exécution standalone
load_dotenv()

logger = logging.getLogger(__name__)

# Répertoire de stockage de la base vectorielle
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./rag/chroma_db")
COLLECTION_NAME: str = "odoo_copilot_docs"

# Backend d'embeddings : "chroma-onnx" (léger) ou "sentence-transformers" (optionnel)
EMBEDDING_BACKEND: str = os.getenv("RAG_EMBEDDING_BACKEND", "chroma-onnx").strip().lower()
_ST_BACKENDS = {"sentence-transformers", "sentence_transformers", "st"}
_ST_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Signature commune des backends : liste de textes -> liste de vecteurs
Embedder = Callable[[list[str]], list[list[float]]]

# Importations optionnelles : RAG inactif si ChromaDB est absent
try:
    import chromadb
    from chromadb.config import Settings

    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    logger.warning(
        "RAG non disponible : installez le RAG optionnel avec "
        "`pip install -r requirements-rag.txt`. Le service fonctionne sans RAG."
    )


def _build_onnx_embedder() -> Embedder:
    """Construit le backend ONNX fourni par ChromaDB (sans PyTorch)."""
    from chromadb.utils import embedding_functions

    # DefaultEmbeddingFunction = ONNXMiniLM_L6_V2 selon les versions de ChromaDB
    factory = getattr(embedding_functions, "DefaultEmbeddingFunction", None)
    if factory is None:
        factory = embedding_functions.ONNXMiniLM_L6_V2

    embedding_function = factory()
    logger.info("Backend d'embeddings : ONNX MiniLM (ChromaDB, sans PyTorch).")
    return embedding_function


def _build_sentence_transformer_embedder() -> Embedder:
    """Construit le backend Sentence-Transformers (nécessite PyTorch)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(_ST_MODEL_NAME)
    logger.info("Backend d'embeddings : Sentence-Transformers (%s).", _ST_MODEL_NAME)

    def encode(texts: list[str]) -> list[list[float]]:
        return model.encode(texts, normalize_embeddings=True).tolist()

    return encode


class RagRetriever:
    """Interface de recherche documentaire via ChromaDB.

    La classe est en mode dégradé si les packages RAG ne sont pas installés.
    """

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._embedder: Embedder | None = None
        self._ready = False

        if _CHROMA_AVAILABLE:
            self._init_chroma()

    def _init_chroma(self) -> None:
        """Initialise le client ChromaDB et le backend d'embeddings."""
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
            self._embedder = self._build_embedder()
            self._ready = True
            logger.info(
                "ChromaDB initialisé : collection '%s', %d documents.",
                COLLECTION_NAME,
                self._collection.count(),
            )
        except Exception as exc:
            logger.error("Erreur d'initialisation ChromaDB : %s", exc)
            self._ready = False

    @staticmethod
    def _build_embedder() -> Embedder:
        """Sélectionne le backend d'embeddings configuré.

        Si Sentence-Transformers est demandé mais absent, on retombe
        automatiquement sur les embeddings ONNX (aucun téléchargement lourd).
        """
        if EMBEDDING_BACKEND in _ST_BACKENDS:
            try:
                return _build_sentence_transformer_embedder()
            except ImportError:
                logger.warning(
                    "RAG_EMBEDDING_BACKEND=%s mais sentence-transformers n'est pas "
                    "installé — bascule sur les embeddings ONNX.",
                    EMBEDDING_BACKEND,
                )
        return _build_onnx_embedder()

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Calcule les vecteurs d'une liste de textes avec le backend actif."""
        if not texts:
            return []
        if self._embedder is None:
            raise RuntimeError("Backend d'embeddings non initialisé.")
        embeddings = self._embedder(texts)
        return [[float(value) for value in embedding] for embedding in embeddings]

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

        valid_docs = [doc for doc in documents if doc.get("id") and doc.get("text")]
        if not valid_docs:
            return 0

        # Calcul groupé des embeddings (beaucoup plus rapide qu'un appel par document)
        try:
            self._collection.upsert(
                ids=[doc["id"] for doc in valid_docs],
                embeddings=self._embed([doc["text"] for doc in valid_docs]),
                documents=[doc["text"] for doc in valid_docs],
                metadatas=[doc.get("metadata") or {} for doc in valid_docs],
            )
            indexed = len(valid_docs)
        except Exception as exc:
            logger.error(
                "Erreur d'indexation groupée : %s — nouvel essai document par document.",
                exc,
            )
            indexed = 0
            for doc in valid_docs:
                try:
                    self._collection.upsert(
                        ids=[doc["id"]],
                        embeddings=self._embed([doc["text"]]),
                        documents=[doc["text"]],
                        metadatas=[doc.get("metadata") or {}],
                    )
                    indexed += 1
                except Exception as doc_exc:
                    logger.error(
                        "Erreur d'indexation du document '%s' : %s",
                        doc.get("id"),
                        doc_exc,
                    )

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
            results = self._collection.query(
                query_embeddings=self._embed([query]),
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

    @property
    def embedding_backend(self) -> str:
        """Retourne le backend d'embeddings configuré."""
        return EMBEDDING_BACKEND

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
