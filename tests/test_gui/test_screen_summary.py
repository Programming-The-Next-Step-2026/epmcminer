"""Tests for epmcminer.gui.screens.screen_summary."""

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from epmcminer.gui.screens.screen_summary import ExportWorker, ScreenSummary
from epmcminer.services.models import DownloadResult, Paper, SearchParams
from epmcminer.services.report_service import ReportService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paper() -> Paper:
    return Paper(
        pmid="1",
        doi="10.1000/test",
        title="Sleep-dependent memory consolidation in adolescents",
        authors="Smith J, van der Berg A",
        journal="Nature Neuroscience",
        year="2024",
        abstract="",
        pdf_url="https://example.com/paper.pdf",
    )


def _make_downloaded() -> DownloadResult:
    return DownloadResult(
        paper=_make_paper(),
        status="downloaded",
        reason=None,
        file_path=Path("/tmp/test.pdf"),
    )


def _make_skipped(reason: str = "PDF unavailable") -> DownloadResult:
    return DownloadResult(paper=_make_paper(), status="skipped", reason=reason, file_path=None)


def _make_failed(reason: str = "HTTP 403") -> DownloadResult:
    return DownloadResult(paper=_make_paper(), status="failed", reason=reason, file_path=None)


def _make_params(**overrides: object) -> SearchParams:
    defaults: dict = {
        "query": "sleep AND memory",
        "date_from": "2020-01-01",
        "date_to": "2025-01-01",
        "count": 10,
    }
    defaults.update(overrides)
    return SearchParams(**defaults)


def _make_report_service() -> MagicMock:
    return MagicMock(spec=ReportService)


def _make_screen() -> ScreenSummary:
    return ScreenSummary(_make_report_service())


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestExportWorkerRun
# ---------------------------------------------------------------------------


class TestExportWorkerRun:
    """Tests for ExportWorker.run() called synchronously."""

    def test_export_done_emitted_with_path_on_success(self, qapp: QApplication) -> None:
        """export_done is emitted with the file path string on success."""
        fn = MagicMock()
        worker = ExportWorker(fn, "/tmp/report.xlsx")
        done: list[str] = []
        worker.export_done.connect(done.append)
        worker.run()
        assert done == ["/tmp/report.xlsx"]

    def test_fn_is_called(self, qapp: QApplication) -> None:
        """The export callable is invoked exactly once."""
        fn = MagicMock()
        worker = ExportWorker(fn, "/tmp/report.xlsx")
        worker.run()
        fn.assert_called_once()

    def test_export_error_emitted_on_exception(self, qapp: QApplication) -> None:
        """export_error is emitted with the exception message when fn raises."""
        fn = MagicMock(side_effect=OSError("disk full"))
        worker = ExportWorker(fn, "/tmp/report.xlsx")
        errors: list[str] = []
        worker.export_error.connect(errors.append)
        worker.run()
        assert len(errors) == 1
        assert "disk full" in errors[0]

    def test_export_done_not_emitted_on_error(self, qapp: QApplication) -> None:
        """export_done is not emitted when fn raises."""
        fn = MagicMock(side_effect=OSError("disk full"))
        worker = ExportWorker(fn, "/tmp/report.xlsx")
        done: list[str] = []
        worker.export_done.connect(done.append)
        worker.run()
        assert done == []

    def test_export_error_not_emitted_on_success(self, qapp: QApplication) -> None:
        """export_error is not emitted on a successful export."""
        fn = MagicMock()
        worker = ExportWorker(fn, "/tmp/report.xlsx")
        errors: list[str] = []
        worker.export_error.connect(errors.append)
        worker.run()
        assert errors == []


# ---------------------------------------------------------------------------
# TestScreenSummaryDefaults
# ---------------------------------------------------------------------------


class TestScreenSummaryDefaults:
    """Verify the initial state of a freshly created ScreenSummary."""

    def test_is_qwidget(self, qapp: QApplication) -> None:
        """ScreenSummary is a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        assert isinstance(_make_screen(), QWidget)

    def test_has_new_search_requested_signal(self, qapp: QApplication) -> None:
        """ScreenSummary exposes a new_search_requested signal."""
        assert hasattr(ScreenSummary, "new_search_requested")

    def test_skipped_card_hidden_initially(self, qapp: QApplication) -> None:
        """Skipped papers card is hidden before load() is called."""
        assert _make_screen()._skipped_card.isHidden()

    def test_new_search_button_present(self, qapp: QApplication) -> None:
        """Screen has a new search button."""
        assert _make_screen()._new_search_btn is not None

    def test_export_excel_button_present(self, qapp: QApplication) -> None:
        """Screen has an Export Excel button."""
        assert _make_screen()._export_excel_btn is not None

    def test_export_pdf_button_present(self, qapp: QApplication) -> None:
        """Screen has an Export PDF button."""
        assert _make_screen()._export_pdf_btn is not None


# ---------------------------------------------------------------------------
# TestScreenSummaryLoad
# ---------------------------------------------------------------------------


class TestScreenSummaryLoad:
    """Tests for ScreenSummary.load()."""

    def test_downloaded_stat_matches_results(self, qapp: QApplication) -> None:
        """Downloaded stat shows the count of status='downloaded' results."""
        w = _make_screen()
        w.load([_make_downloaded(), _make_downloaded(), _make_skipped()], _make_params(), 100)
        assert w._stat_downloaded_lbl.text() == "2"

    def test_skipped_stat_includes_skipped_and_failed(self, qapp: QApplication) -> None:
        """Skipped stat counts both 'skipped' and 'failed' results together."""
        w = _make_screen()
        w.load(
            [_make_downloaded(), _make_skipped(), _make_failed()],
            _make_params(),
            100,
        )
        assert w._stat_skipped_lbl.text() == "2"

    def test_total_stat_matches_total_found(self, qapp: QApplication) -> None:
        """Total results stat shows total_found formatted with comma separators."""
        w = _make_screen()
        w.load([_make_downloaded()], _make_params(), 1247)
        assert w._stat_total_lbl.text() == "1,247"

    def test_downloaded_sub_shows_processed_count(self, qapp: QApplication) -> None:
        """Downloaded card sub-text shows the total number of papers processed, not requested."""
        w = _make_screen()
        results = [_make_downloaded(), _make_skipped(), _make_skipped()]
        w.load(results, _make_params(count=50), 100)
        assert "3" in w._stat_downloaded_sub.text()
        assert "processed" in w._stat_downloaded_sub.text()

    def test_params_query_shown(self, qapp: QApplication) -> None:
        """Query value label shows the search query from params."""
        w = _make_screen()
        w.load([_make_downloaded()], _make_params(query="depression AND therapy"), 100)
        assert w._param_query_lbl.text() == "depression AND therapy"

    def test_params_sort_shown_capitalised(self, qapp: QApplication) -> None:
        """Sort value label shows the sort order capitalised."""
        w = _make_screen()
        w.load([_make_downloaded()], _make_params(), 100)
        assert w._param_sort_lbl.text() == "Relevance"

    def test_params_date_range_shown(self, qapp: QApplication) -> None:
        """Date label contains both from and to dates."""
        w = _make_screen()
        params = _make_params(date_from="2021-06-01", date_to="2024-12-31")
        w.load([_make_downloaded()], params, 100)
        assert "2021-06-01" in w._param_date_lbl.text()
        assert "2024-12-31" in w._param_date_lbl.text()

    def test_skipped_card_hidden_when_all_downloaded(self, qapp: QApplication) -> None:
        """Skipped card is hidden when every result has status='downloaded'."""
        w = _make_screen()
        w.load([_make_downloaded(), _make_downloaded()], _make_params(), 100)
        assert w._skipped_card.isHidden()

    def test_skipped_card_visible_when_some_not_downloaded(self, qapp: QApplication) -> None:
        """Skipped card is visible when at least one result is not downloaded."""
        w = _make_screen()
        w.load([_make_downloaded(), _make_skipped()], _make_params(), 100)
        assert not w._skipped_card.isHidden()

    def test_skipped_list_widget_count_matches_non_downloaded(self, qapp: QApplication) -> None:
        """Skipped list has one row widget per non-downloaded result."""
        w = _make_screen()
        w.load(
            [_make_downloaded(), _make_skipped(), _make_failed()],
            _make_params(),
            100,
        )
        count = sum(
            1
            for i in range(w._skipped_list_layout.count())
            if w._skipped_list_layout.itemAt(i).widget() is not None
        )
        assert count == 2

    def test_load_stores_results_for_export(self, qapp: QApplication) -> None:
        """load() stores the results list for later use in export."""
        w = _make_screen()
        results = [_make_downloaded()]
        w.load(results, _make_params(), 100)
        assert w._results is results

    def test_load_stores_params_for_export(self, qapp: QApplication) -> None:
        """load() stores the params for later use in export."""
        w = _make_screen()
        params = _make_params()
        w.load([_make_downloaded()], params, 100)
        assert w._params is params

    def test_second_load_resets_skipped_list(self, qapp: QApplication) -> None:
        """Calling load() a second time replaces the skipped list content."""
        w = _make_screen()
        w.load([_make_skipped(), _make_skipped()], _make_params(), 100)
        w.load([_make_downloaded()], _make_params(), 100)
        count = sum(
            1
            for i in range(w._skipped_list_layout.count())
            if w._skipped_list_layout.itemAt(i).widget() is not None
        )
        assert count == 0


# ---------------------------------------------------------------------------
# TestScreenSummaryNewSearch
# ---------------------------------------------------------------------------


class TestScreenSummaryNewSearch:
    """Tests for the New search button."""

    def test_new_search_button_emits_signal(self, qapp: QApplication) -> None:
        """Clicking the New search button emits new_search_requested."""
        w = _make_screen()
        received: list[None] = []
        w.new_search_requested.connect(lambda: received.append(None))
        w._new_search_btn.click()
        assert len(received) == 1


# ---------------------------------------------------------------------------
# TestScreenSummaryExport
# ---------------------------------------------------------------------------


class TestScreenSummaryExport:
    """Tests for the Export Excel and Export PDF buttons."""

    def _loaded_screen(self) -> ScreenSummary:
        w = _make_screen()
        w.load([_make_downloaded()], _make_params(), 100)
        return w

    def test_export_excel_opens_file_dialog(self, qapp: QApplication) -> None:
        """Clicking Export Excel opens a QFileDialog."""
        w = self._loaded_screen()
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("", ""),
            ) as mock_dialog,
            patch("epmcminer.gui.screens.screen_summary.ExportWorker"),
        ):
            w._export_excel_btn.click()
        mock_dialog.assert_called_once()

    def test_export_pdf_opens_file_dialog(self, qapp: QApplication) -> None:
        """Clicking Export PDF opens a QFileDialog."""
        w = self._loaded_screen()
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("", ""),
            ) as mock_dialog,
            patch("epmcminer.gui.screens.screen_summary.ExportWorker"),
        ):
            w._export_pdf_btn.click()
        mock_dialog.assert_called_once()

    def test_cancelled_dialog_starts_no_worker(self, qapp: QApplication) -> None:
        """If the file dialog is cancelled, no export worker is started."""
        w = self._loaded_screen()
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("", ""),
            ),
            patch("epmcminer.gui.screens.screen_summary.ExportWorker") as MockWorker,
        ):
            w._export_excel_btn.click()
        MockWorker.assert_not_called()

    def test_export_excel_worker_receives_path(self, qapp: QApplication) -> None:
        """ExportWorker is created with the path chosen in the file dialog."""
        w = self._loaded_screen()
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("/tmp/report.xlsx", "Excel Files (*.xlsx)"),
            ),
            patch("epmcminer.gui.screens.screen_summary.ExportWorker") as MockWorker,
        ):
            w._export_excel_btn.click()
        _, path = MockWorker.call_args.args
        assert path == "/tmp/report.xlsx"

    def test_export_pdf_worker_receives_path(self, qapp: QApplication) -> None:
        """ExportWorker is created with the path chosen in the file dialog."""
        w = self._loaded_screen()
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("/tmp/report.pdf", "PDF Files (*.pdf)"),
            ),
            patch("epmcminer.gui.screens.screen_summary.ExportWorker") as MockWorker,
        ):
            w._export_pdf_btn.click()
        _, path = MockWorker.call_args.args
        assert path == "/tmp/report.pdf"

    def test_export_excel_fn_calls_report_service(self, qapp: QApplication) -> None:
        """The fn passed to ExportWorker calls report_service.export_excel()."""
        report_svc = _make_report_service()
        w = ScreenSummary(report_svc)
        w.load([_make_downloaded()], _make_params(), 100)
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("/tmp/report.xlsx", ""),
            ),
            patch("epmcminer.gui.screens.screen_summary.ExportWorker") as MockWorker,
        ):
            w._export_excel_btn.click()
        fn, _ = MockWorker.call_args.args
        fn()
        report_svc.export_excel.assert_called_once()

    def test_export_pdf_fn_calls_report_service(self, qapp: QApplication) -> None:
        """The fn passed to ExportWorker calls report_service.export_pdf()."""
        report_svc = _make_report_service()
        w = ScreenSummary(report_svc)
        w.load([_make_downloaded()], _make_params(), 100)
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
                return_value=("/tmp/report.pdf", ""),
            ),
            patch("epmcminer.gui.screens.screen_summary.ExportWorker") as MockWorker,
        ):
            w._export_pdf_btn.click()
        fn, _ = MockWorker.call_args.args
        fn()
        report_svc.export_pdf.assert_called_once()

    def test_export_done_shows_success_toast(self, qapp: QApplication) -> None:
        """_on_export_done shows a success toast with the filename (not the full path)."""
        w = _make_screen()
        w._on_export_done("/tmp/report.xlsx")
        assert not w._toast.isHidden()
        assert "report.xlsx" in w._toast._msg_lbl.text()

    def test_export_error_shows_error_toast(self, qapp: QApplication) -> None:
        """_on_export_error shows an error toast containing the error message."""
        w = _make_screen()
        w._on_export_error("disk full")
        assert not w._toast.isHidden()
        assert "disk full" in w._toast._msg_lbl.text()

    def test_export_does_nothing_before_load(self, qapp: QApplication) -> None:
        """Export buttons do nothing if load() has not been called."""
        w = _make_screen()
        with (
            patch(
                "epmcminer.gui.screens.screen_summary.QFileDialog.getSaveFileName",
            ) as mock_dialog,
            patch("epmcminer.gui.screens.screen_summary.ExportWorker") as MockWorker,
        ):
            w._export_excel_btn.click()
        mock_dialog.assert_not_called()
        MockWorker.assert_not_called()
