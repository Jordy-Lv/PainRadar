"""Logging estructurado. En consola sale legible; en fichero/Docker sale JSON."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(level: str = "INFO", *, json_output: bool | None = None) -> None:
    if json_output is None:
        json_output = not sys.stderr.isatty()

    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level.upper())

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[level.upper()]
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
