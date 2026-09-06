"""Render the Cloud Run service manifest from deployment variables."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from string import Template
from typing import Final

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "deploy" / "cloud-run-service.template.yaml"
OUTPUT_PATH = PROJECT_ROOT / "deploy" / "cloud-run-service.yaml"
DEFAULT_REGION: Final = "us-central1"
DEFAULT_IMAGE_TAG: Final = "latest"
DEFAULT_HUGGINGFACE_MODEL: Final = "openai/gpt-oss-20b:fastest"


def environment_value(name: str) -> str:
    """Return a stripped environment variable or an empty string."""
    return os.getenv(name, "").strip()


def gcloud_value(arguments: list[str]) -> str:
    """Run gcloud and return one configuration value."""
    executable = shutil.which("gcloud")
    if executable is None:
        fallback = Path.home() / "google-cloud-sdk" / "bin" / "gcloud"
        executable = str(fallback) if fallback.is_file() else None
    if executable is None:
        raise SystemExit("gcloud is required to resolve deployment configuration.")

    completed = subprocess.run(
        [executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unknown gcloud error"
        raise SystemExit(f"gcloud configuration lookup failed: {detail}")

    value = completed.stdout.strip()
    return "" if value == "(unset)" else value


def resolve_template_values() -> dict[str, str]:
    """Resolve deployment values from overrides and active gcloud configuration."""
    project_id = environment_value("PROJECT_ID") or gcloud_value(["config", "get-value", "project"])
    if not project_id:
        raise SystemExit("Set PROJECT_ID or select a project with gcloud config set project.")

    project_number = environment_value("PROJECT_NUMBER") or gcloud_value(
        ["projects", "describe", project_id, "--format=value(projectNumber)"]
    )
    if not project_number:
        raise SystemExit("Could not resolve the Google Cloud project number.")

    region = environment_value("REGION") or gcloud_value(["config", "get-value", "run/region"])
    region = region or DEFAULT_REGION
    image_tag = environment_value("IMAGE_TAG") or DEFAULT_IMAGE_TAG
    model = environment_value("HUGGINGFACE_MODEL") or DEFAULT_HUGGINGFACE_MODEL
    image_url = f"{region}-docker.pkg.dev/{project_id}/contexthub/contexthub:{image_tag}"

    return {
        "PROJECT_ID": project_id,
        "PROJECT_NUMBER": project_number,
        "IMAGE_URL": image_url,
        "HUGGINGFACE_MODEL": model,
    }


def main() -> None:
    """Render the deployable manifest without placing secrets in it."""
    values = resolve_template_values()
    rendered = Template(TEMPLATE_PATH.read_text(encoding="utf-8")).substitute(values)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Rendered {OUTPUT_PATH}")
    print(f"Container image: {values['IMAGE_URL']}")


if __name__ == "__main__":
    main()
