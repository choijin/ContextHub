# Project Overview

**Project:** ContextHub  
**Subtitle:** Production-Oriented Retrieval-Augmented Generation (RAG) Reference Application  
**Version:** 1.0  
**Author:** Jin Choi  
**Status:** Ready for Implementation

---

# 1. Vision

ContextHub is a production-oriented RAG application built to demonstrate Machine
Learning Engineering and software engineering practices.

Rather than being a notebook-based “chat with your PDF” demo, ContextHub is a
complete deployable application. A visitor opens the web interface, submits a
question, receives a grounded answer, and reviews citations linked to the indexed
documents.

The application follows a build-once, query-many model. Project maintainers replace
the fixed PDF corpus and rebuild the index offline. Runtime users do not upload or
manage documents.

---

# 2. Problem Statement

Many RAG projects demonstrate retrieval and generation but stop at a notebook or an
API endpoint. They often lack:

- modular architecture;
- automated testing;
- reproducible indexing;
- retrieval evaluation;
- deployment readiness;
- provider abstraction;
- a usable browser interface.

ContextHub demonstrates how to deliver a small but complete RAG product without
introducing enterprise-scale complexity.

---

# 3. Project Goals

## Primary Goals

- Demonstrate Machine Learning Engineering practices.
- Demonstrate clean software architecture.
- Build a reusable RAG backend.
- Expose the system through a simple browser-based interface.
- Show reproducible indexing and retrieval evaluation.
- Deploy a portfolio application that hiring managers can use directly.
- Keep infrastructure and operating cost minimal.

## Secondary Goals

- Support interchangeable LLM providers.
- Support interchangeable embedding providers.
- Support interchangeable vector stores.
- Keep the frontend thin and the backend independently testable.
- Make the project easy to explain in technical interviews.

---

# 4. Version 1 Workflow

## Corpus Build

```text
Replace PDFs in data/pdfs/
        ↓
Run scripts/ingest.py
        ↓
Parse and Chunk Documents
        ↓
Generate Embeddings
        ↓
Build FAISS Vector Index, SQLite Metadata Database, and Manifest
```

## User Experience

```text
Open ContextHub Web Page
        ↓
Enter a Question
        ↓
Web UI Calls POST /v1/query
        ↓
FastAPI Retrieves Context
        ↓
Hugging Face Generates an Answer
        ↓
UI Displays Answer and Sources
```

Documents are **not uploaded at runtime**.

---

# 5. Version 1 Scope

## Included

- Fixed PDF corpus.
- Offline PDF parsing and indexing.
- Recursive page-aware chunking.
- Sentence-transformer embeddings.
- FAISS vector retrieval.
- Grounded answer generation.
- Validated citations.
- FastAPI backend.
- Minimal Streamlit demonstration client.
- Docker.
- GitHub Actions.
- Structured logging.
- Unit, integration, API, and frontend tests.
- Retrieval evaluation.
- Environment-based configuration.
- Public web deployment.

## Excluded

- Runtime uploads.
- Document collections.
- Authentication and user accounts.
- Conversation history.
- OCR.
- Agents.
- Tool calling.
- LangChain (reserved for Version 2).
- Workflow orchestration.
- Multi-tenancy.
- Kubernetes.
- Production database.
- Complex frontend state management.

---

# 6. Target Users

The runtime user is a hiring manager, interviewer, developer, or other portfolio
visitor who wants to test the application through a browser.

The repository user is a developer who wants to replace the PDF corpus, rebuild the
index, run evaluations, or extend providers.

---

# 7. Technology Stack

| Area | Technology |
|---|---|
| Backend language | Python 3.12 |
| Backend API | FastAPI |
| Validation | Pydantic v2 |
| Python package manager | uv |
| PDF parsing | PyMuPDF |
| Embeddings | sentence-transformers |
| Vector index | FAISS |
| Metadata database | SQLite |
| LLM | Hugging Face Inference API |
| Frontend | Streamlit |
| Frontend HTTP | requests (HTTP client) |
| Backend tests | pytest |
| Python quality | Ruff and mypy |
| Containerization | Docker |
| CI/CD | GitHub Actions |

The Streamlit client is intentionally thin. It communicates with FastAPI exclusively over HTTP. All retrieval, generation, and business logic belong in the FastAPI backend.

---

# 8. Version 1 User Interface

The Streamlit demonstration client should contain:

- project title and brief explanation;
- question input;
- submit button;
- loading state;
- answer panel;
- source cards with document name and page range;
- insufficient-context message;
- recoverable error message.

The interface does not need:

- login;
- document upload;
- chat history;
- multiple conversations;
- rich text editing;
- administrative pages;
- complex navigation.

---

# 9. Success Criteria

Version 1 is complete when:

- A new corpus can be indexed by replacing the PDF folder.
- The saved FAISS index and SQLite metadata database can be loaded after restart.
- Every FAISS result maps deterministically to a chunk stored in SQLite.
- Retrieval returns relevant passages.
- Answers are grounded only in retrieved context.
- Responses include validated citations.
- Retrieval metrics can be generated.
- A visitor can open a deployed URL and submit a question.
- The web UI displays answers, citations, loading, errors, and abstention.
- The application runs locally through Docker.
- GitHub Actions passes backend typing, linting, testing, Docker, and application checks.

---

# 10. Final Portfolio Demonstration

A reviewer should be able to:

1. Open the deployed ContextHub URL.
2. Read what corpus the application covers.
3. Ask an answerable question.
4. View the answer and supporting sources.
5. Ask an unanswerable question.
6. See an explicit insufficient-context response.
7. Review the repository for architecture, tests, CI, Docker, and evaluation results.

---

# 11. Roadmap

## Version 1
Build every RAG component from first principles using FastAPI, Streamlit, FAISS, and Hugging Face.

## Version 2
Introduce LangChain selectively while preserving the FastAPI API contract and Streamlit client.

## Version 2.5
Deploy the application publicly with a free or minimal-cost hosting platform and include a demo video as a fallback.

---

# 12. Future Enhancements

Potential future improvements include:

- Ollama or another local LLM provider.
- OpenAI, Anthropic, or Gemini providers.
- pgvector or OpenSearch.
- Hybrid retrieval.
- Metadata filtering.
- Reranking.
- Streaming responses.
- Richer source previews.
- Additional deployment targets.

These enhancements should use existing interfaces without rewriting application
services.
