from uuid import uuid4

import pytest

from contexthub.application.services.citation_builder import CitationBuilder
from contexthub.application.services.query_service import (
    INSUFFICIENT_CONTEXT_ANSWER,
    QueryService,
)
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.enums import AnswerStatus
from contexthub.domain.exceptions import CitationValidationError, LLMProviderResponseError
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.query import QueryRequest, RetrievalResult, RetrievedChunk
from contexthub.infrastructure.prompts.grounded_qa_prompt_builder import GroundedQAPromptBuilder
from tests.fakes.indexing import FakeLLMProvider, FakeRetriever


def test_query_service_returns_fake_llm_answer_with_trusted_citation() -> None:
    retrieved_chunk = _retrieved_chunk("chunk-a", "Probability measures uncertainty.")
    retriever = FakeRetriever(_retrieval_result([retrieved_chunk]))
    llm_provider = FakeLLMProvider(
        '{"answer": "Probability measures uncertainty.", "citation_ids": ["chunk-a"]}'
    )
    service = _service(retriever, llm_provider)

    answer = service.query(QueryRequest(question="What is probability?"))

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.answer == "Probability measures uncertainty."
    assert answer.citations[0].chunk_id == "chunk-a"
    assert answer.citations[0].document_name == "stats.pdf"
    assert len(llm_provider.calls) == 1


def test_query_service_invalid_provider_json_fails_safely() -> None:
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider("not json"),
    )

    with pytest.raises(LLMProviderResponseError):
        service.query(QueryRequest(question="What is probability?"))


def test_query_service_unknown_citation_fails_safely() -> None:
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider('{"answer": "answer", "citation_ids": ["missing"]}'),
    )

    with pytest.raises(CitationValidationError):
        service.query(QueryRequest(question="What is probability?"))


def test_query_service_empty_retrieval_abstains_without_calling_llm() -> None:
    llm_provider = FakeLLMProvider()
    service = _service(FakeRetriever(_retrieval_result([])), llm_provider)

    answer = service.query(QueryRequest(question="What is probability?"))

    assert answer.status is AnswerStatus.INSUFFICIENT_CONTEXT
    assert answer.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert answer.citations == []
    assert llm_provider.calls == []


def _service(retriever: FakeRetriever, llm_provider: FakeLLMProvider) -> QueryService:
    return QueryService(
        retriever=retriever,
        prompt_builder=GroundedQAPromptBuilder(max_context_characters=2000),
        llm_provider=llm_provider,
        citation_builder=CitationBuilder(),
        settings=ApplicationSettings(
            huggingface_model="test-model",
            huggingface_api_token="test-token",
        ),
    )


def _retrieval_result(chunks: list[RetrievedChunk]) -> RetrievalResult:
    return RetrievalResult(
        request_id=uuid4(),
        query="What is probability?",
        chunks=chunks,
        retrieval_duration_ms=1,
    )


def _retrieved_chunk(chunk_id: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=chunk_id,
            document_id=uuid4(),
            text=text,
            chunk_index=0,
            page_start=1,
            page_end=1,
            content_hash="hash",
        ),
        score=0.9,
        rank=1,
        document_name="stats.pdf",
    )
