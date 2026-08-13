"""Query and retrieval domain models."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from contexthub.domain.models.chunk import Chunk


class VectorSearchResult(BaseModel):
    position: int
    score: float
    rank: int

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: int) -> int:
        if value < 0:
            raise ValueError("position must be non-negative")
        return value

    @field_validator("rank")
    @classmethod
    def validate_search_rank(cls, value: int) -> int:
        if value < 1:
            raise ValueError("rank must be one-based")
        return value


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be blank")
        return normalized

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("top_k must be positive")
        return value


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float
    rank: int
    document_name: str

    @field_validator("rank")
    @classmethod
    def validate_rank(cls, value: int) -> int:
        if value < 1:
            raise ValueError("rank must be one-based")
        return value

    @field_validator("document_name")
    @classmethod
    def validate_document_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("document_name must not be blank")
        return value


class RetrievalResult(BaseModel):
    request_id: UUID
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieval_duration_ms: int

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value

    @field_validator("retrieval_duration_ms")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value < 0:
            raise ValueError("retrieval_duration_ms must be non-negative")
        return value
