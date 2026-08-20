"""Health endpoint."""

from fastapi import APIRouter, Request

from contexthub.api.request_id import get_request_id
from contexthub.api.schemas import HealthResponse
from contexthub.config.settings import ApplicationSettings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check process health",
    description="Confirms that the FastAPI process is running without calling providers.",
)
def health(request: Request) -> HealthResponse:
    settings: ApplicationSettings = request.app.state.settings
    return HealthResponse(
        service=settings.service_name,
        version=settings.app_version,
        request_id=get_request_id(request),
    )
