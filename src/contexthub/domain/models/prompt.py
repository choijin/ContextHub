"""Prompt domain models."""

from pydantic import BaseModel, Field, field_validator, model_validator


class PromptContext(BaseModel):
    source_index: int
    chunk_id: str
    document_name: str
    page_start: int
    page_end: int
    text: str

    @field_validator("chunk_id", "document_name", "text")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("source_index")
    @classmethod
    def validate_source_index(cls, value: int) -> int:
        if value < 1:
            raise ValueError("source_index must be one-based")
        return value

    @model_validator(mode="after")
    def validate_page_range(self) -> "PromptContext":
        if self.page_start < 1:
            raise ValueError("page_start must be one-based")
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class PromptRequest(BaseModel):
    system_prompt: str
    question: str
    context: list[PromptContext] = Field(default_factory=list)

    @field_validator("system_prompt", "question")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value
