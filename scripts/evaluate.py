"""Offline retrieval evaluation harness."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from contexthub.api.dependencies import get_runtime_container
from contexthub.application.services.retrieval_evaluator import RetrievalEvaluator
from contexthub.config.settings import ApplicationSettings
from contexthub.domain.exceptions import ContextHubError
from contexthub.domain.models.evaluation import EvaluationQuestion, EvaluationReport
from contexthub.observability.logging import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval against a JSONL dataset.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to JSONL evaluation cases.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for versioned JSON reports.",
    )
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--similarity-threshold", type=float, default=None)
    args = parser.parse_args(argv)

    settings = ApplicationSettings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)

    dataset_path = args.dataset or settings.evaluation_directory / "evaluation_questions.jsonl"
    output_dir = args.output_dir or settings.evaluation_directory / "reports"
    top_k = args.top_k or settings.default_top_k

    try:
        questions = load_evaluation_questions(dataset_path)
    except (OSError, ValueError, ValidationError) as exc:
        print(f"Invalid evaluation dataset: {exc}", file=sys.stderr)
        return 1

    runtime = get_runtime_container(settings)
    if runtime.retrieval_service is None:
        print("Retrieval runtime is not ready.", file=sys.stderr)
        for check in runtime.checks:
            print(f"- {check.name}: {check.detail}", file=sys.stderr)
        runtime.close()
        return 1

    try:
        evaluator = RetrievalEvaluator(
            retriever=runtime.retrieval_service,
            settings=settings,
        )
        report = evaluator.evaluate(
            questions=questions,
            dataset_path=dataset_path,
            top_k=top_k,
            similarity_threshold=args.similarity_threshold,
        )
        report_path = write_report(report, output_dir)
    except (ContextHubError, OSError, ValueError) as exc:
        print(f"Retrieval evaluation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        runtime.close()

    metrics = report.metrics
    print(
        "retrieval_evaluation_completed "
        f"cases={metrics.case_count} "
        f"answerable={metrics.answerable_case_count} "
        f"unanswerable={metrics.unanswerable_case_count} "
        f"top_k={metrics.top_k} "
        f"recall_at_k={metrics.recall_at_k:.4f} "
        f"hit_rate_at_k={metrics.hit_rate_at_k:.4f} "
        f"mrr={metrics.mean_reciprocal_rank:.4f} "
        f"average_latency_ms={metrics.average_retrieval_latency_ms:.2f} "
        f"report={report_path}"
    )
    return 0


def load_evaluation_questions(path: Path) -> list[EvaluationQuestion]:
    questions: list[EvaluationQuestion] = []
    seen_ids: set[str] = set()

    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                question = EvaluationQuestion.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"{path}:{line_number}: malformed evaluation case") from exc
            if question.id in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate evaluation id {question.id!r}")
            seen_ids.add(question.id)
            questions.append(question)

    if not questions:
        raise ValueError("evaluation dataset must contain at least one question")
    return questions


def write_report(report: EvaluationReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    report_path = output_dir / f"retrieval_evaluation_{timestamp}.json"
    report.report_path = report_path
    payload = report.model_dump(mode="json")
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


if __name__ == "__main__":
    raise SystemExit(main())
