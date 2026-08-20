"""Request ID middleware and helpers."""

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from contexthub.observability.timing import Stopwatch

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger("contexthub.http")


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        return request_id
    return "unknown"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and emit one structured trace for every HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request.state.request_id = request_id
        stopwatch = Stopwatch()
        trace_fields = {
            "request_id": request_id,
            "operation": "http_request",
            "method": request.method,
            "path": request.url.path,
        }
        logger.info(
            "request_started",
            extra={"extra_fields": trace_fields},
        )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "extra_fields": {
                        **trace_fields,
                        "duration_ms": stopwatch.elapsed_ms,
                        "status": "error",
                    }
                },
            )
            raise
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_completed",
            extra={
                "extra_fields": {
                    **trace_fields,
                    "duration_ms": stopwatch.elapsed_ms,
                    "status": "success" if response.status_code < 400 else "error",
                    "status_code": response.status_code,
                }
            },
        )
        return response
