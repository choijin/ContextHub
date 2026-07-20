# ContextHub

ContextHub is a production-oriented retrieval-augmented generation reference
application. Phase 1 establishes the runnable FastAPI backend foundation and quality
tooling; retrieval, indexing, generation, Streamlit, Docker, and CI are implemented in
later phases.

## Current Phase

Implemented:

- Python 3.12 project metadata for `uv`;
- FastAPI application factory at `contexthub.main:create_app`;
- environment-driven Pydantic settings;
- structured key-value logging setup;
- lifespan startup with a dependency-injection skeleton;
- request ID middleware;
- standard error response schema;
- `GET /health`;
- `GET /ready`;
- pytest, Ruff, and mypy configuration.

Not implemented yet:

- PDF indexing;
- embeddings;
- FAISS;
- SQLite metadata persistence;
- Hugging Face calls;
- `POST /v1/query`;
- Streamlit frontend;
- Docker and GitHub Actions.

## Local Development

Install dependencies:

```bash
uv sync
```

Run the API:

```bash
uv run uvicorn contexthub.main:app --reload
```

Check the foundation endpoints:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Run quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
