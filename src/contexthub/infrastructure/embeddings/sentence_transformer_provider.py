"""Sentence-transformers embedding provider."""

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from contexthub.domain.exceptions import EmbeddingProviderError


class SentenceTransformerEmbeddingProvider:
    """Generate normalized sentence-transformer embeddings."""

    def __init__(
        self,
        model_name: str,
        batch_size: int = 32,
        device: str = "cpu",
        model: Any | None = None,
    ) -> None:
        if batch_size <= 0:
            raise EmbeddingProviderError("embedding batch size must be positive")
        self._model_name = model_name
        self._batch_size = batch_size
        self._device = device
        self._model = model
        self._dimensions: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        self._ensure_model()
        if self._dimensions is None:
            model = self._model
            if model is None:
                raise EmbeddingProviderError("embedding model is not initialized")
            dimension = model.get_sentence_embedding_dimension()
            if not isinstance(dimension, int) or dimension <= 0:
                raise EmbeddingProviderError("embedding dimension is invalid")
            self._dimensions = dimension
        return self._dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise EmbeddingProviderError("document embedding batch must not be empty")
        if any(not text.strip() for text in texts):
            raise EmbeddingProviderError("document text must not be blank")
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingProviderError("query text must not be blank")
        return self._embed([text])[0]

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name, device=self._device)
        except Exception as exc:
            raise EmbeddingProviderError("Failed to initialize embedding provider.") from exc

    def _embed(self, texts: list[str]) -> list[list[float]]:
        self._ensure_model()
        try:
            encoded = self._model.encode(  # type: ignore[union-attr]
                texts,
                batch_size=self._batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            vectors = cast(NDArray[np.float32], np.asarray(encoded, dtype=np.float32))
            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            if vectors.shape[1] != self.dimensions:
                raise EmbeddingProviderError("embedding dimension mismatch")
            values = cast(list[list[float]], vectors.astype(float).tolist())
            return values
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError("Failed to generate embeddings.") from exc
