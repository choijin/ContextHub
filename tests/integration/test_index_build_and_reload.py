import json
from pathlib import Path

import pytest

from contexthub.application.services.index_builder import IndexBuilder
from contexthub.infrastructure.chunking.recursive_chunker import RecursiveChunker
from contexthub.infrastructure.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)
from contexthub.infrastructure.vectorstores.faiss_vector_store import FaissVectorStore
from tests.fakes.indexing import (
    FailingVectorStore,
    FakeDocumentParser,
    FakeEmbeddingProvider,
    small_chunking_config,
)


def test_index_builder_writes_reloadable_artifacts(tmp_path: Path) -> None:
    pdf_directory = tmp_path / "pdfs"
    output_directory = tmp_path / "index"
    pdf_directory.mkdir()
    (pdf_directory / "sample.pdf").write_bytes(b"%PDF-pretend")
    repository = SQLiteDocumentRepository(output_directory / "metadata.db")
    builder = _builder(repository, FaissVectorStore(dimensions=3))

    result = builder.build(pdf_directory, output_directory)

    manifest = json.loads((output_directory / "manifest.json").read_text(encoding="utf-8"))
    loaded_store = FaissVectorStore(dimensions=3)
    loaded_store.load(output_directory)
    loaded_repository = SQLiteDocumentRepository(output_directory / "metadata.db", read_only=True)

    assert result.document_count == 1
    assert result.chunk_count == manifest["chunk_count"]
    assert (output_directory / "faiss.index").exists()
    assert (output_directory / "metadata.db").exists()
    assert loaded_store.vector_count == loaded_repository.chunk_count()
    assert loaded_repository.faiss_positions() == list(range(result.chunk_count))
    loaded_repository.close()
    repository.close()


def test_failed_index_build_preserves_previous_index(tmp_path: Path) -> None:
    pdf_directory = tmp_path / "pdfs"
    output_directory = tmp_path / "index"
    pdf_directory.mkdir()
    (pdf_directory / "sample.pdf").write_bytes(b"%PDF-pretend")
    output_directory.mkdir()
    sentinel = output_directory / "manifest.json"
    sentinel.write_text('{"previous": true}', encoding="utf-8")
    repository = SQLiteDocumentRepository(output_directory / "metadata.db")
    builder = _builder(repository, FailingVectorStore())

    with pytest.raises(RuntimeError, match="simulated vector"):
        builder.build(pdf_directory, output_directory)

    assert sentinel.read_text(encoding="utf-8") == '{"previous": true}'
    repository.close()


def _builder(repository, vector_store) -> IndexBuilder:  # type: ignore[no-untyped-def]
    return IndexBuilder(
        parser=FakeDocumentParser(["alpha beta gamma delta epsilon"] * 2),
        chunker=RecursiveChunker(),
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=vector_store,
        document_repository=repository,
        chunking_config=small_chunking_config(),
    )
