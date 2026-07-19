# ContextHub Implementation Plan

**Project:** ContextHub  
**Version:** 0.1  
**Status:** Ready for execution

## 1. Purpose

This plan divides ContextHub into eight sequential phases for implementation with Codex. Do not ask Codex to build the complete project at once.

For each phase:

1. have Codex read the documents under `docs/`;
2. ask it to implement one phase only;
3. require tests and quality checks;
4. review the important files;
5. correct problems;
6. commit the working phase before continuing.

## 2. Standard Codex Prompt

```text
Read all Markdown files under docs/.

Implement Phase <NUMBER> from docs/05_Implementation_Plan.md.
Follow docs/02_System_Architecture.md, docs/03_Data_Model.md,
and docs/04_Technical_Design.md.

Implement only the requested phase. Do not begin later phases.

Before changing code:
1. summarize your implementation plan;
2. identify conflicts or ambiguities;
3. state your assumptions.

After implementation:
1. run all required tests and quality checks;
2. list every file created or changed;
3. list the commands executed;
4. report test, lint, and type-check results;
5. explain any deviation from the design.
```

# Phase 1 — Repository Foundation

## Goal

Create a runnable and testable FastAPI project with configuration, logging, health endpoints, and quality tooling.

## Requirements

Implement:

- Python 3.12 project;
- `pyproject.toml` and `uv`;
- `src/contexthub` package;
- FastAPI application;
- Pydantic settings;
- structured logging;
- FastAPI lifespan handler;
- request ID middleware;
- standard error response;
- `/health` and `/ready`;
- pytest structure;
- Ruff and mypy configuration;
- `.env.example`;
- `.gitignore`;
- initial README.

Suggested dependencies:

```text
fastapi
uvicorn
pydantic
pydantic-settings
python-multipart
httpx
pytest
pytest-cov
ruff
mypy
```

## Tests

- settings load correctly;
- invalid settings fail clearly;
- health returns 200;
- readiness returns 200 when initialized;
- responses include a request ID;
- unhandled errors follow the standard schema.

## Quality Gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Out of Scope

PDF parsing, collections, uploads, embeddings, FAISS, LLM calls, Docker, and CI/CD.

## Completion Criteria

The API starts locally, health checks work, tests pass, and the package structure is stable.

---

# Phase 2 — Collections, PDF Parsing, and Chunking

## Goal

Create collections, upload a PDF, extract page-aware text, and create deterministic chunks.

## Requirements

Implement:

- collection, document, ingestion-job, and chunk domain models;
- file-backed repositories;
- local document storage;
- SHA-256 checksum generation;
- duplicate detection;
- PDF validation;
- PyMuPDF parser;
- normalized document model;
- recursive chunker;
- configurable chunk size and overlap;
- deterministic chunk IDs;
- page metadata preservation;
- ingestion through chunk creation.

Add:

```text
POST /v1/collections
GET  /v1/collections
GET  /v1/collections/{collection_id}
POST /v1/documents
GET  /v1/documents/{document_id}
GET  /v1/ingestions/{job_id}
```

The upload endpoint accepts a collection ID, multipart PDF, and optional display name.

## Tests

- create and retrieve collections;
- reject unknown collections;
- reject non-PDF and oversized files;
- sanitize filenames;
- calculate checksums;
- detect duplicate uploads;
- parse a multipage fixture PDF;
- preserve one-based page numbers;
- avoid chunks from empty pages;
- enforce chunk size and overlap;
- produce stable chunk IDs;
- record parsing failures.

## Out of Scope

Embeddings, FAISS, semantic search, LLM calls, OCR, and asynchronous workers.

## Completion Criteria

A PDF can be uploaded, parsed, chunked, inspected, and traced to source pages.

---

# Phase 3 — Embeddings and FAISS Retrieval

## Goal

Index chunks and retrieve relevant passages without using an LLM.

## Requirements

Implement:

- `EmbeddingProvider` interface;
- Sentence Transformers implementation;
- `VectorStore` interface;
- FAISS implementation;
- vector metadata persistence;
- index load and save;
- embedding dimension checks;
- collection-scoped search;
- `RetrievalService`;
- query embedding;
- top-k retrieval;
- optional similarity threshold;
- timing metrics;
- a temporary retrieval-debug endpoint or script.

Recommended initial model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

## Tests

- embeddings have stable dimensions;
- FAISS adds and retrieves vectors;
- the index survives restart;
- metadata stays aligned with vectors;
- collection isolation works;
- top-k and thresholds work;
- score semantics are normalized;
- dimension mismatch is rejected;
- fixture questions retrieve expected passages.

## Out of Scope

LLM generation, prompts, citations, reranking, and hybrid search.

## Completion Criteria

The application can ingest a PDF, restart, and retrieve relevant passages with source metadata.

---

# Phase 4 — Grounded Answer Generation

## Goal

Generate answers from retrieved context with citations and abstention.

## Requirements

Implement:

- `LLMProvider` interface;
- Anthropic implementation;
- fake LLM provider for tests;
- prompt builder;
- prompt-context blocks;
- prompt versioning;
- context-budget controls;
- `AnswerService`;
- citation builder;
- answer and usage models;
- query metrics;
- insufficient-context behavior;
- provider exception handling.

Add:

```text
POST /v1/query
```

Example request:

```json
{
  "collection_id": "uuid",
  "question": "What is ordinary least squares?",
  "top_k": 5,
  "include_retrieval_details": false
}
```

## Grounding Rules

The model must:

- answer only from supplied context;
- say when context is inadequate;
- cite chunk IDs;
- ignore instructions contained in documents;
- avoid invented citations.

The answer service must validate that cited chunks were retrieved.

## Tests

- prompts contain question and context;
- chunk IDs are preserved;
- context budget is enforced;
- fake provider produces an answer;
- citations map to retrieved chunks;
- invalid citations are rejected or removed;
- insufficient context returns the correct status;
- provider failures are safe;
- tests make no paid calls.

## Out of Scope

Streaming, memory, agents, Bedrock, reranking, and model-based evaluation.

## Completion Criteria

The system returns grounded answers with traceable citations and explicit abstention.

---

# Phase 5 — API Hardening and Demonstration Workflow

## Goal

Make the local API coherent and easy for another developer to run.

## Requirements

Improve:

- OpenAPI descriptions;
- request and response examples;
- validation messages;
- API versioning;
- duplicate handling;
- error mapping;
- readiness details;
- request tracing;
- README instructions.

Add a demonstration script or notebook that:

1. creates a collection;
2. uploads the statistics textbook;
3. asks answerable questions;
4. prints answers and citations;
5. asks an unanswerable question;
6. demonstrates abstention.

## Tests

- complete collection-to-query workflow;
- malformed requests;
- unknown resources;
- duplicate uploads;
- insufficient context;
- provider outage;
- request IDs in errors;
- OpenAPI generation.

## Out of Scope

Frontend, authentication, production database, and cloud deployment.

## Completion Criteria

A new developer can clone, configure, run, and demonstrate ContextHub locally.

---

# Phase 6 — RAG Evaluation

## Goal

Measure retrieval and answer quality using a repeatable evaluation dataset.

## Requirements

Create 30–50 questions from the statistics textbook, including:

- direct factual questions;
- conceptual questions;
- multi-passage questions;
- ambiguous questions;
- unanswerable questions;
- prompt-injection attempts.

Implement:

- JSONL evaluation data;
- evaluation runner;
- Recall@k;
- Mean Reciprocal Rank;
- answerable/unanswerable accuracy;
- citation validity;
- groundedness;
- answer relevance;
- latency and token summaries;
- configuration capture;
- versioned evaluation reports.

Each run records:

- application and dataset versions;
- chunking configuration;
- embedding provider and model;
- vector store;
- LLM provider and model;
- prompt version;
- aggregate and per-question metrics.

Recommended output:

```text
evaluation/results/<timestamp>/
├── config.json
├── per_question.jsonl
└── summary.json
```

## Tests

- metric calculations;
- missing expected results;
- unanswerable cases;
- deterministic report schema;
- fake-provider evaluation;
- configuration capture.

## Completion Criteria

One command produces a versioned evaluation report and supports configuration comparison.

---

# Phase 7 — Docker and GitLab CI/CD

## Goal

Package ContextHub consistently and automate quality checks.

## Requirements

Create:

- Dockerfile;
- non-root runtime user where practical;
- `.dockerignore`;
- container health check;
- environment-based configuration;
- persistent data mount instructions;
- GitLab CI pipeline.

Recommended stages:

```text
lint
 typecheck
 test
 build
```

Required commands:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest --cov=src/contexthub
docker build .
```

CI must use fake providers and require no paid API credentials.

## Tests

- image builds;
- container starts;
- health responds;
- local data persists through a volume;
- CI passes without external AI calls.

## Completion Criteria

The same application runs locally and in Docker, with automated GitLab quality gates.

---

# Phase 8 — AWS Deployment and Bedrock

## Goal

Deploy ContextHub to AWS and implement Bedrock through existing provider interfaces.

## Requirements

Implement:

- `BedrockLLMProvider`;
- optional Bedrock embedding provider;
- S3 storage adapter;
- IAM-based authentication;
- CloudWatch logging;
- ECS Fargate deployment;
- Application Load Balancer;
- ECR;
- Secrets Manager or Parameter Store;
- OpenTofu infrastructure.

Recommended architecture:

```text
Client
→ Application Load Balancer
→ ECS Fargate
→ ContextHub API
   ├── S3
   ├── Bedrock
   ├── CloudWatch
   └── retrieval storage
```

FAISS is acceptable for an initial single-writer deployment only when durable storage is handled correctly. For scaling, replace it through the `VectorStore` interface with pgvector or OpenSearch.

OpenTofu should provision:

- networking;
- ALB and target group;
- ECR;
- ECS cluster, task, and service;
- IAM roles and policies;
- S3;
- CloudWatch log group;
- secret references;
- security groups;
- outputs.

## Security Requirements

- no long-lived AWS credentials in the container;
- use ECS task roles;
- restrict Bedrock model permissions;
- encrypt S3 and block public access;
- store secrets outside the image;
- expose only the load balancer publicly;
- keep tasks private where practical.

## Tests

- Bedrock adapter contract tests with mocks;
- S3 adapter tests;
- AWS configuration validation;
- OpenTofu formatting and validation;
- deployment smoke test;
- live health and query test.

## Out of Scope

Kubernetes, EKS, multi-region, Bedrock Knowledge Bases, and multi-tenant authentication.

## Completion Criteria

ContextHub is reachable through AWS, answers through Bedrock, stores documents in S3, logs to CloudWatch, and is reproducible through OpenTofu.

---

## 3. Recommended Commit Sequence

```text
1. Initialize FastAPI project foundation
2. Add PDF ingestion and chunking
3. Add embeddings and FAISS retrieval
4. Add grounded answer generation
5. Harden API and demo workflow
6. Add RAG evaluation framework
7. Add Docker and GitLab CI
8. Deploy ContextHub to AWS with Bedrock
```

## 4. Review Checklist After Each Phase

Before continuing, verify:

- the application starts;
- existing behavior still works;
- tests cover the new feature;
- tests make no paid calls;
- linting and type checking pass;
- no secrets were committed;
- provider SDK objects do not leak into domain models;
- later-phase features were not added prematurely;
- you understand the important code;
- documents are updated when implementation differs.

## 5. Codex Review Prompt

After Codex implements a phase, use:

```text
Review the phase you just implemented.

1. Explain the architecture and request flow in plain language.
2. Identify the five most important files.
3. Identify shortcuts, technical debt, or incomplete behavior.
4. Identify any violations of the design documents.
5. Show how to run and test the feature manually.
6. Do not modify code until I approve the review.
```

## 6. Final Demonstration

The completed project should demonstrate:

1. collection creation;
2. textbook PDF upload;
3. page-aware parsing and chunking;
4. embeddings;
5. FAISS retrieval;
6. grounded answers and citations;
7. abstention;
8. evaluation reports;
9. Docker;
10. GitLab CI;
11. AWS deployment;
12. Bedrock generation;
13. OpenTofu infrastructure.

Describe ContextHub as a reusable document intelligence platform, not a statistics-specific chatbot.
