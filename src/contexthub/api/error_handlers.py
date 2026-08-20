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
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderResponseError,
    LLMProviderTimeoutError,
    LLMProviderUnavailableError,
)


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Request validation failed."

    error = errors[0]
    error_type = str(error.get("type", ""))
    location = error.get("loc", ())
    field = next(
        (
            item
            for item in reversed(location)
            if isinstance(item, str) and item not in {"body", "query", "path"}
        ),
        None,
    )

    if error_type == "json_invalid":
        return "Request body must contain valid JSON."
    if field == "question":
        if error_type == "missing":
            return "The question field is required."
        if error_type in {"string_type", "string_unicode"}:
            return "Question must be text."
        return "Question must not be blank."
    if field == "top_k":
        if error_type in {"int_parsing", "int_type"}:
            return "top_k must be an integer."
        return "top_k must be positive."
    if error_type == "missing" and field is not None:
        return f"The {field} field is required."
    if field is not None:
        return f"The {field} field is invalid."
    return "Request validation failed."


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
    elif isinstance(
        exc,
        IndexNotLoadedError
        | IndexLoadError
        | IndexCompatibilityError
        | LLMProviderUnavailableError
        | LLMProviderTimeoutError
        | LLMProviderRateLimitError,
    ):
        status_code = 503
    elif isinstance(exc, LLMProviderAuthenticationError):
        status_code = 500
    elif isinstance(exc, LLMProviderResponseError | LLMProviderError):
        status_code = 502
    return _error_response(request, status_code, exc.code, str(exc))


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await unhandled_error_handler(request, exc)
    return _error_response(request, 422, "VALIDATION_ERROR", _validation_message(exc))


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")
