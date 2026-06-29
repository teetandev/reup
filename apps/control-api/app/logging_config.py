"""Logging configuration for the Control API."""

from __future__ import annotations

import logging
import re
from logging.config import dictConfig

_CONFIGURED = False

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


class SecretRedactingFilter(logging.Filter):
    """Redact secrets from log records."""

    SECRET_PATTERNS = [
        (re.compile(r'(NODE_TOKEN["\']?\s*[:=]\s*["\']?)([^"\'\s]+)'), r'\1***REDACTED***'),
        (re.compile(r'(GROQ_API_KEY["\']?\s*[:=]\s*["\']?)([^"\'\s]+)'), r'\1***REDACTED***'),
        (re.compile(r'(GEMINI_API_KEY["\']?\s*[:=]\s*["\']?)([^"\'\s]+)'), r'\1***REDACTED***'),
        (re.compile(r'(JWT_SECRET["\']?\s*[:=]\s*["\']?)([^"\'\s]+)'), r'\1***REDACTED***'),
        (re.compile(r'(upload_token["\']?\s*[:=]\s*["\']?)([^"\'\s]{10,})'), r'\1***REDACTED***'),
        (re.compile(r'(Bearer\s+)([A-Za-z0-9_-]{20,})'), r'\1***REDACTED***'),
        (re.compile(r'(sub_live_[a-z0-9]{4})[a-z0-9]+'), r'\1***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.SECRET_PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(v) for v in record.args)
        return True

    def _redact_value(self, value):
        if isinstance(value, str):
            for pattern, replacement in self.SECRET_PATTERNS:
                value = pattern.sub(replacement, value)
        return value


def configure_logging(level: str = "INFO") -> None:
    """Configure root + uvicorn loggers with a concise, consistent format.

    Idempotent: safe to call more than once (e.g. on reload).
    """
    global _CONFIGURED
    level = (level or "INFO").upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": _LOG_FORMAT}},
            "filters": {
                "secret_redacting": {
                    "()": SecretRedactingFilter,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["secret_redacting"],
                }
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                # Let uvicorn loggers propagate through our handler/format.
                "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": level, "propagate": False},
            },
        }
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger, ensuring logging is configured at least once."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
