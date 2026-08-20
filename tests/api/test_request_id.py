import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from contexthub.api.request_id import RequestIDMiddleware
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


def test_request_trace_logs_start_and_completion(caplog) -> None:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/trace")
    def trace() -> dict[str, str]:
        return {"status": "ok"}

    caplog.set_level(logging.INFO, logger="contexthub.http")
    with TestClient(app) as client:
        response = client.get("/trace", headers={"X-Request-ID": "trace-request"})

    assert response.status_code == 200
    started = next(record for record in caplog.records if record.message == "request_started")
    completed = next(record for record in caplog.records if record.message == "request_completed")
    assert started.extra_fields == {
        "request_id": "trace-request",
        "operation": "http_request",
        "method": "GET",
        "path": "/trace",
    }
    assert completed.extra_fields["request_id"] == "trace-request"
    assert completed.extra_fields["status_code"] == 200
    assert completed.extra_fields["status"] == "success"
    assert completed.extra_fields["duration_ms"] >= 0
