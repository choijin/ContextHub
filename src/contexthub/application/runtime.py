"""Runtime dependency state for the Phase 1 backend skeleton."""

from dataclasses import dataclass, field


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

    @property
    def ready(self) -> bool:
        return self.initialized and all(check.ready for check in self.checks)
