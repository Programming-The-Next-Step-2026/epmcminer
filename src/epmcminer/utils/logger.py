"""Timestamped file logger setup."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured for epmcminer.

    Args:
        name: The logger name, typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
