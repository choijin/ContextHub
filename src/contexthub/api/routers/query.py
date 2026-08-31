"""Grounded query API route."""

from typing import Annotated

from fastapi import APIRouter, Body, Request

from contexthub.api.schemas import ErrorResponse
from contexthub.application.runtime import RuntimeContainer
from contexthub.domain.exceptions import IndexNotLoadedError
from contexthub.domain.models.answer import Answer
from contexthub.domain.models.query import QueryRequest

router = APIRouter(tags=["query"])

QUERY_EXAMPLES = {
    "answerable": {
        "summary": "Question supported by the indexed corpus",
        "value": {
            "question": "How does a policy deductible affect claim payments?",
            "top_k": 5,
        },
    },
    "unanswerable": {
        "summary": "Question outside the indexed corpus",
        "value": {"question": "What is the capital of South Korea?", "top_k": 5},
    },
}

ANSWERED_RESPONSE_EXAMPLE = {
    "request_id": "2ddc67de-93d3-4c9e-93e2-267e9f107d46",
    "question": "How does a policy deductible affect claim payments?",
    "answer": (
        "A policy deductible reduces the insurer's payment by requiring the policyholder "
        "to absorb losses up to the deductible amount."
    ),
    "status": "answered",
    "citations": [
        {
            "chunk_id": "example-chunk-id",
            "document_name": "loss_data_analytics_2nd_ed.pdf",
            "page_start": 170,
            "page_end": 171,
            "excerpt": "A deductible modifies the amount paid by the insurer for a covered loss.",
        }
    ],
}


@router.post(
    "/v1/query",
    response_model=Answer,
    summary="Ask a grounded document question",
    description=(
        "Retrieves relevant indexed passages, generates an answer from that context, "
        "and returns citations whose metadata is controlled by the application."
    ),
    responses={
        200: {
            "description": "Grounded answer, abstention, or safety refusal.",
            "content": {"application/json": {"example": ANSWERED_RESPONSE_EXAMPLE}},
        },
        422: {"model": ErrorResponse, "description": "The query request is invalid."},
        502: {"model": ErrorResponse, "description": "The LLM returned an unusable response."},
        503: {"model": ErrorResponse, "description": "The runtime or provider is unavailable."},
    },
)
def query_documents(
    request: Request,
    query_request: Annotated[QueryRequest, Body(openapi_examples=QUERY_EXAMPLES)],
) -> Answer:
    runtime_container: RuntimeContainer = request.app.state.runtime_container
    if not runtime_container.ready or runtime_container.query_service is None:
        raise IndexNotLoadedError("Query service is not ready.")
    return runtime_container.query_service.query(query_request)
