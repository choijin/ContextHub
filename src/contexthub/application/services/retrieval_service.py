"""Runtime retrieval service."""

import logging
from uuid import uuid4

from contexthub.application.ports.document_repository import DocumentRepository
from contexthub.application.ports.embedding_provider import EmbeddingProvider
from contexthub.application.ports.vector_store import VectorStore
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.exceptions import (
    EmbeddingProviderError,
    IndexCompatibilityError,
    InvalidQueryError,
    RepositoryError,
    VectorStoreError,
)
from contexthub.domain.models.query import RetrievalResult, RetrievedChunk
from contexthub.observability.timing import Stopwatch


class RetrievalService:
    """Embed a question, search FAISS, and resolve trusted chunks from SQLite."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        document_repository: DocumentRepository,
        settings: ApplicationSettings,
        logger: logging.Logger | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._document_repository = document_repository
        self._settings = settings
        self._logger = logger or logging.getLogger(__name__)

    def retrieve(
        self,
        question: str,
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> RetrievalResult:
        stopwatch = Stopwatch()
        normalized_question = question.strip()
        if not normalized_question:
            raise InvalidQueryError("Question must not be blank.")
        if top_k <= 0:
            raise InvalidQueryError("top_k must be positive.")
        if top_k > self._settings.max_top_k:
            raise InvalidQueryError("top_k exceeds max_top_k.")

        threshold = (
            self._settings.similarity_threshold
            if similarity_threshold is None
            else similarity_threshold
        )

        try:
            query_embedding = self._embedding_provider.embed_query(normalized_question)
            vector_results = self._vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                similarity_threshold=threshold,
            )
            chunks = self._document_repository.get_chunks_by_positions(
                [result.position for result in vector_results]
            )
            document_filenames = self._document_repository.get_document_filenames(
                [chunk.document_id for chunk in chunks]
            )
        except (EmbeddingProviderError, VectorStoreError, RepositoryError) as exc:
            raise InvalidQueryError("Retrieval failed.") from exc

        if len(chunks) != len(vector_results):
            raise IndexCompatibilityError("Retrieved chunk count does not match vector results.")

        retrieved_chunks = [
            RetrievedChunk(
                chunk=chunk,
                score=result.score,
                rank=result.rank,
                document_name=document_filenames[chunk.document_id],
            )
            for chunk, result in zip(chunks, vector_results, strict=True)
        ]
        retrieval_result = RetrievalResult(
            request_id=uuid4(),
            query=normalized_question,
            chunks=retrieved_chunks,
            retrieval_duration_ms=stopwatch.elapsed_ms,
        )
        self._logger.info(
            "retrieval_completed",
            extra={
                "extra_fields": {
                    "chunk_count": len(retrieved_chunks),
                    "duration_ms": retrieval_result.retrieval_duration_ms,
                }
            },
        )
        return retrieval_result
