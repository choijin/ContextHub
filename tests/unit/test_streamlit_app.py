from typing import Any

import httpx

from frontend.streamlit_app import (
    build_api_url,
    citation_heading,
    extract_error_message,
    fetch_readiness,
    normalize_api_base_url,
    readiness_label,
    submit_question,
)


def test_normalize_api_base_url_uses_default_for_blank_values() -> None:
    assert normalize_api_base_url(None) == "http://127.0.0.1:8000"
    assert normalize_api_base_url("   ") == "http://127.0.0.1:8000"


def test_build_api_url_handles_slashes() -> None:
    assert build_api_url("http://localhost:8000/", "v1/query") == "http://localhost:8000/v1/query"
    assert build_api_url("http://localhost:8000", "/ready") == "http://localhost:8000/ready"


def test_extract_error_message_prefers_standard_api_error() -> None:
    assert (
        extract_error_message({"error": {"code": "INDEX_NOT_LOADED", "message": "not ready"}})
        == "not ready"
    )


def test_readiness_label_formats_known_states() -> None:
    assert readiness_label({"ready": True}) == "API ready"
    assert readiness_label({"ready": False}) == "API not ready"
    assert readiness_label(None) == "Readiness unavailable"


def test_citation_heading_formats_single_and_multi_page_sources() -> None:
    assert (
        citation_heading(
            {"document_name": "stats.pdf", "page_start": 3, "page_end": 3},
            index=1,
        )
        == "Source 1: stats.pdf, page 3"
    )
    assert (
        citation_heading(
            {"document_name": "stats.pdf", "page_start": 3, "page_end": 5},
            index=2,
        )
        == "Source 2: stats.pdf, pages 3-5"
    )


def test_fetch_readiness_returns_payload(monkeypatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        assert url == "http://api.test/ready"
        assert timeout == 30.0
        return httpx.Response(200, json={"ready": True})

    monkeypatch.setattr("frontend.streamlit_app.httpx.get", fake_get)

    payload, error = fetch_readiness("http://api.test")

    assert payload == {"ready": True}
    assert error is None


def test_submit_question_posts_query_payload(monkeypatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        assert url == "http://api.test/v1/query"
        assert json == {"question": "What is probability?", "top_k": 3}
        assert timeout == 30.0
        return httpx.Response(
            200,
            json={
                "status": "answered",
                "answer": "Probability measures uncertainty.",
                "citations": [],
            },
        )

    monkeypatch.setattr("frontend.streamlit_app.httpx.post", fake_post)

    payload, error = submit_question("http://api.test", "What is probability?", 3)

    assert payload is not None
    assert payload["status"] == "answered"
    assert error is None


def test_submit_question_returns_recoverable_error(monkeypatch) -> None:
    def fake_post(url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": {"code": "INDEX_NOT_LOADED", "message": "Query service is not ready."}},
        )

    monkeypatch.setattr("frontend.streamlit_app.httpx.post", fake_post)

    payload, error = submit_question("http://api.test", "What is probability?", 3)

    assert payload is None
    assert error == "Query service is not ready."
