from collections.abc import Callable

import httpx
import pytest

from contexthub.domain.exceptions import (
    LLMProviderAuthenticationError,
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)
from contexthub.domain.models.prompt import PromptContext, PromptRequest
from contexthub.infrastructure.llms.huggingface_provider import HuggingFaceLLMProvider


def test_huggingface_provider_returns_generation_result() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        payload = request.read().decode()
        assert request.headers["authorization"] == "Bearer token"
        assert str(request.url) == "https://router.huggingface.co/v1/chat/completions"
        assert '"model":"model"' in payload
        assert '"role":"system"' in payload
        assert '"role":"user"' in payload
        assert '"response_format"' in payload
        assert '"type":"json_schema"' in payload
        assert '"strict":true' in payload
        assert "cited_source_indices" in payload
        assert "chunk-a" in payload
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"answerable":true,"answer":"a","cited_source_indices":[1]}'
                            ),
                        }
                    }
                ]
            },
        )

    provider = _provider(handler)

    result = provider.generate(_prompt())

    assert result.text == '{"answerable":true,"answer":"a","cited_source_indices":[1]}'
    assert result.provider == "huggingface"
    assert result.model == "model"
    assert request_count == 1


def test_huggingface_provider_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    provider = _provider(handler, max_retries=0)

    with pytest.raises(LLMProviderTimeoutError):
        provider.generate(_prompt())


@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [
        (401, LLMProviderAuthenticationError),
        (403, LLMProviderAuthenticationError),
        (429, LLMProviderRateLimitError),
        (503, LLMProviderUnavailableError),
    ],
)
def test_huggingface_provider_maps_provider_outages(
    status_code: int,
    exception_type: type[Exception],
) -> None:
    provider = _provider(lambda request: httpx.Response(status_code, json={"error": "hidden"}))

    with pytest.raises(exception_type):
        provider.generate(_prompt())


def test_huggingface_provider_rejects_malformed_response() -> None:
    provider = _provider(lambda request: httpx.Response(200, json={"unexpected": "shape"}))

    with pytest.raises(LLMProviderResponseError):
        provider.generate(_prompt())


def _provider(
    handler: httpx.MockTransport | Callable[[httpx.Request], httpx.Response],
    max_retries: int = 0,
) -> HuggingFaceLLMProvider:
    transport = (
        handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    )
    return HuggingFaceLLMProvider(
        api_token="token",
        model_name="model",
        timeout_seconds=1.0,
        max_retries=max_retries,
        temperature=0.0,
        max_output_tokens=32,
        client=httpx.Client(transport=transport),
    )


def _prompt() -> PromptRequest:
    return PromptRequest(
        system_prompt="system",
        question="question",
        context=[
            PromptContext(
                source_index=1,
                chunk_id="chunk-a",
                document_name="fixture.pdf",
                page_start=1,
                page_end=1,
                text="source",
            )
        ],
    )
