# System Architecture

**Project:** ContextHub  
**Subtitle:** Production-Oriented RAG Reference Application  
**Version:** 1.0  
**Status:** Ready for Implementation

---

# 1. Purpose

This document defines the high-level architecture of ContextHub.

ContextHub is not a document-management platform. Project maintainers build a fixed
document index offline. Runtime visitors access the application through a browser and
ask questions against that prepared knowledge base.

The architecture is intentionally small enough for a portfolio project while still
demonstrating:

- Clean Architecture;
- interface-driven design;
- testability;
- reproducibility;
- deployment readiness;
- separation between presentation, application, and infrastructure concerns.

---

# 2. System Overview

Version 1 consists of three workflows.

## 2.1 Offline Build Pipeline

```text
PDF Folder
    ↓
Document Parser
    ↓
Recursive Chunker
    ↓
Embedding Provider
    ↓
FAISS Index + SQLite Metadata Database
    ↓
Chunk Metadata + Index Manifest
```

This pipeline runs through `scripts/ingest.py` before deployment.

## 2.2 Runtime Query Pipeline

```text
Browser
    ↓
Streamlit Demonstration Client
    ↓ HTTPS
FastAPI
    ↓
Query Service
    ↓
Retriever
    ↓
FAISS
    ↓
Prompt Builder
    ↓
Hugging Face LLM Provider
    ↓
Answer + Validated Citations
    ↓
Streamlit Demonstration Client
```

## 2.3 Deployment Pipeline

```text
Git Push
    ↓
GitHub Actions
    ├── Backend lint, type check, and tests
    ├── Frontend lint, tests, and build
    └── Docker build
            ↓
       Deployment Platform
            ↓
       Public HTTPS URL
```

---

# 3. Deployment Topology

The preferred Version 1 topology is a single deployable application.

```text
Public Browser
      ↓ HTTPS
Application Container
      ├── Streamlit Application
      └── FastAPI under /api or /v1
              ├── FAISS Index + SQLite Metadata Database
              ├── Chunk Metadata
              └── Hugging Face Inference API
```

Streamlit runs as a lightweight client that communicates with FastAPI over HTTP. It never imports backend services directly.

A same-origin deployment is preferred because it:

- avoids unnecessary CORS complexity;
- requires only one public URL;
- simplifies local and portfolio deployment;
- keeps the frontend and backend version aligned.

A split frontend/backend deployment is allowed later, but is not the default Version 1
design.

---

# 4. Architectural Principles

## 4.1 Clean Architecture

Backend dependencies point inward.

```text
FastAPI API
    ↓
Application Services
    ↓
Domain

Infrastructure ─────► Application Ports
```

The frontend communicates only through the documented HTTP API. It does not import or
share backend implementation code.

## 4.2 Thin Presentation Layer

The web UI owns:

- question input;
- request submission;
- loading state;
- answer rendering;
- citation rendering;
- user-facing error messages.

The web UI must not own:

- embedding;
- retrieval;
- prompt construction;
- citation validation;
- provider selection;
- access to the FAISS vector index;
- read-only access to the SQLite metadata database.

## 4.3 Interface-Driven Backend

Infrastructure implements interfaces defined by the application layer.

Required interfaces:

- `DocumentParser`
- `Chunker`
- `EmbeddingProvider`
- `VectorStore`
- `Retriever`
- `PromptBuilder`
- `LLMProvider`

Replacing a provider should require changing only composition and infrastructure code.

## 4.4 Stateless Runtime

The runtime does not modify the corpus.

Each query:

1. accepts a question;
2. embeds it;
3. retrieves context;
4. builds a prompt;
5. generates an answer;
6. validates citations;
7. returns a structured response.

The UI may hold temporary component state, but the server stores no conversation
history.

---

# 5. Major Components

## 5.1 Streamlit Demonstration Client

Responsibilities:

- explain the project and corpus;
- accept a question;
- call `POST /v1/query`;
- display loading and errors;
- render answer status;
- render citations with document names and page ranges;
- support keyboard and screen-reader use.

The interface should remain a single-page experience.

## 5.2 FastAPI Layer

Responsibilities:

- validate requests;
- serialize responses;
- inject dependencies;
- map internal exceptions;
- expose health and readiness endpoints;
- serve static frontend assets when using the single-container topology.

No retrieval or generation logic belongs in routes.

## 5.3 Offline Index Builder

Responsibilities:

- discover PDFs;
- extract page-aware text;
- create deterministic chunks;
- generate embeddings;
- build FAISS;
- persist chunk metadata;
- write a compatibility manifest;
- atomically replace the previous index.

## 5.4 Query Service

Coordinates the runtime workflow:

- retrieve context;
- detect insufficient evidence;
- build the prompt;
- invoke the LLM;
- validate cited chunk IDs;
- construct trusted citations;
- return a structured answer.

## 5.5 Document Parser

Version 1 uses PyMuPDF.

## 5.6 Chunker

Responsibilities:

- deterministic recursive splitting;
- configurable size and overlap;
- page-range preservation;
- stable chunk IDs.

## 5.7 Embedding Provider

Version 1 uses sentence-transformers.

## 5.8 Vector Store

Version 1 uses normalized embeddings with FAISS `IndexFlatIP`.

## 5.9 Prompt Builder

Responsibilities:

- delimit untrusted source text;
- preserve chunk IDs;
- enforce the context budget;
- request a structured provider response.

## 5.10 LLM Provider

Version 1 uses the Hugging Face Inference API through an application interface.

The configured model remains environment-driven because free hosted availability may
change.

---

# 6. HTTP Contract

## Endpoints

```text
GET  /health
GET  /ready
POST /v1/query
```

The browser uses only `POST /v1/query`.

Example request:

```json
{
  "question": "Why is regularization used in linear models?",
  "top_k": 5
}
```

Example response:

```json
{
  "request_id": "uuid",
  "question": "Why is regularization used in linear models?",
  "answer": "Regularization constrains model complexity...",
  "status": "answered",
  "citations": [
    {
      "chunk_id": "chunk-id",
      "document_name": "statistics.pdf",
      "page_start": 142,
      "page_end": 143,
      "excerpt": "..."
    }
  ]
}
```

---

# 7. Browser Request Flow

```text
Visitor enters question
        ↓
UI validates non-empty input
        ↓
UI disables submit and shows loading state
        ↓
HTTP POST /v1/query
        ↓
FastAPI validates QueryRequest
        ↓
QueryService retrieves and generates
        ↓
FastAPI returns Answer JSON
        ↓
UI branches on status
        ├── answered → answer + source cards
        └── insufficient_context → abstention message
```

For network or server failures, the UI displays a recoverable error and keeps the
question available for resubmission.

---

# 8. Frontend Component Structure

Recommended components:

```text
App
├── Header
├── ProjectSummary
├── QuestionForm
├── LoadingIndicator
├── AnswerPanel
├── CitationList
│   └── CitationCard
└── ErrorMessage
```

Recommended frontend modules:

```text
frontend/
└── streamlit_app.py
```

Do not add Redux, a router, or a component framework unless a later requirement
justifies it.

---

# 9. Repository Structure

```text
contexthub/
├── frontend/
│   └── streamlit_app.py
├── scripts/
│   ├── ingest.py
│   └── evaluate.py
├── src/contexthub/
│   ├── api/
│   ├── application/
│   │   ├── ports/
│   │   └── services/
│   ├── domain/
│   ├── infrastructure/
│   │   ├── chunking/
│   │   ├── embeddings/
│   │   ├── llms/
│   │   ├── parsers/
│   │   ├── repositories/
│   │   └── vectorstores/
│   ├── config/
│   └── observability/
├── data/
│   ├── pdfs/
│   ├── index/
│   └── evaluation/
├── tests/
├── Dockerfile
├── pyproject.toml
└── .github/workflows/ci.yml
```

# 10. Data and Persistence

| Artifact | Storage |
|---|---|
| Source PDFs | `data/pdfs/` during index build |
| FAISS vectors | `data/index/faiss.index` |
| Documents and chunks | `data/index/metadata.db` |
| Index compatibility manifest | `data/index/manifest.json` |
| Evaluation cases and reports | `data/evaluation/` |
| Runtime conversation data | Not stored |

SQLite stores document records, chunk text, page ranges, hashes, and each chunk's
`faiss_position`. FAISS stores vectors only. Runtime retrieval first obtains ranked
FAISS positions, then resolves the corresponding trusted chunk records from SQLite.

The Streamlit client stores no credentials and does not persist questions or answers.

# 11. Health and Readiness

`GET /health` confirms that the process is running.

`GET /ready` confirms that:

- settings are valid;
- the embedding provider initialized;
- FAISS loaded;
- the SQLite metadata database opened successfully;
- FAISS vector count matches the SQLite chunk mapping count;
- manifest compatibility checks passed;
- required Hugging Face configuration exists.

The UI may use readiness at initial page load to display whether the demo is available,
but readiness must not call the external LLM on every request.

---

# 12. Security

Version 1 must:

- keep the Hugging Face token on the server;
- never expose provider credentials in frontend code;
- validate all API input;
- render answers as text rather than unsanitized HTML;
- treat document text as untrusted;
- validate all citations against retrieved chunks;
- use bounded request timeouts;
- avoid logging full documents or prompts;
- use HTTPS in public deployment;
- run the container as non-root where practical.

---

# 13. Testing Strategy

## Backend

- unit tests for services and adapters;
- integration tests for parsing, indexing, and retrieval;
- API tests for health, readiness, and query behavior.

## Frontend

- component tests for form submission;
- loading-state tests;
- answered-response rendering;
- insufficient-context rendering;
- error rendering;
- API client tests with mocked fetch.

## End-to-End Smoke Test

A deployed smoke test should verify:

1. the page loads;
2. the API is ready;
3. a known question returns an answer;
4. at least one citation is displayed.

---

# 14. Deployment

The final portfolio deliverable must expose a public HTTPS URL.

The deployment must provide:

- the Streamlit application;
- FastAPI;
- the built FAISS index;
- the SQLite metadata database;
- chunk metadata and manifest;
- server-side Hugging Face credentials;
- health and readiness checks.

The public runtime must not require users to install Python, download a local model, or
supply their own API key.

---

# 15. Acceptance Criteria

The architecture is correctly implemented when:

- the offline corpus build is independent from runtime querying;
- the backend follows documented dependency boundaries;
- a browser visitor can ask a question through the web UI;
- the UI communicates only through the FastAPI contract;
- answers and sources render correctly;
- insufficient context is clearly displayed;
- provider credentials never reach the browser;
- frontend and backend tests pass;
- the same application runs locally and from a public HTTPS URL.
