"""LLM provider port for later query phases."""

from typing import Protocol

from contexthub.domain.models.generation import GenerationResult
from contexthub.domain.models.prompt import PromptRequest


class LLMProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def generate(self, prompt: PromptRequest) -> GenerationResult: ...
