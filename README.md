# ContextHub

ContextHub is a production-oriented retrieval-augmented generation (RAG) reference
application. It indexes a fixed PDF corpus offline, retrieves relevant passages with
sentence-transformer embeddings and FAISS, generates a grounded answer through a
Hugging Face model, and returns citations backed by trusted SQLite metadata.

The browser experience is a thin Streamlit client. Retrieval, prompt construction,
generation, guardrails, and citation validation remain in the FastAPI backend.

## Architecture

```text
Offline build

data/pdfs/ -> PyMuPDF -> page-aware chunks -> sentence-transformers
            -> FAISS vectors + SQLite metadata + manifest

Runtime query

Browser -> Streamlit -> POST /v1/query -> FastAPI QueryService
                                      -> query embedding
                                      -> FAISS retrieval
                                      -> SQLite source metadata
                                      -> grounded prompt
                                      -> Hugging Face LLM
                                      -> validated answer + citations
```

The runtime index is read-only. Users cannot upload, replace, or delete documents.

## Prerequisites

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- a Hugging Face token allowed to use Inference Providers
- a compatible hosted model name

Install the locked project dependencies:

```bash
uv sync
```

Create local configuration:

```bash
cp .env.example .env
```

Set these values in `.env`:

```dotenv
CONTEXTHUB_HUGGINGFACE_MODEL=your-provider-model
CONTEXTHUB_HUGGINGFACE_API_TOKEN=your-token
```

Never commit `.env` or a real provider token.

## Build The Index

Place the fixed corpus PDFs under `data/pdfs/`, then run:

```bash
uv run python scripts/ingest.py
```

The reproducible build writes:

```text
data/index/
├── faiss.index
├── manifest.json
└── metadata.db
```

Indexing is an offline maintainer operation. It is not performed when the API starts.

## Start The Application

Start FastAPI and Streamlit together with one command:

```bash
uv run python scripts/run_local.py
```

Open <http://127.0.0.1:8501>. The launcher waits for FastAPI health before starting
Streamlit and stops both processes when you press `Ctrl+C`.

Ports can be changed without editing code:

```bash
uv run python scripts/run_local.py --api-port 8100 --ui-port 8601
```

For development with backend auto-reload, use separate terminals:

```bash
uv run uvicorn contexthub.main:app --reload
```

```bash
CONTEXTHUB_API_BASE_URL=http://127.0.0.1:8000 \
  uv run streamlit run frontend/streamlit_app.py
```

`CONTEXTHUB_API_BASE_URL` controls the FastAPI address used by Streamlit in local and
deployed environments. Streamlit performs server-side HTTP requests, and the current
same-origin-oriented design does not enable browser CORS.

## Demonstration

The sidebar reports whether the API and its runtime dependencies are ready. Once it
shows `API ready`, submit a question. An answered response displays trusted source
cards; a question unsupported by the corpus displays an explicit abstention. The most
recent response or recoverable error remains visible across ordinary Streamlit reruns.

Known questions for the current loss data analytics corpus include:

- `What is the difference between claim frequency and claim severity?`
- `How does a policy deductible affect claim payments?`
- `Why is the normal distribution often inappropriate for insurance loss data?`
- `How do deductibles affect both claim severity and claim frequency?`

An unanswerable control question is:

- `What is the capital of South Korea?`

Expected behavior is `insufficient_context` with no citations.

## Docker

The image includes the fixed-corpus FAISS index, SQLite metadata database, and manifest.
Docker never runs ingestion automatically. Rebuild the artifacts before rebuilding the
image only when the corpus or indexing configuration changes:

```bash
uv run python scripts/ingest.py
```

Create `.env` from `.env.example` and set valid Hugging Face values:

```text
CONTEXTHUB_HUGGINGFACE_MODEL=your-provider-model
CONTEXTHUB_HUGGINGFACE_API_TOKEN=your-token
```

Build and start the FastAPI and Streamlit services:

```bash
docker compose up --build
```

Open <http://127.0.0.1:8501>. FastAPI remains available at
<http://127.0.0.1:8000>, including its `/health`, `/ready`, and `/docs` routes.
If either host port is already occupied, override it while leaving the container ports
unchanged:

```bash
CONTEXTHUB_API_PORT=8001 CONTEXTHUB_UI_PORT=8502 docker compose up --build
```

Compose starts two containers from the same image. The `api` service reads the bundled
index from `/app/data/index` and starts Uvicorn. The non-root runtime user cannot modify
the root-owned index artifacts. The `ui` service starts Streamlit and reaches FastAPI
over the private Compose network at `http://api:8000`. A named volume preserves the
downloaded embedding model between container recreations.

Stop the application with:

```bash
docker compose down
```

The raw PDF, local `.env`, virtual environments, tests, and development caches are
excluded from the image.

The bundled index is derived from *Loss Data Analytics, Second Edition*, Version 2.0
(October 2024), edited by Hélène Cossette, Edward (Jed) Frees, Brian Hartman, and Tim
Higgins. The source is <https://openacttexts.github.io/LDAVer2/> and is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). ContextHub transforms the
work by extracting, chunking, embedding, and indexing its text; the original editors
do not endorse this application.

## API

With FastAPI running:

- OpenAPI UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>
- Process health: <http://127.0.0.1:8000/health>
- Runtime readiness: <http://127.0.0.1:8000/ready>

Submit a query directly:

```bash
curl -X POST http://127.0.0.1:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: local-demo" \
  -d '{"question": "How does a policy deductible affect claim payments?", "top_k": 5}'
```

Every HTTP response includes `X-Request-ID`. Request logs include the same identifier,
method, path, status code, and duration so one request can be traced without logging
questions, prompts, documents, credentials, or complete model responses.

## Retrieval Evaluation

Run the offline retrieval evaluation without calling an LLM:

```bash
uv run python scripts/evaluate.py
```

Versioned JSON reports are written under `data/evaluation/reports/`.

Inspect retrieval independently of generation:

```bash
uv run python scripts/retrieve.py "What is loss data analytics?" --top-k 5
```

## Verification

Run all local quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Tests use deterministic fakes and do not require Hugging Face credentials or internet
access.

## Troubleshooting

`/health` returns `200` when the FastAPI process is alive. `/ready` returns `200` only
when the manifest, embedding model, FAISS index, SQLite mappings, retrieval service,
and LLM configuration are ready.

If Streamlit reports that the API is unavailable, confirm the configured base URL and
check:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

If readiness fails, inspect its `checks` array. It identifies whether the problem is
the index, embedding compatibility, metadata mapping, or LLM configuration.

## Project Status

Phases 1 through 7 and the Docker portion of Phase 8 are implemented. GitHub Actions
and public deployment remain Phase 8 work.
