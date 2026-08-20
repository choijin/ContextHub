"""API response schemas used by operational endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Safe user-facing error message.")


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "request_id": "2ddc67de-93d3-4c9e-93e2-267e9f107d46",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Question must not be blank.",
                    },
                }
            ]
        }
    )

    request_id: str = Field(description="Request trace identifier.")
    error: ErrorDetail


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "healthy",
                    "service": "contexthub-api",
                    "version": "1.0.0",
                    "request_id": "2ddc67de-93d3-4c9e-93e2-267e9f107d46",
                }
            ]
        }
    )

    status: str = "healthy"
    service: str
    version: str
    request_id: str


class ReadinessCheckResponse(BaseModel):
    name: str
    ready: bool
    detail: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ready",
                    "ready": True,
                    "service": "contexthub-api",
                    "version": "1.0.0",
                    "request_id": "2ddc67de-93d3-4c9e-93e2-267e9f107d46",
                    "checks": [
                        {
                            "name": "manifest",
                            "ready": True,
                            "detail": "Index manifest loaded.",
                        }
                    ],
                }
            ]
        }
    )

    status: str
    ready: bool
    service: str
    version: str
    request_id: str
    checks: list[ReadinessCheckResponse] = Field(default_factory=list)
