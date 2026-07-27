"""Development-only retrieval harness."""

import argparse
import sys

from contexthub.api.dependencies import get_runtime_container
from contexthub.config.settings import ApplicationSettings
from contexthub.observability.logging import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve ranked chunks from the saved index.")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--similarity-threshold", type=float, default=None)
    args = parser.parse_args(argv)

    settings = ApplicationSettings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    runtime = get_runtime_container(settings)
    if not runtime.ready or runtime.retrieval_service is None:
        print("Retrieval runtime is not ready.", file=sys.stderr)
        for check in runtime.checks:
            print(f"- {check.name}: {check.detail}", file=sys.stderr)
        runtime.close()
        return 1

    try:
        result = runtime.retrieval_service.retrieve(
            question=args.question,
            top_k=args.top_k or settings.default_top_k,
            similarity_threshold=args.similarity_threshold,
        )
    finally:
        runtime.close()

    print(
        f"request_id={result.request_id} "
        f"chunks={len(result.chunks)} "
        f"duration_ms={result.retrieval_duration_ms}"
    )
    for retrieved in result.chunks:
        chunk = retrieved.chunk
        preview = " ".join(chunk.text.split())[:240]
        print(
            f"\n#{retrieved.rank} score={retrieved.score:.4f} "
            f"chunk_id={chunk.id} pages={chunk.page_start}-{chunk.page_end}"
        )
        print(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
