from pathlib import Path
from uuid import uuid4

import pytest

from contexthub.domain.exceptions import IndexCompatibilityError
from contexthub.domain.models.chunk import Chunk
from contexthub.infrastructure.vectorstores.faiss_vector_store import FaissVectorStore


def test_faiss_vector_store_build_save_and_load(tmp_path: Path) -> None:
    chunks = [_chunk("chunk-a", 0), _chunk("chunk-b", 1)]
    store = FaissVectorStore(dimensions=3)

    store.build([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], chunks)
    results = store.search([1.0, 0.0, 0.0], top_k=1)
    store.save(tmp_path)

    loaded = FaissVectorStore(dimensions=3)
    loaded.load(tmp_path)

    assert results[0].position == 0
    assert (tmp_path / "faiss.index").exists()
    assert loaded.is_loaded()
    assert loaded.vector_count == 2


def test_faiss_vector_store_rejects_dimension_mismatch() -> None:
    store = FaissVectorStore(dimensions=3)

    with pytest.raises(IndexCompatibilityError, match="dimensions"):
        store.build([[1.0, 0.0]], [_chunk("chunk-a", 0)])


def _chunk(chunk_id: str, index: int) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id=uuid4(),
        text=f"text {index}",
        chunk_index=index,
        page_start=1,
        page_end=1,
        content_hash=f"hash-{index}",
    )
