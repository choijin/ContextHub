"""Chunker port."""

from typing import Protocol

from contexthub.domain.models.chunk import Chunk, ChunkingConfig
from contexthub.domain.models.document import NormalizedDocument


class Chunker(Protocol):
    def chunk(self, document: NormalizedDocument, config: ChunkingConfig) -> list[Chunk]: ...
