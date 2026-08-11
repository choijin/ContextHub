"""Grounded query API route."""

from fastapi import APIRouter, Request

from contexthub.application.runtime import RuntimeContainer
from contexthub.domain.exceptions import IndexNotLoadedError
from contexthub.domain.models.answer import Answer
from contexthub.domain.models.query import QueryRequest

router = APIRouter()


@router.post("/v1/query", response_model=Answer)
def query_documents(request: Request, query_request: QueryRequest) -> Answer:
    runtime_container: RuntimeContainer = request.app.state.runtime_container
    if not runtime_container.ready or runtime_container.query_service is None:
        raise IndexNotLoadedError("Query service is not ready.")
    return runtime_container.query_service.query(query_request)
