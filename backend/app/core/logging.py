"""Structured logging setup.

Logs are emitted as single-line JSON so they can be consumed by log
collectors. Sensitive values (passwords, API keys, tokens) must never be
passed to log calls.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_LOGGER_NAME = "roleshift"


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter with no external dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure root logging once and return the application logger."""
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]

    logger = logging.getLogger(_LOGGER_NAME)
    logger.propagate = True
    return logger


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return a child logger, e.g. get_logger("api.routes.roles")."""
    return logging.getLogger(f"{_LOGGER_NAME}.{name}" if name != _LOGGER_NAME else name)