"""Tests for epmcminer.gui.app — MainWindow navigation and signal wiring."""

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtWidgets import QApplication

from epmcminer.api.download_result import DownloadResult
from epmcminer.api.models import Paper, SearchParams
from epmcminer.gui.app import APP_TITLE, MINIMUM_HEIGHT, MINIMUM_WIDTH, MainWindow

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


def _make_params(count: int = 5) -> SearchParams:
    return SearchParams(
        query="test",
        date_from="2020-01-01",
        date_to="2025-01-01",
        count=count,
        output_folder=Path("/tmp/out"),
    )


def _make_result(status: str = "downloaded") -> DownloadResult:
    return DownloadResult(
        paper=_make_paper(),
        status=status,
        reason=None,
        file_path=Path("/tmp/test.pdf") if status == "downloaded" else None,
    )


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestMainWindowInit
# ---------------------------------------------------------------------------


class TestMainWindowInit:
    """Verify the initial state of a freshly created MainWindow."""

    def test_window_title(self, qapp: QApplication) -> None:
        """Window title is 'epmcminer'."""
        w = MainWindow()
        assert w.windowTitle() == APP_TITLE

    def test_minimum_width(self, qapp: QApplication) -> None:
        """Minimum width is 820."""
        w = MainWindow()
        assert w.minimumWidth() == MINIMUM_WIDTH

    def test_minimum_height(self, qapp: QApplication) -> None:
        """Minimum height is 600."""
        w = MainWindow()
        assert w.minimumHeight() == MINIMUM_HEIGHT

    def test_initial_screen_is_search(self, qapp: QApplication) -> None:
        """The stacked widget starts at index 0 (ScreenSearch)."""
        w = MainWindow()
        assert w._stack.currentIndex() == 0

    def test_stack_has_four_screens(self, qapp: QApplication) -> None:
        """The stacked widget contains exactly four screens."""
        w = MainWindow()
        assert w._stack.count() == 4

    def test_step_indicator_has_four_circles(self, qapp: QApplication) -> None:
        """The title bar step indicator tracks four steps."""
        w = MainWindow()
        assert len(w._title_bar._circles) == 4

    def test_step_indicator_has_three_connector_lines(self, qapp: QApplication) -> None:
        """Three connector lines connect the four step circles."""
        w = MainWindow()
        assert len(w._title_bar._connector_lines) == 3


# ---------------------------------------------------------------------------
# TestMainWindowNavigateTo
# ---------------------------------------------------------------------------


class TestMainWindowNavigateTo:
    """Tests for navigate_to() and update_step_indicator()."""

    def test_navigate_to_1(self, qapp: QApplication) -> None:
        """navigate_to(1) switches the stack to index 1."""
        w = MainWindow()
        w.navigate_to(1)
        assert w._stack.currentIndex() == 1

    def test_navigate_to_2(self, qapp: QApplication) -> None:
        """navigate_to(2) switches the stack to index 2."""
        w = MainWindow()
        w.navigate_to(2)
        assert w._stack.currentIndex() == 2

    def test_navigate_to_3(self, qapp: QApplication) -> None:
        """navigate_to(3) switches the stack to index 3."""
        w = MainWindow()
        w.navigate_to(3)
        assert w._stack.currentIndex() == 3

    def test_navigate_to_0_from_3(self, qapp: QApplication) -> None:
        """navigate_to(0) works from any screen."""
        w = MainWindow()
        w.navigate_to(3)
        w.navigate_to(0)
        assert w._stack.currentIndex() == 0

    def test_navigate_to_updates_step_indicator(self, qapp: QApplication) -> None:
        """navigate_to() calls update_steps on the title bar."""
        w = MainWindow()
        with patch.object(w._title_bar, "update_steps") as mock:
            w.navigate_to(2)
        mock.assert_called_once_with(2)

    def test_update_step_indicator_does_not_change_stack(self, qapp: QApplication) -> None:
        """update_step_indicator() updates the indicator without switching screens."""
        w = MainWindow()
        w.update_step_indicator(2)
        assert w._stack.currentIndex() == 0


# ---------------------------------------------------------------------------
# TestTitleBarStepIndicator
# ---------------------------------------------------------------------------


class TestTitleBarStepIndicator:
    """Tests for _TitleBar.update_steps() style transitions."""

    def test_active_circle_text_is_number(self, qapp: QApplication) -> None:
        """The active step circle shows its 1-based step number."""
        w = MainWindow()
        w._title_bar.update_steps(2)
        assert w._title_bar._circles[2].text() == "3"

    def test_completed_circle_shows_checkmark(self, qapp: QApplication) -> None:
        """Completed step circles show a checkmark character."""
        w = MainWindow()
        w._title_bar.update_steps(2)
        assert w._title_bar._circles[0].text() == "✓"
        assert w._title_bar._circles[1].text() == "✓"

    def test_inactive_circle_shows_number(self, qapp: QApplication) -> None:
        """Inactive step circles show their 1-based step number."""
        w = MainWindow()
        w._title_bar.update_steps(1)
        assert w._title_bar._circles[2].text() == "3"
        assert w._title_bar._circles[3].text() == "4"


# ---------------------------------------------------------------------------
# TestMainWindowSignalWiring
# ---------------------------------------------------------------------------


class TestMainWindowSignalWiring:
    """Tests for signal → slot connections between screens and MainWindow."""

    def test_search_requested_navigates_to_preview(self, qapp: QApplication) -> None:
        """search_requested from ScreenSearch navigates to screen 1."""
        w = MainWindow()
        with patch.object(w._screen_preview, "load"):
            w._screen_search.search_requested.emit(_make_params())
        assert w._stack.currentIndex() == 1

    def test_search_requested_calls_preview_load(self, qapp: QApplication) -> None:
        """search_requested triggers ScreenPreview.load() with the params."""
        w = MainWindow()
        params = _make_params()
        with patch.object(w._screen_preview, "load") as mock_load:
            w._screen_search.search_requested.emit(params)
        mock_load.assert_called_once_with(params)

    def test_back_requested_returns_to_search(self, qapp: QApplication) -> None:
        """back_requested from ScreenPreview navigates to screen 0."""
        w = MainWindow()
        w.navigate_to(1)
        w._screen_preview.back_requested.emit()
        assert w._stack.currentIndex() == 0

    def test_download_requested_navigates_to_download(self, qapp: QApplication) -> None:
        """download_requested from ScreenPreview navigates to screen 2."""
        w = MainWindow()
        params = _make_params()
        with patch.object(w._screen_download, "start"):
            w._screen_preview.download_requested.emit(params)
        assert w._stack.currentIndex() == 2

    def test_download_requested_calls_download_start(self, qapp: QApplication) -> None:
        """download_requested triggers ScreenDownload.start() with the params."""
        w = MainWindow()
        params = _make_params()
        with patch.object(w._screen_download, "start") as mock_start:
            w._screen_preview.download_requested.emit(params)
        mock_start.assert_called_once_with(params)

    def test_download_requested_stores_params(self, qapp: QApplication) -> None:
        """download_requested stores the params for later use by ScreenSummary."""
        w = MainWindow()
        params = _make_params()
        with patch.object(w._screen_download, "start"):
            w._screen_preview.download_requested.emit(params)
        assert w._last_params is params

    def test_result_loaded_stores_total_found(self, qapp: QApplication) -> None:
        """result_loaded from ScreenPreview stores the total_found count."""
        w = MainWindow()
        w._screen_preview.result_loaded.emit(999)
        assert w._total_found == 999

    def test_download_complete_navigates_to_summary(self, qapp: QApplication) -> None:
        """download_complete from ScreenDownload navigates to screen 3."""
        w = MainWindow()
        w._last_params = _make_params()
        with patch.object(w._screen_summary, "load"):
            w._screen_download.download_complete.emit([_make_result()])
        assert w._stack.currentIndex() == 3

    def test_download_complete_calls_summary_load(self, qapp: QApplication) -> None:
        """download_complete calls ScreenSummary.load() with results, params, total_found."""
        w = MainWindow()
        params = _make_params()
        w._last_params = params
        w._total_found = 42
        results = [_make_result()]
        with patch.object(w._screen_summary, "load") as mock_load:
            w._screen_download.download_complete.emit(results)
        mock_load.assert_called_once_with(results, params, 42)

    def test_download_complete_skips_load_when_params_none(self, qapp: QApplication) -> None:
        """download_complete does not call load() or navigate if no params were stored."""
        w = MainWindow()
        with patch.object(w._screen_summary, "load") as mock_load:
            w._screen_download.download_complete.emit([])
        mock_load.assert_not_called()
        assert w._stack.currentIndex() == 0

    def test_new_search_returns_to_search(self, qapp: QApplication) -> None:
        """new_search_requested from ScreenSummary navigates to screen 0."""
        w = MainWindow()
        w.navigate_to(3)
        w._screen_summary.new_search_requested.emit()
        assert w._stack.currentIndex() == 0
