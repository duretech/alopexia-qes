"""Structured JSON logging setup using structlog.

In production: JSON renderer (machine-parseable, shipped to log aggregator).
In development: colored console renderer (human-friendly).

Standard fields on every log line:
  timestamp, level, logger, event, request_id, correlation_id

Integrates with stdlib logging so SQLAlchemy, uvicorn, and other libraries
also emit structured JSON.
"""

import logging
import sys
import re
from typing import Any

import structlog


# Sensitive field patterns to redact from logs
_SENSITIVE_FIELDS = {
    "password", "pin", "pin_encrypted", "otp", "otp_encrypted", "token",
    "auth_token", "session_id", "secret", "api_key", "access_key",
    "phone", "phone_encrypted", "email", "ssn", "tax_id",
    "credit_card", "bank_account"
}

_SENSITIVE_PATTERNS = {
    "password": re.compile(r"password[\"']?\s*[:=]\s*[\"']?[^\"'\s]+", re.IGNORECASE),
    "token": re.compile(r"(auth|bearer|token)[\"']?\s*[:=]\s*[\"']?[^\"'\s]+", re.IGNORECASE),
    "pin": re.compile(r"pin[\"']?\s*[:=]\s*\d+", re.IGNORECASE),
    "phone": re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", re.IGNORECASE),
}


def _mask_sensitive_data(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields from log events.

    This processor masks:
    - Known sensitive field names (password, token, pin, etc.)
    - Field values that match sensitive patterns (phone numbers, etc.)
    """
    masked_dict = {}
    for key, value in event_dict.items():
        if key.lower() in _SENSITIVE_FIELDS or any(pat in key.lower() for pat in _SENSITIVE_FIELDS):
            # Mask the entire field
            masked_dict[key] = "***REDACTED***"
        elif isinstance(value, str):
            # Check against regex patterns
            redacted = value
            for pattern_name, pattern in _SENSITIVE_PATTERNS.items():
                redacted = pattern.sub(f"***{pattern_name.upper()}_REDACTED***", redacted)
            masked_dict[key] = redacted
        else:
            masked_dict[key] = value
    return masked_dict


def setup_logging(*, log_level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog and stdlib logging for the entire application.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: True for JSON renderer (production), False for console (dev).
    """
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors applied to every log event (structlog + stdlib)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _mask_sensitive_data,  # Redact sensitive fields from all logs
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            # Format exception info for the final renderer
            structlog.processors.format_exc_info,
            # If coming from stdlib, add structlog formatting
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ProcessorFormatter bridges stdlib → structlog pipeline
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Root handler — all stdlib loggers (uvicorn, sqlalchemy, etc.) go through here
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(root_handler)
    root_logger.setLevel(log_level_int)

    # Silence noisy loggers in production
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(
            logging.WARNING if log_level_int > logging.DEBUG else log_level_int
        )


def get_logger(**initial_binds: Any) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger with optional initial context bindings."""
    return structlog.get_logger(**initial_binds)
