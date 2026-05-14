"""Timestamped file logger setup."""

import logging
from datetime import datetime
from pathlib import Path

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d_%H-%M"
_ROOT_LOGGER_NAME = "epmcminer"


def setup_logger(output_folder: Path) -> logging.Logger:
    """Create a timestamped log file in output_folder/logs/ and return a configured logger.

    The log file is named with the timestamp of this call (not import time) in
    the format ``YYYY-MM-DD_HH-MM.log``. All child loggers obtained via
    :func:`get_logger` inherit this file handler through Python's logger
    hierarchy.

    Args:
        output_folder: Root directory for the session. The ``logs/``
            subdirectory is created automatically if it does not exist.

    Returns:
        The configured ``epmcminer`` root logger instance.
    """
    logs_dir = output_folder / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(_LOG_DATE_FORMAT)
    log_file = logs_dir / f"{timestamp}.log"

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    # Replace any existing FileHandlers so repeated calls do not accumulate
    # handlers and cause duplicate log entries across multiple log files.
    for existing in list(logger.handlers):
        if isinstance(existing, logging.FileHandler):
            existing.close()
            logger.removeHandler(existing)

    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured for epmcminer.

    Args:
        name: The logger name, typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
