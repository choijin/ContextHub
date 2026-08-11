from uuid import uuid4

import pytest

from contexthub.application.services.citation_builder import CitationBuilder
from contexthub.domain.exceptions import CitationValidationError
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.query import RetrievedChunk


def test_citation_builder_preserves_order_deduplicates_and_truncates_excerpts() -> None:
    chunks = [
        _retrieved_chunk("chunk-a", "alpha " * 20, rank=1),
        _retrieved_chunk("chunk-b", "beta source", rank=2),
    ]
    builder = CitationBuilder(excerpt_characters=20)

    citations = builder.build(["chunk-b", "chunk-a", "chunk-b"], chunks)

    assert [citation.chunk_id for citation in citations] == ["chunk-b", "chunk-a"]
    assert citations[0].document_name == "fixture.pdf"
    assert citations[0].page_start == 2
    assert citations[1].excerpt.endswith("...")
    assert len(citations[1].excerpt) <= 20


def test_citation_builder_rejects_unknown_chunk_ids() -> None:
    builder = CitationBuilder()

    with pytest.raises(CitationValidationError, match="unknown"):
        builder.build(["missing"], [_retrieved_chunk("chunk-a", "alpha", rank=1)])


def _retrieved_chunk(chunk_id: str, text: str, rank: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=chunk_id,
            document_id=uuid4(),
            text=text,
            chunk_index=rank - 1,
            page_start=rank,
            page_end=rank,
            content_hash=f"hash-{rank}",
        ),
        score=0.9,
        rank=rank,
        document_name="fixture.pdf",
    )
