"""Tests for the Cloud Run manifest renderer."""

import pytest

from scripts import render_cloud_run_service

DEPLOYMENT_VARIABLES = (
    "PROJECT_ID",
    "PROJECT_NUMBER",
    "REGION",
    "IMAGE_TAG",
    "HUGGINGFACE_MODEL",
)


def clear_deployment_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in DEPLOYMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def test_resolve_template_values_uses_gcloud_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_deployment_environment(monkeypatch)
    values_by_command = {
        ("config", "get-value", "project"): "contexthub-rag-app",
        (
            "projects",
            "describe",
            "contexthub-rag-app",
            "--format=value(projectNumber)",
        ): "825051407585",
        ("config", "get-value", "run/region"): "us-central1",
    }
    monkeypatch.setattr(
        render_cloud_run_service,
        "gcloud_value",
        lambda arguments: values_by_command[tuple(arguments)],
    )

    values = render_cloud_run_service.resolve_template_values()

    assert values == {
        "PROJECT_ID": "contexthub-rag-app",
        "PROJECT_NUMBER": "825051407585",
        "IMAGE_URL": ("us-central1-docker.pkg.dev/contexthub-rag-app/contexthub/contexthub:latest"),
        "HUGGINGFACE_MODEL": "openai/gpt-oss-20b:fastest",
    }


def test_resolve_template_values_prefers_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overrides = {
        "PROJECT_ID": "alternate-project",
        "PROJECT_NUMBER": "123456789",
        "REGION": "us-east1",
        "IMAGE_TAG": "abc123",
        "HUGGINGFACE_MODEL": "example/model",
    }
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        render_cloud_run_service,
        "gcloud_value",
        lambda arguments: pytest.fail(f"Unexpected gcloud call: {arguments}"),
    )

    values = render_cloud_run_service.resolve_template_values()

    assert values["PROJECT_ID"] == "alternate-project"
    assert values["PROJECT_NUMBER"] == "123456789"
    assert values["IMAGE_URL"].endswith("/contexthub/contexthub:abc123")
    assert values["IMAGE_URL"].startswith("us-east1-docker.pkg.dev/")
    assert values["HUGGINGFACE_MODEL"] == "example/model"


def test_resolve_template_values_requires_an_active_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_deployment_environment(monkeypatch)
    monkeypatch.setattr(render_cloud_run_service, "gcloud_value", lambda arguments: "")

    with pytest.raises(SystemExit, match="select a project"):
        render_cloud_run_service.resolve_template_values()
