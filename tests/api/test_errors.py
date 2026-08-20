from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from contexthub.domain.exceptions import IndexNotLoadedError
from contexthub.main import create_app
from tests.conftest import make_settings


class DemoPayload(BaseModel):
    name: str = Field(min_length=1)


def test_context_errors_use_standard_schema() -> None:
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise IndexNotLoadedError("Index is unavailable.")

    app = create_app(make_settings())
    app.include_router(router)

    with TestClient(app) as client:
        response = client.get("/boom", headers={"X-Request-ID": "req-test"})

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "req-test"
    assert response.json() == {
        "request_id": "req-test",
        "error": {
            "code": "INDEX_NOT_LOADED",
            "message": "Index is unavailable.",
        },
    }


def test_validation_errors_use_standard_schema() -> None:
    router = APIRouter()

    @router.post("/payload")
    def payload(_: DemoPayload) -> dict[str, str]:
        return {"ok": "true"}

    app = create_app(make_settings())
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post("/payload", json={"name": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "The name field is invalid."
    assert body["request_id"]


def test_query_validation_error_explains_missing_question() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        response = client.post("/v1/query", json={"top_k": 5})

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "The question field is required."


def test_query_validation_error_explains_blank_question() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        response = client.post("/v1/query", json={"question": "   ", "top_k": 5})

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Question must not be blank."


def test_query_validation_error_explains_invalid_top_k() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        response = client.post(
            "/v1/query",
            json={"question": "What is probability?", "top_k": "many"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "top_k must be an integer."


def test_query_validation_error_explains_malformed_json() -> None:
    app = create_app(make_settings())

    with TestClient(app) as client:
        response = client.post(
            "/v1/query",
            content=b'{"question":',
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Request body must contain valid JSON."
