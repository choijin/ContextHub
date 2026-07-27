"""Provider-independent enumerations."""

from enum import StrEnum


class SourceType(StrEnum):
    PDF = "pdf"


class RetrievalStrategy(StrEnum):
    SIMILARITY = "similarity"


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    PROVIDER_ERROR = "provider_error"
