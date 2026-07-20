"""API response schemas used by foundation endpoints."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    request_id: str
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str
    version: str
    request_id: str


class ReadinessCheckResponse(BaseModel):
    name: str
    ready: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    ready: bool
    service: str
    version: str
    request_id: str
    checks: list[ReadinessCheckResponse] = Field(default_factory=list)
