"""Fakes for offline indexing tests."""

from pathlib import Path
from uuid import UUID

from contexthub.domain.models.chunk import Chunk, ChunkingConfig
from contexthub.domain.models.document import Document, DocumentPage, NormalizedDocument
from contexthub.domain.models.generation import GenerationResult
from contexthub.domain.models.prompt import PromptRequest
from contexthub.domain.models.query import RetrievalResult, VectorSearchResult


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
        lowered = text.lower()
        if "alpha" in lowered or "regularization" in lowered:
            return [1.0, 0.0, 0.0]
        if "beta" in lowered or "probability" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


class TrackingEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self) -> None:
        self.query_calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return super().embed_query(text)


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
    ) -> list[VectorSearchResult]:
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

    def get_document_filenames(self, document_ids: list[UUID]) -> dict[UUID, str]:
        by_id = {document.id: document.filename for document in self.documents}
        return {document_id: by_id[document_id] for document_id in document_ids}

    def chunk_count(self) -> int:
        return len(self.chunks)

    def close(self) -> None:
        return None

    def validate_faiss_positions(self, expected_count: int) -> None:
        return None


class InMemoryVectorStore:
    dimensions = 3
    vector_count = 3

    def __init__(self, results: list[VectorSearchResult] | None = None) -> None:
        self.results = results or [
            VectorSearchResult(position=0, score=0.9, rank=1),
            VectorSearchResult(position=1, score=0.8, rank=2),
        ]
        self.search_calls: list[tuple[list[float], int, float | None]] = []

    def build(self, embeddings: list[list[float]], chunks: list[Chunk]) -> None:
        return None

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        self.search_calls.append((query_embedding, top_k, similarity_threshold))
        return [
            result
            for result in self.results[:top_k]
            if similarity_threshold is None or result.score >= similarity_threshold
        ]

    def save(self, directory: Path) -> None:
        return None

    def load(self, directory: Path) -> None:
        return None

    def is_loaded(self) -> bool:
        return True


def small_chunking_config() -> ChunkingConfig:
    return ChunkingConfig(chunk_size=80, chunk_overlap=10)


class FakeRetriever:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.calls: list[tuple[str, int, float | None]] = []

    def retrieve(
        self,
        question: str,
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> RetrievalResult:
        self.calls.append((question, top_k, similarity_threshold))
        return self.result


class FakeLLMProvider:
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self, text: str = '{"answer": "Fake answer.", "citation_ids": []}') -> None:
        self.text = text
        self.calls: list[PromptRequest] = []

    def generate(self, prompt: PromptRequest) -> GenerationResult:
        self.calls.append(prompt)
        return GenerationResult(text=self.text, provider=self.provider_name, model=self.model_name)
