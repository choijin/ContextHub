"""Environment-driven application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    """Validated settings for the ContextHub backend foundation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CONTEXTHUB_",
        extra="ignore",
    )

    app_name: str = "ContextHub"
    app_version: str = "1.0.0"
    environment: str = "local"
    log_level: str = "INFO"

    pdf_directory: Path = Path("./data/pdfs")
    index_directory: Path = Path("./data/index")
    metadata_database_path: Path = Path("./data/index/metadata.db")
    evaluation_directory: Path = Path("./data/evaluation")

    chunk_size: int = 1000
    chunk_overlap: int = 150
    max_context_characters: int = 12000

    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_device: str = "cpu"

    vector_store_provider: str = "faiss"

    llm_provider: str = "huggingface"
    huggingface_api_token: SecretStr | None = None
    huggingface_model: str = ""

    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 512

    default_top_k: int = 5
    max_top_k: int = 20
    similarity_threshold: float | None = None

    allow_start_without_index: bool = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @model_validator(mode="after")
    def validate_numeric_constraints(self) -> "ApplicationSettings":
        positive_int_fields = {
            "chunk_size": self.chunk_size,
            "max_context_characters": self.max_context_characters,
            "embedding_batch_size": self.embedding_batch_size,
            "default_top_k": self.default_top_k,
            "max_top_k": self.max_top_k,
            "llm_max_output_tokens": self.llm_max_output_tokens,
        }
        for field_name, value in positive_int_fields.items():
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")

        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.llm_timeout_seconds <= 0:
            raise ValueError("llm_timeout_seconds must be positive")
        if self.llm_max_retries < 0:
            raise ValueError("llm_max_retries must be non-negative")
        if not 0 <= self.llm_temperature <= 2:
            raise ValueError("llm_temperature must be between 0 and 2")
        if self.default_top_k > self.max_top_k:
            raise ValueError("default_top_k must not exceed max_top_k")
        if self.similarity_threshold is not None and not -1 <= self.similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between -1 and 1")
        return self

    @property
    def service_name(self) -> str:
        return "contexthub-api"

    @property
    def has_required_llm_configuration(self) -> bool:
        return bool(self.huggingface_model and self.huggingface_api_token)


@lru_cache
def get_settings() -> ApplicationSettings:
    """Return cached settings for production composition."""

    return ApplicationSettings()
