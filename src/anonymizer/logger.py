"""Logging configuration following project guidelines."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

# Log file location in temp directory
LOG_FILE_PATH = Path(tempfile.gettempdir()) / "anonymizer.log"

# Track if file handler has been added to root logger
_file_handler_initialized = False


def _ensure_file_handler() -> None:
    """Add file handler to root logger if not already added."""
    global _file_handler_initialized
    if _file_handler_initialized:
        return

    root_logger = logging.getLogger()
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s.%(funcName)s] %(message)s")
    )
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    _file_handler_initialized = True


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Create logger with project-standard format.

    Format: [method] message key=value;key=value

    Logs are written to both console and a file in the temp directory.
    Log file location: {tempdir}/anonymizer.log

    Args:
        name: Logger name (typically module name)
        level: Optional logging level (defaults to INFO)

    Returns:
        Configured logger instance
    """
    _ensure_file_handler()

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(funcName)s] %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level or logging.INFO)
    return logger


def get_log_file_path() -> Path:
    """Return the path to the log file."""
    return LOG_FILE_PATH
