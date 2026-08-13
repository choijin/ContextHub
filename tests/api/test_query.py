from uuid import uuid4

from fastapi.testclient import TestClient

from contexthub.application.runtime import ReadinessCheck, RuntimeContainer
from contexthub.domain.enums import AnswerStatus
from contexthub.domain.exceptions import LLMProviderUnavailableError
from contexthub.domain.models.answer import Answer, Citation
from contexthub.domain.models.query import QueryRequest
from contexthub.main import create_app
from tests.conftest import make_settings


def test_query_route_returns_answer_from_query_service() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        app.state.runtime_container = RuntimeContainer(
            initialized=True,
            checks=[ReadinessCheck(name="query_service", ready=True, detail="ready")],
            query_service=FakeQueryService(),
        )
        response = client.post("/v1/query", json={"question": "What is probability?", "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["citations"][0]["chunk_id"] == "chunk-a"


def test_query_route_rejects_when_runtime_not_ready() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        app.state.runtime_container = RuntimeContainer(initialized=True)
        response = client.post("/v1/query", json={"question": "What is probability?"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INDEX_NOT_LOADED"


def test_query_route_maps_provider_unavailable() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        app.state.runtime_container = RuntimeContainer(
            initialized=True,
            checks=[ReadinessCheck(name="query_service", ready=True, detail="ready")],
            query_service=FailingQueryService(),
        )
        response = client.post("/v1/query", json={"question": "What is probability?"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_PROVIDER_UNAVAILABLE"


def test_upload_route_is_not_implemented_in_phase_4() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        response = client.post("/v1/upload", files={"file": ("x.pdf", b"%PDF")})

    assert response.status_code == 404


class FakeQueryService:
    def query(self, request: QueryRequest) -> Answer:
        return Answer(
            request_id=uuid4(),
            question=request.question,
            answer="Probability measures uncertainty.",
            status=AnswerStatus.ANSWERED,
            citations=[
                Citation(
                    chunk_id="chunk-a",
                    document_name="stats.pdf",
                    page_start=1,
                    page_end=1,
                    excerpt="Probability measures uncertainty.",
                )
            ],
        )


class FailingQueryService:
    def query(self, request: QueryRequest) -> Answer:
        raise LLMProviderUnavailableError("LLM provider is unavailable.")
