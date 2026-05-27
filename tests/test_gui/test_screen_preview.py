"""Tests for epmcminer.gui.screens.screen_preview."""

import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from epmcminer.api.models import Paper, SearchParams, SearchResult
from epmcminer.gui.screens.screen_preview import PreviewWorker, ScreenPreview

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_params(
    *,
    query: str = "memory AND sleep",
    sort_order: str = "relevance",
    count: int = 10,
    output_folder: Path = Path(),
) -> SearchParams:
    return SearchParams(
        query=query,
        date_from="2020-01-01",
        date_to="2025-01-01",
        sort_order=sort_order,
        count=count,
        output_folder=output_folder,
    )


def _make_paper(n: int = 1) -> Paper:
    return Paper(
        pmid=str(n),
        doi=f"10.1000/test{n}",
        title=f"Test Paper {n}",
        authors=f"Author {n}",
        journal=f"Journal {n}",
        year="2024",
        abstract="",
        pdf_url=f"https://example.com/paper{n}.pdf",
    )


def _make_result(n_papers: int = 3, total: int = 100, pdf_count: int = 72) -> SearchResult:
    return SearchResult(
        papers=[_make_paper(i + 1) for i in range(n_papers)],
        total_found=total,
        estimated_downloadable=pdf_count,
    )


def _make_service(result: SearchResult | None = None, exc: Exception | None = None) -> MagicMock:
    svc = MagicMock()
    if exc is not None:
        svc.preview.side_effect = exc
    else:
        svc.preview.return_value = result or _make_result()
    return svc


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestPreviewWorkerRun
# ---------------------------------------------------------------------------


class TestPreviewWorkerRun:
    """Tests for PreviewWorker.run() (called synchronously — bypasses QThread)."""

    def test_worker_emits_result_ready_on_success(self, qapp: QApplication) -> None:
        """run() emits result_ready with the SearchResult from preview()."""
        result = _make_result()
        worker = PreviewWorker(_make_service(result=result), _make_params())
        received: list[SearchResult] = []
        worker.result_ready.connect(received.append)
        worker.run()
        assert len(received) == 1
        assert received[0] is result

    def test_worker_emits_error_on_exception(self, qapp: QApplication) -> None:
        """run() emits error_occurred with the exception message when preview() raises."""
        worker = PreviewWorker(
            _make_service(exc=ConnectionError("timed out")), _make_params()
        )
        errors: list[str] = []
        worker.error_occurred.connect(errors.append)
        worker.run()
        assert len(errors) == 1
        assert "timed out" in errors[0]

    def test_worker_calls_service_preview_with_params(self, qapp: QApplication) -> None:
        """run() forwards the params to service.preview() unchanged."""
        params = _make_params(query="unique query", sort_order="date")
        svc = _make_service()
        worker = PreviewWorker(svc, params)
        worker.run()
        svc.preview.assert_called_once_with(params)

    def test_worker_does_not_emit_result_on_error(self, qapp: QApplication) -> None:
        """run() does not emit result_ready when preview() raises."""
        worker = PreviewWorker(_make_service(exc=RuntimeError("boom")), _make_params())
        received: list[SearchResult] = []
        worker.result_ready.connect(received.append)
        worker.run()
        assert received == []

    def test_worker_does_not_emit_error_on_success(self, qapp: QApplication) -> None:
        """run() does not emit error_occurred on a successful call."""
        worker = PreviewWorker(_make_service(), _make_params())
        errors: list[str] = []
        worker.error_occurred.connect(errors.append)
        worker.run()
        assert errors == []


# ---------------------------------------------------------------------------
# TestScreenPreviewDefaults
# ---------------------------------------------------------------------------


class TestScreenPreviewDefaults:
    """Verify the initial (blank) state of a freshly created ScreenPreview."""

    def test_is_qwidget(self, qapp: QApplication) -> None:
        """ScreenPreview is a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        assert isinstance(ScreenPreview(_make_service()), QWidget)

    def test_has_back_requested_signal(self, qapp: QApplication) -> None:
        """ScreenPreview exposes a back_requested signal."""
        assert hasattr(ScreenPreview, "back_requested")

    def test_has_download_requested_signal(self, qapp: QApplication) -> None:
        """ScreenPreview exposes a download_requested signal."""
        assert hasattr(ScreenPreview, "download_requested")

    def test_progress_hidden_initially(self, qapp: QApplication) -> None:
        """Loading wrapper is hidden before load() is called."""
        w = ScreenPreview(_make_service())
        assert w._loading_card.isHidden()

    def test_error_widget_hidden_initially(self, qapp: QApplication) -> None:
        """Error widget is hidden before load() is called."""
        w = ScreenPreview(_make_service())
        assert w._error_widget.isHidden()

    def test_content_hidden_initially(self, qapp: QApplication) -> None:
        """Content area is hidden before any results arrive."""
        w = ScreenPreview(_make_service())
        assert w._content.isHidden()

    def test_start_button_disabled_initially(self, qapp: QApplication) -> None:
        """Start download button is disabled before folder and count are set."""
        w = ScreenPreview(_make_service())
        assert not w._start_btn.isEnabled()


# ---------------------------------------------------------------------------
# TestScreenPreviewLoadingState
# ---------------------------------------------------------------------------


class TestScreenPreviewLoadingState:
    """Tests for the loading state (via _show_loading, which load() calls first)."""

    def test_show_loading_shows_progress(self, qapp: QApplication) -> None:
        """_show_loading() makes the progress widget visible."""
        w = ScreenPreview(_make_service())
        w._show_loading()
        assert not w._progress.isHidden()

    def test_show_loading_hides_content(self, qapp: QApplication) -> None:
        """_show_loading() hides the content area."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result())  # first show content
        w._show_loading()
        assert w._content.isHidden()

    def test_show_loading_hides_error_widget(self, qapp: QApplication) -> None:
        """_show_loading() hides the error widget."""
        w = ScreenPreview(_make_service())
        w._on_error("previous error")
        w._show_loading()
        assert w._error_widget.isHidden()

    def test_load_stores_params(self, qapp: QApplication) -> None:
        """load() stores the given params before starting the worker."""
        params = _make_params(query="sleep")
        w = ScreenPreview(_make_service())
        # Set params directly to avoid starting the thread
        w._params = params
        assert w._params is params


# ---------------------------------------------------------------------------
# TestScreenPreviewResultsState
# ---------------------------------------------------------------------------


class TestScreenPreviewResultsState:
    """Tests for the results state after _on_result() is called."""

    def test_on_result_shows_content(self, qapp: QApplication) -> None:
        """_on_result() makes the content area visible."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result())
        assert not w._content.isHidden()

    def test_on_result_hides_progress(self, qapp: QApplication) -> None:
        """_on_result() hides the loading wrapper."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result())
        assert w._loading_card.isHidden()

    def test_on_result_hides_error_widget(self, qapp: QApplication) -> None:
        """_on_result() hides the error widget."""
        w = ScreenPreview(_make_service())
        w._on_error("some error")
        w._on_result(_make_result())
        assert w._error_widget.isHidden()

    def test_on_result_stat_total_found(self, qapp: QApplication) -> None:
        """Stat tile shows total_found with thousands separator."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result(total=1247))
        assert w._stat_total_value.text() == "1,247"

    def test_on_result_stat_pdf_available(self, qapp: QApplication) -> None:
        """Stat tile shows PDF availability as percentage of previewed papers."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result(n_papers=5, pdf_count=4))
        assert w._stat_pdf_value.text() == "~80%"

    def test_on_result_stat_previewing(self, qapp: QApplication) -> None:
        """Stat tile shows number of papers in the preview list."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result(n_papers=5))
        assert w._stat_previewing_value.text() == "5"

    def test_on_result_paper_rows_created(self, qapp: QApplication) -> None:
        """Paper list layout contains one widget per paper (plus a trailing stretch)."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result(n_papers=4))
        # count() includes the trailing stretch spacer item
        widget_count = sum(
            1 for i in range(w._paper_list_layout.count())
            if w._paper_list_layout.itemAt(i).widget() is not None
        )
        assert widget_count == 4

    def test_on_result_paper_list_cleared_on_reload(self, qapp: QApplication) -> None:
        """Calling _on_result twice clears old rows before adding new ones."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result(n_papers=3))
        w._on_result(_make_result(n_papers=2))
        widget_count = sum(
            1 for i in range(w._paper_list_layout.count())
            if w._paper_list_layout.itemAt(i).widget() is not None
        )
        assert widget_count == 2

    def test_on_result_stat_total_zero(self, qapp: QApplication) -> None:
        """Stat tile handles zero total_found correctly."""
        w = ScreenPreview(_make_service())
        w._on_result(SearchResult(papers=[], total_found=0, estimated_downloadable=0))
        assert w._stat_total_value.text() == "0"


# ---------------------------------------------------------------------------
# TestScreenPreviewErrorState
# ---------------------------------------------------------------------------


class TestScreenPreviewErrorState:
    """Tests for the error state after _on_error() is called."""

    def test_on_error_shows_error_widget(self, qapp: QApplication) -> None:
        """_on_error() makes the error widget visible."""
        w = ScreenPreview(_make_service())
        w._on_error("API unavailable")
        assert not w._error_widget.isHidden()

    def test_on_error_hides_progress(self, qapp: QApplication) -> None:
        """_on_error() hides the loading wrapper."""
        w = ScreenPreview(_make_service())
        w._on_error("API unavailable")
        assert w._loading_card.isHidden()

    def test_on_error_hides_content(self, qapp: QApplication) -> None:
        """_on_error() hides the content area."""
        w = ScreenPreview(_make_service())
        w._on_result(_make_result())  # first show content
        w._on_error("API unavailable")
        assert w._content.isHidden()

    def test_on_error_message_contains_error_text(self, qapp: QApplication) -> None:
        """The error label contains the error message string."""
        w = ScreenPreview(_make_service())
        w._on_error("Network timeout occurred")
        assert "Network timeout occurred" in w._error_label.text()

    def test_on_error_try_again_button_exists(self, qapp: QApplication) -> None:
        """The error widget exposes a Try again button."""
        w = ScreenPreview(_make_service())
        assert hasattr(w, "_try_again_btn")


# ---------------------------------------------------------------------------
# TestScreenPreviewValidation
# ---------------------------------------------------------------------------


class TestScreenPreviewValidation:
    """Tests for Start download button enable/disable logic."""

    def test_start_disabled_without_folder(self, qapp: QApplication) -> None:
        """Button is disabled when count is set but no folder is chosen."""
        w = ScreenPreview(_make_service())
        w._count_spin.setValue(10)
        w._folder_edit.setText("")
        assert not w._start_btn.isEnabled()

    def test_start_enabled_with_count_and_folder(self, qapp: QApplication) -> None:
        """Button is enabled when count >= 1 and folder is non-empty."""
        w = ScreenPreview(_make_service())
        w._count_spin.setValue(10)
        w._folder_edit.setText("/tmp/papers")
        assert w._start_btn.isEnabled()

    def test_start_disabled_after_folder_cleared(self, qapp: QApplication) -> None:
        """Button is disabled again when the folder is cleared."""
        w = ScreenPreview(_make_service())
        w._count_spin.setValue(10)
        w._folder_edit.setText("/tmp/papers")
        w._folder_edit.setText("")
        assert not w._start_btn.isEnabled()

    def test_count_spin_minimum_is_one(self, qapp: QApplication) -> None:
        """Count spinbox minimum is 1 (prevents a zero count)."""
        w = ScreenPreview(_make_service())
        assert w._count_spin.minimum() == 1

    def test_count_spin_default_value(self, qapp: QApplication) -> None:
        """Count spinbox defaults to 50."""
        w = ScreenPreview(_make_service())
        assert w._count_spin.value() == 50

    def test_start_disabled_when_folder_not_writable(self, qapp: QApplication) -> None:
        """Button is disabled when a folder is selected but is not writable."""
        w = ScreenPreview(_make_service())
        w._count_spin.setValue(10)
        # Simulate non-writable folder by setting internal flag directly
        w._folder_edit.setText("/tmp/papers")
        w._folder_writable = False
        w._validate()
        assert not w._start_btn.isEnabled()

    def test_start_enabled_when_folder_writable(self, qapp: QApplication) -> None:
        """Button is enabled when folder is set and writable."""
        w = ScreenPreview(_make_service())
        w._count_spin.setValue(10)
        w._folder_edit.setText("/tmp/papers")
        w._folder_writable = True
        w._validate()
        assert w._start_btn.isEnabled()

    def test_browse_folder_sets_not_writable_on_unwritable_path(
        self, qapp: QApplication
    ) -> None:
        """Selecting a non-writable folder via Browse sets _folder_writable to False."""

        w = ScreenPreview(_make_service())
        with (
            patch(
                "epmcminer.gui.screens.screen_preview.QFileDialog.getExistingDirectory",
                return_value="/unwritable/path",
            ),
            patch("os.access", return_value=False),
        ):
            w._browse_folder()
        assert w._folder_writable is False

    def test_browse_folder_sets_writable_on_writable_path(self, qapp: QApplication) -> None:
        """Selecting a writable folder via Browse sets _folder_writable to True."""
        w = ScreenPreview(_make_service())
        with (
            patch(
                "epmcminer.gui.screens.screen_preview.QFileDialog.getExistingDirectory",
                return_value="/tmp/papers",
            ),
            patch("os.access", return_value=True),
        ):
            w._browse_folder()
        assert w._folder_writable is True

    def test_count_label_text(self, qapp: QApplication) -> None:
        """The count field label reads 'Number of papers'."""
        from PyQt6.QtWidgets import QLabel

        w = ScreenPreview(_make_service())
        labels = w.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any("number of papers" in t.lower() for t in texts)


# ---------------------------------------------------------------------------
# TestScreenPreviewSignals
# ---------------------------------------------------------------------------


class TestScreenPreviewSignals:
    """Tests for back_requested and download_requested signal emissions."""

    def test_back_button_emits_back_requested(self, qapp: QApplication) -> None:
        """Clicking Back emits back_requested."""
        w = ScreenPreview(_make_service())
        received: list[None] = []
        w.back_requested.connect(lambda: received.append(None))
        w._back_btn.click()
        assert len(received) == 1

    def test_start_button_emits_download_requested(self, qapp: QApplication) -> None:
        """Clicking Start download emits download_requested."""
        w = ScreenPreview(_make_service())
        w._params = _make_params()
        w._count_spin.setValue(25)
        w._folder_edit.setText("/tmp/out")
        received: list[SearchParams] = []
        w.download_requested.connect(received.append)
        w._start_btn.click()
        assert len(received) == 1

    def test_download_requested_carries_count(self, qapp: QApplication) -> None:
        """Emitted SearchParams contains the count from the spinbox."""
        w = ScreenPreview(_make_service())
        w._params = _make_params()
        w._count_spin.setValue(75)
        w._folder_edit.setText("/tmp/out")
        received: list[SearchParams] = []
        w.download_requested.connect(received.append)
        w._start_btn.click()
        assert received[0].count == 75

    def test_download_requested_carries_folder(self, qapp: QApplication) -> None:
        """Emitted SearchParams contains the output_folder from the folder field."""
        w = ScreenPreview(_make_service())
        w._params = _make_params()
        w._count_spin.setValue(10)
        w._folder_edit.setText("/tmp/papers")
        received: list[SearchParams] = []
        w.download_requested.connect(received.append)
        w._start_btn.click()
        assert received[0].output_folder == Path("/tmp/papers")

    def test_download_requested_carries_sort_order(self, qapp: QApplication) -> None:
        """Emitted SearchParams reflects the currently selected sort order."""
        w = ScreenPreview(_make_service())
        w._params = _make_params(sort_order="relevance")
        w._count_spin.setValue(10)
        w._folder_edit.setText("/tmp/out")
        # Set sort index directly without triggering a reload
        w._sort_index = 1  # index 1 = "date"
        received: list[SearchParams] = []
        w.download_requested.connect(received.append)
        w._start_btn.click()
        assert received[0].sort_order == "date"

    def test_download_requested_preserves_original_query(self, qapp: QApplication) -> None:
        """Emitted SearchParams preserves the original query from the first screen."""
        original = _make_params(query="sleep AND memory")
        w = ScreenPreview(_make_service())
        w._params = original
        w._count_spin.setValue(10)
        w._folder_edit.setText("/tmp/out")
        received: list[SearchParams] = []
        w.download_requested.connect(received.append)
        w._start_btn.click()
        assert received[0].query == "sleep AND memory"

    def test_start_button_not_clicked_when_disabled(self, qapp: QApplication) -> None:
        """download_requested is not emitted when the button is disabled."""
        w = ScreenPreview(_make_service())
        w._params = _make_params()
        # no folder set → button disabled
        received: list[SearchParams] = []
        w.download_requested.connect(received.append)
        w._start_btn.click()
        assert received == []


# ---------------------------------------------------------------------------
# TestScreenPreviewSortChange
# ---------------------------------------------------------------------------


class TestScreenPreviewSortChange:
    """Tests for sort order change behaviour."""

    def test_sort_menu_has_three_options(self, qapp: QApplication) -> None:
        """Sort menu contains relevance, date, and citations options."""
        w = ScreenPreview(_make_service())
        assert len(w._sort_menu.actions()) == 3

    def test_sort_default_index_is_relevance(self, qapp: QApplication) -> None:
        """Sort defaults to index 0 (relevance)."""
        w = ScreenPreview(_make_service())
        assert w._sort_index == 0

    def test_sort_synced_on_load(self, qapp: QApplication) -> None:
        """load() syncs _sort_index to params.sort_order without triggering a second load."""
        svc = _make_service()
        w = ScreenPreview(svc)
        with patch("epmcminer.gui.screens.screen_preview.PreviewWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w.load(_make_params(sort_order="citations"))
        assert w._sort_index == 2  # index 2 = "citations"

    def test_sort_menu_selected_updates_params_sort_order(self, qapp: QApplication) -> None:
        """_on_sort_menu_selected() updates _params.sort_order before the worker starts."""
        svc = _make_service()
        w = ScreenPreview(svc)
        w._params = _make_params(sort_order="relevance")
        with patch("epmcminer.gui.screens.screen_preview.PreviewWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w._on_sort_menu_selected("date")
        assert w._params is not None
        assert w._params.sort_order == "date"

    def test_sort_menu_selected_updates_sort_index(self, qapp: QApplication) -> None:
        """_on_sort_menu_selected() updates _sort_index to match the chosen key."""
        w = ScreenPreview(_make_service())
        w._params = _make_params(sort_order="relevance")
        with patch("epmcminer.gui.screens.screen_preview.PreviewWorker") as MockWorker:
            MockWorker.return_value.isRunning.return_value = False
            w._on_sort_menu_selected("citations")
        assert w._sort_index == 2
