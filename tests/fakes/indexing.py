"""Fakes for offline indexing tests."""

from pathlib import Path
from uuid import UUID

from contexthub.domain.models.chunk import Chunk, ChunkingConfig
from contexthub.domain.models.document import Document, DocumentPage, NormalizedDocument


class FakeDocumentParser:
    def __init__(self, pages: list[str]) -> None:
        self._pages = pages

    def parse(self, file_path: Path, document_id: UUID) -> NormalizedDocument:
        return NormalizedDocument(
            document_id=document_id,
            pages=[
                DocumentPage(document_id=document_id, page_number=index + 1, text=text)
                for index, text in enumerate(self._pages)
            ],
        )


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"
    dimensions = 3

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        length = float(max(len(text), 1))
        return [length, length / 2.0, 1.0]


class FailingVectorStore:
    dimensions = 3

    def build(self, embeddings: list[list[float]], chunks: list[Chunk]) -> None:
        msg = "simulated vector build failure"
        raise RuntimeError(msg)

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> list[object]:
        return []

    def save(self, directory: Path) -> None:
        return None

    def load(self, directory: Path) -> None:
        return None

    def is_loaded(self) -> bool:
        return False


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.chunks: list[Chunk] = []
        self.positions: dict[str, int] = {}

    def initialize_schema(self) -> None:
        return None

    def replace_all(
        self,
        documents: list[Document],
        chunks: list[Chunk],
        faiss_positions: dict[str, int],
    ) -> None:
        self.documents = documents
        self.chunks = chunks
        self.positions = faiss_positions

    def get_chunks_by_positions(self, positions: list[int]) -> list[Chunk]:
        reverse = {position: chunk_id for chunk_id, position in self.positions.items()}
        by_id = {chunk.id: chunk for chunk in self.chunks}
        return [by_id[reverse[position]] for position in positions]

    def chunk_count(self) -> int:
        return len(self.chunks)

    def close(self) -> None:
        return None


def small_chunking_config() -> ChunkingConfig:
    return ChunkingConfig(chunk_size=80, chunk_overlap=10)
