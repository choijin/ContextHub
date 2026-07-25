"""Chunk domain models."""

from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


class Chunk(BaseModel):
    id: str
    document_id: UUID
    text: str
    chunk_index: int
    page_start: int
    page_end: int
    content_hash: str

    @field_validator("id", "text", "content_hash")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_chunk(self) -> "Chunk":
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")
        if self.page_start < 1:
            raise ValueError("page_start must be one-based")
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class ChunkingConfig(BaseModel):
    chunk_size: int = 1000
    chunk_overlap: int = 150

    @model_validator(mode="after")
    def validate_config(self) -> "ChunkingConfig":
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self
