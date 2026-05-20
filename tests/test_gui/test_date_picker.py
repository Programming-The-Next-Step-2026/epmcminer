"""Tests for epmcminer.gui.widgets.date_picker."""

import sys
from collections.abc import Generator

import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication, QWidget

from epmcminer.gui.widgets.date_picker import DatePicker

# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestDatePickerDefaults
# ---------------------------------------------------------------------------


class TestDatePickerDefaults:
    """Verify the initial state of a freshly created DatePicker."""

    def test_is_qwidget_instance(self, qapp: QApplication) -> None:
        """DatePicker is a QWidget subclass."""
        assert isinstance(DatePicker(), QWidget)

    def test_default_date_is_today(self, qapp: QApplication) -> None:
        """The default selected date is today."""
        assert DatePicker().date() == QDate.currentDate()

    def test_min_date_defaults_to_none(self, qapp: QApplication) -> None:
        """minimumDate() returns None when no lower bound is set."""
        assert DatePicker().minimumDate() is None

    def test_max_date_defaults_to_none(self, qapp: QApplication) -> None:
        """maximumDate() returns None when no upper bound is set."""
        assert DatePicker().maximumDate() is None

    def test_has_stylesheet(self, qapp: QApplication) -> None:
        """A non-empty stylesheet is applied on construction."""
        assert DatePicker().styleSheet() != ""

    def test_style_is_set(self, qapp: QApplication) -> None:
        """A QStyle is applied on construction (not None)."""
        assert DatePicker().style() is not None

    def test_min_date_set_via_constructor(self, qapp: QApplication) -> None:
        """The min_date constructor parameter is stored and returned by minimumDate()."""
        min_d = QDate(2020, 1, 1)
        assert DatePicker(min_date=min_d).minimumDate() == min_d

    def test_max_date_set_via_constructor(self, qapp: QApplication) -> None:
        """The max_date constructor parameter is stored and returned by maximumDate()."""
        max_d = QDate(2030, 12, 31)
        assert DatePicker(max_date=max_d).maximumDate() == max_d


# ---------------------------------------------------------------------------
# TestDatePickerBehaviour
# ---------------------------------------------------------------------------


class TestDatePickerBehaviour:
    """Tests for DatePicker date-handling API."""

    def test_setdate_and_date_roundtrip(self, qapp: QApplication) -> None:
        """setDate / date() round-trips the value correctly."""
        dp = DatePicker()
        target = QDate(2022, 6, 15)
        dp.setDate(target)
        assert dp.date() == target

    def test_date_changed_signal_fires_on_setdate(self, qapp: QApplication) -> None:
        """dateChanged is emitted exactly once when setDate is called with a new date."""
        dp = DatePicker()
        received: list[QDate] = []
        dp.dateChanged.connect(received.append)
        dp.setDate(QDate(2021, 3, 1))
        assert len(received) == 1
        assert received[0] == QDate(2021, 3, 1)

    def test_date_changed_not_emitted_when_date_unchanged(self, qapp: QApplication) -> None:
        """dateChanged is not emitted when setDate is called with the same date."""
        dp = DatePicker()
        dp.setDate(QDate(2021, 3, 1))
        received: list[QDate] = []
        dp.dateChanged.connect(received.append)
        dp.setDate(QDate(2021, 3, 1))
        assert len(received) == 0

    def test_setminimumdate_stored(self, qapp: QApplication) -> None:
        """setMinimumDate stores the value readable back via minimumDate()."""
        dp = DatePicker()
        min_d = QDate(2010, 1, 1)
        dp.setMinimumDate(min_d)
        assert dp.minimumDate() == min_d

    def test_setmaximumdate_stored(self, qapp: QApplication) -> None:
        """setMaximumDate stores the value readable back via maximumDate()."""
        dp = DatePicker()
        max_d = QDate(2030, 12, 31)
        dp.setMaximumDate(max_d)
        assert dp.maximumDate() == max_d

    def test_date_clamped_to_minimum_on_setdate(self, qapp: QApplication) -> None:
        """setDate clamps a date below the minimum to the minimum."""
        dp = DatePicker()
        dp.setMinimumDate(QDate(2020, 1, 1))
        dp.setDate(QDate(2015, 6, 1))
        assert dp.date() == QDate(2020, 1, 1)

    def test_date_clamped_to_maximum_on_setdate(self, qapp: QApplication) -> None:
        """setDate clamps a date above the maximum to the maximum."""
        dp = DatePicker()
        dp.setMaximumDate(QDate(2020, 12, 31))
        dp.setDate(QDate(2030, 1, 1))
        assert dp.date() == QDate(2020, 12, 31)

    def test_setminimumdate_clamps_current_date(self, qapp: QApplication) -> None:
        """setMinimumDate clamps the current date when it falls below the new minimum."""
        dp = DatePicker()
        dp.setDate(QDate(2015, 1, 1))
        dp.setMinimumDate(QDate(2020, 1, 1))
        assert dp.date() == QDate(2020, 1, 1)

    def test_setmaximumdate_clamps_current_date(self, qapp: QApplication) -> None:
        """setMaximumDate clamps the current date when it exceeds the new maximum."""
        dp = DatePicker()
        dp.setDate(QDate(2030, 1, 1))
        dp.setMaximumDate(QDate(2025, 12, 31))
        assert dp.date() == QDate(2025, 12, 31)

    def test_display_text_reflects_selected_date(self, qapp: QApplication) -> None:
        """The display button text contains the currently selected date."""
        dp = DatePicker()
        target = QDate(2022, 6, 15)
        dp.setDate(target)
        assert target.toString("d MMM yyyy") in dp._display.text()
