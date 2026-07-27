"""Retriever port for later runtime phases."""

from typing import Protocol

from contexthub.domain.models.query import RetrievalResult


class Retriever(Protocol):
    def retrieve(
        self,
        question: str,
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> RetrievalResult: ...
