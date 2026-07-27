import json
from pathlib import Path

from fastapi.testclient import TestClient

from contexthub.application.runtime import RuntimeContainer
from contexthub.main import create_app
from tests.conftest import make_client, make_settings


def test_ready_returns_200_when_runtime_is_initialized() -> None:
    client: TestClient
    with make_client() as client:
        response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["status"] == "ready"


def test_ready_returns_503_when_runtime_is_uninitialized() -> None:
    app = create_app(make_settings())
    app.state.runtime_container = RuntimeContainer(initialized=False)

    with TestClient(app) as client:
        app.state.runtime_container = RuntimeContainer(initialized=False)
        response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert body["status"] == "not_ready"


def test_ready_reflects_index_not_ready_when_index_required() -> None:
    client: TestClient
    with make_client(
        index_directory=Path("missing-index"),
        allow_start_without_index=False,
    ) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["ready"] is False
    assert any(check["name"] == "index" for check in body["checks"])


def test_ready_returns_503_for_incompatible_manifest(tmp_path: Path) -> None:
    index_directory = tmp_path / "index"
    index_directory.mkdir()
    (index_directory / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "0.0",
                "application_version": "1.0.0",
                "built_at": "2026-01-01T00:00:00+00:00",
                "embedding_provider": "sentence_transformers",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "embedding_dimensions": 384,
                "vector_index_type": "IndexFlatIP",
                "chunk_size": 1000,
                "chunk_overlap": 150,
                "document_count": 1,
                "chunk_count": 1,
                "source_documents": [],
            }
        ),
        encoding="utf-8",
    )
    app = create_app(
        make_settings(
            index_directory=index_directory,
            metadata_database_path=index_directory / "metadata.db",
            allow_start_without_index=False,
        )
    )

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert "schema version" in response.json()["checks"][-1]["detail"]
