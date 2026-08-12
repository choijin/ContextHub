"""Internal structured-output models for LLM responses."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMAnswer(BaseModel):
    """LLM-generated answer content before trusted citation enrichment."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(
        description="Answer grounded only in the supplied retrieved context.",
    )
    cited_source_indices: list[int] = Field(
        description="One-based source_index values that support the answer.",
    )

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("answer must not be blank")
        return normalized

    @field_validator("cited_source_indices")
    @classmethod
    def validate_cited_source_indices(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("at least one citation is required")
        if any(index < 1 for index in value):
            raise ValueError("source indices must be one-based")
        return value
