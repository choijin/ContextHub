"""Vector store port."""

from pathlib import Path
from typing import Protocol

from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.query import VectorSearchResult


class VectorStore(Protocol):
    @property
    def dimensions(self) -> int: ...

    @property
    def vector_count(self) -> int: ...

    def build(self, embeddings: list[list[float]], chunks: list[Chunk]) -> None: ...

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> list[VectorSearchResult]: ...

    def save(self, directory: Path) -> None: ...

    def load(self, directory: Path) -> None: ...

    def is_loaded(self) -> bool: ...
