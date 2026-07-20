from fastapi.testclient import TestClient

from tests.conftest import make_client


def test_health_returns_200() -> None:
    client: TestClient
    with make_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "contexthub-api"
    assert body["version"] == "1.0.0"
    assert body["request_id"]
