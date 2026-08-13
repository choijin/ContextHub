from pathlib import Path
from uuid import UUID, uuid4

from contexthub.application.services.retrieval_service import RetrievalService
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.document import Document
from contexthub.infrastructure.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)
from contexthub.infrastructure.vectorstores.faiss_vector_store import FaissVectorStore
from tests.fakes.indexing import FakeEmbeddingProvider


def test_saved_index_retrieval_resolves_ranked_chunks_from_sqlite(tmp_path: Path) -> None:
    index_directory = tmp_path / "index"
    database_path = index_directory / "metadata.db"
    document_id = uuid4()
    chunks = [
        _chunk("regularization-chunk", document_id, 0, "regularization controls complexity"),
        _chunk("probability-chunk", document_id, 1, "probability measures uncertainty"),
    ]
    vector_store = FaissVectorStore(dimensions=3)
    embedding_provider = FakeEmbeddingProvider()
    vector_store.build(embedding_provider.embed_documents([chunk.text for chunk in chunks]), chunks)
    vector_store.save(index_directory)
    repository = SQLiteDocumentRepository(database_path)
    repository.initialize_schema()
    repository.replace_all(
        [
            Document(
                id=document_id,
                filename="fixture.pdf",
                checksum_sha256="checksum",
                page_count=2,
            )
        ],
        chunks,
        {chunk.id: position for position, chunk in enumerate(chunks)},
    )
    repository.close()

    runtime_repository = SQLiteDocumentRepository(database_path, read_only=True)
    loaded_store = FaissVectorStore(dimensions=3)
    loaded_store.load(index_directory)
    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=loaded_store,
        document_repository=runtime_repository,
        settings=ApplicationSettings(huggingface_model="test-model"),
    )

    result = service.retrieve("regularization", top_k=2)

    assert result.chunks[0].chunk.id == "regularization-chunk"
    assert result.chunks[0].rank == 1
    assert result.chunks[0].document_name == "fixture.pdf"
    assert result.chunks[0].chunk.page_start == 1
    assert result.chunks[1].chunk.id == "probability-chunk"
    runtime_repository.close()


def _chunk(chunk_id: str, document_id: UUID, index: int, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id=document_id,
        text=text,
        chunk_index=index,
        page_start=index + 1,
        page_end=index + 1,
        content_hash=f"hash-{index}",
    )
