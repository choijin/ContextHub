from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from contexthub.domain.exceptions import RepositoryError
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.document import Document
from contexthub.infrastructure.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)


def test_sqlite_repository_persists_chunks_in_faiss_position_order(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    repository = SQLiteDocumentRepository(database_path)
    document_id = uuid4()
    document = Document(
        id=document_id,
        filename="sample.pdf",
        title=None,
        checksum_sha256="abc",
        page_count=1,
    )
    chunks = [
        _chunk("chunk-a", document_id, 0),
        _chunk("chunk-b", document_id, 1),
    ]

    repository.initialize_schema()
    repository.replace_all([document], chunks, {"chunk-a": 1, "chunk-b": 0})
    loaded = repository.get_chunks_by_positions([0, 1])

    assert [chunk.id for chunk in loaded] == ["chunk-b", "chunk-a"]
    assert repository.chunk_count() == 2
    assert repository.faiss_positions() == [0, 1]
    repository.close()


def test_sqlite_repository_supports_reads_from_worker_thread(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata.db"
    document_id = uuid4()
    document = Document(
        id=document_id,
        filename="sample.pdf",
        title=None,
        checksum_sha256="abc",
        page_count=1,
    )
    repository = SQLiteDocumentRepository(database_path)
    repository.initialize_schema()
    repository.replace_all(
        [document],
        [_chunk("chunk-a", document_id, 0)],
        {"chunk-a": 0},
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        chunk = executor.submit(repository.get_chunks_by_positions, [0]).result()[0]
        filenames = executor.submit(repository.get_document_filenames, [document_id]).result()

    assert chunk.id == "chunk-a"
    assert filenames == {document_id: "sample.pdf"}
    repository.close()


def test_sqlite_repository_rejects_missing_position_mapping(tmp_path: Path) -> None:
    repository = SQLiteDocumentRepository(tmp_path / "metadata.db")
    document_id = uuid4()
    document = Document(
        id=document_id,
        filename="sample.pdf",
        checksum_sha256="abc",
        page_count=1,
    )
    repository.initialize_schema()

    with pytest.raises(RepositoryError, match="Every chunk"):
        repository.replace_all([document], [_chunk("chunk-a", document_id, 0)], {})

    repository.close()


def _chunk(chunk_id: str, document_id: UUID, index: int) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id=document_id,
        text=f"text {index}",
        chunk_index=index,
        page_start=1,
        page_end=1,
        content_hash=f"hash-{index}",
    )
