"""Structured logging setup."""

import logging
from collections.abc import Mapping
from typing import Any


class KeyValueFormatter(logging.Formatter):
    """Small key-value formatter suitable for local and container logs."""

    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, Mapping):
            fields.update(extra)
        return " ".join(f"{key}={value}" for key, value in fields.items())


def configure_logging(log_level: str, service: str, environment: str) -> None:
    """Configure process logging with stable service metadata."""

    handler = logging.StreamHandler()
    handler.setFormatter(KeyValueFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)
    logging.getLogger("contexthub").info(
        "logging_configured",
        extra={"extra_fields": {"service": service, "environment": environment}},
    )
