"""Logging configuration for Pet Health Cost Explorer."""

import logging
import sys
from pathlib import Path
from typing import Optional

from petcost.config import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Set up logging for the application.

    Args:
        log_level: Override log level from settings
        log_file: Override log file path from settings

    Returns:
        Configured logger instance
    """
    settings = get_settings()

    # Use provided values or fall back to settings
    level = log_level or settings.log_level
    file_path = log_file or settings.log_file_absolute

    # Ensure log directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger("petcost")
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = logging.Formatter(
        fmt="%(levelname)-8s | %(message)s",
    )

    # Console handler (simple format)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed format)
    file_handler = logging.FileHandler(file_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"petcost.{name}")


# Initialize logging on module import
_root_logger = setup_logging()
