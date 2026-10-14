from __future__ import annotations

import logging
import sys
import structlog
from structlog.types import Processor

def configure_logging(app_env: str = "development") -> None:
    """
    Configure central structlog logging.
    Enables contextvars merging (for request IDs), time stamping, and dev/prod formatters.
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if app_env == "production":
        # JSON logs for structured querying in production
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Readable, colored terminal logs for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bridge standard library logging to structlog if needed
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )
