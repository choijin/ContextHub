from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from contexthub.application.runtime import ReadinessCheck, RuntimeContainer
from contexthub.domain.enums import AnswerStatus
from contexthub.domain.models.answer import Answer, Citation
from contexthub.domain.models.query import QueryRequest
from contexthub.main import create_app
from frontend.streamlit_app import fetch_readiness, submit_question
from tests.conftest import make_settings


class IntegratedQueryService:
    def __init__(self, status: AnswerStatus) -> None:
        self._status = status

    def query(self, request: QueryRequest) -> Answer:
        if self._status is AnswerStatus.ANSWERED:
            return Answer(
                request_id=uuid4(),
                question=request.question,
                answer="Conditional probability updates probability using known information.",
                status=AnswerStatus.ANSWERED,
                citations=[
                    Citation(
                        chunk_id="chunk-a",
                        document_name="probability.pdf",
                        page_start=10,
                        page_end=10,
                        excerpt="Conditional probability incorporates known information.",
                    )
                ],
            )
        return Answer(
            request_id=uuid4(),
            question=request.question,
            answer="The available documents do not provide enough information.",
            status=AnswerStatus.INSUFFICIENT_CONTEXT,
            citations=[],
        )


@pytest.mark.parametrize(
    ("status", "expected_citation_count"),
    [
        (AnswerStatus.ANSWERED, 1),
        (AnswerStatus.INSUFFICIENT_CONTEXT, 0),
    ],
)
def test_streamlit_client_reaches_fastapi_query_flow(
    monkeypatch: pytest.MonkeyPatch,
    status: AnswerStatus,
    expected_citation_count: int,
) -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        app.state.runtime_container = RuntimeContainer(
            initialized=True,
            checks=[ReadinessCheck(name="query_service", ready=True, detail="ready")],
            query_service=IntegratedQueryService(status),
        )
        monkeypatch.setattr(
            "frontend.streamlit_app.httpx.get",
            lambda url, timeout: client.get("/ready"),
        )
        monkeypatch.setattr(
            "frontend.streamlit_app.httpx.post",
            lambda url, json, timeout: client.post("/v1/query", json=json),
        )

        readiness, readiness_error = fetch_readiness("http://api.test")
        payload, query_error = submit_question(
            "http://api.test",
            "What is conditional probability?",
            top_k=5,
        )

    assert readiness_error is None
    assert readiness is not None and readiness["ready"] is True
    assert query_error is None
    assert payload is not None
    assert payload["status"] == status.value
    assert len(payload["citations"]) == expected_citation_count
