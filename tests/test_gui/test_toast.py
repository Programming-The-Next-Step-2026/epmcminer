"""Tests for the Toast overlay notification widget."""

import sys
from collections.abc import Generator

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from epmcminer.gui.widgets.toast import (
    _ERROR_BADGE_BG,
    _ERROR_STRIPE,
    _HOLD_MS_ERROR,
    _HOLD_MS_SUCCESS,
    _SUCCESS_BADGE_BG,
    _SUCCESS_STRIPE,
    _TOAST_BG,
    Toast,
)

# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parent_widget(qapp) -> QWidget:
    w = QWidget()
    w.resize(800, 600)
    return w


@pytest.fixture
def toast(parent_widget) -> Toast:
    return Toast(parent_widget)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestToastInitialState:
    def test_hidden_on_creation(self, toast: Toast) -> None:
        assert toast.isHidden()

    def test_message_empty_on_creation(self, toast: Toast) -> None:
        assert toast._msg_lbl.text() == ""

    def test_icon_empty_on_creation(self, toast: Toast) -> None:
        assert toast._icon_lbl.text() == ""

    def test_icon_badge_fixed_size(self, toast: Toast) -> None:
        from epmcminer.gui.widgets.toast import _BADGE_SIZE

        assert toast._icon_lbl.width() == _BADGE_SIZE
        assert toast._icon_lbl.height() == _BADGE_SIZE


# ---------------------------------------------------------------------------
# show_message — success variant
# ---------------------------------------------------------------------------


class TestToastShowSuccess:
    def test_visible_after_show(self, toast: Toast) -> None:
        toast.show_message("Saved!", success=True)
        assert not toast.isHidden()

    def test_check_icon_shown(self, toast: Toast) -> None:
        toast.show_message("Saved!", success=True)
        assert toast._icon_lbl.text() == "✓"

    def test_message_text_set(self, toast: Toast) -> None:
        toast.show_message("Saved to results.xlsx", success=True)
        assert toast._msg_lbl.text() == "Saved to results.xlsx"

    def test_success_badge_bg_in_icon_stylesheet(self, toast: Toast) -> None:
        """Icon badge background uses the success badge color."""
        toast.show_message("ok", success=True)
        assert _SUCCESS_BADGE_BG in toast._icon_lbl.styleSheet()

    def test_success_stripe_in_toast_stylesheet(self, toast: Toast) -> None:
        """Toast border uses the success stripe color."""
        toast.show_message("ok", success=True)
        assert _SUCCESS_STRIPE in toast.styleSheet()

    def test_toast_bg_in_stylesheet(self, toast: Toast) -> None:
        toast.show_message("ok", success=True)
        assert _TOAST_BG in toast.styleSheet()

    def test_hold_timer_interval_is_success_duration(self, toast: Toast) -> None:
        toast.show_message("ok", success=True)
        assert toast._hold_timer.interval() == _HOLD_MS_SUCCESS


# ---------------------------------------------------------------------------
# show_message — error variant
# ---------------------------------------------------------------------------


class TestToastShowError:
    def test_visible_after_show(self, toast: Toast) -> None:
        toast.show_message("Export failed", success=False)
        assert not toast.isHidden()

    def test_cross_icon_shown(self, toast: Toast) -> None:
        toast.show_message("Export failed", success=False)
        assert toast._icon_lbl.text() == "✗"

    def test_message_text_set(self, toast: Toast) -> None:
        toast.show_message("Connection error", success=False)
        assert toast._msg_lbl.text() == "Connection error"

    def test_error_badge_bg_in_icon_stylesheet(self, toast: Toast) -> None:
        """Icon badge background uses the error badge color."""
        toast.show_message("fail", success=False)
        assert _ERROR_BADGE_BG in toast._icon_lbl.styleSheet()

    def test_error_stripe_in_toast_stylesheet(self, toast: Toast) -> None:
        """Toast border uses the error stripe color."""
        toast.show_message("fail", success=False)
        assert _ERROR_STRIPE in toast.styleSheet()

    def test_hold_timer_interval_is_error_duration(self, toast: Toast) -> None:
        toast.show_message("fail", success=False)
        assert toast._hold_timer.interval() == _HOLD_MS_ERROR

    def test_hold_durations_are_both_10_seconds(self) -> None:
        # 10 000 ms (10 s) was chosen to give users enough reading time for long
        # file-path messages.  Update this test deliberately if the hold time changes.
        assert _HOLD_MS_SUCCESS == 10000
        assert _HOLD_MS_ERROR == 10000


# ---------------------------------------------------------------------------
# Interruption — calling show_message while one is already visible
# ---------------------------------------------------------------------------


class TestToastInterruption:
    def test_message_replaced_when_interrupted(self, toast: Toast) -> None:
        toast.show_message("First message", success=True)
        toast.show_message("Second message", success=False)
        assert toast._msg_lbl.text() == "Second message"

    def test_icon_replaced_when_interrupted(self, toast: Toast) -> None:
        toast.show_message("First", success=True)
        toast.show_message("Second", success=False)
        assert toast._icon_lbl.text() == "✗"

    def test_stripe_switches_on_interrupt(self, toast: Toast) -> None:
        """Stripe color updates when a new toast interrupts a running one."""
        toast.show_message("First", success=True)
        toast.show_message("Second", success=False)
        assert _ERROR_STRIPE in toast.styleSheet()
        assert _SUCCESS_STRIPE not in toast.styleSheet()

    def test_still_visible_after_interruption(self, toast: Toast) -> None:
        toast.show_message("First", success=True)
        toast.show_message("Second", success=False)
        assert not toast.isHidden()

    def test_fading_out_flag_reset_on_interrupt(self, toast: Toast) -> None:
        toast.show_message("First", success=True)
        # Simulate being mid-fade-out.
        toast._fading_out = True
        toast.show_message("Second", success=True)
        assert not toast._fading_out


# ---------------------------------------------------------------------------
# Repositioning
# ---------------------------------------------------------------------------


class TestToastRepositioning:
    def test_repositioned_within_parent_bounds(
        self, toast: Toast, parent_widget: QWidget
    ) -> None:
        toast.show_message("Saved!", success=True)
        # x should be non-negative (not clipped left of parent).
        assert toast.x() >= 0
        # y should be above the bottom edge of the parent.
        assert toast.y() < parent_widget.height()

    def test_reposition_noop_without_parent(self, parent_widget: QWidget) -> None:
        """reposition() must not raise when the widget has no parent."""
        t = Toast(parent_widget)
        t.setParent(None)  # type: ignore[arg-type]
        t.reposition()  # must not raise
