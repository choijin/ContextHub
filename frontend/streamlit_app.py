"""Streamlit demonstration client for ContextHub."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
API_BASE_URL_ENV = "CONTEXTHUB_API_BASE_URL"
REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_TOP_K = 5


def normalize_api_base_url(value: str | None) -> str:
    raw_value = (value or DEFAULT_API_BASE_URL).strip()
    return raw_value.rstrip("/") or DEFAULT_API_BASE_URL


def build_api_url(api_base_url: str, path: str) -> str:
    normalized_base = normalize_api_base_url(api_base_url)
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base}{normalized_path}"


def extract_error_message(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message
    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail
    return "The request failed. Please try again."


def readiness_label(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "Readiness unavailable"
    ready = payload.get("ready")
    if ready is True:
        return "API ready"
    if ready is False:
        return "API not ready"
    return "Readiness unavailable"


def citation_heading(citation: dict[str, Any], index: int) -> str:
    document_name = citation.get("document_name") or "Unknown document"
    page_start = citation.get("page_start")
    page_end = citation.get("page_end")
    if isinstance(page_start, int) and isinstance(page_end, int):
        page_label = (
            f"pages {page_start}-{page_end}" if page_start != page_end else f"page {page_start}"
        )
    else:
        page_label = "pages unavailable"
    return f"Source {index}: {document_name}, {page_label}"


def fetch_readiness(api_base_url: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        response = httpx.get(
            build_api_url(api_base_url, "/ready"),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return None, f"Could not reach the API readiness endpoint: {exc}"

    try:
        payload = response.json()
    except ValueError:
        return None, "The readiness endpoint returned an invalid response."

    if response.status_code >= 500:
        return payload, extract_error_message(payload)
    return payload, None


def submit_question(
    api_base_url: str,
    question: str,
    top_k: int,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        response = httpx.post(
            build_api_url(api_base_url, "/v1/query"),
            json={"question": question, "top_k": top_k},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return None, f"Could not reach the API: {exc}"

    try:
        payload = response.json()
    except ValueError:
        return None, "The API returned an invalid response."

    if response.status_code >= 400:
        return None, extract_error_message(payload)
    return payload, None


def render_answer(payload: dict[str, Any]) -> None:
    status = payload.get("status")
    answer = payload.get("answer")
    citations = payload.get("citations")

    if status == "answered":
        st.subheader("Answer")
        st.write(answer or "No answer text was returned.")
        render_citations(citations if isinstance(citations, list) else [])
        return

    if status == "insufficient_context":
        st.info(answer or "The available documents do not provide enough information.")
        return

    if status == "refused":
        st.warning(answer or "This question was refused by the safety guardrails.")
        return

    st.warning(answer or "The API returned an unknown answer status.")


def render_citations(citations: list[Any]) -> None:
    if not citations:
        st.caption("No citations were returned.")
        return

    st.subheader("Sources Used")
    for index, citation in enumerate(citations, start=1):
        if not isinstance(citation, dict):
            continue
        with st.container(border=True):
            st.markdown(f"**{citation_heading(citation, index)}**")
            excerpt = citation.get("excerpt")
            if isinstance(excerpt, str) and excerpt.strip():
                st.write(excerpt)
            chunk_id = citation.get("chunk_id")
            if isinstance(chunk_id, str) and chunk_id.strip():
                st.caption(f"chunk_id: {chunk_id}")


def render_readiness(api_base_url: str) -> None:
    payload, error = fetch_readiness(api_base_url)
    label = readiness_label(payload)
    if payload and payload.get("ready") is True:
        st.sidebar.success(label)
    elif payload and payload.get("ready") is False:
        st.sidebar.warning(label)
    else:
        st.sidebar.info(label)

    if error:
        st.sidebar.caption(error)
    if payload and isinstance(payload.get("checks"), list):
        with st.sidebar.expander("Readiness checks", expanded=False):
            for check in payload["checks"]:
                if not isinstance(check, dict):
                    continue
                name = check.get("name", "check")
                ready = "ready" if check.get("ready") else "not ready"
                detail = check.get("detail", "")
                st.caption(f"{name}: {ready}. {detail}")


def main() -> None:
    st.set_page_config(page_title="ContextHub", layout="centered")

    api_base_url = normalize_api_base_url(os.getenv(API_BASE_URL_ENV))

    st.title("ContextHub")
    st.caption("Production-oriented retrieval-augmented generation reference application.")
    st.write(
        "Ask questions against the indexed PDF corpus. ContextHub retrieves trusted "
        "document chunks, generates a grounded answer through the FastAPI backend, "
        "and displays citations returned by the API."
    )

    st.sidebar.header("API")
    api_base_url = normalize_api_base_url(
        st.sidebar.text_input("FastAPI base URL", value=api_base_url)
    )
    render_readiness(api_base_url)

    with st.form("question_form"):
        question = st.text_area(
            "Question",
            placeholder="What is conditional probability?",
            height=120,
        )
        submitted = st.form_submit_button("Submit")

    if not submitted:
        return

    normalized_question = question.strip()
    if not normalized_question:
        st.error("Enter a question before submitting.")
        return

    with st.spinner("Querying ContextHub..."):
        payload, error = submit_question(api_base_url, normalized_question, DEFAULT_TOP_K)

    if error:
        st.error(error)
        return
    if payload is None:
        st.error("The API did not return a response.")
        return

    render_answer(payload)


if __name__ == "__main__":
    main()
