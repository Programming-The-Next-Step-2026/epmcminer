"""Tests for epmcminer.gui.screens.screen_download."""

import sys
import threading
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from epmcminer.gui.screens.screen_download import DownloadWorker, ScreenDownload
from epmcminer.services.models import DownloadResult, Paper, SearchParams

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paper() -> Paper:
    return Paper(
        pmid="1",
        doi="10.1000/test",
        title="Test Paper",
        authors="Author A",
        journal="Journal",
        year="2024",
        abstract="",
        pdf_url="https://example.com/paper.pdf",
    )


def _make_download_result(status: str = "downloaded") -> DownloadResult:
    paper = _make_paper()
    if status == "downloaded":
        return DownloadResult(
            paper=paper, status="downloaded", reason=None, file_path=Path("/tmp/test.pdf")
        )
    if status == "skipped":
        return DownloadResult(
            paper=paper, status="skipped", reason="PDF unavailable", file_path=None
        )
    return DownloadResult(paper=paper, status="failed", reason="HTTP 404", file_path=None)


def _make_params(count: int = 10, output_folder: Path = Path("/tmp/out")) -> SearchParams:
    return SearchParams(
        query="sleep AND memory",
        date_from="2020-01-01",
        date_to="2025-01-01",
        count=count,
        output_folder=output_folder,
    )


def _make_service(
    results: list[DownloadResult] | None = None,
    exc: Exception | None = None,
) -> MagicMock:
    """Return a mock DownloadService whose download() calls the callback for each result."""
    svc = MagicMock()
    _results = results or [_make_download_result()]

    def fake_download(params, progress_callback, cancel_event):
        for r in _results:
            progress_callback(r)
        return _results

    if exc is not None:
        svc.download.side_effect = exc
    else:
        svc.download.side_effect = fake_download
    return svc


def _make_report_service() -> MagicMock:
    return MagicMock()


def _make_screen(
    results: list[DownloadResult] | None = None,
    exc: Exception | None = None,
) -> ScreenDownload:
    return ScreenDownload(_make_service(results, exc), _make_report_service())


def _log_row_count(w: ScreenDownload) -> int:
    """Return the number of row *widgets* in the log layout (excludes the trailing stretch)."""
    return sum(
        1 for i in range(w._log_layout.count()) if w._log_layout.itemAt(i).widget() is not None
    )


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestDownloadWorkerRun
# ---------------------------------------------------------------------------


class TestDownloadWorkerRun:
    """Tests for DownloadWorker.run() called synchronously."""

    def test_worker_emits_progress_for_each_result(self, qapp: QApplication) -> None:
        """progress_updated is emitted once per result returned by the callback."""
        results = [_make_download_result("downloaded"), _make_download_result("skipped")]
        worker = DownloadWorker(_make_service(results), _make_params())
        received: list[DownloadResult] = []
        worker.progress_updated.connect(received.append)
        worker.run()
        assert len(received) == 2

    def test_worker_emits_finished_with_all_results(self, qapp: QApplication) -> None:
        """download_finished is emitted with the full list on success."""
        results = [_make_download_result(), _make_download_result("skipped")]
        worker = DownloadWorker(_make_service(results), _make_params())
        finished: list[list] = []
        worker.download_finished.connect(finished.append)
        worker.run()
        assert len(finished) == 1
        assert len(finished[0]) == 2

    def test_worker_emits_error_on_exception(self, qapp: QApplication) -> None:
        """error_occurred is emitted with the exception message when download() raises."""
        worker = DownloadWorker(_make_service(exc=ConnectionError("timeout")), _make_params())
        errors: list[str] = []
        worker.error_occurred.connect(errors.append)
        worker.run()
        assert len(errors) == 1
        assert "timeout" in errors[0]

    def test_worker_does_not_emit_finished_on_error(self, qapp: QApplication) -> None:
        """download_finished is not emitted when download() raises."""
        worker = DownloadWorker(_make_service(exc=RuntimeError("boom")), _make_params())
        finished: list[list] = []
        worker.download_finished.connect(finished.append)
        worker.run()
        assert finished == []

    def test_worker_does_not_emit_error_on_success(self, qapp: QApplication) -> None:
        """error_occurred is not emitted on a successful download."""
        worker = DownloadWorker(_make_service(), _make_params())
        errors: list[str] = []
        worker.error_occurred.connect(errors.append)
        worker.run()
        assert errors == []

    def test_worker_exposes_cancel_event(self, qapp: QApplication) -> None:
        """Worker has a cancel_event threading.Event accessible from outside."""
        worker = DownloadWorker(_make_service(), _make_params())
        assert isinstance(worker.cancel_event, threading.Event)
        assert not worker.cancel_event.is_set()

    def test_worker_passes_cancel_event_to_service(self, qapp: QApplication) -> None:
        """Worker passes its cancel_event to download_service.download()."""
        svc = MagicMock()
        svc.download.return_value = []
        worker = DownloadWorker(svc, _make_params())
        worker.run()
        _, kwargs = svc.download.call_args
        assert kwargs.get("cancel_event") is worker.cancel_event


# ---------------------------------------------------------------------------
# TestScreenDownloadDefaults
# ---------------------------------------------------------------------------


class TestScreenDownloadDefaults:
    """Verify the initial state of a freshly created ScreenDownload."""

    def test_is_qwidget(self, qapp: QApplication) -> None:
        """ScreenDownload is a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        assert isinstance(_make_screen(), QWidget)

    def test_has_download_complete_signal(self, qapp: QApplication) -> None:
        """ScreenDownload exposes a download_complete signal."""
        assert hasattr(ScreenDownload, "download_complete")

    def test_cancel_button_disabled_initially(self, qapp: QApplication) -> None:
        """Cancel button is disabled before start() is called."""
        w = _make_screen()
        assert not w._cancel_btn.isEnabled()

    def test_log_empty_initially(self, qapp: QApplication) -> None:
        """Log layout contains no rows before start() is called."""
        w = _make_screen()
        assert _log_row_count(w) == 0

    def test_progress_widget_present(self, qapp: QApplication) -> None:
        """Screen has a ProgressWidget instance."""
        from epmcminer.gui.widgets.progress_widget import ProgressWidget

        w = _make_screen()
        assert isinstance(w._progress, ProgressWidget)


# ---------------------------------------------------------------------------
# TestScreenDownloadStart
# ---------------------------------------------------------------------------


class TestScreenDownloadStart:
    """Tests for start() behaviour (worker patched to avoid real threads)."""

    def test_start_enables_cancel_button(self, qapp: QApplication) -> None:
        """start() enables the cancel button."""
        w = _make_screen()
        with patch("epmcminer.gui.screens.screen_download.DownloadWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w.start(_make_params())
        assert w._cancel_btn.isEnabled()

    def test_start_sets_folder_label(self, qapp: QApplication) -> None:
        """start() shows the output folder path in the action bar label."""
        w = _make_screen()
        params = _make_params(output_folder=Path("/tmp/papers"))
        with patch("epmcminer.gui.screens.screen_download.DownloadWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w.start(params)
        assert "/tmp/papers" in w._folder_label.text()

    def test_start_stores_params(self, qapp: QApplication) -> None:
        """start() stores the params for use in _on_finished."""
        w = _make_screen()
        params = _make_params()
        with patch("epmcminer.gui.screens.screen_download.DownloadWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w.start(params)
        assert w._params is params

    def test_start_clears_previous_log(self, qapp: QApplication) -> None:
        """start() clears any log rows from a previous run."""
        w = _make_screen()
        w._on_progress(_make_download_result())
        assert _log_row_count(w) == 1
        with patch("epmcminer.gui.screens.screen_download.DownloadWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w.start(_make_params())
        assert _log_row_count(w) == 0

    def test_start_resets_completed_count(self, qapp: QApplication) -> None:
        """start() resets the completed counter to zero."""
        w = _make_screen()
        w._completed = 7
        with patch("epmcminer.gui.screens.screen_download.DownloadWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w.start(_make_params())
        assert w._completed == 0


# ---------------------------------------------------------------------------
# TestScreenDownloadProgress
# ---------------------------------------------------------------------------


class TestScreenDownloadProgress:
    """Tests for _on_progress() called directly (no threading)."""

    def test_on_progress_adds_log_row(self, qapp: QApplication) -> None:
        """Each _on_progress call adds one row to the log layout."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result("downloaded"))
        assert _log_row_count(w) == 1

    def test_on_progress_multiple_rows(self, qapp: QApplication) -> None:
        """Multiple _on_progress calls each add a row."""
        w = _make_screen()
        w._total = 5
        for _ in range(3):
            w._on_progress(_make_download_result("downloaded"))
        assert _log_row_count(w) == 3

    def test_on_progress_increments_completed(self, qapp: QApplication) -> None:
        """_on_progress increments the completed counter."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result())
        assert w._completed == 1

    def test_on_progress_appends_result(self, qapp: QApplication) -> None:
        """_on_progress appends the result to _results."""
        w = _make_screen()
        w._total = 5
        r = _make_download_result()
        w._on_progress(r)
        assert r in w._results

    def test_log_row_widget_for_downloaded(self, qapp: QApplication) -> None:
        """A downloaded result produces a visible log row widget."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result("downloaded"))
        assert _log_row_count(w) == 1

    def test_log_row_widget_for_skipped(self, qapp: QApplication) -> None:
        """A skipped result also produces a log row widget."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result("skipped"))
        assert _log_row_count(w) == 1

    def test_log_row_widget_for_failed(self, qapp: QApplication) -> None:
        """A failed result also produces a log row widget."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result("failed"))
        assert _log_row_count(w) == 1

    def test_downloaded_count_only_counts_successful(self, qapp: QApplication) -> None:
        """_downloaded_count returns only results with status 'downloaded'."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result("downloaded"))
        w._on_progress(_make_download_result("skipped"))
        w._on_progress(_make_download_result("failed"))
        assert w._downloaded_count() == 1

    def test_progress_reflects_successful_downloads_not_total_attempts(
        self, qapp: QApplication
    ) -> None:
        """Progress bar tracks successful downloads, not total attempts including failures."""
        w = _make_screen()
        w._total = 5
        w._on_progress(_make_download_result("failed"))
        w._on_progress(_make_download_result("failed"))
        w._on_progress(_make_download_result("downloaded"))
        # _completed is 3 (total attempts), but downloaded count is 1
        assert w._completed == 3
        assert w._downloaded_count() == 1


# ---------------------------------------------------------------------------
# TestScreenDownloadFinished
# ---------------------------------------------------------------------------


class TestScreenDownloadFinished:
    """Tests for _on_finished() called directly."""

    def test_on_finished_emits_download_complete(self, qapp: QApplication) -> None:
        """_on_finished emits download_complete with the result list."""
        w = _make_screen()
        w._params = _make_params()
        results = [_make_download_result()]
        received: list[list] = []
        w.download_complete.connect(received.append)
        w._on_finished(results)
        assert len(received) == 1
        assert received[0] == results

    def test_on_finished_disables_cancel_button(self, qapp: QApplication) -> None:
        """_on_finished disables the cancel button."""
        w = _make_screen()
        w._params = _make_params()
        w._cancel_btn.setEnabled(True)
        w._on_finished([])
        assert not w._cancel_btn.isEnabled()

    def test_on_finished_calls_report_service_save_csv(self, qapp: QApplication) -> None:
        """_on_finished calls report_service.save_csv() with results and params."""
        report_svc = _make_report_service()
        w = ScreenDownload(_make_service(), report_svc)
        params = _make_params()
        w._params = params
        results = [_make_download_result()]
        w._on_finished(results)
        report_svc.save_csv.assert_called_once_with(results, params, params.output_folder)

    def test_on_finished_skips_csv_when_params_none(self, qapp: QApplication) -> None:
        """_on_finished does not call save_csv when _params is None."""
        report_svc = _make_report_service()
        w = ScreenDownload(_make_service(), report_svc)
        w._on_finished([])
        report_svc.save_csv.assert_not_called()


# ---------------------------------------------------------------------------
# TestScreenDownloadCancel
# ---------------------------------------------------------------------------


class TestScreenDownloadCancel:
    """Tests for the cancel button."""

    def test_cancel_sets_cancel_event(self, qapp: QApplication) -> None:
        """Clicking Cancel sets the worker's cancel_event."""
        w = _make_screen()
        mock_worker = MagicMock()
        mock_worker.cancel_event = threading.Event()
        w._worker = mock_worker
        w._cancel_btn.setEnabled(True)
        w._cancel_btn.click()
        assert mock_worker.cancel_event.is_set()

    def test_cancel_disables_itself(self, qapp: QApplication) -> None:
        """Clicking Cancel disables the cancel button."""
        w = _make_screen()
        w._worker = MagicMock()
        w._worker.cancel_event = threading.Event()
        w._cancel_btn.setEnabled(True)
        w._cancel_btn.click()
        assert not w._cancel_btn.isEnabled()

    def test_cancel_tolerates_no_worker(self, qapp: QApplication) -> None:
        """Clicking Cancel with no worker does not raise."""
        w = _make_screen()
        w._cancel_btn.setEnabled(True)
        w._cancel_btn.click()  # should not raise


# ---------------------------------------------------------------------------
# TestScreenDownloadError
# ---------------------------------------------------------------------------


class TestScreenDownloadError:
    """Tests for _on_error() called directly."""

    def test_on_error_disables_cancel_button(self, qapp: QApplication) -> None:
        """_on_error disables the cancel button."""
        w = _make_screen()
        w._cancel_btn.setEnabled(True)
        w._on_error("something went wrong")
        assert not w._cancel_btn.isEnabled()

    def test_on_error_shows_error_toast(self, qapp: QApplication) -> None:
        """_on_error shows an error toast containing the error message."""
        w = _make_screen()
        w._on_error("connection timeout")
        assert not w._toast.isHidden()
        assert "connection timeout" in w._toast._msg_lbl.text()

    def test_on_error_hides_thread_row(self, qapp: QApplication) -> None:
        """_on_error calls set_progress so the thread-count row is hidden.

        This prevents the UI from freezing on a stale thread count when the
        worker exits via an unhandled exception rather than the normal finish
        path (which calls _on_finished and clears the display itself).
        """
        w = _make_screen()
        w._total = 5
        # Show a live thread count first (simulates mid-download state).
        w._progress.set_progress(1, 5, thread_count=2, processed=1)
        assert not w._progress._thread_row.isHidden()
        # Error fires — thread row must be cleared.
        w._on_error("connection timeout")
        assert w._progress._thread_row.isHidden()
