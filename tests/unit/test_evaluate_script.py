import json
from pathlib import Path

import pytest

from contexthub.domain.models.evaluation import (
    EvaluationCaseResult,
    EvaluationMetrics,
    EvaluationReport,
    EvaluationResult,
)
from scripts.evaluate import load_evaluation_questions, write_report


def test_load_evaluation_questions_reads_jsonl_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "evaluation.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                '{"id":"q1","question":"What is alpha?","expected_chunk_ids":["chunk-a"],'
                '"answerable":true}',
                "",
                '{"id":"q2","question":"What is unavailable?","expected_chunk_ids":[],'
                '"answerable":false}',
            ]
        ),
        encoding="utf-8",
    )

    questions = load_evaluation_questions(dataset_path)

    assert [question.id for question in questions] == ["q1", "q2"]
    assert questions[0].expected_chunk_ids == ["chunk-a"]
    assert questions[1].answerable is False


def test_load_evaluation_questions_rejects_malformed_jsonl(tmp_path: Path) -> None:
    dataset_path = tmp_path / "evaluation.jsonl"
    dataset_path.write_text('{"id":"q1","question":"broken"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="malformed evaluation case"):
        load_evaluation_questions(dataset_path)


def test_load_evaluation_questions_rejects_duplicate_ids(tmp_path: Path) -> None:
    dataset_path = tmp_path / "evaluation.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                '{"id":"q1","question":"What is alpha?","expected_chunk_ids":["chunk-a"],'
                '"answerable":true}',
                '{"id":"q1","question":"What is beta?","expected_chunk_ids":["chunk-b"],'
                '"answerable":true}',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate evaluation id"):
        load_evaluation_questions(dataset_path)


def test_load_evaluation_questions_rejects_invalid_answerability(tmp_path: Path) -> None:
    dataset_path = tmp_path / "evaluation.jsonl"
    dataset_path.write_text(
        '{"id":"q1","question":"What is alpha?","expected_chunk_ids":[],"answerable":true}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="malformed evaluation case"):
        load_evaluation_questions(dataset_path)


def test_write_report_uses_deterministic_schema(tmp_path: Path) -> None:
    report = EvaluationReport(
        dataset_path=Path("data/evaluation/evaluation_questions.jsonl"),
        configuration={"top_k": 2, "embedding_model": "fake-model"},
        metrics=EvaluationMetrics(
            top_k=2,
            case_count=1,
            answerable_case_count=1,
            unanswerable_case_count=0,
            recall_at_k=1,
            hit_rate_at_k=1,
            mean_reciprocal_rank=1,
            average_retrieval_latency_ms=12,
        ),
        cases=[
            EvaluationCaseResult(
                id="q1",
                question="What is alpha?",
                answerable=True,
                expected_chunk_ids=["chunk-a"],
                retrieved_chunk_ids=["chunk-a"],
                retrieved_scores=[0.9],
                result=EvaluationResult(
                    recall_at_k=1,
                    hit_rate_at_k=1,
                    mrr=1,
                    latency_ms=12,
                ),
            )
        ],
    )

    report_path = write_report(report, tmp_path)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_path.name.startswith("retrieval_evaluation_")
    assert set(payload) == {
        "cases",
        "configuration",
        "dataset_path",
        "generated_at",
        "metrics",
        "report_path",
        "schema_version",
    }
    assert payload["schema_version"] == "1.0"
    assert payload["report_path"] == str(report_path)
    assert set(payload["metrics"]) == {
        "answerable_case_count",
        "average_retrieval_latency_ms",
        "case_count",
        "hit_rate_at_k",
        "mean_reciprocal_rank",
        "recall_at_k",
        "top_k",
        "unanswerable_case_count",
    }
    assert set(payload["cases"][0]) == {
        "answerable",
        "expected_chunk_ids",
        "id",
        "question",
        "result",
        "retrieved_chunk_ids",
        "retrieved_scores",
    }
