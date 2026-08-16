from pathlib import Path
from uuid import UUID, uuid4

from contexthub.application.services.retrieval_evaluator import RetrievalEvaluator
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.models.chunk import Chunk
from contexthub.domain.models.evaluation import EvaluationQuestion
from contexthub.domain.models.query import RetrievalResult, RetrievedChunk


def test_retrieval_evaluator_calculates_required_metrics() -> None:
    document_id = uuid4()
    retriever = StaticRetriever(
        {
            "alpha question": _retrieval_result(
                [
                    _retrieved_chunk("chunk-a", document_id, rank=1, score=0.9),
                    _retrieved_chunk("chunk-b", document_id, rank=2, score=0.8),
                ],
                latency_ms=10,
            ),
            "missing question": _retrieval_result(
                [_retrieved_chunk("chunk-c", document_id, rank=1, score=0.7)],
                latency_ms=20,
            ),
            "unanswerable question": _retrieval_result(
                [_retrieved_chunk("chunk-z", document_id, rank=1, score=0.6)],
                latency_ms=30,
            ),
        }
    )
    evaluator = RetrievalEvaluator(
        retriever=retriever,
        settings=ApplicationSettings(huggingface_model="test-model"),
    )

    report = evaluator.evaluate(
        questions=[
            EvaluationQuestion(
                id="q1",
                question="alpha question",
                expected_chunk_ids=["chunk-b"],
                answerable=True,
            ),
            EvaluationQuestion(
                id="q2",
                question="missing question",
                expected_chunk_ids=["chunk-missing"],
                answerable=True,
            ),
            EvaluationQuestion(
                id="q3",
                question="unanswerable question",
                expected_chunk_ids=[],
                answerable=False,
            ),
        ],
        dataset_path=Path("eval.jsonl"),
        top_k=2,
        similarity_threshold=0.25,
    )

    assert report.metrics.case_count == 3
    assert report.metrics.answerable_case_count == 2
    assert report.metrics.unanswerable_case_count == 1
    assert report.metrics.recall_at_k == 0.5
    assert report.metrics.hit_rate_at_k == 0.5
    assert report.metrics.mean_reciprocal_rank == 0.25
    assert report.metrics.average_retrieval_latency_ms == 20
    assert report.cases[0].result.recall_at_k == 1
    assert report.cases[0].result.mrr == 0.5
    assert report.cases[1].result.hit_rate_at_k == 0
    assert report.cases[2].result.recall_at_k == 0
    assert retriever.calls == [
        ("alpha question", 2, 0.25),
        ("missing question", 2, 0.25),
        ("unanswerable question", 2, 0.25),
    ]


def test_retrieval_evaluator_handles_multi_expected_chunk_recall() -> None:
    document_id = uuid4()
    retriever = StaticRetriever(
        {
            "multi": _retrieval_result(
                [
                    _retrieved_chunk("chunk-a", document_id, rank=1, score=0.9),
                    _retrieved_chunk("chunk-c", document_id, rank=2, score=0.7),
                ],
                latency_ms=5,
            )
        }
    )
    evaluator = RetrievalEvaluator(
        retriever=retriever,
        settings=ApplicationSettings(huggingface_model="test-model"),
    )

    report = evaluator.evaluate(
        questions=[
            EvaluationQuestion(
                id="q1",
                question="multi",
                expected_chunk_ids=["chunk-a", "chunk-b"],
                answerable=True,
            )
        ],
        dataset_path=Path("eval.jsonl"),
        top_k=2,
    )

    assert report.metrics.recall_at_k == 0.5
    assert report.metrics.hit_rate_at_k == 1
    assert report.metrics.mean_reciprocal_rank == 1


class StaticRetriever:
    def __init__(self, results: dict[str, RetrievalResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, int, float | None]] = []

    def retrieve(
        self,
        question: str,
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> RetrievalResult:
        self.calls.append((question, top_k, similarity_threshold))
        return self.results[question]


def _retrieval_result(chunks: list[RetrievedChunk], latency_ms: int) -> RetrievalResult:
    return RetrievalResult(
        request_id=uuid4(),
        query="query",
        chunks=chunks,
        retrieval_duration_ms=latency_ms,
    )


def _retrieved_chunk(
    chunk_id: str,
    document_id: UUID,
    rank: int,
    score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=chunk_id,
            document_id=document_id,
            text=f"text for {chunk_id}",
            chunk_index=rank - 1,
            page_start=1,
            page_end=1,
            content_hash=f"hash-{chunk_id}",
        ),
        score=score,
        rank=rank,
        document_name="fixture.pdf",
    )
