"""Answer and citation domain models."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from contexthub.domain.enums import AnswerStatus


class Citation(BaseModel):
    chunk_id: str
    document_name: str
    page_start: int
    page_end: int
    excerpt: str

    @field_validator("chunk_id", "document_name", "excerpt")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_page_range(self) -> "Citation":
        if self.page_start < 1:
            raise ValueError("page_start must be one-based")
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class Answer(BaseModel):
    request_id: UUID
    question: str
    answer: str
    status: AnswerStatus
    citations: list[Citation] = Field(default_factory=list)

    @field_validator("question", "answer")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value
