from uuid import uuid4

import pytest
from pydantic import ValidationError

from contexthub.domain.models.chunk import Chunk, ChunkingConfig
from contexthub.domain.models.document import DocumentPage, NormalizedDocument


def test_document_pages_are_one_based() -> None:
    with pytest.raises(ValidationError, match="one-based"):
        DocumentPage(document_id=uuid4(), page_number=0, text="text")


def test_normalized_document_rejects_pages_from_another_document() -> None:
    document_id = uuid4()
    other_id = uuid4()

    with pytest.raises(ValidationError, match="all pages"):
        NormalizedDocument(
            document_id=document_id,
            pages=[DocumentPage(document_id=other_id, page_number=1, text="text")],
        )


def test_chunk_config_requires_overlap_smaller_than_size() -> None:
    with pytest.raises(ValidationError, match="chunk_overlap"):
        ChunkingConfig(chunk_size=10, chunk_overlap=10)


def test_chunk_rejects_invalid_page_range() -> None:
    with pytest.raises(ValidationError, match="page_end"):
        Chunk(
            id="chunk",
            document_id=uuid4(),
            text="text",
            chunk_index=0,
            page_start=2,
            page_end=1,
            content_hash="hash",
        )
