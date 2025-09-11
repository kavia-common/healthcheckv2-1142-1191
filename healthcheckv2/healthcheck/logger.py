"""
Logging setup for healthcheckv2, including Loki HTTP handler integration.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional

from .loki_handler import LokiHTTPHandler


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        # Attach optional extras safely
        for key in ("site_id", "cluster_id", "env"):
            value = getattr(record, key, None)
            if value is not None:
                base[key] = value

        # Format exception info robustly:
        # - If record.exc_info is True, fetch current exception via sys.exc_info()
        # - If it's a tuple-like exc_info, pass as-is
        # - Otherwise, ignore to avoid formatting errors
        if record.exc_info:
            exc_info = record.exc_info
            try:
                if exc_info is True:
                    exc_info = sys.exc_info()
                # Ensure exc_info is a 3-tuple before formatting
                if isinstance(exc_info, tuple) and len(exc_info) == 3:
                    base["exc_info"] = self.formatException(exc_info)
            except Exception:
                # Defensive: never let logging crash due to formatting issues
                pass

        return json.dumps(base, ensure_ascii=False)


# PUBLIC_INTERFACE
def get_logger(
    name: str = "healthcheckv2",
    level: str = "INFO",
    json_output: bool = True,
    loki_handler: Optional[LokiHTTPHandler] = None,
) -> logging.Logger:
    """Get configured logger with optional Loki handler.

    Args:
        name: Logger name.
        level: Log level as string.
        json_output: Whether to use JSON formatter.
        loki_handler: Optional Loki handler to send logs to Loki.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False  # Avoid duplicate logs

    # Clear existing handlers for idempotency
    logger.handlers.clear()

    stream = logging.StreamHandler(stream=sys.stderr)
    if json_output:
        stream.setFormatter(JsonFormatter())
    else:
        stream.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(stream)

    if loki_handler:
        # Add Loki with level from configuration
        logger.addHandler(loki_handler)

    # Basic security: do not accidentally log sensitive envs
    for env_key in ("KAFKA_PASSWORD", "SASL_PASSWORD"):
        if os.environ.get(env_key):
            os.environ[env_key] = "***"  # Redact in env for child processes

    return logger
