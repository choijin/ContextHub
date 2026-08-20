from uuid import uuid4

import pytest

from contexthub.application.services.citation_builder import CitationBuilder
from contexthub.application.services.query_service import (
    INSUFFICIENT_CONTEXT_ANSWER,
    QueryService,
)
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.enums import AnswerStatus
from contexthub.domain.exceptions import LLMProviderResponseError
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.query import QueryRequest, RetrievalResult, RetrievedChunk
from contexthub.infrastructure.prompts.grounded_qa_prompt_builder import GroundedQAPromptBuilder
from tests.fakes.indexing import FakeLLMProvider, FakeRetriever


def test_query_service_returns_fake_llm_answer_with_trusted_citation() -> None:
    retrieved_chunk = _retrieved_chunk("chunk-a", "Probability measures uncertainty.")
    retriever = FakeRetriever(_retrieval_result([retrieved_chunk]))
    llm_provider = FakeLLMProvider(
        '{"answerable": true, "answer": "Probability measures uncertainty.", '
        '"cited_source_indices": [1]}'
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


def test_query_service_logs_invalid_provider_json_preview(caplog: pytest.LogCaptureFixture) -> None:
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider("not json"),
    )

    with pytest.raises(LLMProviderResponseError):
        service.query(QueryRequest(question="What is probability?"))

    record = next(
        record for record in caplog.records if record.message == "llm_provider_invalid_json"
    )
    assert record.extra_fields["response_preview"] == "not json"


def test_query_service_logs_retrieved_chunk_metadata(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "source text")])),
        FakeLLMProvider('{"answerable": true, "answer": "answer", "cited_source_indices": [1]}'),
    )

    answer = service.query(QueryRequest(question="What is probability?"))

    assert answer.status is AnswerStatus.ANSWERED
    record = next(
        record for record in caplog.records if record.message == "query_retrieved_context"
    )
    logged_chunk = record.extra_fields["chunks"][0]
    assert logged_chunk["chunk_id"] == "chunk-a"
    assert logged_chunk["document_name"] == "stats.pdf"
    assert logged_chunk["pages"] == "1-1"
    assert logged_chunk["text_preview"] == "source text"


def test_query_service_rejects_json_wrapped_in_markdown_fence() -> None:
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider(
            '```json\n{"answerable": true, "answer": "answer", "cited_source_indices": [1]}\n```'
        ),
    )

    with pytest.raises(LLMProviderResponseError):
        service.query(QueryRequest(question="What is probability?"))


def test_query_service_rejects_json_with_raw_latex_backslashes() -> None:
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider(
            '{"answer": "Conditional probability is denoted \\(P(A|B)\\).", '
            '"cited_source_indices": [1]}'
        ),
    )

    with pytest.raises(LLMProviderResponseError):
        service.query(QueryRequest(question="What is probability?"))


def test_query_service_unknown_source_index_falls_back_to_prompt_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider('{"answerable": true, "answer": "answer", "cited_source_indices": [2]}'),
    )

    answer = service.query(QueryRequest(question="What is probability?"))

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.answer == "answer"
    assert [citation.chunk_id for citation in answer.citations] == ["chunk-a"]
    record = next(
        record
        for record in caplog.records
        if record.message == "query_citations_fell_back_to_prompt_context"
    )
    assert record.extra_fields["citation_count"] == 1


def test_query_service_ignores_unknown_source_indices_when_valid_citations_remain(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("WARNING")
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        FakeLLMProvider(
            '{"answerable": true, "answer": "answer", "cited_source_indices": [1, 99]}'
        ),
    )

    answer = service.query(QueryRequest(question="What is probability?"))

    assert answer.status is AnswerStatus.ANSWERED
    assert [citation.chunk_id for citation in answer.citations] == ["chunk-a"]
    record = next(
        record for record in caplog.records if record.message == "llm_citation_indices_ignored"
    )
    assert record.extra_fields["returned_source_indices"] == [1, 99]
    assert record.extra_fields["valid_source_indices"] == [1]
    assert record.extra_fields["ignored_source_indices"] == [99]
    assert record.extra_fields["allowed_source_indices"] == [1]


def test_query_service_empty_llm_citations_fall_back_to_prompt_context() -> None:
    service = _service(
        FakeRetriever(
            _retrieval_result(
                [
                    _retrieved_chunk("chunk-a", "alpha"),
                    _retrieved_chunk("chunk-b", "beta"),
                ]
            )
        ),
        FakeLLMProvider('{"answerable": true, "answer": "answer", "cited_source_indices": []}'),
    )

    answer = service.query(QueryRequest(question="What is probability?"))

    assert answer.status is AnswerStatus.ANSWERED
    assert [citation.chunk_id for citation in answer.citations] == ["chunk-a", "chunk-b"]


def test_query_service_llm_unanswerable_returns_insufficient_context() -> None:
    llm_provider = FakeLLMProvider(
        '{"answerable": false, "answer": "", "cited_source_indices": []}'
    )
    service = _service(
        FakeRetriever(_retrieval_result([_retrieved_chunk("chunk-a", "text")])),
        llm_provider,
    )

    answer = service.query(QueryRequest(question="What is the capital of South Korea?"))

    assert answer.status is AnswerStatus.INSUFFICIENT_CONTEXT
    assert answer.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert answer.citations == []
    assert len(llm_provider.calls) == 1


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
