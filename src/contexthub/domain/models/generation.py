"""Generation domain models."""

from pydantic import BaseModel, field_validator


class GenerationResult(BaseModel):
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None

    @field_validator("text", "provider", "model")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @field_validator("input_tokens", "output_tokens", "duration_ms")
    @classmethod
    def validate_non_negative_optional(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("value must be non-negative")
        return value
