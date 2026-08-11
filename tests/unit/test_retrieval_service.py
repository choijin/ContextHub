from uuid import UUID, uuid4

import pytest

from contexthub.application.services.retrieval_service import RetrievalService
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.exceptions import InvalidQueryError
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.document import Document
from tests.fakes.indexing import (
    InMemoryDocumentRepository,
    InMemoryVectorStore,
    TrackingEmbeddingProvider,
)


def test_retrieval_service_embeds_query_and_searches_vector_store() -> None:
    embedding_provider = TrackingEmbeddingProvider()
    vector_store = InMemoryVectorStore()
    repository = _repository()
    service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        document_repository=repository,
        settings=ApplicationSettings(huggingface_model="test-model"),
    )

    result = service.retrieve(" alpha question ", top_k=2, similarity_threshold=0.5)

    assert embedding_provider.query_calls == ["alpha question"]
    assert len(vector_store.search_calls) == 1
    assert vector_store.search_calls[0][1:] == (2, 0.5)
    assert [chunk.chunk.id for chunk in result.chunks] == ["chunk-a", "chunk-b"]
    assert [chunk.rank for chunk in result.chunks] == [1, 2]
    assert [chunk.document_name for chunk in result.chunks] == ["fixture.pdf", "fixture.pdf"]


def test_retrieval_service_rejects_blank_question() -> None:
    service = RetrievalService(
        embedding_provider=TrackingEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
        document_repository=_repository(),
        settings=ApplicationSettings(huggingface_model="test-model"),
    )

    with pytest.raises(InvalidQueryError, match="blank"):
        service.retrieve(" ", top_k=1)


def test_retrieval_service_rejects_top_k_above_maximum() -> None:
    service = RetrievalService(
        embedding_provider=TrackingEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
        document_repository=_repository(),
        settings=ApplicationSettings(
            huggingface_model="test-model",
            default_top_k=2,
            max_top_k=2,
        ),
    )

    with pytest.raises(InvalidQueryError, match="max_top_k"):
        service.retrieve("alpha", top_k=3)


def test_retrieval_service_applies_similarity_threshold() -> None:
    service = RetrievalService(
        embedding_provider=TrackingEmbeddingProvider(),
        vector_store=InMemoryVectorStore(),
        document_repository=_repository(),
        settings=ApplicationSettings(huggingface_model="test-model"),
    )

    result = service.retrieve("alpha", top_k=2, similarity_threshold=0.85)

    assert [chunk.chunk.id for chunk in result.chunks] == ["chunk-a"]


def _repository() -> InMemoryDocumentRepository:
    document_id = uuid4()
    repository = InMemoryDocumentRepository()
    repository.documents = [
        Document(
            id=document_id,
            filename="fixture.pdf",
            checksum_sha256="checksum",
            page_count=1,
        )
    ]
    repository.chunks = [
        _chunk("chunk-a", document_id, 0),
        _chunk("chunk-b", document_id, 1),
    ]
    repository.positions = {"chunk-a": 0, "chunk-b": 1}
    return repository


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
