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
    assert body["request_id"]
