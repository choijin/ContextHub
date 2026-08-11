"""Composition helpers for runtime dependencies."""

import logging

from contexthub.application.runtime import ReadinessCheck, RuntimeContainer
from contexthub.application.services.citation_builder import CitationBuilder
from contexthub.application.services.query_service import QueryService
from contexthub.application.services.retrieval_service import RetrievalService
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.exceptions import ContextHubError
from contexthub.infrastructure.embeddings.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)
from contexthub.infrastructure.index.manifest import (
    load_manifest,
    validate_manifest,
    validate_manifest_settings,
)
from contexthub.infrastructure.llms.huggingface_provider import HuggingFaceLLMProvider
from contexthub.infrastructure.prompts.grounded_qa_prompt_builder import GroundedQAPromptBuilder
from contexthub.infrastructure.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)
from contexthub.infrastructure.vectorstores.faiss_vector_store import FaissVectorStore


def build_runtime_container(settings: ApplicationSettings) -> RuntimeContainer:
    """Build runtime dependencies for retrieval."""

    checks: list[ReadinessCheck] = [
        ReadinessCheck(name="settings", ready=True, detail="Application settings loaded.")
    ]
    try:
        return _build_ready_container(settings, checks)
    except ContextHubError as exc:
        checks.append(
            ReadinessCheck(
                name="index",
                ready=False,
                detail=str(exc),
            )
        )
        return RuntimeContainer(initialized=True, checks=checks)


def _build_ready_container(
    settings: ApplicationSettings,
    checks: list[ReadinessCheck],
) -> RuntimeContainer:
    manifest = load_manifest(settings.index_directory)
    validate_manifest_settings(manifest, settings)
    checks.append(ReadinessCheck(name="manifest", ready=True, detail="Index manifest loaded."))

    embedding_provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.embedding_model,
        batch_size=settings.embedding_batch_size,
        device=settings.embedding_device,
    )
    embedding_dimensions = embedding_provider.dimensions
    validate_manifest(manifest, settings, embedding_dimensions)
    checks.append(
        ReadinessCheck(
            name="embedding_provider",
            ready=True,
            detail="Embedding provider initialized and manifest-compatible.",
        )
    )

    vector_store = FaissVectorStore(dimensions=embedding_dimensions)
    vector_store.load(settings.index_directory)
    if vector_store.vector_count != manifest.chunk_count:
        msg = "FAISS vector count does not match manifest chunk count."
        raise ContextHubError(msg)
    checks.append(ReadinessCheck(name="faiss", ready=True, detail="FAISS index loaded."))

    repository = SQLiteDocumentRepository(settings.metadata_database_path, read_only=True)
    if repository.chunk_count() != manifest.chunk_count:
        repository.close()
        msg = "SQLite chunk count does not match manifest chunk count."
        raise ContextHubError(msg)
    repository.validate_faiss_positions(vector_store.vector_count)
    checks.append(
        ReadinessCheck(
            name="metadata_database",
            ready=True,
            detail="SQLite metadata database opened and FAISS positions validated.",
        )
    )

    retrieval_service = RetrievalService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        document_repository=repository,
        settings=settings,
        logger=logging.getLogger("contexthub.retrieval"),
    )
    if not settings.has_required_llm_configuration:
        checks.append(
            ReadinessCheck(
                name="llm_provider",
                ready=False,
                detail="Hugging Face model and API token are required for query generation.",
            )
        )
        return RuntimeContainer(
            initialized=True,
            checks=checks,
            retrieval_service=retrieval_service,
            document_repository=repository,
            manifest=manifest,
        )

    llm_provider = HuggingFaceLLMProvider(
        api_token=settings.huggingface_api_token.get_secret_value()
        if settings.huggingface_api_token is not None
        else "",
        model_name=settings.huggingface_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    prompt_builder = GroundedQAPromptBuilder(
        max_context_characters=settings.max_context_characters,
    )
    citation_builder = CitationBuilder()
    query_service = QueryService(
        retriever=retrieval_service,
        prompt_builder=prompt_builder,
        llm_provider=llm_provider,
        citation_builder=citation_builder,
        settings=settings,
        logger=logging.getLogger("contexthub.query"),
    )
    checks = [
        *checks,
        ReadinessCheck(
            name="retrieval_service",
            ready=True,
            detail="Retrieval service initialized.",
        ),
        ReadinessCheck(
            name="llm_provider",
            ready=True,
            detail="LLM provider initialized.",
        ),
        ReadinessCheck(
            name="query_service",
            ready=True,
            detail="Grounded query service initialized.",
        ),
    ]
    return RuntimeContainer(
        initialized=True,
        checks=checks,
        retrieval_service=retrieval_service,
        query_service=query_service,
        document_repository=repository,
        llm_provider=llm_provider,
        manifest=manifest,
    )


def get_runtime_container(settings: ApplicationSettings) -> RuntimeContainer:
    return build_runtime_container(settings)
