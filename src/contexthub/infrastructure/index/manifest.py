"""Index manifest model and validation."""

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from contexthub.config.settings import ApplicationSettings
from contexthub.domain.exceptions import IndexCompatibilityError, IndexLoadError

MANIFEST_FILENAME = "manifest.json"
SCHEMA_VERSION = "1.0"
VECTOR_INDEX_TYPE = "IndexFlatIP"
EMBEDDING_PROVIDER = "sentence_transformers"


class SourceDocumentManifest(BaseModel):
    relative_path: str
    checksum_sha256: str


class IndexManifest(BaseModel):
    schema_version: str
    application_version: str
    built_at: datetime
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    vector_index_type: str
    chunk_size: int
    chunk_overlap: int
    document_count: int
    chunk_count: int
    source_documents: list[SourceDocumentManifest] = Field(default_factory=list)

    @field_validator("embedding_dimensions", "chunk_size", "document_count", "chunk_count")
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, value: int) -> int:
        if value < 0:
            raise ValueError("chunk_overlap must be non-negative")
        return value


def load_manifest(index_directory: Path) -> IndexManifest:
    manifest_path = index_directory / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise IndexLoadError("Index manifest is missing.")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return IndexManifest.model_validate(payload)
    except json.JSONDecodeError as exc:
        raise IndexLoadError("Index manifest is malformed JSON.") from exc
    except ValueError as exc:
        raise IndexLoadError("Index manifest is invalid.") from exc


def validate_manifest(
    manifest: IndexManifest,
    settings: ApplicationSettings,
    embedding_dimensions: int,
) -> None:
    validate_manifest_settings(manifest, settings)
    if manifest.embedding_dimensions != embedding_dimensions:
        raise IndexCompatibilityError("Index embedding dimensions are incompatible.")


def validate_manifest_settings(
    manifest: IndexManifest,
    settings: ApplicationSettings,
) -> None:
    if manifest.schema_version != SCHEMA_VERSION:
        raise IndexCompatibilityError("Index schema version is incompatible.")
    if manifest.application_version != settings.app_version:
        raise IndexCompatibilityError("Index application version is incompatible.")
    if manifest.embedding_provider != EMBEDDING_PROVIDER:
        raise IndexCompatibilityError("Index embedding provider is incompatible.")
    if manifest.embedding_model != settings.embedding_model:
        raise IndexCompatibilityError("Index embedding model is incompatible.")
    if manifest.vector_index_type != VECTOR_INDEX_TYPE:
        raise IndexCompatibilityError("Index vector type is incompatible.")
    if manifest.chunk_size != settings.chunk_size:
        raise IndexCompatibilityError("Index chunk size is incompatible.")
    if manifest.chunk_overlap != settings.chunk_overlap:
        raise IndexCompatibilityError("Index chunk overlap is incompatible.")
