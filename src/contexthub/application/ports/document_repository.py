"""Document metadata repository port."""

from typing import Protocol

from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.document import Document


class DocumentRepository(Protocol):
    def initialize_schema(self) -> None: ...

    def replace_all(
        self,
        documents: list[Document],
        chunks: list[Chunk],
        faiss_positions: dict[str, int],
    ) -> None: ...

    def get_chunks_by_positions(self, positions: list[int]) -> list[Chunk]: ...

    def chunk_count(self) -> int: ...

    def validate_faiss_positions(self, expected_count: int) -> None: ...

    def close(self) -> None: ...
