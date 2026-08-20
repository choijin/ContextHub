from pathlib import Path
from typing import Any

import httpx
from streamlit.testing.v1 import AppTest

from frontend.streamlit_app import (
    API_BASE_URL_STATE_KEY,
    LAST_ERROR_STATE_KEY,
    LAST_RESPONSE_STATE_KEY,
    QUESTION_STATE_KEY,
    build_api_url,
    citation_heading,
    extract_error_message,
    fetch_readiness,
    initialize_session_state,
    normalize_api_base_url,
    readiness_label,
    store_query_result,
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


def test_session_state_retains_recoverable_query_result() -> None:
    state: dict[str, Any] = {}
    initialize_session_state(state, "http://api.test")
    payload = {
        "status": "answered",
        "answer": "Probability measures uncertainty.",
        "citations": [],
    }

    store_query_result(state, payload, None)
    initialize_session_state(state, "http://different-api.test")

    assert state[API_BASE_URL_STATE_KEY] == "http://api.test"
    assert state[QUESTION_STATE_KEY] == ""
    assert state[LAST_RESPONSE_STATE_KEY] == payload
    assert state[LAST_ERROR_STATE_KEY] is None


def test_streamlit_app_loads_and_preserves_answer_across_reruns() -> None:
    app_path = Path(__file__).parents[2] / "frontend" / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10)

    app.run()
    app.session_state[LAST_RESPONSE_STATE_KEY] = {
        "status": "answered",
        "answer": "Probability measures uncertainty.",
        "citations": [],
    }
    app.run()
    assert "Probability measures uncertainty." in [message.value for message in app.markdown]

    app.run()
    assert "Probability measures uncertainty." in [message.value for message in app.markdown]


def test_streamlit_client_contains_no_backend_imports_or_provider_credentials() -> None:
    source = (Path(__file__).parents[2] / "frontend" / "streamlit_app.py").read_text(
        encoding="utf-8"
    )
    normalized_source = source.lower()

    assert "from contexthub" not in normalized_source
    assert "import contexthub" not in normalized_source
    assert "huggingface_api_token" not in normalized_source
    assert "authorization" not in normalized_source
    assert "bearer " not in normalized_source
