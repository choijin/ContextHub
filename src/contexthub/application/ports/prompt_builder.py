"""Prompt builder port for later query phases."""

from typing import Protocol

from contexthub.domain.models.prompt import PromptRequest
from contexthub.domain.models.query import RetrievedChunk


class PromptBuilder(Protocol):
    @property
    def prompt_version(self) -> str: ...

    def build(self, question: str, chunks: list[RetrievedChunk]) -> PromptRequest: ...
