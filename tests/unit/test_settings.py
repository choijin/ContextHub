import pytest
from pydantic import ValidationError

from contexthub.config.settings import ApplicationSettings


def test_settings_load_defaults() -> None:
    settings = ApplicationSettings(huggingface_model="test-model")

    assert settings.app_name == "ContextHub"
    assert settings.default_top_k == 5
    assert settings.embedding_provider == "sentence_transformers"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("chunk_size", 0),
        ("chunk_overlap", -1),
        ("embedding_batch_size", 0),
        ("llm_timeout_seconds", 0),
        ("llm_max_retries", -1),
        ("default_top_k", 0),
        ("max_top_k", 0),
    ],
)
def test_invalid_numeric_settings_fail_clearly(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match=field):
        ApplicationSettings(huggingface_model="test-model", **{field: value})


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="chunk_overlap"):
        ApplicationSettings(huggingface_model="test-model", chunk_size=100, chunk_overlap=100)


def test_default_top_k_must_not_exceed_max_top_k() -> None:
    with pytest.raises(ValidationError, match="default_top_k"):
        ApplicationSettings(huggingface_model="test-model", default_top_k=21, max_top_k=20)


def test_invalid_log_level_fails() -> None:
    with pytest.raises(ValidationError, match="log_level"):
        ApplicationSettings(huggingface_model="test-model", log_level="LOUD")
