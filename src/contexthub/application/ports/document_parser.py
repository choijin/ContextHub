"""Document parser port."""

from pathlib import Path
from typing import Protocol
from uuid import UUID

from contexthub.domain.models.document import NormalizedDocument


class DocumentParser(Protocol):
    def parse(self, file_path: Path, document_id: UUID) -> NormalizedDocument: ...
