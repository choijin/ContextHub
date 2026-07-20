from fastapi.testclient import TestClient

from tests.conftest import make_client


def test_request_id_header_is_returned_when_provided() -> None:
    client: TestClient
    with make_client() as client:
        response = client.get("/health", headers={"X-Request-ID": "known-request"})

    assert response.headers["X-Request-ID"] == "known-request"
    assert response.json()["request_id"] == "known-request"


def test_request_id_is_generated_when_missing() -> None:
    client: TestClient
    with make_client() as client:
        response = client.get("/health")

    assert response.headers["X-Request-ID"]
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
