from fastapi.testclient import TestClient

from contexthub.application.runtime import RuntimeContainer
from contexthub.main import create_app
from tests.conftest import make_client, make_settings


def test_ready_returns_200_when_runtime_is_initialized() -> None:
    client: TestClient
    with make_client() as client:
        response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["status"] == "ready"


def test_ready_returns_503_when_runtime_is_uninitialized() -> None:
    app = create_app(make_settings())
    app.state.runtime_container = RuntimeContainer(initialized=False)

    with TestClient(app) as client:
        app.state.runtime_container = RuntimeContainer(initialized=False)
        response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert body["status"] == "not_ready"


def test_ready_reflects_index_not_ready_when_index_required() -> None:
    client: TestClient
    with make_client(allow_start_without_index=False) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert any(check["name"] == "index" for check in body["checks"])
