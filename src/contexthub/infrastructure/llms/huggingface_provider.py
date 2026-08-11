"""Hugging Face Inference API LLM provider."""

import time
from typing import Any

import httpx

from contexthub.domain.exceptions import (
    LLMProviderAuthenticationError,
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)
from contexthub.domain.models.generation import GenerationResult
from contexthub.domain.models.prompt import PromptRequest
from contexthub.observability.timing import Stopwatch


class HuggingFaceLLMProvider:
    """Synchronous Hugging Face adapter behind the LLMProvider port."""

    provider_name = "huggingface"

    def __init__(
        self,
        api_token: str,
        model_name: str,
        timeout_seconds: float,
        max_retries: int,
        temperature: float,
        max_output_tokens: int,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_token.strip():
            raise LLMProviderAuthenticationError("Hugging Face API token is required.")
        if not model_name.strip():
            raise LLMProviderError("Hugging Face model is required.")
        self._api_token = api_token
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: PromptRequest) -> GenerationResult:
        stopwatch = Stopwatch()
        payload = {
            "inputs": self._render_prompt(prompt),
            "parameters": {
                "temperature": self._temperature,
                "max_new_tokens": self._max_output_tokens,
                "return_full_text": False,
            },
        }
        response = self._post_with_retries(payload)
        generated_text = self._extract_generated_text(response)
        return GenerationResult(
            text=generated_text,
            provider=self.provider_name,
            model=self.model_name,
            duration_ms=stopwatch.elapsed_ms,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _post_with_retries(self, payload: dict[str, Any]) -> Any:
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.post(
                    f"https://api-inference.huggingface.co/models/{self._model_name}",
                    headers={"Authorization": f"Bearer {self._api_token}"},
                    json=payload,
                    timeout=self._timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                if attempt == attempts - 1:
                    raise LLMProviderTimeoutError("LLM provider timed out.") from exc
                self._sleep_before_retry(attempt)
                continue
            except httpx.HTTPError as exc:
                raise LLMProviderError("LLM provider request failed.") from exc

            if response.status_code in {401, 403}:
                raise LLMProviderAuthenticationError("LLM provider authentication failed.")
            if response.status_code == 429:
                if attempt == attempts - 1:
                    raise LLMProviderRateLimitError("LLM provider rate limit exceeded.")
                self._sleep_before_retry(attempt)
                continue
            if 500 <= response.status_code <= 599:
                if attempt == attempts - 1:
                    raise LLMProviderUnavailableError("LLM provider is unavailable.")
                self._sleep_before_retry(attempt)
                continue
            if response.status_code >= 400:
                raise LLMProviderError("LLM provider request was rejected.")

            try:
                return response.json()
            except ValueError as exc:
                raise LLMProviderResponseError("LLM provider returned malformed JSON.") from exc

        raise LLMProviderUnavailableError("LLM provider is unavailable.")

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        time.sleep(min(2.0, 0.25 * (2**attempt)))

    @classmethod
    def _extract_generated_text(cls, response_json: Any) -> str:
        generated_text: object
        if isinstance(response_json, list) and response_json:
            first = response_json[0]
            if not isinstance(first, dict):
                raise LLMProviderResponseError("LLM provider response is malformed.")
            generated_text = first.get("generated_text")
        elif isinstance(response_json, dict):
            generated_text = response_json.get("generated_text")
            if generated_text is None and isinstance(response_json.get("choices"), list):
                generated_text = cls._extract_choice_text(response_json["choices"])
        else:
            raise LLMProviderResponseError("LLM provider response is malformed.")

        if not isinstance(generated_text, str) or not generated_text.strip():
            raise LLMProviderResponseError("LLM provider response did not include text.")
        return generated_text.strip()

    @staticmethod
    def _extract_choice_text(choices: object) -> object:
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        message = first.get("message")
        if isinstance(message, dict):
            return message.get("content")
        return first.get("text")

    @staticmethod
    def _render_prompt(prompt: PromptRequest) -> str:
        context_blocks = [
            (
                "<CONTEXT_BLOCK>\n"
                f"chunk_id: {context.chunk_id}\n"
                f"document: {context.document_name}\n"
                f"pages: {context.page_start}-{context.page_end}\n"
                "text:\n"
                f"{context.text}\n"
                "</CONTEXT_BLOCK>"
            )
            for context in prompt.context
        ]
        context_text = "\n\n".join(context_blocks) if context_blocks else "No context provided."
        return (
            f"{prompt.system_prompt}\n\n"
            f"Question:\n{prompt.question}\n\n"
            f"Context:\n{context_text}\n\n"
            "Return only the required JSON object."
        )
