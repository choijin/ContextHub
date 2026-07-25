"""Offline evaluation domain models."""

from pydantic import BaseModel, Field, field_validator


class EvaluationQuestion(BaseModel):
    id: str
    question: str
    expected_chunk_ids: list[str] = Field(default_factory=list)
    answerable: bool

    @field_validator("id", "question")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class EvaluationResult(BaseModel):
    recall_at_k: float
    mrr: float
    latency_ms: int

    @field_validator("recall_at_k", "mrr")
    @classmethod
    def validate_ratio(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("metric must be between 0 and 1")
        return value

    @field_validator("latency_ms")
    @classmethod
    def validate_latency(cls, value: int) -> int:
        if value < 0:
            raise ValueError("latency_ms must be non-negative")
        return value
