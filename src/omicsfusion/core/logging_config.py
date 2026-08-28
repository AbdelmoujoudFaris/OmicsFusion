"""Centralised logging configuration for OmicsFusion.

Every module logs through ``logging.getLogger("omicsfusion.<module>")`` so
that log level, format, and destination (console + optional file) are
controlled from a single place, and so that a project run can capture a
complete, reproducible log alongside its results.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False


def setup_logging(
    level: str = "INFO", log_file: Path | str | None = None
) -> logging.Logger:
    """Configure the root ``omicsfusion`` logger.

    Safe to call multiple times: the console handler is installed once,
    later calls just adjust the level so repeated CLI invocations in the
    same process don't duplicate console output. A ``log_file`` may be
    added on any call (e.g. once a project's output directory is known)
    and is only attached once per path.
    """
    global _CONFIGURED
    logger = logging.getLogger("omicsfusion")
    logger.setLevel(level.upper())
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not _CONFIGURED:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(fmt)
        logger.addHandler(console)
        _CONFIGURED = True

    if log_file is not None:
        log_file = Path(log_file).resolve()
        already_attached = any(
            isinstance(h, logging.FileHandler)
            and Path(h.baseFilename).resolve() == log_file
            for h in logger.handlers
        )
        if not already_attached:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(fmt)
            logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"omicsfusion.{name}")
