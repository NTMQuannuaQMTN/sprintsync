"""Structured logging setup (Phase 12 — observability).

Without this, structlog.get_logger() calls throughout the ingestion/
reasoning/matching/sync pipeline still work (structlog has usable
defaults) but render as unstructured text with no timestamps — this
gives every log line a consistent, machine-parseable shape (JSON in
production, colored key=value in development) and a timestamp/level.

Never log secrets: nothing in this codebase passes GitHub tokens, the
webhook secret, the Anthropic API key, or Notion tokens as log fields —
call sites only log ids, names, counts, and error messages.
"""
import logging

import structlog

from src.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.ENV == "development":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
