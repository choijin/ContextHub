# ContextHub

ContextHub is a production-oriented retrieval-augmented generation reference
application. Phase 1 established the runnable FastAPI backend foundation and quality
tooling. Phase 2 adds the offline PDF indexing pipeline that builds FAISS vectors,
SQLite metadata, and a manifest.

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
- pytest, Ruff, and mypy configuration;
- provider-independent document, chunk, retrieval, prompt, generation, answer, and
  evaluation models;
- PyMuPDF PDF parser;
- deterministic recursive chunker;
- sentence-transformers embedding adapter;
- FAISS `IndexFlatIP` vector store;
- SQLite document/chunk metadata repository;
- atomic offline index builder;
- `scripts/ingest.py`.

Not implemented yet:

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

Build the offline index from `data/pdfs/`:

```bash
uv run python scripts/ingest.py
```

The generated artifacts are written to `data/index/`:

```text
faiss.index
metadata.db
manifest.json
```

Run quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
