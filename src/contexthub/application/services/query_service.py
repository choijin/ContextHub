"""Grounded query orchestration service."""

import logging

from pydantic import ValidationError

from contexthub.application.ports.llm_provider import LLMProvider
from contexthub.application.ports.prompt_builder import PromptBuilder
from contexthub.application.ports.retriever import Retriever
from contexthub.application.services.citation_builder import CitationBuilder
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.enums import AnswerStatus
from contexthub.domain.exceptions import CitationValidationError, LLMProviderResponseError
from contexthub.domain.models.answer import Answer
from contexthub.domain.models.llm import LLMAnswer
from contexthub.domain.models.prompt import PromptRequest
from contexthub.domain.models.query import QueryRequest, RetrievalResult
from contexthub.observability.timing import Stopwatch

INSUFFICIENT_CONTEXT_ANSWER = (
    "The available documents do not provide enough information to answer this question."
)
LLM_RESPONSE_PREVIEW_CHARACTERS = 500
RETRIEVED_CHUNK_PREVIEW_CHARACTERS = 240


class QueryService:
    """Run retrieval, prompt construction, generation, and citation validation."""

    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
        citation_builder: CitationBuilder,
        settings: ApplicationSettings,
        logger: logging.Logger | None = None,
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._llm_provider = llm_provider
        self._citation_builder = citation_builder
        self._settings = settings
        self._logger = logger or logging.getLogger(__name__)

    def query(self, request: QueryRequest) -> Answer:
        stopwatch = Stopwatch()
        retrieval_result = self._retriever.retrieve(
            question=request.question,
            top_k=request.top_k,
            similarity_threshold=self._settings.similarity_threshold,
        )
        self._log_retrieved_context(retrieval_result)
        if self._has_insufficient_context(retrieval_result):
            self._log_completed(retrieval_result, AnswerStatus.INSUFFICIENT_CONTEXT, stopwatch)
            return Answer(
                request_id=retrieval_result.request_id,
                question=request.question,
                answer=INSUFFICIENT_CONTEXT_ANSWER,
                status=AnswerStatus.INSUFFICIENT_CONTEXT,
                citations=[],
            )

        prompt = self._prompt_builder.build(request.question, retrieval_result.chunks)
        self._log_prompt_context(retrieval_result, prompt)
        generation = self._llm_provider.generate(prompt)
        llm_answer = self._parse_generation(generation.text, self._logger)
        citation_ids = self._source_indices_to_chunk_ids(
            llm_answer.cited_source_indices,
            prompt,
            retrieval_result,
        )
        citations = self._citation_builder.build(citation_ids, retrieval_result.chunks)
        if not citations:
            raise CitationValidationError("Answered response must include at least one citation.")

        answer = Answer(
            request_id=retrieval_result.request_id,
            question=request.question,
            answer=llm_answer.answer,
            status=AnswerStatus.ANSWERED,
            citations=citations,
        )
        self._log_completed(retrieval_result, answer.status, stopwatch)
        return answer

    def _has_insufficient_context(self, retrieval_result: RetrievalResult) -> bool:
        if not retrieval_result.chunks:
            return True
        threshold = self._settings.similarity_threshold
        if threshold is None:
            return False
        return all(retrieved.score < threshold for retrieved in retrieval_result.chunks)

    @staticmethod
    def _parse_generation(generated_text: str, logger: logging.Logger) -> LLMAnswer:
        try:
            return LLMAnswer.model_validate_json(generated_text)
        except ValidationError as exc:
            QueryService._log_invalid_generation(generated_text, logger)
            raise LLMProviderResponseError(
                "LLM provider returned invalid structured output."
            ) from exc

    @staticmethod
    def _source_indices_to_chunk_ids(
        cited_source_indices: list[int],
        prompt: PromptRequest,
        retrieval_result: RetrievalResult,
    ) -> list[str]:
        prompt_context_by_index = {context.source_index: context for context in prompt.context}
        chunk_ids: list[str] = []
        seen: set[int] = set()
        for source_index in cited_source_indices:
            if source_index in seen:
                continue
            context = prompt_context_by_index.get(source_index)
            if context is None:
                raise CitationValidationError("LLM returned an unknown source index.")
            seen.add(source_index)
            chunk_ids.append(context.chunk_id)

        retrieved_chunk_ids = {retrieved.chunk.id for retrieved in retrieval_result.chunks}
        if any(chunk_id not in retrieved_chunk_ids for chunk_id in chunk_ids):
            raise CitationValidationError("LLM cited a source outside retrieved context.")
        return chunk_ids

    @staticmethod
    def _log_invalid_generation(generated_text: str, logger: logging.Logger) -> None:
        preview = generated_text.strip().replace("\n", "\\n")
        logger.warning(
            "llm_provider_invalid_json",
            extra={
                "extra_fields": {
                    "response_length": len(generated_text),
                    "response_preview": preview[:LLM_RESPONSE_PREVIEW_CHARACTERS],
                }
            },
        )

    def _log_retrieved_context(self, retrieval_result: RetrievalResult) -> None:
        self._logger.info(
            "query_retrieved_context",
            extra={
                "extra_fields": {
                    "request_id": str(retrieval_result.request_id),
                    "chunk_count": len(retrieval_result.chunks),
                    "chunks": [
                        {
                            "rank": retrieved.rank,
                            "score": round(retrieved.score, 4),
                            "chunk_id": retrieved.chunk.id,
                            "document_name": retrieved.document_name,
                            "pages": f"{retrieved.chunk.page_start}-{retrieved.chunk.page_end}",
                            "text_preview": " ".join(retrieved.chunk.text.split())[
                                :RETRIEVED_CHUNK_PREVIEW_CHARACTERS
                            ],
                        }
                        for retrieved in retrieval_result.chunks
                    ],
                }
            },
        )

    def _log_prompt_context(self, retrieval_result: RetrievalResult, prompt: PromptRequest) -> None:
        self._logger.info(
            "query_prompt_built",
            extra={
                "extra_fields": {
                    "request_id": str(retrieval_result.request_id),
                    "system_prompt_characters": len(prompt.system_prompt),
                    "context_block_count": len(prompt.context),
                    "context_chunk_ids": [context.chunk_id for context in prompt.context],
                    "context_source_indices": [context.source_index for context in prompt.context],
                }
            },
        )

    def _log_completed(
        self,
        retrieval_result: RetrievalResult,
        status: AnswerStatus,
        stopwatch: Stopwatch,
    ) -> None:
        self._logger.info(
            "query_completed",
            extra={
                "extra_fields": {
                    "request_id": str(retrieval_result.request_id),
                    "status": status.value,
                    "chunk_count": len(retrieval_result.chunks),
                    "duration_ms": stopwatch.elapsed_ms,
                }
            },
        )
