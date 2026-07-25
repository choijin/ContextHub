from uuid import uuid4

from contexthub.domain.models.chunk import ChunkingConfig
from contexthub.domain.models.document import DocumentPage, NormalizedDocument
from contexthub.infrastructure.chunking.recursive_chunker import RecursiveChunker


def test_recursive_chunker_is_deterministic() -> None:
    document = _document(["Alpha beta gamma. " * 8])
    config = ChunkingConfig(chunk_size=50, chunk_overlap=12)
    chunker = RecursiveChunker()

    first = chunker.chunk(document, config)
    second = chunker.chunk(document, config)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert [chunk.text for chunk in first] == [chunk.text for chunk in second]


def test_recursive_chunker_produces_no_empty_chunks() -> None:
    chunks = RecursiveChunker().chunk(_document(["  ", "Real text"]), ChunkingConfig())

    assert [chunk.text for chunk in chunks] == ["Real text"]


def test_recursive_chunker_preserves_page_ranges() -> None:
    chunks = RecursiveChunker().chunk(
        _document(["Page one has useful text.", "Page two has more useful text."]),
        ChunkingConfig(chunk_size=200, chunk_overlap=0),
    )

    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2


def test_recursive_chunker_honors_chunk_size_for_long_text() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 5
    chunks = RecursiveChunker().chunk(
        _document([text]),
        ChunkingConfig(chunk_size=30, chunk_overlap=5),
    )

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 30 for chunk in chunks)


def test_recursive_chunker_retains_overlap_content() -> None:
    chunks = RecursiveChunker().chunk(
        _document(["one two three four five six seven eight nine ten"]),
        ChunkingConfig(chunk_size=24, chunk_overlap=10),
    )

    assert len(chunks) > 1
    assert "four" in chunks[1].text or "five" in chunks[1].text


def _document(pages: list[str]) -> NormalizedDocument:
    document_id = uuid4()
    return NormalizedDocument(
        document_id=document_id,
        pages=[
            DocumentPage(document_id=document_id, page_number=index + 1, text=text)
            for index, text in enumerate(pages)
        ],
    )
