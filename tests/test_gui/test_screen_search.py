"""Tests for epmcminer.gui.screens.screen_search."""

import sys
from collections.abc import Generator
from datetime import date

import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication

from epmcminer.gui.screens.screen_search import DEFAULT_PUBLICATION_TYPES, ScreenSearch
from epmcminer.services.models import SearchParams

# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# TestScreenSearchDefaults
# ---------------------------------------------------------------------------


class TestScreenSearchDefaults:
    """Verify the initial state of a freshly created ScreenSearch."""

    def test_is_qwidget(self, qapp: QApplication) -> None:
        """ScreenSearch is a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        assert isinstance(ScreenSearch(), QWidget)

    def test_has_search_requested_signal(self, qapp: QApplication) -> None:
        """ScreenSearch exposes a search_requested signal."""
        assert hasattr(ScreenSearch, "search_requested")

    def test_query_empty_initially(self, qapp: QApplication) -> None:
        """The query field is empty on creation."""
        assert ScreenSearch()._query_edit.text() == ""

    def test_pub_types_preloaded(self, qapp: QApplication) -> None:
        """Publication types are pre-loaded with all DEFAULT_PUBLICATION_TYPES."""
        w = ScreenSearch()
        assert w._pub_types.get_tags() == DEFAULT_PUBLICATION_TYPES

    def test_default_publication_types_not_empty(self, qapp: QApplication) -> None:
        """DEFAULT_PUBLICATION_TYPES contains at least one entry."""
        assert len(DEFAULT_PUBLICATION_TYPES) > 0

    def test_license_preloaded_cc_by(self, qapp: QApplication) -> None:
        """License is pre-loaded with CC-BY."""
        assert ScreenSearch()._license.get_tags() == ["CC-BY"]

    def test_orcids_empty_initially(self, qapp: QApplication) -> None:
        """Author ORCIDs are empty on creation."""
        assert ScreenSearch()._orcids.get_tags() == []

    def test_date_to_defaults_to_today(self, qapp: QApplication) -> None:
        """End date defaults to today."""
        today = QDate.currentDate()
        assert ScreenSearch()._date_to.date() == today

    def test_date_from_defaults_to_five_years_ago(self, qapp: QApplication) -> None:
        """Start date defaults to today minus five years."""
        expected = QDate.currentDate().addYears(-5)
        assert ScreenSearch()._date_from.date() == expected

    def test_date_to_maximum_is_today(self, qapp: QApplication) -> None:
        """End date has a maximum of today (cannot select a future date)."""
        today = QDate.currentDate()
        assert ScreenSearch()._date_to.maximumDate() == today


# ---------------------------------------------------------------------------
# TestScreenSearchValidation
# ---------------------------------------------------------------------------


class TestScreenSearchValidation:
    """Tests for the 'Continue to preview' button enable/disable logic."""

    def test_continue_button_disabled_initially(self, qapp: QApplication) -> None:
        """Button is disabled when the query is empty (even with pub types loaded)."""
        assert not ScreenSearch()._continue_btn.isEnabled()

    def test_continue_button_enabled_after_query_entered(self, qapp: QApplication) -> None:
        """Button is enabled once the query field contains non-whitespace text."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        assert w._continue_btn.isEnabled()

    def test_continue_button_disabled_after_query_cleared(self, qapp: QApplication) -> None:
        """Button is disabled again when the query is cleared."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        w._query_edit.clear()
        assert not w._continue_btn.isEnabled()

    def test_continue_button_disabled_when_no_pub_types(self, qapp: QApplication) -> None:
        """Button is disabled when all publication types are removed."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        w._pub_types.set_tags([])
        assert not w._continue_btn.isEnabled()

    def test_continue_button_enabled_after_pub_type_restored(self, qapp: QApplication) -> None:
        """Button re-enables when a publication type is added back."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        w._pub_types.set_tags([])
        w._pub_types.add_tag("Review")
        assert w._continue_btn.isEnabled()

    def test_whitespace_only_query_does_not_enable_button(self, qapp: QApplication) -> None:
        """Whitespace-only query text does not count as a valid query."""
        w = ScreenSearch()
        w._query_edit.setText("   ")
        assert not w._continue_btn.isEnabled()

    def test_continue_button_disabled_when_no_license(self, qapp: QApplication) -> None:
        """Button is disabled when all licenses are removed."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        w._license.set_tags([])
        assert not w._continue_btn.isEnabled()

    def test_continue_button_enabled_after_license_restored(self, qapp: QApplication) -> None:
        """Button re-enables when a license is added back."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        w._license.set_tags([])
        w._license.add_tag("CC-BY")
        assert w._continue_btn.isEnabled()

    def test_query_max_length_is_500(self, qapp: QApplication) -> None:
        """Query input enforces a maximum length of 500 characters."""
        w = ScreenSearch()
        assert w._query_edit.maxLength() == 500

    def test_date_from_minimum_is_1900(self, qapp: QApplication) -> None:
        """Date From minimum is 1 January 1900."""
        w = ScreenSearch()
        assert w._date_from.minimumDate() == QDate(1900, 1, 1)


# ---------------------------------------------------------------------------
# TestScreenSearchHintLabel
# ---------------------------------------------------------------------------


class TestScreenSearchHintLabel:
    """Tests for the action-bar hint label driven by _validate."""

    def test_hint_label_hidden_when_all_valid(self, qapp: QApplication) -> None:
        """Hint label is hidden when query and all tag fields are populated."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        assert not w._hint_lbl.isVisible()

    def test_hint_label_visible_when_query_empty(self, qapp: QApplication) -> None:
        """Hint label is not explicitly hidden on initial load (query is empty)."""
        w = ScreenSearch()
        assert not w._hint_lbl.isHidden()

    def test_hint_label_contains_keyword_when_query_missing(self, qapp: QApplication) -> None:
        """Hint text mentions 'keyword' when the query field is empty."""
        w = ScreenSearch()
        assert "keyword" in w._hint_lbl.text().lower()

    def test_hint_label_contains_license_when_only_license_missing(
        self, qapp: QApplication
    ) -> None:
        """Hint text mentions 'license' when only the license field is empty."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        w._license.set_tags([])
        assert "license" in w._hint_lbl.text().lower()

    def test_hint_label_mentions_all_missing_fields(self, qapp: QApplication) -> None:
        """Hint text covers all three missing fields simultaneously."""
        w = ScreenSearch()
        # query empty, pub types cleared, license cleared
        w._pub_types.set_tags([])
        w._license.set_tags([])
        text = w._hint_lbl.text().lower()
        assert "keyword" in text
        assert "publication" in text
        assert "license" in text


# ---------------------------------------------------------------------------
# TestScreenSearchGetParams
# ---------------------------------------------------------------------------


class TestScreenSearchGetParams:
    """Tests for the get_params method."""

    def test_returns_search_params_instance(self, qapp: QApplication) -> None:
        """get_params returns a SearchParams object."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        assert isinstance(w.get_params(), SearchParams)

    def test_get_params_query(self, qapp: QApplication) -> None:
        """get_params reflects the current query field text."""
        w = ScreenSearch()
        w._query_edit.setText("memory AND sleep")
        assert w.get_params().query == "memory AND sleep"

    def test_get_params_strips_query_whitespace(self, qapp: QApplication) -> None:
        """get_params strips leading and trailing whitespace from the query."""
        w = ScreenSearch()
        w._query_edit.setText("  depression  ")
        assert w.get_params().query == "depression"

    def test_get_params_date_from_iso_format(self, qapp: QApplication) -> None:
        """date_from is returned as an ISO-format string (YYYY-MM-DD)."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        params = w.get_params()
        date.fromisoformat(params.date_from)  # raises ValueError if malformed

    def test_get_params_date_to_iso_format(self, qapp: QApplication) -> None:
        """date_to is returned as an ISO-format string (YYYY-MM-DD)."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        params = w.get_params()
        date.fromisoformat(params.date_to)

    def test_get_params_date_to_is_today(self, qapp: QApplication) -> None:
        """date_to defaults to today's date."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        assert w.get_params().date_to == date.today().isoformat()

    def test_get_params_pub_types_default(self, qapp: QApplication) -> None:
        """publication_types contains all 16 default types by default."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        assert w.get_params().publication_types == DEFAULT_PUBLICATION_TYPES

    def test_get_params_licenses_default(self, qapp: QApplication) -> None:
        """licenses contains CC-BY by default."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        assert w.get_params().licenses == ["CC-BY"]

    def test_get_params_author_orcids_empty(self, qapp: QApplication) -> None:
        """author_orcids is empty when no ORCIDs have been added."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        assert w.get_params().author_orcids == []

    def test_get_params_author_orcids_populated(self, qapp: QApplication) -> None:
        """author_orcids reflects tags added to the ORCID TagInput."""
        w = ScreenSearch()
        w._query_edit.setText("q")
        w._orcids.add_tag("0000-0001-2345-6789")
        assert w.get_params().author_orcids == ["0000-0001-2345-6789"]


# ---------------------------------------------------------------------------
# TestScreenSearchSignal
# ---------------------------------------------------------------------------


class TestScreenSearchSignal:
    """Tests for the search_requested signal."""

    def test_signal_emitted_on_continue_click(self, qapp: QApplication) -> None:
        """Clicking Continue emits search_requested."""
        w = ScreenSearch()
        w._query_edit.setText("depression")
        received: list[SearchParams] = []
        w.search_requested.connect(received.append)
        w._continue_btn.click()
        assert len(received) == 1

    def test_signal_carries_correct_query(self, qapp: QApplication) -> None:
        """The emitted SearchParams contains the query from the form."""
        w = ScreenSearch()
        w._query_edit.setText("memory AND sleep")
        received: list[SearchParams] = []
        w.search_requested.connect(received.append)
        w._continue_btn.click()
        assert received[0].query == "memory AND sleep"

    def test_signal_not_emitted_when_button_disabled(self, qapp: QApplication) -> None:
        """search_requested is not emitted when the button is disabled."""
        w = ScreenSearch()
        received: list[SearchParams] = []
        w.search_requested.connect(received.append)
        w._continue_btn.click()
        assert received == []


# ---------------------------------------------------------------------------
# TestScreenSearchDateRange
# ---------------------------------------------------------------------------


class TestScreenSearchDateRange:
    """Tests for date-range constraint enforcement."""

    def test_changing_from_date_updates_to_minimum(self, qapp: QApplication) -> None:
        """Moving the start date forward raises the end date's minimum."""
        w = ScreenSearch()
        new_from = QDate.currentDate().addDays(-10)
        w._date_from.setDate(new_from)
        assert w._date_to.minimumDate() == new_from

    def test_from_date_later_than_to_date_advances_to_date(
        self, qapp: QApplication
    ) -> None:
        """If the start date is set past the end date, end date is moved to match."""
        w = ScreenSearch()
        future_from = QDate.currentDate()
        w._date_to.setDate(QDate.currentDate().addDays(-1))
        w._date_from.setDate(future_from)
        assert w._date_to.date() >= w._date_from.date()
