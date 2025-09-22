"""
Observability Logging
====================

Structured JSON logging for Family AI Memory Backbone architecture.
Provides correlation IDs, context preservation, and performance tracking.
"""

import json
import logging
import time
from contextvars import ContextVar
from typing import Optional

# Context for correlation IDs
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def get_json_logger(name: str) -> logging.Logger:
    """Get a logger configured for JSON output"""
    logger = logging.getLogger(name)

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a standard logger"""
    return logging.getLogger(name)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for request tracking"""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID"""
    correlation_id_var.set(None)
