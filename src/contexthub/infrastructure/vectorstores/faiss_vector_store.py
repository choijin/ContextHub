"""FAISS vector store implementation."""

from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from contexthub.domain.exceptions import (
    IndexCompatibilityError,
    IndexLoadError,
    IndexNotLoadedError,
    VectorStoreError,
)
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.query import VectorSearchResult

FAISS_INDEX_FILENAME = "faiss.index"


class FaissVectorStore:
    """Persist and search normalized vectors with FAISS IndexFlatIP."""

    def __init__(self, dimensions: int) -> None:
        if dimensions <= 0:
            raise IndexCompatibilityError("Vector dimensions must be positive.")
        self._dimensions = dimensions
        self._index: Any | None = None
        self._chunks: list[Chunk] = []

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def vector_count(self) -> int:
        if self._index is None:
            return 0
        return int(self._index.ntotal)

    def build(self, embeddings: list[list[float]], chunks: list[Chunk]) -> None:
        if not embeddings:
            raise VectorStoreError("Embeddings must not be empty.")
        if len(embeddings) != len(chunks):
            raise IndexCompatibilityError("Embedding count must equal chunk count.")
        vectors = self._vectors_from_embeddings(embeddings)
        try:
            import faiss

            index = faiss.IndexFlatIP(self._dimensions)
            index.add(vectors)
        except Exception as exc:
            raise VectorStoreError("Failed to build FAISS index.") from exc
        self._index = index
        self._chunks = list(chunks)

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        if self._index is None:
            raise IndexNotLoadedError("FAISS index is not loaded.")
        if top_k <= 0:
            raise VectorStoreError("top_k must be positive.")
        query = self._vectors_from_embeddings([query_embedding])
        top_k = min(top_k, self.vector_count)
        distances, positions = self._index.search(query, top_k)
        results: list[VectorSearchResult] = []
        for score, position in zip(distances[0].tolist(), positions[0].tolist(), strict=True):
            if position < 0:
                continue
            normalized_score = float(score)
            if similarity_threshold is not None and normalized_score < similarity_threshold:
                continue
            results.append(
                VectorSearchResult(
                    position=int(position),
                    score=normalized_score,
                    rank=len(results) + 1,
                )
            )
        return results

    def save(self, directory: Path) -> None:
        if self._index is None:
            raise IndexNotLoadedError("FAISS index is not loaded.")
        directory.mkdir(parents=True, exist_ok=True)
        try:
            import faiss

            faiss.write_index(self._index, str(directory / FAISS_INDEX_FILENAME))
        except Exception as exc:
            raise VectorStoreError("Failed to save FAISS index.") from exc

    def load(self, directory: Path) -> None:
        index_path = directory / FAISS_INDEX_FILENAME
        if not index_path.exists():
            raise IndexLoadError("FAISS index file is missing.")
        try:
            import faiss

            loaded_index = faiss.read_index(str(index_path))
        except Exception as exc:
            raise IndexLoadError("Failed to load FAISS index.") from exc
        if int(loaded_index.d) != self._dimensions:
            raise IndexCompatibilityError("FAISS index dimensions do not match settings.")
        self._index = loaded_index
        self._chunks = []

    def is_loaded(self) -> bool:
        return self._index is not None

    def _vectors_from_embeddings(self, embeddings: list[list[float]]) -> NDArray[np.float32]:
        vectors = cast(NDArray[np.float32], np.asarray(embeddings, dtype=np.float32))
        if vectors.ndim != 2:
            raise IndexCompatibilityError("Embeddings must be a 2D matrix.")
        if vectors.shape[1] != self._dimensions:
            raise IndexCompatibilityError("Embedding dimensions do not match vector store.")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise IndexCompatibilityError("Embedding vectors must not be zero vectors.")
        return cast(NDArray[np.float32], vectors / norms)
