"""Exception handlers for stable API error responses."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from contexthub.api.request_id import get_request_id
from contexthub.domain.exceptions import (
    ContextHubError,
    IndexCompatibilityError,
    IndexLoadError,
    IndexNotLoadedError,
    InvalidQueryError,
    LLMProviderAuthenticationError,
    LLMProviderRateLimitError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": get_request_id(request),
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


async def contexthub_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ContextHubError):
        return await unhandled_error_handler(request, exc)
    status_code = 500
    if isinstance(exc, InvalidQueryError):
        status_code = 422
    if isinstance(exc, IndexNotLoadedError | IndexLoadError | IndexCompatibilityError):
        status_code = 503
    if isinstance(
        exc,
        LLMProviderUnavailableError | LLMProviderTimeoutError | LLMProviderRateLimitError,
    ):
        status_code = 503
    if isinstance(exc, LLMProviderAuthenticationError):
        status_code = 500
    return _error_response(request, status_code, exc.code, str(exc))


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_error_handler(request, exc)
    return _error_response(request, 422, "VALIDATION_ERROR", "Request validation failed.")


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")
