# ContextHub Implementation Plan

**Project:** ContextHub  
**Version:** 1.0  
**Status:** Ready for Execution

---

# 1. Purpose

This document defines the sequential implementation roadmap for ContextHub.

The final deliverable is a public browser-based RAG application. The backend remains
the engineering core, while a deliberately small Streamlit demonstration client makes the system
usable by hiring managers and other portfolio visitors.

Codex must implement one phase at a time. Each phase must leave the repository in a
working, tested state.

---

# 2. Standard Codex Prompt

```text
Read every Markdown file under docs/.

Implement ONLY Phase <N> from docs/04_Implementation_Plan.md.

Follow:
- docs/00_Project_Overview.md
- docs/01_System_Architecture.md
- docs/02_Data_Model.md
- docs/03_Technical_Design.md

Do not begin later phases.

Before writing code:
1. summarize the implementation plan;
2. identify conflicts or ambiguities;
3. state assumptions.

After implementation:
1. list every file created or changed;
2. list commands executed;
3. report lint, formatting, type-check, test, Streamlit, and Docker results;
4. explain any deviation from the design;
5. identify remaining work for the current phase.
```

---

# Phase 1 — Repository and Backend Foundation

## Goal

Create a runnable, testable backend skeleton and establish quality standards.

## Implement

- Python 3.12 project;
- `pyproject.toml` and `uv`;
- documented backend package structure;
- FastAPI application factory;
- Pydantic settings;
- structured logging;
- lifespan startup;
- dependency-injection skeleton;
- request ID handling;
- standard error responses;
- `GET /health`;
- `GET /ready`;
- pytest;
- Ruff;
- mypy;
- `.env.example`;
- `.gitignore`;
- initial README.

Do not implement indexing, retrieval, LLM calls, or the frontend.

## Tests

- settings load correctly;
- invalid settings fail clearly;
- health returns 200;
- readiness reflects initialized and uninitialized states;
- errors use the standard schema;
- request IDs are returned.

## Quality Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Completion Criteria

The API starts locally, the package boundaries are established, and all quality gates
pass.

---

# Phase 2 — Offline Index Builder

## Goal

Build a deterministic, reproducible PDF indexing pipeline.

## Implement

- document and chunk domain models;
- PyMuPDF parser;
- one-based page metadata;
- recursive chunker;
- deterministic document and chunk IDs;
- SHA-256 checksums;
- sentence-transformer embedding adapter;
- normalized embeddings;
- FAISS `IndexFlatIP`;
- SQLite document and chunk persistence;
- transactional FAISS-position mapping;
- manifest generation;
- compatibility validation;
- atomic index replacement;
- `scripts/ingest.py`.

## Output

```text
data/index/
├── faiss.index
├── metadata.db
└── manifest.json
```

## Tests

- multipage PDF parsing;
- empty-page behavior;
- chunk-size and overlap validation;
- deterministic IDs;
- embedding dimensions;
- FAISS save and load;
- FAISS-to-SQLite position alignment;
- SQLite schema and transaction behavior;
- failed build preserves the previous valid index.

## Completion Criteria

```bash
uv run python scripts/ingest.py
```

builds a reloadable index from `data/pdfs/`.

---

# Phase 3 — Runtime Retrieval

## Goal

Load the saved index and retrieve relevant passages without an LLM.

## Implement

- `EmbeddingProvider` protocol;
- `VectorStore` protocol;
- `DocumentRepository` protocol;
- `SQLiteDocumentRepository`;
- `Retriever` protocol;
- `RetrievalService`;
- startup index loading;
- manifest compatibility checks;
- query embedding;
- top-k FAISS retrieval;
- ranked chunk resolution from SQLite;
- optional similarity threshold;
- retrieval timing;
- a development-only retrieval script or test harness.

Do not create public runtime upload or collection endpoints.

## Tests

- expected chunks rank highly;
- top-k works;
- thresholding works;
- score semantics are consistent;
- dimension mismatch is rejected;
- missing or duplicate SQLite position mappings are rejected;
- missing or malformed index causes not-ready behavior;
- restart and reload work.

## Completion Criteria

A fixture question returns ranked passages with document and page metadata.

---

# Phase 4 — Grounded Query API

## Goal

Expose a complete grounded answer API.

## Implement

- `PromptBuilder`;
- context delimiting and prompt versioning;
- Hugging Face LLM adapter;
- configurable model and server-side token;
- timeout and bounded retry behavior;
- `CitationBuilder`;
- `QueryService`;
- `POST /v1/query`;
- structured answered and insufficient-context responses;
- validated citation IDs.

## Tests

- prompt includes question and retrieved chunks;
- context budget is enforced;
- fake LLM returns an answer;
- invalid provider JSON fails safely;
- unknown citations fail safely;
- empty retrieval returns abstention without calling the LLM;
- provider timeout and outage are mapped;
- tests make no hosted API calls.

## Completion Criteria

The API returns grounded answers and citations through a stable JSON contract.

---

# Phase 5 — Retrieval Evaluation

## Goal

Measure retrieval quality reproducibly before building the presentation layer.

## Implement

- JSONL evaluation dataset;
- answerable and unanswerable cases;
- direct, conceptual, and multi-passage questions;
- prompt-injection retrieval cases;
- `scripts/evaluate.py`;
- Recall@K;
- Hit Rate@K;
- Mean Reciprocal Rank;
- average retrieval latency;
- configuration capture;
- versioned JSON reports.

## Tests

- metric calculations;
- malformed dataset handling;
- deterministic report schema;
- missing expected chunks;
- unanswerable cases.

## Completion Criteria

One command produces a versioned retrieval evaluation report without calling the LLM.

---

# Phase 6 — Streamlit Demonstration Client

## Goal

Create a thin browser interface for portfolio reviewers.

## Technology

- Streamlit;
- requests or httpx.

## Implement

```text
frontend/
└── streamlit_app.py
```

The client must provide:

- ContextHub title and project summary;
- indexed-corpus description;
- configurable FastAPI base URL;
- optional readiness display;
- question input and submit control;
- loading state;
- answer and citation rendering;
- insufficient-context state;
- recoverable server/network error.

The client must not import backend modules, access FAISS or SQLite, expose secrets,
provide uploads, or implement retrieval and prompt logic.

## Tests

Test extracted response-formatting helpers where useful. API contract behavior remains
covered by backend API tests.

## Completion Criteria

A reviewer can start Streamlit, submit a question to FastAPI, and view trusted
citations.

# Phase 7 — Integrated Application and Hardening

## Goal

Combine the frontend and backend into one coherent application.

## Implement

- documented local startup for FastAPI and Streamlit;
- configurable API URL for local and deployed environments;
- OpenAPI descriptions and examples;
- CORS disabled or tightly limited for same-origin deployment;
- refined validation messages;
- readiness display in the UI;
- structured request tracing;
- end-to-end demo instructions;
- polished README screenshots or diagrams;
- known sample questions.

## Tests

- Streamlit loads and reaches the configured FastAPI service;
- API routes remain reachable;
- answered and insufficient-context flows work end to end;
- health and readiness work;
- Streamlit reruns do not lose recoverable application state;
- no provider credentials appear in the client source or logs.

## Completion Criteria

One local command or Docker command starts the complete browser application.

---

# Phase 8 — Docker, CI, and Public Deployment

## Goal

Package and expose the application through a public HTTPS URL.

## Docker

Implement:

- Python container build;
- Streamlit client included or separately runnable;
- SQLite metadata database bundled or mounted read-only;
- non-root user;
- bundled or read-only mounted FAISS index;
- health check;
- environment-based Hugging Face configuration.

The container must not rebuild the corpus at startup.

## GitHub Actions

Run:

```bash
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest

docker build .
```

CI must require no external AI credentials and make no hosted LLM calls.

## Deployment

Deploy to a low-cost platform that supports:

- Docker containers;
- environment variables;
- HTTPS;
- sufficient memory for sentence-transformers and FAISS;
- health checks.

The specific platform must remain configurable because free tiers and resource limits
can change.

## Smoke Test

Verify:

1. public page loads;
2. readiness succeeds;
3. a known question returns an answer;
4. citations render;
5. an unanswerable question displays abstention;
6. secrets are absent from browser assets and logs.

## Completion Criteria

A reviewer can open a public URL and use ContextHub without installing software,
downloading a model, or supplying credentials.

---

# Phase 9 — Optional Enhancements

Potential later enhancements:

- local Ollama provider;
- OpenAI, Anthropic, or Gemini providers;
- pgvector or OpenSearch;
- hybrid retrieval;
- reranking;
- streaming responses;
- richer source previews;
- deployment-specific infrastructure automation.

These changes must use existing interfaces and must not rewrite core application
services.

---

# 3. Recommended Commit Sequence

```text
1. Establish backend repository foundation
2. Add deterministic offline index builder
3. Add runtime retrieval
4. Add grounded query API
5. Add retrieval evaluation
6. Add Streamlit demonstration client
7. Integrate and harden the full application
8. Add Docker, CI, and public deployment
9. Add optional provider or retrieval enhancements
```

---

# 4. Review Checklist After Each Phase

Before continuing, verify:

- the application starts;
- previous behavior still works;
- the new phase is covered by tests;
- no tests make hosted AI calls;
- Python linting, formatting, typing, and tests pass;
- Streamlit client starts and reaches the API once it exists;
- no secrets were committed;
- provider objects do not leak into domain models;
- presentation logic remains outside application services;
- later-phase features were not implemented prematurely;
- documentation reflects material implementation deviations.

---

# 5. Codex Review Prompt

```text
Review the phase you just implemented without modifying code.

1. Explain the architecture and execution flow in plain language.
2. Identify the five most important files.
3. Identify shortcuts, technical debt, or incomplete behavior.
4. Identify violations of the design documents.
5. Show the exact commands for manual verification.
6. Explain what should be reviewed before proceeding.
```

---

# 6. Final Demonstration

The completed project should demonstrate:

1. offline PDF indexing;
2. deterministic page-aware chunking;
3. sentence-transformer embeddings;
4. FAISS retrieval;
5. grounded Hugging Face generation;
6. validated citations;
7. explicit abstention;
8. reproducible retrieval evaluation;
9. Streamlit browser interface;
10. answer and source rendering;
11. Docker;
12. GitHub Actions;
13. a public HTTPS deployment.

Describe ContextHub as a production-oriented RAG reference application, not as an
enterprise document-management platform and not as a statistics-specific chatbot.
