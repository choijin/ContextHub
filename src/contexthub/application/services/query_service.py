"""Grounded query orchestration service."""

import json
import logging
from typing import Any

from contexthub.application.ports.llm_provider import LLMProvider
from contexthub.application.ports.prompt_builder import PromptBuilder
from contexthub.application.ports.retriever import Retriever
from contexthub.application.services.citation_builder import CitationBuilder
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.enums import AnswerStatus
from contexthub.domain.exceptions import CitationValidationError, LLMProviderResponseError
from contexthub.domain.models.answer import Answer
from contexthub.domain.models.query import QueryRequest, RetrievalResult
from contexthub.observability.timing import Stopwatch

INSUFFICIENT_CONTEXT_ANSWER = (
    "The available documents do not provide enough information to answer this question."
)


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
        generation = self._llm_provider.generate(prompt)
        parsed = self._parse_generation(generation.text)
        citations = self._citation_builder.build(parsed["citation_ids"], retrieval_result.chunks)
        if not citations:
            raise CitationValidationError("Answered response must include at least one citation.")

        answer = Answer(
            request_id=retrieval_result.request_id,
            question=request.question,
            answer=parsed["answer"],
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
    def _parse_generation(generated_text: str) -> dict[str, Any]:
        try:
            parsed = json.loads(generated_text)
        except json.JSONDecodeError as exc:
            raise LLMProviderResponseError("LLM provider returned invalid JSON.") from exc

        if not isinstance(parsed, dict):
            raise LLMProviderResponseError("LLM provider returned an invalid response shape.")

        answer = parsed.get("answer")
        citation_ids = parsed.get("citation_ids")
        if not isinstance(answer, str) or not answer.strip():
            raise LLMProviderResponseError("LLM provider response is missing an answer.")
        if not isinstance(citation_ids, list) or not all(
            isinstance(citation_id, str) for citation_id in citation_ids
        ):
            raise LLMProviderResponseError("LLM provider response has invalid citation IDs.")

        return {"answer": answer.strip(), "citation_ids": citation_ids}

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
