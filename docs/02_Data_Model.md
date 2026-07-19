# Data Model

**Project:** ContextHub\
**Subtitle:** Production-Oriented RAG Reference Application\
**Version:** 1.0\
**Status:** Ready for Implementation

------------------------------------------------------------------------

# 1. Purpose

This document defines the core domain models shared across the
application.

The models are intentionally independent of FastAPI, FAISS, SQLite, Hugging
Face, PyMuPDF, and other third-party libraries. Infrastructure adapters
are responsible for translating between provider-specific objects and
these domain models.

------------------------------------------------------------------------

# 2. Design Principles

The data model should be:

-   Provider independent
-   JSON serializable
-   Strongly typed
-   Traceable
-   Deterministic where practical
-   Easy to test

Runtime data should represent the query pipeline only. Documents are
indexed offline before the API starts.

------------------------------------------------------------------------

# 3. Entity Relationships

``` text
PDF
 │
 ▼
Document
 │
 ├── DocumentPage
 │
 └── Chunk
       │
       ▼
RetrievedChunk
       │
       ▼
PromptContext
       │
       ▼
GenerationResult
       │
       ▼
Citation
       │
       ▼
Answer
```

------------------------------------------------------------------------

# 4. Identifier Strategy

Use deterministic identifiers where appropriate. Request IDs use UUIDv4. Document and chunk identifiers should be deterministic so rebuilt indexes remain stable.

Chunk IDs should be deterministic and derived from:

-   document id
-   page range
-   chunk index
-   content hash

This allows rebuilding the index without changing chunk identities.

------------------------------------------------------------------------

# 5. Enumerations

``` python
class SourceType(str, Enum):
    PDF = "pdf"

class RetrievalStrategy(str, Enum):
    SIMILARITY = "similarity"

class AnswerStatus(str, Enum):
    ANSWERED = "answered"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    PROVIDER_ERROR = "provider_error"
```

------------------------------------------------------------------------

# 6. Core Models

## Document

Represents one indexed PDF.

``` python
class Document(BaseModel):
    id: UUID  # deterministic UUIDv5 or equivalent recommended
    filename: str
    title: str | None
    checksum_sha256: str
    page_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## DocumentPage

``` python
class DocumentPage(BaseModel):
    document_id: UUID
    page_number: int
    text: str
```

## NormalizedDocument

``` python
class NormalizedDocument(BaseModel):
    document_id: UUID
    pages: list[DocumentPage]
```

## Chunk

``` python
class Chunk(BaseModel):
    id: str
    document_id: UUID
    text: str
    chunk_index: int
    page_start: int
    page_end: int
    content_hash: str
```

Each chunk must preserve enough metadata to generate citations.

------------------------------------------------------------------------

# 7. Chunking Configuration

``` python
class ChunkingConfig(BaseModel):
    chunk_size: int = 1000
    chunk_overlap: int = 150
```

Validation:

-   chunk_size \> 0
-   overlap \>= 0
-   overlap \< chunk_size

------------------------------------------------------------------------

# 8. Retrieval Models

``` python
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
```

``` python
class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float
    rank: int
```

``` python
class RetrievalResult(BaseModel):
    request_id: UUID
    query: str
    chunks: list[RetrievedChunk]
    retrieval_duration_ms: int
```

Scores returned from the VectorStore should be normalized so larger
values always represent better matches.

------------------------------------------------------------------------

# 9. Prompt Models

``` python
class PromptContext(BaseModel):
    chunk_id: str
    document_name: str
    page_start: int
    page_end: int
    text: str
```

``` python
class PromptRequest(BaseModel):
    system_prompt: str
    question: str
    context: list[PromptContext]
```

Prompt models are provider independent.

------------------------------------------------------------------------

# 10. Generation Models

``` python
class GenerationResult(BaseModel):
    text: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
```

------------------------------------------------------------------------

# 11. Citation Models

``` python
class Citation(BaseModel):
    chunk_id: str
    document_name: str
    page_start: int
    page_end: int
    excerpt: str
```

Every citation must correspond to a retrieved chunk.

------------------------------------------------------------------------

# 12. Answer Model

``` python
class Answer(BaseModel):
    request_id: UUID
    question: str
    answer: str
    status: AnswerStatus
    citations: list[Citation]
```

Grounded answers should contain citations. Insufficient-context
responses may return an empty citation list.

------------------------------------------------------------------------

# 13. Evaluation Models

``` python
class EvaluationQuestion(BaseModel):
    id: str
    question: str
    expected_chunk_ids: list[str]
    answerable: bool
```

``` python
class EvaluationResult(BaseModel):
    recall_at_k: float
    mrr: float
    latency_ms: int
```

These models support offline retrieval evaluation and are not part of the runtime API. They allow Version 1 to measure retrieval quality before introducing framework abstractions in Version 2.

------------------------------------------------------------------------


# 14. Persistence Mapping

SQLite is an infrastructure concern and does not replace the domain models.

Recommended tables:

```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    title TEXT,
    checksum_sha256 TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    faiss_position INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);
```

`faiss_position` is persistence metadata used to map a FAISS result to a chunk.
It must not be added to the provider-independent `Chunk` domain model.

The ingestion transaction must write all document and chunk rows consistently before
the completed index directory replaces the previous active directory.

------------------------------------------------------------------------

# 15. Configuration

``` python
class ApplicationSettings(BaseSettings):
    chunk_size: int = 1000
    chunk_overlap: int = 150
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_provider: str = "huggingface"
    top_k: int = 5
```

Configuration is loaded from environment variables. The models remain independent of Streamlit, FastAPI, FAISS, and any future orchestration framework such as LangChain.

------------------------------------------------------------------------

# 16. Version 1 Required Models

-   Document
-   DocumentPage
-   NormalizedDocument
-   Chunk
-   ChunkingConfig
-   QueryRequest
-   RetrievedChunk
-   RetrievalResult
-   PromptContext
-   PromptRequest
-   GenerationResult
-   Citation
-   Answer
-   EvaluationQuestion
-   EvaluationResult
-   ApplicationSettings

------------------------------------------------------------------------

# 17. Acceptance Criteria

The data model is complete when:

-   Provider SDK objects never appear in domain models.
-   Documents remain traceable to source pages.
-   Chunks remain traceable to documents.
-   Every FAISS vector position resolves to exactly one SQLite chunk record.
-   Citations remain traceable to chunks.
-   Query and answer models are provider independent.
-   All models serialize cleanly to JSON.
