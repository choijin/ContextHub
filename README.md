# ContextHub

ContextHub is a production-oriented retrieval-augmented generation reference
application. Phase 1 established the runnable FastAPI backend foundation and quality
tooling. Phase 2 adds the offline PDF indexing pipeline that builds FAISS vectors,
SQLite metadata, and a manifest. Phase 3 adds runtime retrieval. Phase 4 adds a
grounded answer API.

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
- `scripts/ingest.py`;
- runtime retrieval service and `scripts/retrieve.py`;
- grounded prompt builder;
- Hugging Face LLM provider adapter;
- trusted citation builder;
- `POST /v1/query`.

Not implemented yet:

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

Test runtime retrieval without an LLM:

```bash
uv run python scripts/retrieve.py "What is conditional probability?" --top-k 3
```

This prints ranked chunks, similarity scores, chunk IDs, and source page ranges.

Call the grounded query API after building the index and setting
`CONTEXTHUB_HUGGINGFACE_MODEL` plus `CONTEXTHUB_HUGGINGFACE_API_TOKEN`:

```bash
curl -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is conditional probability?", "top_k": 3}'
```

Run quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```
