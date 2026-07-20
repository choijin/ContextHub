"""Readiness endpoint."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from contexthub.api.request_id import get_request_id
from contexthub.api.schemas import ReadinessCheckResponse, ReadinessResponse
from contexthub.application.runtime import RuntimeContainer
from contexthub.config.settings import ApplicationSettings

router = APIRouter(tags=["readiness"])


@router.get("/ready", response_model=ReadinessResponse)
def ready(request: Request) -> ReadinessResponse | JSONResponse:
    settings: ApplicationSettings = request.app.state.settings
    runtime: RuntimeContainer | None = getattr(request.app.state, "runtime_container", None)
    checks = runtime.checks if runtime is not None else []
    is_ready = bool(runtime and runtime.ready)
    response = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        ready=is_ready,
        service=settings.service_name,
        version=settings.app_version,
        request_id=get_request_id(request),
        checks=[ReadinessCheckResponse(**check.__dict__) for check in checks],
    )
    if is_ready:
        return response
    return JSONResponse(status_code=503, content=response.model_dump())
