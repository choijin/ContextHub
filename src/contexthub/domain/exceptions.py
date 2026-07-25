"""Stable application exceptions for API error mapping."""


class ContextHubError(Exception):
    """Base class for expected ContextHub failures."""

    code = "CONTEXTHUB_ERROR"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class ConfigurationError(ContextHubError):
    """Raised when application configuration is invalid."""

    code = "CONFIGURATION_ERROR"


class DocumentParsingError(ContextHubError):
    """Raised when a document cannot be parsed."""

    code = "DOCUMENT_PARSING_ERROR"


class ChunkingError(ContextHubError):
    """Raised when document chunking fails."""

    code = "CHUNKING_ERROR"


class EmbeddingProviderError(ContextHubError):
    """Raised when embedding generation fails."""

    code = "EMBEDDING_PROVIDER_ERROR"


class VectorStoreError(ContextHubError):
    """Raised when vector-store operations fail."""

    code = "VECTOR_STORE_ERROR"


class RepositoryError(ContextHubError):
    """Raised when metadata persistence fails."""

    code = "REPOSITORY_ERROR"


class IndexNotLoadedError(ContextHubError):
    """Raised when runtime dependencies required for querying are unavailable."""

    code = "INDEX_NOT_LOADED"


class IndexLoadError(ContextHubError):
    """Raised when a saved index cannot be loaded."""

    code = "INDEX_LOAD_ERROR"


class IndexCompatibilityError(ContextHubError):
    """Raised when index artifacts are incompatible."""

    code = "INDEX_COMPATIBILITY_ERROR"


class InvalidQueryError(ContextHubError):
    """Raised when a query cannot be processed."""

    code = "INVALID_QUERY"


class InsufficientContextError(ContextHubError):
    """Raised when retrieved context cannot answer a query."""

    code = "INSUFFICIENT_CONTEXT"


class LLMProviderError(ContextHubError):
    """Raised when an LLM provider fails."""

    code = "LLM_PROVIDER_ERROR"


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when an LLM provider times out."""

    code = "LLM_PROVIDER_TIMEOUT"


class LLMProviderAuthenticationError(LLMProviderError):
    """Raised when LLM credentials are invalid."""

    code = "LLM_PROVIDER_AUTHENTICATION_ERROR"


class LLMProviderRateLimitError(LLMProviderError):
    """Raised when an LLM provider rate-limits requests."""

    code = "LLM_PROVIDER_RATE_LIMIT"


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when an LLM provider is unavailable."""

    code = "LLM_PROVIDER_UNAVAILABLE"


class LLMProviderResponseError(LLMProviderError):
    """Raised when an LLM provider returns malformed output."""

    code = "LLM_PROVIDER_RESPONSE_ERROR"


class CitationValidationError(ContextHubError):
    """Raised when generated citations are invalid."""

    code = "CITATION_VALIDATION_ERROR"
