"""Offline deterministic index builder."""

import json
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import mkdtemp
from time import perf_counter
from typing import cast
from uuid import NAMESPACE_URL, uuid5

from contexthub.application.ports.chunker import Chunker
from contexthub.application.ports.document_parser import DocumentParser
from contexthub.application.ports.document_repository import DocumentRepository
from contexthub.application.ports.embedding_provider import EmbeddingProvider
from contexthub.application.ports.vector_store import VectorStore
from contexthub.domain.exceptions import (
    ConfigurationError,
    IndexCompatibilityError,
)
from contexthub.domain.models.chunk import Chunk, ChunkingConfig
from contexthub.domain.models.document import Document


@dataclass(frozen=True)
class SourceDocumentManifest:
    relative_path: str
    checksum_sha256: str


@dataclass(frozen=True)
class IndexBuildResult:
    document_count: int
    page_count: int
    chunk_count: int
    embedding_count: int
    output_path: Path
    build_duration_ms: int
    manifest_path: Path


class IndexBuilder:
    """Build FAISS, SQLite metadata, and manifest artifacts atomically."""

    def __init__(
        self,
        parser: DocumentParser,
        chunker: Chunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        document_repository: DocumentRepository,
        chunking_config: ChunkingConfig,
        logger: logging.Logger | None = None,
        application_version: str = "1.0.0",
    ) -> None:
        self._parser = parser
        self._chunker = chunker
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        self._document_repository = document_repository
        self._chunking_config = chunking_config
        self._logger = logger or logging.getLogger(__name__)
        self._application_version = application_version

    def build(self, pdf_directory: Path, output_directory: Path) -> IndexBuildResult:
        started = perf_counter()
        pdf_directory = pdf_directory.resolve()
        output_directory = output_directory.resolve()
        pdf_files = self._discover_pdfs(pdf_directory)
        temp_directory = Path(
            mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent)
        )

        try:
            documents: list[Document] = []
            all_chunks: list[Chunk] = []
            source_documents: list[SourceDocumentManifest] = []
            page_count = 0

            for pdf_path in pdf_files:
                checksum = self._sha256_file(pdf_path)
                relative_path = pdf_path.relative_to(pdf_directory).as_posix()
                document_id = uuid5(NAMESPACE_URL, f"{relative_path}:{checksum}")
                normalized_document = self._parser.parse(pdf_path, document_id)
                document = Document(
                    id=document_id,
                    filename=relative_path,
                    title=None,
                    checksum_sha256=checksum,
                    page_count=len(normalized_document.pages),
                    metadata={"relative_path": relative_path},
                )
                chunks = self._chunker.chunk(normalized_document, self._chunking_config)
                documents.append(document)
                all_chunks.extend(chunks)
                source_documents.append(
                    SourceDocumentManifest(relative_path=relative_path, checksum_sha256=checksum)
                )
                page_count += len(normalized_document.pages)

            if not all_chunks:
                raise ConfigurationError("PDF corpus produced no chunks.")

            embeddings = self._embedding_provider.embed_documents(
                [chunk.text for chunk in all_chunks]
            )
            if len(embeddings) != len(all_chunks):
                raise IndexCompatibilityError("Embedding count must equal chunk count.")
            for embedding in embeddings:
                if len(embedding) != self._embedding_provider.dimensions:
                    raise IndexCompatibilityError("Embedding dimension mismatch.")

            self._vector_store.build(embeddings, all_chunks)
            self._vector_store.save(temp_directory)

            faiss_positions = {chunk.id: position for position, chunk in enumerate(all_chunks)}
            self._move_repository_to_temp_directory(temp_directory)
            self._document_repository.initialize_schema()
            self._document_repository.replace_all(documents, all_chunks, faiss_positions)
            if self._document_repository.chunk_count() != len(all_chunks):
                raise IndexCompatibilityError("SQLite chunk count does not match chunk count.")

            manifest_path = temp_directory / "manifest.json"
            manifest = self._manifest(
                documents=documents,
                chunks=all_chunks,
                source_documents=source_documents,
            )
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            self._replace_directory(temp_directory, output_directory)
            result = IndexBuildResult(
                document_count=len(documents),
                page_count=page_count,
                chunk_count=len(all_chunks),
                embedding_count=len(embeddings),
                output_path=output_directory,
                build_duration_ms=round((perf_counter() - started) * 1000),
                manifest_path=output_directory / "manifest.json",
            )
            self._logger.info(
                "index_build_completed",
                extra={
                    "extra_fields": {
                        "document_count": result.document_count,
                        "chunk_count": result.chunk_count,
                        "duration_ms": result.build_duration_ms,
                    }
                },
            )
            return result
        except Exception:
            if temp_directory.exists():
                shutil.rmtree(temp_directory)
            raise

    def _discover_pdfs(self, pdf_directory: Path) -> list[Path]:
        if not pdf_directory.exists() or not pdf_directory.is_dir():
            raise ConfigurationError("PDF directory does not exist.")
        pdf_files = sorted(path for path in pdf_directory.rglob("*.pdf") if path.is_file())
        if not pdf_files:
            raise ConfigurationError("PDF directory contains no PDF files.")
        return pdf_files

    @staticmethod
    def _sha256_file(file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _manifest(
        self,
        documents: list[Document],
        chunks: list[Chunk],
        source_documents: list[SourceDocumentManifest],
    ) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "application_version": self._application_version,
            "built_at": datetime.now(UTC).isoformat(),
            "embedding_provider": "sentence_transformers",
            "embedding_model": self._embedding_provider.model_name,
            "embedding_dimensions": self._embedding_provider.dimensions,
            "vector_index_type": "IndexFlatIP",
            "chunk_size": self._chunking_config.chunk_size,
            "chunk_overlap": self._chunking_config.chunk_overlap,
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "source_documents": [
                {
                    "relative_path": source.relative_path,
                    "checksum_sha256": source.checksum_sha256,
                }
                for source in source_documents
            ],
        }

    def _move_repository_to_temp_directory(self, temp_directory: Path) -> None:
        reopen = getattr(self._document_repository, "reopen", None)
        if callable(reopen):
            cast(Callable[[Path], None], reopen)(temp_directory / "metadata.db")

    @staticmethod
    def _replace_directory(temp_directory: Path, output_directory: Path) -> None:
        backup_directory = output_directory.with_name(f".{output_directory.name}.previous")
        if backup_directory.exists():
            shutil.rmtree(backup_directory)
        if output_directory.exists():
            output_directory.rename(backup_directory)
        try:
            temp_directory.rename(output_directory)
        except Exception:
            if backup_directory.exists() and not output_directory.exists():
                backup_directory.rename(output_directory)
            raise
        if backup_directory.exists():
            shutil.rmtree(backup_directory)
