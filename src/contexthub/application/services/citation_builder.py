"""Build trusted citations from retrieved chunks."""

import logging
import re

from contexthub.domain.exceptions import CitationValidationError
from contexthub.domain.models.answer import Citation
from contexthub.domain.models.prompt import PromptContext
from contexthub.domain.models.query import RetrievalResult, RetrievedChunk


class CitationBuilder:
    """Validate LLM-selected chunk IDs and derive citation metadata locally."""

    def __init__(self, excerpt_characters: int = 300) -> None:
        if excerpt_characters <= 0:
            raise ValueError("excerpt_characters must be positive")
        self._excerpt_characters = excerpt_characters

    def resolve(
        self,
        cited_source_indices: list[int],
        prompt_context: list[PromptContext],
        retrieval_result: RetrievalResult,
        logger: logging.Logger | None = None,
    ) -> list[Citation]:
        """Resolve model selections against trusted sources, with context fallback."""
        self_logger = logger or logging.getLogger(__name__)
        citation_ids = self._source_indices_to_chunk_ids(
            cited_source_indices, prompt_context, retrieval_result, self_logger
        )
        if not citation_ids:
            citation_ids = self._prompt_context_chunk_ids(prompt_context, retrieval_result)
            self_logger.info(
                "query_citations_fell_back_to_prompt_context",
                extra={
                    "extra_fields": {
                        "request_id": str(retrieval_result.request_id),
                        "citation_count": len(citation_ids),
                    }
                },
            )
        return self.build(citation_ids, retrieval_result.chunks)

    def _source_indices_to_chunk_ids(
        self,
        cited_source_indices: list[int],
        prompt_context: list[PromptContext],
        retrieval_result: RetrievalResult,
        logger: logging.Logger,
    ) -> list[str]:
        prompt_context_by_index = {context.source_index: context for context in prompt_context}
        retrieved_chunk_ids = {retrieved.chunk.id for retrieved in retrieval_result.chunks}
        chunk_ids: list[str] = []
        seen: set[int] = set()
        ignored_source_indices: list[int] = []
        for source_index in cited_source_indices:
            if source_index in seen:
                continue
            context = prompt_context_by_index.get(source_index)
            if context is None:
                ignored_source_indices.append(source_index)
                seen.add(source_index)
                continue
            seen.add(source_index)
            if context.chunk_id not in retrieved_chunk_ids:
                ignored_source_indices.append(source_index)
                continue
            chunk_ids.append(context.chunk_id)

        if ignored_source_indices:
            logger.warning(
                "llm_citation_indices_ignored",
                extra={
                    "extra_fields": {
                        "request_id": str(retrieval_result.request_id),
                        "returned_source_indices": cited_source_indices,
                        "valid_source_indices": [
                            source_index
                            for source_index, context in prompt_context_by_index.items()
                            if context.chunk_id in chunk_ids
                        ],
                        "ignored_source_indices": ignored_source_indices,
                        "allowed_source_indices": sorted(prompt_context_by_index),
                    }
                },
            )
        return chunk_ids

    @staticmethod
    def _prompt_context_chunk_ids(
        prompt_context: list[PromptContext],
        retrieval_result: RetrievalResult,
    ) -> list[str]:
        retrieved_chunk_ids = {retrieved.chunk.id for retrieved in retrieval_result.chunks}
        chunk_ids: list[str] = []
        seen: set[str] = set()
        for context in sorted(
            prompt_context,
            key=lambda prompt_context: prompt_context.source_index,
        ):
            if context.chunk_id in seen or context.chunk_id not in retrieved_chunk_ids:
                continue
            seen.add(context.chunk_id)
            chunk_ids.append(context.chunk_id)
        return chunk_ids

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
