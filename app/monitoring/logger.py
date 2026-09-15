"""
Central application logging for EnergyAutomation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


_LOGGER_NAME = "EnergyAutomation"
_initialized = False


def _initialize_logging() -> None:
    """Initialize application logging once."""

    global _initialized

    if _initialized:
        return

    log_directory = Path("data") / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    log_file = log_directory / "energy_automation.log"

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if the module is reloaded.
    if logger.handlers:
        _initialized = True
        return

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    import sys
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass

    console_handler = logging.StreamHandler(stream)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _initialized = True


def get_logger(
    name: Optional[str] = None,
) -> logging.Logger:
    """
    Return the application logger.

    Parameters
    ----------
    name:
        Optional child logger name.

    Returns
    -------
    logging.Logger
    """

    _initialize_logging()

    if name:
        return logging.getLogger(
            f"{_LOGGER_NAME}.{name}"
        )

    return logging.getLogger(_LOGGER_NAME)


logger = get_logger()


__all__ = [
    "get_logger",
    "logger",
]