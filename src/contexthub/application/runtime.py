"""Runtime dependency state for the Phase 1 backend skeleton."""

from dataclasses import dataclass, field

from contexthub.application.ports.document_repository import DocumentRepository
from contexthub.application.ports.llm_provider import LLMProvider
from contexthub.application.services.query_service import QueryService
from contexthub.application.services.retrieval_service import RetrievalService


@dataclass(frozen=True)
class ReadinessCheck:
    """One readiness check result."""

    name: str
    ready: bool
    detail: str


@dataclass
class RuntimeContainer:
    """Container for dependencies initialized during lifespan startup."""

    initialized: bool = False
    checks: list[ReadinessCheck] = field(default_factory=list)
    retrieval_service: RetrievalService | None = None
    query_service: QueryService | None = None
    document_repository: DocumentRepository | None = None
    llm_provider: LLMProvider | None = None
    manifest: object | None = None

    @property
    def ready(self) -> bool:
        return self.initialized and all(check.ready for check in self.checks)

    def close(self) -> None:
        if self.document_repository is not None:
            self.document_repository.close()
        if self.llm_provider is not None and hasattr(self.llm_provider, "close"):
            self.llm_provider.close()
