"""Internal structured-output models for LLM responses."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LLMAnswer(BaseModel):
    """LLM-generated answer content before trusted citation enrichment."""

    model_config = ConfigDict(extra="forbid")

    answerable: bool = Field(
        description="Whether the supplied context contains enough evidence to answer.",
    )
    answer: str = Field(
        description=(
            "Answer grounded only in the supplied retrieved context. Use an empty string when "
            "answerable is false."
        ),
    )
    cited_source_indices: list[int] = Field(
        description="One-based source_index values that support the answer.",
    )

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        return value.strip()

    @field_validator("cited_source_indices")
    @classmethod
    def validate_cited_source_indices(cls, value: list[int]) -> list[int]:
        if any(index < 1 for index in value):
            raise ValueError("source indices must be one-based")
        return value

    @model_validator(mode="after")
    def validate_answerability_contract(self) -> "LLMAnswer":
        if self.answerable:
            if not self.answer:
                raise ValueError("answerable responses require an answer")
            if not self.cited_source_indices:
                raise ValueError("answerable responses require at least one citation")
        else:
            if self.cited_source_indices:
                raise ValueError("unanswerable responses must not cite sources")
        return self
