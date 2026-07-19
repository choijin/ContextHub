# Data Model

**Project:** ContextHub  
**Subtitle:** Production-Ready Document Intelligence Platform  
**Version:** 0.1  
**Status:** Draft

---

# 1. Purpose

This document defines the core domain entities used by ContextHub.

These entities form the shared language between the API layer, ingestion pipeline, retrieval pipeline, provider implementations, persistence layer, evaluation framework, and tests.

The data model is intentionally independent of:

- FastAPI
- FAISS
- LangChain
- Sentence Transformers
- Anthropic
- AWS Bedrock
- PostgreSQL
- OpenSearch

External frameworks and vendor SDKs may convert these domain objects into provider-specific formats, but core application services should operate on the models defined here.

---

# 2. Design Principles

## Provider Independent

Domain models shall not contain objects imported from external AI frameworks or vendor SDKs.

For example, the core `Chunk` model shall not contain:

- LangChain `Document` objects
- FAISS index objects
- Anthropic message objects
- Bedrock response objects

Adapters are responsible for translating between external representations and ContextHub domain models.

---

## Immutable Where Practical

Identifiers, checksums, source references, and creation timestamps should not change after creation.

Immutable models reduce accidental mutation and make testing more predictable.

---

## Serializable

All domain models should be serializable to JSON-compatible structures.

This supports:

- REST APIs
- persistence
- structured logging
- test fixtures
- event messages
- evaluation datasets

---

## Explicit

Fields should use explicit types and validation rules.

Avoid unstructured dictionaries except for extensible metadata fields.

---

## Traceable

Every derived object should be traceable to its source.

For example:

```text
Citation
    ↓
Chunk
    ↓
Document
    ↓
Collection
```

---

# 3. Entity Relationships

```text
Collection
    │
    ├── Document
    │       │
    │       ├── DocumentPage
    │       │
    │       └── Chunk
    │               │
    │               └── EmbeddingRecord
    │
    └── Query
            │
            ├── RetrievalResult
            │       └── RetrievedChunk
            │
            └── Answer
                    └── Citation
```

---

# 4. Identifier Strategy

ContextHub shall use string-based unique identifiers.

Recommended implementation:

```text
UUID version 4
```

Examples:

```text
collection_id: 1d5c2321-7c93-41ba-bacc-7a6bbcb75d54
document_id:   c024c807-ce9e-445d-93ce-e5cc3268c6c6
chunk_id:      3e17e986-b132-4998-b10a-72ebfe20a4c7
request_id:    24e384fd-07a7-4e96-944c-1b6fca650471
```

Deterministic identifiers may be used for document chunks when idempotent ingestion is required.

A deterministic chunk identifier may be generated from:

```text
document_id
page_number
section
chunk_index
content_hash
```

---

# 5. Enumerations

## DocumentStatus

Represents the ingestion lifecycle of a document.

```python
class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"
```

---

## CollectionStatus

Represents whether a collection is available for queries.

```python
class CollectionStatus(str, Enum):
    ACTIVE = "active"
    PROCESSING = "processing"
    UNAVAILABLE = "unavailable"
    ARCHIVED = "archived"
```

---

## SourceType

Identifies the original document format.

```python
class SourceType(str, Enum):
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
```

Version 1 only requires `PDF`.

---

## IngestionStage

Represents the current ingestion operation.

```python
class IngestionStage(str, Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    PARSING = "parsing"
    NORMALIZING = "normalizing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETE = "complete"
    FAILED = "failed"
```

---

## QueryStatus

```python
class QueryStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
```

---

## AnswerStatus

```python
class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    PROVIDER_ERROR = "provider_error"
    BLOCKED = "blocked"
```

---

## RetrievalStrategy

```python
class RetrievalStrategy(str, Enum):
    SIMILARITY = "similarity"
    MAXIMAL_MARGINAL_RELEVANCE = "mmr"
    HYBRID = "hybrid"
```

Version 1 requires `SIMILARITY`.

---

# 6. Collection Model

A collection represents an isolated group of related documents.

Examples:

- Statistics textbook
- Insurance manuals
- Machine learning documentation
- Financial filings

Documents from one collection should not be retrieved for queries submitted to another collection.

```python
class Collection(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    status: CollectionStatus
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = {}
```

## Field Definitions

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | UUID | Yes | Unique collection identifier |
| `name` | string | Yes | Human-readable collection name |
| `description` | string | No | Description of the collection |
| `status` | enum | Yes | Current collection status |
| `document_count` | integer | Yes | Number of active documents |
| `created_at` | datetime | Yes | Creation timestamp |
| `updated_at` | datetime | Yes | Last update timestamp |
| `metadata` | object | No | Extensible collection metadata |

## Validation Rules

- `name` must contain between 1 and 100 characters.
- `document_count` cannot be negative.
- Collection names do not need to be globally unique.
- Collection identifiers must be globally unique.

---

# 7. Document Model

A document represents one source file uploaded to ContextHub.

```python
class Document(BaseModel):
    id: UUID
    collection_id: UUID
    filename: str
    display_name: str
    source_type: SourceType
    media_type: str
    file_size_bytes: int
    checksum_sha256: str
    status: DocumentStatus
    page_count: int | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    version: str | None = None
    source_uri: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = {}
```

## Field Definitions

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | UUID | Yes | Unique document identifier |
| `collection_id` | UUID | Yes | Parent collection |
| `filename` | string | Yes | Original uploaded filename |
| `display_name` | string | Yes | User-facing document name |
| `source_type` | enum | Yes | Original file format |
| `media_type` | string | Yes | MIME type |
| `file_size_bytes` | integer | Yes | Original file size |
| `checksum_sha256` | string | Yes | SHA-256 checksum |
| `status` | enum | Yes | Ingestion status |
| `page_count` | integer | No | Number of pages |
| `title` | string | No | Extracted or supplied title |
| `author` | string | No | Extracted or supplied author |
| `language` | string | No | ISO language code |
| `version` | string | No | Document version |
| `source_uri` | string | No | Storage location |
| `created_at` | datetime | Yes | Upload timestamp |
| `updated_at` | datetime | Yes | Last status update |
| `metadata` | object | No | Additional metadata |

## Validation Rules

- Version 1 accepts PDF files only.
- `file_size_bytes` must be greater than zero.
- `checksum_sha256` must be a 64-character hexadecimal string.
- `page_count`, when present, must be greater than zero.
- Files exceeding the configured maximum upload size must be rejected.
- Duplicate handling is based on collection ID and checksum.

---

# 8. Document Page Model

A document page represents text extracted from one physical PDF page.

This model preserves page boundaries so citations can point to the original source page.

```python
class DocumentPage(BaseModel):
    document_id: UUID
    page_number: int
    text: str
    character_count: int
    metadata: dict[str, Any] = {}
```

## Field Definitions

| Field | Type | Required | Description |
|---|---|---:|---|
| `document_id` | UUID | Yes | Parent document identifier |
| `page_number` | integer | Yes | One-based page number |
| `text` | string | Yes | Extracted page text |
| `character_count` | integer | Yes | Text length |
| `metadata` | object | No | Page-specific metadata |

## Validation Rules

- `page_number` begins at `1`.
- Empty pages may be retained but should not produce chunks.
- Extracted text must preserve page origin.
- OCR is not required in Version 1.

---

# 9. Normalized Document Model

A normalized document contains cleaned text produced by the parsing and normalization pipeline.

```python
class NormalizedDocument(BaseModel):
    document_id: UUID
    collection_id: UUID
    pages: list[DocumentPage]
    full_text: str
    normalization_version: str
    created_at: datetime
    metadata: dict[str, Any] = {}
```

## Purpose

This model separates raw file parsing from chunk generation.

It allows:

- chunking strategies to operate without knowing the source format;
- normalization logic to evolve independently;
- future support for HTML, Markdown, DOCX, and text files.

---

# 10. Chunk Model

A chunk is the smallest indexed unit available for retrieval.

```python
class Chunk(BaseModel):
    id: str
    document_id: UUID
    collection_id: UUID
    text: str
    chunk_index: int
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    token_count: int | None = None
    character_count: int
    content_hash: str
    chunking_strategy: str
    chunking_version: str
    created_at: datetime
    metadata: dict[str, Any] = {}
```

## Field Definitions

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | string | Yes | Unique or deterministic chunk ID |
| `document_id` | UUID | Yes | Parent document |
| `collection_id` | UUID | Yes | Parent collection |
| `text` | string | Yes | Chunk content |
| `chunk_index` | integer | Yes | Position in document |
| `page_start` | integer | No | First source page |
| `page_end` | integer | No | Last source page |
| `section_title` | string | No | Associated heading or section |
| `token_count` | integer | No | Token count |
| `character_count` | integer | Yes | Character count |
| `content_hash` | string | Yes | Hash of normalized chunk text |
| `chunking_strategy` | string | Yes | Strategy used |
| `chunking_version` | string | Yes | Version of chunking configuration |
| `created_at` | datetime | Yes | Creation timestamp |
| `metadata` | object | No | Additional metadata |

## Validation Rules

- `text` must not be empty.
- `chunk_index` must be zero or greater.
- `page_start` cannot exceed `page_end`.
- `character_count` must match the text length.
- Chunk identifiers should remain stable when the source and chunking configuration have not changed.
- Metadata must preserve enough information to generate a citation.

---

# 11. Chunking Configuration Model

```python
class ChunkingConfig(BaseModel):
    strategy: str = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    length_unit: str = "characters"
    preserve_page_boundaries: bool = True
    preserve_section_titles: bool = True
```

## Validation Rules

- `chunk_size` must be greater than zero.
- `chunk_overlap` must be zero or greater.
- `chunk_overlap` must be smaller than `chunk_size`.
- Version 1 may use character-based chunking.
- Token-based chunking may be added later.

---

# 12. Embedding Record Model

An embedding record connects a chunk to its generated vector.

```python
class EmbeddingRecord(BaseModel):
    chunk_id: str
    document_id: UUID
    collection_id: UUID
    embedding: list[float]
    dimensions: int
    provider: str
    model: str
    model_version: str | None = None
    created_at: datetime
```

## Validation Rules

- `dimensions` must equal the length of `embedding`.
- Embeddings must not contain `NaN` or infinite values.
- The embedding model and vector index must use compatible dimensions.
- An index should not mix incompatible embedding models.

## Storage Consideration

The domain model may include the vector for interoperability and testing.

Production persistence implementations may store vectors in:

- FAISS
- pgvector
- OpenSearch
- another vector database

without exposing database-native objects to the domain layer.

---

# 13. Ingestion Job Model

An ingestion job tracks document-processing progress.

```python
class IngestionJob(BaseModel):
    id: UUID
    document_id: UUID
    collection_id: UUID
    stage: IngestionStage
    progress_percent: float
    started_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    metrics: IngestionMetrics | None = None
```

## Ingestion Metrics

```python
class IngestionMetrics(BaseModel):
    page_count: int = 0
    extracted_character_count: int = 0
    chunk_count: int = 0
    embedding_count: int = 0
    parsing_duration_ms: int = 0
    chunking_duration_ms: int = 0
    embedding_duration_ms: int = 0
    indexing_duration_ms: int = 0
    total_duration_ms: int = 0
```

## Validation Rules

- `progress_percent` must be between `0` and `100`.
- Failed jobs must include an error code or message.
- Completed jobs must include `completed_at`.
- A document should not become `READY` until indexing succeeds.

---

# 14. Query Request Model

```python
class QueryRequest(BaseModel):
    collection_id: UUID
    question: str
    top_k: int = 5
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.SIMILARITY
    similarity_threshold: float | None = None
    metadata_filters: dict[str, Any] = {}
    include_retrieval_details: bool = False
```

## Field Definitions

| Field | Type | Required | Description |
|---|---|---:|---|
| `collection_id` | UUID | Yes | Collection to search |
| `question` | string | Yes | User question |
| `top_k` | integer | No | Maximum chunks to retrieve |
| `retrieval_strategy` | enum | No | Retrieval method |
| `similarity_threshold` | float | No | Minimum similarity |
| `metadata_filters` | object | No | Retrieval filters |
| `include_retrieval_details` | boolean | No | Include debug metadata |

## Validation Rules

- `question` must not be blank.
- `question` must not exceed the configured maximum length.
- `top_k` must be between `1` and the configured maximum.
- Similarity threshold must fall within the vector store’s supported score range.
- The collection must exist and be available.

---

# 15. Retrieval Result Model

```python
class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float
    rank: int
    retrieval_strategy: RetrievalStrategy
```

```python
class RetrievalResult(BaseModel):
    request_id: UUID
    collection_id: UUID
    query: str
    chunks: list[RetrievedChunk]
    retrieval_duration_ms: int
    embedding_duration_ms: int
    total_candidates: int | None = None
```

## Design Notes

The meaning of `score` may vary by vector store.

The retriever or vector-store adapter must normalize or clearly document score semantics.

For example:

- larger score means more similar;
- smaller distance means more similar.

Core application logic should not assume provider-specific score behavior.

---

# 16. Prompt Request Model

A prompt request is the normalized input passed to an LLM provider.

```python
class PromptRequest(BaseModel):
    system_prompt: str
    user_question: str
    context_blocks: list[PromptContextBlock]
    response_format: str = "json"
    temperature: float = 0.0
    max_output_tokens: int | None = None
```

```python
class PromptContextBlock(BaseModel):
    chunk_id: str
    document_id: UUID
    document_name: str
    page_start: int | None = None
    page_end: int | None = None
    text: str
```

## Validation Rules

- At least one context block should normally be supplied.
- If no context meets the minimum threshold, the answer service should return an insufficient-context response rather than invoking the LLM unnecessarily.
- Context block identifiers must match retrieved chunks.

---

# 17. LLM Generation Result Model

```python
class GenerationResult(BaseModel):
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    duration_ms: int
    raw_citation_ids: list[str] = []
    provider_request_id: str | None = None
```

## Design Notes

Provider-specific response objects must be converted into `GenerationResult`.

The raw provider response should not flow through application services.

Sensitive provider responses should not be included in standard logs.

---

# 18. Citation Model

A citation identifies the evidence supporting an answer.

```python
class Citation(BaseModel):
    citation_id: str
    chunk_id: str
    document_id: UUID
    document_name: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    excerpt: str
    retrieval_score: float | None = None
```

## Validation Rules

- A citation must refer to a retrieved chunk.
- The excerpt must be derived from the source chunk.
- Citation excerpts should be length-limited.
- The API must not expose full copyrighted pages unnecessarily.
- Page references should use one-based numbering.

---

# 19. Answer Model

```python
class Answer(BaseModel):
    request_id: UUID
    collection_id: UUID
    question: str
    answer: str
    status: AnswerStatus
    citations: list[Citation]
    created_at: datetime
    model: ModelUsage | None = None
    metrics: QueryMetrics
    retrieval_details: RetrievalResult | None = None
```

## Model Usage

```python
class ModelUsage(BaseModel):
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: Decimal | None = None
```

## Query Metrics

```python
class QueryMetrics(BaseModel):
    embedding_duration_ms: int
    retrieval_duration_ms: int
    prompt_build_duration_ms: int
    generation_duration_ms: int
    total_duration_ms: int
    retrieved_chunk_count: int
```

## Validation Rules

- `ANSWERED` responses should include at least one citation.
- `INSUFFICIENT_CONTEXT` responses may return no citations.
- Internal retrieval details should only be included when explicitly requested or enabled.
- Cost must be labeled as estimated unless obtained directly from authoritative billing data.

---

# 20. Error Model

All API errors should use a consistent structure.

```python
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None
```

```python
class ErrorResponse(BaseModel):
    request_id: UUID
    error: ErrorDetail
    timestamp: datetime
```

## Example

```json
{
  "request_id": "24e384fd-07a7-4e96-944c-1b6fca650471",
  "error": {
    "code": "DOCUMENT_TYPE_UNSUPPORTED",
    "message": "Only PDF documents are supported in Version 1.",
    "field": "file"
  },
  "timestamp": "2026-07-19T03:00:00Z"
}
```

---

# 21. Health and Readiness Models

## Health Response

```python
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
```

Example:

```json
{
  "status": "healthy",
  "service": "contexthub-api",
  "version": "0.1.0",
  "timestamp": "2026-07-19T03:00:00Z"
}
```

## Readiness Response

```python
class DependencyStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None
```

```python
class ReadinessResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]
    timestamp: datetime
```

Readiness checks may include:

- vector store loaded;
- embedding provider available;
- required configuration present;
- LLM provider reachable, when configured.

---

# 22. Evaluation Models

## Evaluation Question

```python
class EvaluationQuestion(BaseModel):
    id: str
    collection_id: UUID
    question: str
    answerable: bool
    expected_document_ids: list[UUID] = []
    expected_chunk_ids: list[str] = []
    reference_answer: str | None = None
    category: str | None = None
    metadata: dict[str, Any] = {}
```

## Retrieval Evaluation Result

```python
class RetrievalEvaluationResult(BaseModel):
    question_id: str
    recall_at_k: float
    reciprocal_rank: float
    retrieved_chunk_ids: list[str]
    expected_chunk_ids: list[str]
```

## Generation Evaluation Result

```python
class GenerationEvaluationResult(BaseModel):
    question_id: str
    groundedness_score: float | None = None
    answer_relevance_score: float | None = None
    citation_correctness_score: float | None = None
    abstention_correct: bool | None = None
    schema_valid: bool
    evaluator: str
```

## Evaluation Run

```python
class EvaluationRun(BaseModel):
    id: UUID
    dataset_version: str
    application_version: str
    embedding_provider: str
    embedding_model: str
    vector_store: str
    llm_provider: str
    llm_model: str
    chunking_configuration: ChunkingConfig
    started_at: datetime
    completed_at: datetime | None = None
    summary_metrics: dict[str, float] = {}
```

---

# 23. Configuration Models

Configuration should be loaded from environment variables or configuration files using Pydantic Settings.

```python
class ApplicationSettings(BaseSettings):
    app_name: str = "ContextHub"
    environment: str = "local"
    log_level: str = "INFO"

    max_upload_size_mb: int = 50
    default_top_k: int = 5

    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "all-MiniLM-L6-v2"

    vector_store_provider: str = "faiss"
    vector_index_path: str = "./data/index"

    llm_provider: str
    llm_model: str

    chunk_size: int = 1000
    chunk_overlap: int = 150
```

Secrets must not be represented in logs or API responses.

Examples include:

- API keys
- AWS credentials
- database passwords
- authentication tokens

---

# 24. Persistence Boundaries

The domain models do not dictate a specific database.

Version 1 may persist data using:

| Data | Initial Storage |
|---|---|
| Raw documents | Local filesystem |
| Document metadata | JSON or lightweight local repository |
| Chunks | FAISS metadata store or local persistence |
| Embeddings | FAISS |
| Evaluation datasets | JSONL |
| Logs | Standard output |

Future implementations may use:

| Data | Future Storage |
|---|---|
| Raw documents | Amazon S3 |
| Document metadata | PostgreSQL |
| Embeddings | pgvector or OpenSearch |
| Evaluation artifacts | S3 and MLflow |
| Logs and metrics | CloudWatch |

Application services should interact through repository interfaces rather than direct filesystem or database calls.

---

# 25. Metadata Guidelines

Metadata fields must support filtering and traceability without becoming an uncontrolled dumping ground.

Recommended document metadata:

```json
{
  "subject": "statistics",
  "edition": "third",
  "publisher": "example publisher",
  "publication_year": 2022
}
```

Recommended chunk metadata:

```json
{
  "chapter": "Linear Regression",
  "section": "Ordinary Least Squares",
  "page_start": 142,
  "page_end": 143
}
```

Metadata values should be JSON serializable.

Sensitive information should not be stored unless required and approved.

---

# 26. Data Lifecycle

## Document Creation

```text
Upload
    ↓
Document status = UPLOADED
    ↓
Ingestion begins
    ↓
Document status = PROCESSING
```

## Successful Ingestion

```text
Parsing complete
    ↓
Chunks created
    ↓
Embeddings generated
    ↓
Vector index updated
    ↓
Document status = READY
```

## Failed Ingestion

```text
Processing error
    ↓
Ingestion job = FAILED
    ↓
Document status = FAILED
    ↓
Error recorded
```

## Deletion

Future deletion should remove:

- original source file;
- document metadata;
- chunks;
- embeddings;
- vector index entries.

Deletion must not leave orphaned searchable chunks.

---

# 27. Idempotency

Uploading the same document multiple times should not unintentionally create duplicate index entries.

Version 1 duplicate detection should use:

```text
collection_id + SHA-256 checksum
```

Possible behavior:

- reject the duplicate;
- return the existing document;
- allow explicit replacement.

The exact API behavior will be defined in the API specification.

---

# 28. Versioning

The following components should be versioned:

- normalization logic;
- chunking configuration;
- embedding model;
- prompt template;
- evaluation dataset;
- application release.

This enables comparison across experiments and reproducible indexing.

Example:

```json
{
  "normalization_version": "1.0",
  "chunking_version": "recursive-1000-150-v1",
  "embedding_model": "all-MiniLM-L6-v2",
  "prompt_version": "qa-grounded-v1"
}
```

A change to the embedding model generally requires rebuilding the vector index.

A significant chunking change generally requires rechunking and re-embedding the corpus.

---

# 29. Privacy and Security Considerations

The data model should support future enterprise controls.

Future fields may include:

- tenant ID;
- owner ID;
- access classification;
- retention policy;
- data residency;
- document sensitivity;
- permitted roles.

Version 1 does not implement multi-user access control.

Uploaded documents should still be treated as untrusted input.

Filename, metadata, and extracted content must not be executed as code or treated as system instructions.

---

# 30. Version 1 Required Models

The first implementation must include:

- `Collection`
- `Document`
- `DocumentPage`
- `NormalizedDocument`
- `Chunk`
- `ChunkingConfig`
- `EmbeddingRecord`
- `IngestionJob`
- `IngestionMetrics`
- `QueryRequest`
- `RetrievedChunk`
- `RetrievalResult`
- `PromptRequest`
- `PromptContextBlock`
- `GenerationResult`
- `Citation`
- `Answer`
- `ModelUsage`
- `QueryMetrics`
- `ErrorResponse`
- `HealthResponse`
- `ReadinessResponse`
- `ApplicationSettings`

Evaluation models may be implemented after the initial query pipeline is functional.

---

# 31. Acceptance Criteria

This data model is considered ready for implementation when:

- Every major system component uses shared domain terminology.
- Provider-specific objects are excluded from the domain layer.
- Documents remain traceable to collections.
- Chunks remain traceable to documents and pages.
- Citations remain traceable to retrieved chunks.
- Query and answer models support structured API responses.
- Ingestion status and failure details are represented.
- Configuration supports provider replacement.
- Evaluation models support future RAG benchmarking.
- All models can be serialized into JSON-compatible representations.