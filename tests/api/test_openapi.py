from contexthub.main import create_app
from tests.conftest import make_settings


def test_openapi_documents_operational_and_query_routes() -> None:
    schema = create_app(make_settings()).openapi()

    assert schema["info"]["title"] == "ContextHub"
    assert "retrieval-augmented generation" in schema["info"]["description"]
    assert {tag["name"] for tag in schema["tags"]} == {"health", "readiness", "query"}
    assert schema["paths"]["/health"]["get"]["summary"] == "Check process health"
    assert schema["paths"]["/ready"]["get"]["summary"] == "Check runtime readiness"

    query_operation = schema["paths"]["/v1/query"]["post"]
    assert query_operation["summary"] == "Ask a grounded document question"
    examples = query_operation["requestBody"]["content"]["application/json"]["examples"]
    assert examples["answerable"]["value"]["question"] == "What is conditional probability?"
    response_example = query_operation["responses"]["200"]["content"]["application/json"]["example"]
    assert response_example["status"] == "answered"
    assert response_example["citations"][0]["document_name"] == "probability.pdf"
    assert {"200", "422", "502", "503"} <= set(query_operation["responses"])


def test_cors_is_disabled() -> None:
    app = create_app(make_settings())

    assert all(middleware.cls.__name__ != "CORSMiddleware" for middleware in app.user_middleware)
