"""Composition helpers for runtime dependencies."""

from contexthub.application.runtime import ReadinessCheck, RuntimeContainer
from contexthub.config.settings import ApplicationSettings


def build_runtime_container(settings: ApplicationSettings) -> RuntimeContainer:
    """Build the Phase 1 dependency container.

    Later phases will add concrete index, repository, embedding, and LLM providers here.
    """

    checks = [
        ReadinessCheck(
            name="settings",
            ready=True,
            detail="Application settings loaded.",
        ),
        ReadinessCheck(
            name="runtime_dependencies",
            ready=True,
            detail="Phase 1 runtime dependency skeleton initialized.",
        ),
    ]

    if not settings.allow_start_without_index:
        checks.append(
            ReadinessCheck(
                name="index",
                ready=False,
                detail="Index loading is implemented in a later phase.",
            )
        )

    return RuntimeContainer(initialized=True, checks=checks)


def get_runtime_container(settings: ApplicationSettings) -> RuntimeContainer:
    return build_runtime_container(settings)
