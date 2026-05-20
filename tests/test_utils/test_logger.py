"""Tests for epmcminer.utils.logger.

Created alongside issue-8 which adds setup_logger to logger.py.
Mirrors the test_file_utils.py pattern: one file per utility module.
"""

import logging
import re
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from epmcminer.utils.logger import setup_logger

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LOGGER_NAME = "epmcminer"
_LOG_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.log$")


@pytest.fixture(autouse=True)
def _cleanup_logger_handlers() -> Generator[None, None, None]:
    """Remove all file handlers added to the epmcminer logger after each test.

    Prevents handler accumulation and file-lock issues across tests.
    """
    yield
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# TestSetupLogger
# ---------------------------------------------------------------------------


class TestSetupLogger:
    """Tests for setup_logger."""

    def test_creates_logs_directory(self, tmp_path: Path) -> None:
        """setup_logger creates output_folder/logs/ when it does not exist."""
        setup_logger(tmp_path)
        assert (tmp_path / "logs").is_dir()

    def test_creates_log_file_in_logs_dir(self, tmp_path: Path) -> None:
        """A log file is written inside output_folder/logs/."""
        setup_logger(tmp_path)
        log_files = list((tmp_path / "logs").iterdir())
        assert len(log_files) == 1

    def test_log_filename_format(self, tmp_path: Path) -> None:
        """The log filename matches YYYY-MM-DD_HH-MM.log."""
        setup_logger(tmp_path)
        log_files = list((tmp_path / "logs").iterdir())
        assert _LOG_FILENAME_RE.match(log_files[0].name)

    def test_returns_logger_instance(self, tmp_path: Path) -> None:
        """setup_logger returns a logging.Logger instance."""
        result = setup_logger(tmp_path)
        assert isinstance(result, logging.Logger)

    def test_creates_missing_output_folder(self, tmp_path: Path) -> None:
        """setup_logger creates output_folder itself when it is absent."""
        folder = tmp_path / "new" / "nested"
        setup_logger(folder)
        assert (folder / "logs").is_dir()

    def test_logger_writes_to_file(self, tmp_path: Path) -> None:
        """Messages written to the returned logger appear in the log file."""
        logger = setup_logger(tmp_path)
        logger.info("test message")

        log_file = next((tmp_path / "logs").iterdir())
        # Flush the handler so content is on disk before reading.
        for handler in logger.handlers:
            handler.flush()

        assert "test message" in log_file.read_text()

    def test_repeated_calls_do_not_accumulate_handlers(self, tmp_path: Path) -> None:
        """Calling setup_logger twice replaces the handler instead of stacking it."""
        setup_logger(tmp_path / "session1")
        setup_logger(tmp_path / "session2")
        logger = logging.getLogger("epmcminer")
        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

    def test_log_file_named_at_call_time(self, tmp_path: Path) -> None:
        """The log filename reflects the time of the setup_logger call, not import time."""
        before = datetime.now().strftime("%Y-%m-%d_%H-%M")
        setup_logger(tmp_path)
        after = datetime.now().strftime("%Y-%m-%d_%H-%M")

        log_files = list((tmp_path / "logs").iterdir())
        stem = log_files[0].stem  # e.g. "2026-05-14_10-30"
        assert before <= stem <= after, (
            f"Log filename '{stem}' is not between '{before}' and '{after}'"
        )
