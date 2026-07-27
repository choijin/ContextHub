"""Document domain models."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class Document(BaseModel):
    id: UUID
    filename: str
    title: str | None = None
    checksum_sha256: str
    page_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("filename", "checksum_sha256")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("page_count")
    @classmethod
    def validate_page_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("page_count must be non-negative")
        return value


class DocumentPage(BaseModel):
    document_id: UUID
    page_number: int
    text: str

    @field_validator("page_number")
    @classmethod
    def validate_page_number(cls, value: int) -> int:
        if value < 1:
            raise ValueError("page_number must be one-based")
        return value


class NormalizedDocument(BaseModel):
    document_id: UUID
    pages: list[DocumentPage] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pages_match_document(self) -> "NormalizedDocument":
        for page in self.pages:
            if page.document_id != self.document_id:
                raise ValueError("all pages must belong to document_id")
        return self
