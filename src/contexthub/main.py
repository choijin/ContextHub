"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from contexthub.api.dependencies import get_runtime_container
from contexthub.api.error_handlers import (
    contexthub_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from contexthub.api.request_id import RequestIDMiddleware
from contexthub.api.routers import health, readiness
from contexthub.config.settings import ApplicationSettings, get_settings
from contexthub.domain.exceptions import ContextHubError
from contexthub.observability.logging import configure_logging


def create_app(settings: ApplicationSettings | None = None) -> FastAPI:
    """Create a configured FastAPI app for production or tests."""

    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(
            resolved_settings.log_level,
            resolved_settings.service_name,
            resolved_settings.environment,
        )
        app.state.runtime_container = get_runtime_container(resolved_settings)
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(ContextHubError, contexthub_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(health.router)
    app.include_router(readiness.router)
    return app


app = create_app()
