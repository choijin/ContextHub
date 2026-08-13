from uuid import uuid4

from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.query import RetrievedChunk
from contexthub.infrastructure.prompts.grounded_qa_prompt_builder import GroundedQAPromptBuilder


def test_prompt_builder_includes_question_and_retrieved_chunks() -> None:
    builder = GroundedQAPromptBuilder(max_context_characters=2000)

    prompt = builder.build(
        "What is probability?",
        [_retrieved_chunk("chunk-a", "Probability measures uncertainty.", rank=1)],
    )

    assert builder.prompt_version == "grounded_qa_v1"
    assert prompt.question == "What is probability?"
    assert "Do not use outside knowledge" in prompt.system_prompt
    assert "Do not use Markdown, LaTeX, or raw backslashes" in prompt.system_prompt
    assert "answerable" in prompt.system_prompt
    assert '"answerable": false, "answer": ""' in prompt.system_prompt
    assert "cited_source_indices" in prompt.system_prompt
    assert prompt.context[0].source_index == 1
    assert prompt.context[0].chunk_id == "chunk-a"
    assert prompt.context[0].document_name == "stats.pdf"
    assert prompt.context[0].text == "Probability measures uncertainty."


def test_prompt_builder_enforces_context_budget_without_splitting_chunks() -> None:
    builder = GroundedQAPromptBuilder(max_context_characters=180)
    chunks = [
        _retrieved_chunk("chunk-a", "alpha " * 10, rank=1),
        _retrieved_chunk("chunk-b", "beta " * 10, rank=2),
    ]

    prompt = builder.build("question", chunks)

    assert [context.chunk_id for context in prompt.context] == ["chunk-a"]
    assert prompt.context[0].text == "alpha " * 10


def test_prompt_builder_includes_at_least_one_chunk_when_first_exceeds_budget() -> None:
    builder = GroundedQAPromptBuilder(max_context_characters=10)

    prompt = builder.build("question", [_retrieved_chunk("chunk-a", "alpha " * 50, rank=1)])

    assert [context.chunk_id for context in prompt.context] == ["chunk-a"]


def _retrieved_chunk(chunk_id: str, text: str, rank: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=chunk_id,
            document_id=uuid4(),
            text=text,
            chunk_index=rank - 1,
            page_start=rank,
            page_end=rank,
            content_hash=f"hash-{rank}",
        ),
        score=0.9,
        rank=rank,
        document_name="stats.pdf",
    )
