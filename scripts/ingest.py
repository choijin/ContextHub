"""Build the offline ContextHub index."""

import argparse
import logging
import sys
from pathlib import Path

from contexthub.application.services.index_builder import IndexBuilder
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.models.chunk import ChunkingConfig
from contexthub.infrastructure.chunking.recursive_chunker import RecursiveChunker
from contexthub.infrastructure.embeddings.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)
from contexthub.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser
from contexthub.infrastructure.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)
from contexthub.infrastructure.vectorstores.faiss_vector_store import FaissVectorStore
from contexthub.observability.logging import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ContextHub offline index.")
    parser.add_argument("--pdf-directory", type=Path, default=None)
    parser.add_argument("--output-directory", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--chunk-overlap", type=int, default=None)
    args = parser.parse_args(argv)

    settings = ApplicationSettings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    pdf_directory = args.pdf_directory or settings.pdf_directory
    output_directory = args.output_directory or settings.index_directory
    chunk_size = args.chunk_size or settings.chunk_size
    chunk_overlap = args.chunk_overlap if args.chunk_overlap is not None else settings.chunk_overlap
    chunking_config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    repository = SQLiteDocumentRepository(output_directory / "metadata.db")
    try:
        embedding_provider = SentenceTransformerEmbeddingProvider(
            model_name=settings.embedding_model,
            batch_size=settings.embedding_batch_size,
            device=settings.embedding_device,
        )
        vector_store = FaissVectorStore(dimensions=embedding_provider.dimensions)
        builder = IndexBuilder(
            parser=PyMuPDFDocumentParser(),
            chunker=RecursiveChunker(),
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            document_repository=repository,
            chunking_config=chunking_config,
            logger=logging.getLogger("contexthub.ingest"),
            application_version=settings.app_version,
        )
        result = builder.build(pdf_directory, output_directory)
    except Exception as exc:
        logging.getLogger("contexthub.ingest").error(
            "index_build_failed",
            extra={"extra_fields": {"error_code": getattr(exc, "code", "UNKNOWN")}},
        )
        print(f"Index build failed: {exc}", file=sys.stderr)
        return 1
    finally:
        repository.close()

    print(
        "Index build completed: "
        f"documents={result.document_count} "
        f"pages={result.page_count} "
        f"chunks={result.chunk_count} "
        f"embeddings={result.embedding_count} "
        f"output={result.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
