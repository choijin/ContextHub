"""Retrieval-only evaluation service."""

from pathlib import Path

from contexthub.application.ports.retriever import Retriever
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.models.evaluation import (
    EvaluationCaseResult,
    EvaluationMetrics,
    EvaluationQuestion,
    EvaluationReport,
    EvaluationResult,
)


class RetrievalEvaluator:
    """Run JSONL evaluation cases against a retriever without generation."""

    def __init__(
        self,
        retriever: Retriever,
        settings: ApplicationSettings,
    ) -> None:
        self._retriever = retriever
        self._settings = settings

    def evaluate(
        self,
        questions: list[EvaluationQuestion],
        dataset_path: Path,
        top_k: int,
        similarity_threshold: float | None = None,
    ) -> EvaluationReport:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not questions:
            raise ValueError("evaluation dataset must contain at least one question")

        case_results = [
            self._evaluate_question(
                question=question,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )
            for question in questions
        ]
        metrics = self._calculate_metrics(case_results, top_k)
        return EvaluationReport(
            dataset_path=dataset_path,
            configuration=self._configuration_snapshot(top_k, similarity_threshold),
            metrics=metrics,
            cases=case_results,
        )

    def _evaluate_question(
        self,
        question: EvaluationQuestion,
        top_k: int,
        similarity_threshold: float | None,
    ) -> EvaluationCaseResult:
        retrieval_result = self._retriever.retrieve(
            question=question.question,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        retrieved_chunk_ids = [retrieved.chunk.id for retrieved in retrieval_result.chunks]
        retrieved_scores = [retrieved.score for retrieved in retrieval_result.chunks]
        expected_chunk_ids = set(question.expected_chunk_ids)

        if question.answerable:
            hits = [
                rank
                for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1)
                if chunk_id in expected_chunk_ids
            ]
            recall_at_k = len(set(retrieved_chunk_ids) & expected_chunk_ids) / len(
                expected_chunk_ids
            )
            hit_rate_at_k = 1.0 if hits else 0.0
            mrr = 1 / hits[0] if hits else 0.0
        else:
            recall_at_k = 0.0
            hit_rate_at_k = 0.0
            mrr = 0.0

        return EvaluationCaseResult(
            id=question.id,
            question=question.question,
            answerable=question.answerable,
            expected_chunk_ids=question.expected_chunk_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            retrieved_scores=retrieved_scores,
            result=EvaluationResult(
                recall_at_k=recall_at_k,
                hit_rate_at_k=hit_rate_at_k,
                mrr=mrr,
                latency_ms=retrieval_result.retrieval_duration_ms,
            ),
        )

    def _calculate_metrics(
        self,
        case_results: list[EvaluationCaseResult],
        top_k: int,
    ) -> EvaluationMetrics:
        answerable_results = [case for case in case_results if case.answerable]
        answerable_count = len(answerable_results)
        unanswerable_count = len(case_results) - answerable_count

        if answerable_results:
            recall_at_k = _average([case.result.recall_at_k for case in answerable_results])
            hit_rate_at_k = _average([case.result.hit_rate_at_k for case in answerable_results])
            mean_reciprocal_rank = _average([case.result.mrr for case in answerable_results])
        else:
            recall_at_k = 0.0
            hit_rate_at_k = 0.0
            mean_reciprocal_rank = 0.0

        return EvaluationMetrics(
            top_k=top_k,
            case_count=len(case_results),
            answerable_case_count=answerable_count,
            unanswerable_case_count=unanswerable_count,
            recall_at_k=recall_at_k,
            hit_rate_at_k=hit_rate_at_k,
            mean_reciprocal_rank=mean_reciprocal_rank,
            average_retrieval_latency_ms=_average(
                [case.result.latency_ms for case in case_results]
            ),
        )

    def _configuration_snapshot(
        self,
        top_k: int,
        similarity_threshold: float | None,
    ) -> dict[str, object]:
        return {
            "app_version": self._settings.app_version,
            "embedding_provider": self._settings.embedding_provider,
            "embedding_model": self._settings.embedding_model,
            "vector_store_provider": self._settings.vector_store_provider,
            "index_directory": str(self._settings.index_directory),
            "metadata_database_path": str(self._settings.metadata_database_path),
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
        }


def _average(values: list[float] | list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
