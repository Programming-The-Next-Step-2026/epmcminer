"""Tests for epmcminer.gui.widgets.progress_widget."""

import sys
from collections.abc import Generator

import pytest
from PyQt6.QtWidgets import QApplication

from epmcminer.gui.widgets.progress_widget import ProgressWidget

# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestProgressWidgetDefaults
# ---------------------------------------------------------------------------


class TestProgressWidgetDefaults:
    """Verify the initial (reset) state of a freshly created ProgressWidget."""

    def test_is_qwidget(self, qapp: QApplication) -> None:
        """ProgressWidget is a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        assert isinstance(ProgressWidget(), QWidget)

    def test_bar_hidden_initially(self, qapp: QApplication) -> None:
        """Progress bar is hidden before any state method is called."""
        assert ProgressWidget()._bar.isHidden()

    def test_loading_row_hidden_initially(self, qapp: QApplication) -> None:
        """Loading row is hidden before any state method is called."""
        assert ProgressWidget()._loading_row.isHidden()

    def test_stats_row_hidden_initially(self, qapp: QApplication) -> None:
        """Stats row is hidden before any state method is called."""
        assert ProgressWidget()._stats_row.isHidden()


# ---------------------------------------------------------------------------
# TestProgressWidgetLoadingState
# ---------------------------------------------------------------------------


class TestProgressWidgetLoadingState:
    """Tests for the indeterminate loading state."""

    def test_set_loading_shows_bar(self, qapp: QApplication) -> None:
        """set_loading makes the progress bar visible."""
        w = ProgressWidget()
        w.set_loading()
        assert not w._bar.isHidden()

    def test_set_loading_bar_is_indeterminate(self, qapp: QApplication) -> None:
        """set_loading sets the progress bar to indeterminate (range 0–0)."""
        w = ProgressWidget()
        w.set_loading()
        assert w._bar.minimum() == 0
        assert w._bar.maximum() == 0

    def test_set_loading_shows_loading_row(self, qapp: QApplication) -> None:
        """set_loading makes the loading row (dots + message) visible."""
        w = ProgressWidget()
        w.set_loading()
        assert not w._loading_row.isHidden()

    def test_set_loading_hides_stats_row(self, qapp: QApplication) -> None:
        """set_loading hides the progress stats row."""
        w = ProgressWidget()
        w.set_loading()
        assert w._stats_row.isHidden()

    def test_set_loading_default_message(self, qapp: QApplication) -> None:
        """set_loading without arguments shows 'Loading...'."""
        w = ProgressWidget()
        w.set_loading()
        assert w._msg_label.text() == "Loading..."

    def test_set_loading_custom_message(self, qapp: QApplication) -> None:
        """set_loading with a custom message displays that message."""
        w = ProgressWidget()
        w.set_loading("Fetching results…")
        assert w._msg_label.text() == "Fetching results…"

    def test_set_loading_has_dot_frames(self, qapp: QApplication) -> None:
        """Loading row contains three animated dot frames."""
        w = ProgressWidget()
        assert len(w._loading_dot_frames) == 3


# ---------------------------------------------------------------------------
# TestProgressWidgetProgressState
# ---------------------------------------------------------------------------


class TestProgressWidgetProgressState:
    """Tests for the determinate progress state."""

    def test_set_progress_shows_bar(self, qapp: QApplication) -> None:
        """set_progress makes the progress bar visible."""
        w = ProgressWidget()
        w.set_progress(10, 50)
        assert not w._bar.isHidden()

    def test_set_progress_bar_is_determinate(self, qapp: QApplication) -> None:
        """set_progress sets a non-zero range on the progress bar."""
        w = ProgressWidget()
        w.set_progress(10, 50)
        assert w._bar.maximum() == 50

    def test_set_progress_bar_value(self, qapp: QApplication) -> None:
        """set_progress sets the bar value to current."""
        w = ProgressWidget()
        w.set_progress(23, 50)
        assert w._bar.value() == 23

    def test_set_progress_hides_loading_row(self, qapp: QApplication) -> None:
        """set_progress hides the loading row."""
        w = ProgressWidget()
        w.set_progress(10, 50)
        assert w._loading_row.isHidden()

    def test_set_progress_shows_stats_row(self, qapp: QApplication) -> None:
        """set_progress makes the stats row visible."""
        w = ProgressWidget()
        w.set_progress(10, 50)
        assert not w._stats_row.isHidden()

    def test_set_progress_percentage_label(self, qapp: QApplication) -> None:
        """Percentage label shows rounded integer percentage."""
        w = ProgressWidget()
        w.set_progress(23, 50)
        assert w._pct_label.text() == "46%"

    def test_set_progress_count_label_without_processed(self, qapp: QApplication) -> None:
        """Count label shows 'downloaded X out of Y' when processed is not given."""
        w = ProgressWidget()
        w.set_progress(23, 50)
        assert w._count_label.text() == "downloaded 23 out of 50"

    def test_set_progress_count_label_with_processed(self, qapp: QApplication) -> None:
        """Count label includes processed count when the processed argument is provided."""
        w = ProgressWidget()
        w.set_progress(23, 50, processed=30)
        assert w._count_label.text() == "downloaded 23 out of 50  –  processed 30 results"

    def test_set_progress_percentage_zero(self, qapp: QApplication) -> None:
        """Percentage is 0% when current is 0."""
        w = ProgressWidget()
        w.set_progress(0, 50)
        assert w._pct_label.text() == "0%"

    def test_set_progress_percentage_complete(self, qapp: QApplication) -> None:
        """Percentage is 100% when current equals total."""
        w = ProgressWidget()
        w.set_progress(50, 50)
        assert w._pct_label.text() == "100%"

    def test_set_progress_repeated_calls_update_labels(self, qapp: QApplication) -> None:
        """Repeated set_progress calls update all labels correctly."""
        w = ProgressWidget()
        w.set_progress(10, 50)
        w.set_progress(30, 50)
        assert w._pct_label.text() == "60%"
        assert w._count_label.text() == "downloaded 30 out of 50"


# ---------------------------------------------------------------------------
# TestProgressWidgetETA
# ---------------------------------------------------------------------------


class TestProgressWidgetETA:
    """Tests for the ETA (estimated time remaining) display."""

    def test_eta_hidden_when_none(self, qapp: QApplication) -> None:
        """ETA column is hidden when eta_seconds is None."""
        w = ProgressWidget()
        w.set_progress(10, 50, eta_seconds=None)
        assert w._eta_col.isHidden()

    def test_eta_visible_when_provided(self, qapp: QApplication) -> None:
        """ETA column is visible when eta_seconds is given."""
        w = ProgressWidget()
        w.set_progress(10, 50, eta_seconds=240)
        assert not w._eta_col.isHidden()

    def test_eta_formats_minutes(self, qapp: QApplication) -> None:
        """ETA of 60+ seconds is shown as '~N min'."""
        w = ProgressWidget()
        w.set_progress(10, 50, eta_seconds=240)
        assert w._eta_value.text() == "~4 min"

    def test_eta_formats_seconds(self, qapp: QApplication) -> None:
        """ETA under 60 seconds is shown as '~Ns'."""
        w = ProgressWidget()
        w.set_progress(10, 50, eta_seconds=45)
        assert w._eta_value.text() == "~45s"

    def test_eta_exactly_60_seconds_shows_minutes(self, qapp: QApplication) -> None:
        """ETA of exactly 60 seconds rounds to '~1 min'."""
        w = ProgressWidget()
        w.set_progress(10, 50, eta_seconds=60)
        assert w._eta_value.text() == "~1 min"

    def test_eta_hidden_after_none_call(self, qapp: QApplication) -> None:
        """Calling set_progress with eta_seconds=None hides ETA even after prior visible call."""
        w = ProgressWidget()
        w.set_progress(10, 50, eta_seconds=120)
        w.set_progress(20, 50, eta_seconds=None)
        assert w._eta_col.isHidden()


# ---------------------------------------------------------------------------
# TestProgressWidgetThreadDots
# ---------------------------------------------------------------------------


class TestProgressWidgetThreadDots:
    """Tests for the thread count dot indicators."""

    def test_thread_row_visible_when_provided(self, qapp: QApplication) -> None:
        """Thread row is visible when thread_count is given."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=3)
        assert not w._thread_row.isHidden()

    def test_thread_label_singular(self, qapp: QApplication) -> None:
        """thread_count=1 shows '1 thread running'."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=1)
        assert w._thread_label.text() == "1 thread running"

    def test_thread_label_plural(self, qapp: QApplication) -> None:
        """thread_count > 1 shows 'N threads running'."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=3)
        assert w._thread_label.text() == "3 threads running"

    def test_thread_dots_always_three(self, qapp: QApplication) -> None:
        """All 3 thread dots are always visible regardless of thread_count."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=1)
        assert len(w._thread_dots) == 3
        assert all(not d.isHidden() for d in w._thread_dots)

    def test_thread_row_hidden_after_none_call(self, qapp: QApplication) -> None:
        """Thread row is hidden when set_progress is called with thread_count=None."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=3)
        w.set_progress(20, 50, thread_count=None)
        assert w._thread_row.isHidden()

    def test_thread_label_cancelling_singular(self, qapp: QApplication) -> None:
        """cancelling=True with thread_count=1 shows 'cancelling, waiting for 1 thread'."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=1, cancelling=True)
        assert w._thread_label.text() == "cancelling, waiting for 1 thread"

    def test_thread_label_cancelling_plural(self, qapp: QApplication) -> None:
        """cancelling=True with thread_count>1 shows 'cancelling, waiting for N threads'."""
        w = ProgressWidget()
        w.set_progress(10, 50, thread_count=3, cancelling=True)
        assert w._thread_label.text() == "cancelling, waiting for 3 threads"


# ---------------------------------------------------------------------------
# TestProgressWidgetReset
# ---------------------------------------------------------------------------


class TestProgressWidgetReset:
    """Tests for the reset method."""

    def test_reset_hides_bar(self, qapp: QApplication) -> None:
        """reset hides the progress bar."""
        w = ProgressWidget()
        w.set_loading()
        w.reset()
        assert w._bar.isHidden()

    def test_reset_hides_loading_row(self, qapp: QApplication) -> None:
        """reset hides the loading row."""
        w = ProgressWidget()
        w.set_loading()
        w.reset()
        assert w._loading_row.isHidden()

    def test_reset_hides_stats_row(self, qapp: QApplication) -> None:
        """reset hides the stats row."""
        w = ProgressWidget()
        w.set_progress(10, 50)
        w.reset()
        assert w._stats_row.isHidden()


# ---------------------------------------------------------------------------
# TestProgressWidgetStateTransitions
# ---------------------------------------------------------------------------


class TestProgressWidgetStateTransitions:
    """Tests that state transitions work in any order without errors."""

    def test_loading_then_progress(self, qapp: QApplication) -> None:
        """Switching from loading to progress shows the stats row and hides loading row."""
        w = ProgressWidget()
        w.set_loading("Querying API…")
        w.set_progress(5, 50)
        assert not w._stats_row.isHidden()
        assert w._loading_row.isHidden()

    def test_progress_then_loading(self, qapp: QApplication) -> None:
        """Switching from progress to loading shows loading row and hides stats row."""
        w = ProgressWidget()
        w.set_progress(5, 50)
        w.set_loading("Re-querying…")
        assert not w._loading_row.isHidden()
        assert w._stats_row.isHidden()

    def test_reset_then_loading(self, qapp: QApplication) -> None:
        """Calling set_loading after reset works correctly."""
        w = ProgressWidget()
        w.reset()
        w.set_loading()
        assert not w._bar.isHidden()
        assert not w._loading_row.isHidden()

    def test_reset_then_progress(self, qapp: QApplication) -> None:
        """Calling set_progress after reset works correctly."""
        w = ProgressWidget()
        w.reset()
        w.set_progress(10, 50)
        assert not w._bar.isHidden()
        assert not w._stats_row.isHidden()

    def test_multiple_loading_calls_update_message(self, qapp: QApplication) -> None:
        """Calling set_loading twice updates the message label."""
        w = ProgressWidget()
        w.set_loading("First")
        w.set_loading("Second")
        assert w._msg_label.text() == "Second"
