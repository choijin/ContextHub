import numpy as np
import pytest

from contexthub.domain.exceptions import EmbeddingProviderError
from contexthub.infrastructure.embeddings.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)


class DummySentenceTransformer:
    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def encode(
        self,
        texts: list[str],
        batch_size: int,
        convert_to_numpy: bool,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> np.ndarray:
        vectors = np.array([[float(len(text)), 1.0, 1.0] for text in texts], dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / norms


def test_embedding_provider_returns_normalized_vectors() -> None:
    provider = SentenceTransformerEmbeddingProvider("dummy", model=DummySentenceTransformer())

    vectors = provider.embed_documents(["alpha", "beta"])

    assert provider.dimensions == 3
    assert len(vectors) == 2
    assert pytest.approx(np.linalg.norm(vectors[0])) == 1.0


def test_embedding_provider_rejects_empty_batches() -> None:
    provider = SentenceTransformerEmbeddingProvider("dummy", model=DummySentenceTransformer())

    with pytest.raises(EmbeddingProviderError, match="must not be empty"):
        provider.embed_documents([])
