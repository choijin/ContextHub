"""Stable application exceptions for API error mapping."""


class ContextHubError(Exception):
    """Base class for expected ContextHub failures."""

    code = "CONTEXTHUB_ERROR"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class ConfigurationError(ContextHubError):
    """Raised when application configuration is invalid."""

    code = "CONFIGURATION_ERROR"


class IndexNotLoadedError(ContextHubError):
    """Raised when runtime dependencies required for querying are unavailable."""

    code = "INDEX_NOT_LOADED"


class InvalidQueryError(ContextHubError):
    """Raised when a query cannot be processed."""

    code = "INVALID_QUERY"
