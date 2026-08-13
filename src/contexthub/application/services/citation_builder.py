"""Build trusted citations from retrieved chunks."""

import re

from contexthub.domain.exceptions import CitationValidationError
from contexthub.domain.models.answer import Citation
from contexthub.domain.models.query import RetrievedChunk


class CitationBuilder:
    """Validate LLM-selected chunk IDs and derive citation metadata locally."""

    def __init__(self, excerpt_characters: int = 300) -> None:
        if excerpt_characters <= 0:
            raise ValueError("excerpt_characters must be positive")
        self._excerpt_characters = excerpt_characters

    def build(
        self,
        citation_ids: list[str],
        retrieved_chunks: list[RetrievedChunk],
    ) -> list[Citation]:
        by_chunk_id = {retrieved.chunk.id: retrieved for retrieved in retrieved_chunks}
        citations: list[Citation] = []
        seen: set[str] = set()

        for chunk_id in citation_ids:
            normalized_chunk_id = chunk_id.strip()
            if not normalized_chunk_id or normalized_chunk_id in seen:
                continue
            retrieved = by_chunk_id.get(normalized_chunk_id)
            if retrieved is None:
                raise CitationValidationError("LLM returned an unknown citation ID.")

            seen.add(normalized_chunk_id)
            chunk = retrieved.chunk
            citations.append(
                Citation(
                    chunk_id=chunk.id,
                    document_name=retrieved.document_name,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    excerpt=self._excerpt(chunk.text),
                )
            )

        return citations

    def _excerpt(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= self._excerpt_characters:
            return normalized
        return f"{normalized[: self._excerpt_characters - 3].rstrip()}..."
