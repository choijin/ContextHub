"""Offline retrieval evaluation domain models."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvaluationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    @field_validator("expected_chunk_ids")
    @classmethod
    def validate_expected_chunk_ids(cls, value: list[str]) -> list[str]:
        if any(not chunk_id.strip() for chunk_id in value):
            raise ValueError("expected_chunk_ids must not contain blank values")
        if len(set(value)) != len(value):
            raise ValueError("expected_chunk_ids must not contain duplicates")
        return value

    @model_validator(mode="after")
    def validate_answerability(self) -> "EvaluationQuestion":
        if self.answerable and not self.expected_chunk_ids:
            raise ValueError("answerable questions must include expected_chunk_ids")
        if not self.answerable and self.expected_chunk_ids:
            raise ValueError("unanswerable questions must not include expected_chunk_ids")
        return self


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recall_at_k: float
    hit_rate_at_k: float
    mrr: float
    latency_ms: int

    @field_validator("recall_at_k", "hit_rate_at_k", "mrr")
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


class EvaluationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    answerable: bool
    expected_chunk_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    retrieved_scores: list[float] = Field(default_factory=list)
    result: EvaluationResult


class EvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top_k: int
    case_count: int
    answerable_case_count: int
    unanswerable_case_count: int
    recall_at_k: float
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    average_retrieval_latency_ms: float

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("top_k must be positive")
        return value

    @field_validator("case_count", "answerable_case_count", "unanswerable_case_count")
    @classmethod
    def validate_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("counts must be non-negative")
        return value

    @field_validator("recall_at_k", "hit_rate_at_k", "mean_reciprocal_rank")
    @classmethod
    def validate_aggregate_ratio(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("metric must be between 0 and 1")
        return value

    @field_validator("average_retrieval_latency_ms")
    @classmethod
    def validate_average_latency(cls, value: float) -> float:
        if value < 0:
            raise ValueError("average_retrieval_latency_ms must be non-negative")
        return value


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dataset_path: Path
    report_path: Path | None = None
    configuration: dict[str, Any]
    metrics: EvaluationMetrics
    cases: list[EvaluationCaseResult]
