from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from contexthub.config.settings import ApplicationSettings
from contexthub.main import create_app


def make_settings(**overrides: object) -> ApplicationSettings:
    values = {
        "allow_start_without_index": True,
        "huggingface_model": "test-model",
    }
    values.update(overrides)
    return ApplicationSettings(**values)


@contextmanager
def make_client(**settings_overrides: object) -> Iterator[TestClient]:
    app = create_app(make_settings(**settings_overrides))
    with TestClient(app) as client:
        yield client
