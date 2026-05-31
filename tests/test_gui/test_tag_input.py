"""Tests for epmcminer.gui.widgets.tag_input."""

import sys
from collections.abc import Generator

import pytest
from PyQt6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMenu,
    QPushButton,
)

from epmcminer.gui.widgets.tag_input import TagInput

# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Provide a single QApplication for the entire test session."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pills(widget: TagInput) -> list[QPushButton]:
    """Return pill QPushButtons (those whose text contains '×')."""
    return [b for b in widget.findChildren(QPushButton) if "×" in b.text()]


def _get_add_btn(widget: TagInput) -> QPushButton:
    """Return the inline add button (text contains '+')."""
    return next(b for b in widget.findChildren(QPushButton) if "+" in b.text())


def _get_confirm_btn(widget: TagInput) -> QPushButton:
    """Return the confirm button inside the input slot (text is '✓')."""
    return next(b for b in widget.findChildren(QPushButton) if b.text() == "✓")


# ---------------------------------------------------------------------------
# TestTagInputDefaults
# ---------------------------------------------------------------------------


class TestTagInputDefaults:
    """Verify the initial state of a freshly created TagInput."""

    def test_starts_empty(self, qapp: QApplication) -> None:
        """get_tags() returns an empty list when no tags have been added."""
        widget = TagInput()
        assert widget.get_tags() == []

    def test_is_qwidget(self, qapp: QApplication) -> None:
        """TagInput is a QWidget subclass."""
        from PyQt6.QtWidgets import QWidget

        widget = TagInput()
        assert isinstance(widget, QWidget)

    def test_has_tags_changed_signal(self, qapp: QApplication) -> None:
        """TagInput exposes a tags_changed signal."""
        widget = TagInput()
        assert hasattr(widget, "tags_changed")

    def test_has_add_button(self, qapp: QApplication) -> None:
        """TagInput contains an inline add ('+') button."""
        widget = TagInput()
        assert _get_add_btn(widget) is not None

    def test_free_text_input_hidden_by_default(self, qapp: QApplication) -> None:
        """In free-text mode, the input field is hidden until the add button is clicked."""
        widget = TagInput()
        assert widget._slot._input is not None
        assert widget._slot._input.isHidden()

    def test_free_text_confirm_hidden_by_default(self, qapp: QApplication) -> None:
        """In free-text mode, the confirm button is hidden until the add button is clicked."""
        widget = TagInput()
        assert widget._slot._confirm_btn is not None
        assert widget._slot._confirm_btn.isHidden()

    def test_free_text_mode_has_line_edit(self, qapp: QApplication) -> None:
        """Without available_options, the slot contains a QLineEdit."""
        widget = TagInput()
        assert isinstance(widget._slot._input, QLineEdit)

    def test_options_mode_has_no_line_edit(self, qapp: QApplication) -> None:
        """With available_options, there is no inline QLineEdit."""
        widget = TagInput(available_options=["A", "B", "C"])
        assert widget._slot._input is None
        assert len(widget.findChildren(QLineEdit)) == 0

    def test_options_mode_has_menu(self, qapp: QApplication) -> None:
        """With available_options, a QMenu is present on the slot."""
        widget = TagInput(available_options=["A", "B", "C"])
        assert isinstance(widget._slot._menu, QMenu)

    def test_custom_add_label(self, qapp: QApplication) -> None:
        """add_label parameter sets the text of the add button."""
        widget = TagInput(add_label="+ Add ORCID")
        assert "Add ORCID" in _get_add_btn(widget).text()


# ---------------------------------------------------------------------------
# TestTagInputToggle  (free-text mode only)
# ---------------------------------------------------------------------------


class TestTagInputToggle:
    """Tests for the add-button toggle behaviour (free-text mode)."""

    def test_add_button_shows_input(self, qapp: QApplication) -> None:
        """Clicking the add button makes the input field visible."""
        widget = TagInput()
        _get_add_btn(widget).click()
        assert not widget._slot._input.isHidden()  # type: ignore[union-attr]

    def test_add_button_hides_itself(self, qapp: QApplication) -> None:
        """Clicking the add button hides the add button itself."""
        widget = TagInput()
        _get_add_btn(widget).click()
        assert widget._slot._add_btn.isHidden()

    def test_add_button_shows_confirm(self, qapp: QApplication) -> None:
        """Clicking the add button reveals the confirm button."""
        widget = TagInput()
        _get_add_btn(widget).click()
        assert not widget._slot._confirm_btn.isHidden()  # type: ignore[union-attr]

    def test_confirm_hides_input(self, qapp: QApplication) -> None:
        """Clicking the confirm button hides the input field."""
        widget = TagInput()
        _get_add_btn(widget).click()
        widget._slot._input.setText("alpha")  # type: ignore[union-attr]
        _get_confirm_btn(widget).click()
        assert widget._slot._input.isHidden()  # type: ignore[union-attr]

    def test_confirm_restores_add_button(self, qapp: QApplication) -> None:
        """Clicking confirm makes the add button visible again."""
        widget = TagInput()
        _get_add_btn(widget).click()
        _get_confirm_btn(widget).click()
        assert not widget._slot._add_btn.isHidden()

    def test_return_key_hides_input(self, qapp: QApplication) -> None:
        """Pressing Enter in the QLineEdit hides the input field after adding the tag."""
        widget = TagInput()
        _get_add_btn(widget).click()
        widget._slot._input.setText("beta")  # type: ignore[union-attr]
        widget._slot._input.returnPressed.emit()  # type: ignore[union-attr]
        assert widget._slot._input.isHidden()  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# TestTagInputAddTag
# ---------------------------------------------------------------------------


class TestTagInputAddTag:
    """Tests for the add_tag method and the confirm-button interaction."""

    def test_add_tag_increases_count(self, qapp: QApplication) -> None:
        """add_tag adds one tag to the list."""
        widget = TagInput()
        widget.add_tag("alpha")
        assert widget.get_tags() == ["alpha"]

    def test_add_multiple_tags(self, qapp: QApplication) -> None:
        """Multiple calls to add_tag accumulate in order."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.add_tag("beta")
        assert widget.get_tags() == ["alpha", "beta"]

    def test_add_duplicate_ignored(self, qapp: QApplication) -> None:
        """Adding a tag that already exists is silently ignored."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.add_tag("alpha")
        assert widget.get_tags().count("alpha") == 1

    def test_add_blank_ignored(self, qapp: QApplication) -> None:
        """Adding an empty or whitespace-only string is silently ignored."""
        widget = TagInput()
        widget.add_tag("")
        widget.add_tag("   ")
        assert widget.get_tags() == []

    def test_add_tag_emits_signal(self, qapp: QApplication) -> None:
        """add_tag emits tags_changed with the new tag list."""
        widget = TagInput()
        received: list[list[str]] = []
        widget.tags_changed.connect(lambda tags: received.append(tags))
        widget.add_tag("alpha")
        assert received == [["alpha"]]

    def test_add_duplicate_does_not_emit_signal(self, qapp: QApplication) -> None:
        """Adding a duplicate tag does not emit tags_changed."""
        widget = TagInput()
        widget.add_tag("alpha")
        received: list[list[str]] = []
        widget.tags_changed.connect(lambda tags: received.append(tags))
        widget.add_tag("alpha")
        assert received == []

    def test_confirm_button_adds_tag_from_line_edit(self, qapp: QApplication) -> None:
        """Clicking confirm adds text from the QLineEdit as a tag."""
        widget = TagInput()
        _get_add_btn(widget).click()
        widget._slot._input.setText("gamma")  # type: ignore[union-attr]
        _get_confirm_btn(widget).click()
        assert "gamma" in widget.get_tags()

    def test_confirm_button_clears_line_edit(self, qapp: QApplication) -> None:
        """Clicking confirm clears the QLineEdit."""
        widget = TagInput()
        _get_add_btn(widget).click()
        line_edit = widget._slot._input
        assert line_edit is not None
        line_edit.setText("delta")
        _get_confirm_btn(widget).click()
        assert line_edit.text() == ""

    def test_return_key_adds_tag(self, qapp: QApplication) -> None:
        """Pressing Return/Enter in the QLineEdit adds the tag."""
        widget = TagInput()
        _get_add_btn(widget).click()
        widget._slot._input.setText("epsilon")  # type: ignore[union-attr]
        widget._slot._input.returnPressed.emit()  # type: ignore[union-attr]
        assert "epsilon" in widget.get_tags()


# ---------------------------------------------------------------------------
# TestTagInputRemoveTag
# ---------------------------------------------------------------------------


class TestTagInputRemoveTag:
    """Tests for the remove_tag method."""

    def test_remove_existing_tag(self, qapp: QApplication) -> None:
        """remove_tag removes the specified tag from the list."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.remove_tag("alpha")
        assert widget.get_tags() == []

    def test_remove_one_of_many(self, qapp: QApplication) -> None:
        """remove_tag only removes the specified tag, leaving others intact."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.add_tag("beta")
        widget.remove_tag("alpha")
        assert widget.get_tags() == ["beta"]

    def test_remove_nonexistent_tag_no_error(self, qapp: QApplication) -> None:
        """Calling remove_tag for a tag not in the list does not raise."""
        widget = TagInput()
        widget.remove_tag("missing")

    def test_remove_tag_emits_signal(self, qapp: QApplication) -> None:
        """remove_tag emits tags_changed with the updated list."""
        widget = TagInput()
        widget.add_tag("alpha")
        received: list[list[str]] = []
        widget.tags_changed.connect(lambda tags: received.append(tags))
        widget.remove_tag("alpha")
        assert received == [[]]


# ---------------------------------------------------------------------------
# TestTagInputSetTags
# ---------------------------------------------------------------------------


class TestTagInputSetTags:
    """Tests for the set_tags method."""

    def test_set_tags_replaces_all(self, qapp: QApplication) -> None:
        """set_tags replaces the existing tag list entirely."""
        widget = TagInput()
        widget.add_tag("old")
        widget.set_tags(["new1", "new2"])
        assert widget.get_tags() == ["new1", "new2"]

    def test_set_tags_empty_list_clears(self, qapp: QApplication) -> None:
        """set_tags([]) clears all tags."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.set_tags([])
        assert widget.get_tags() == []

    def test_set_tags_emits_signal(self, qapp: QApplication) -> None:
        """set_tags emits tags_changed once with the new list."""
        widget = TagInput()
        received: list[list[str]] = []
        widget.tags_changed.connect(lambda tags: received.append(tags))
        widget.set_tags(["x", "y"])
        assert received == [["x", "y"]]

    def test_set_tags_deduplicates(self, qapp: QApplication) -> None:
        """set_tags silently deduplicates the provided list."""
        widget = TagInput()
        widget.set_tags(["a", "a", "b"])
        assert widget.get_tags().count("a") == 1

    def test_set_tags_filters_blank(self, qapp: QApplication) -> None:
        """set_tags ignores blank/whitespace-only strings."""
        widget = TagInput()
        widget.set_tags(["", "  ", "valid"])
        assert widget.get_tags() == ["valid"]


# ---------------------------------------------------------------------------
# TestTagInputPills
# ---------------------------------------------------------------------------


class TestTagInputPills:
    """Tests for pill rendering in the flow layout."""

    def test_pill_count_matches_tags(self, qapp: QApplication) -> None:
        """The number of pill buttons equals the number of tags."""
        widget = TagInput()
        widget.set_tags(["a", "b", "c"])
        assert len(_get_pills(widget)) == 3

    def test_pill_text_contains_tag(self, qapp: QApplication) -> None:
        """Each pill button's text contains the tag value."""
        widget = TagInput()
        widget.add_tag("my-tag")
        assert any("my-tag" in p.text() for p in _get_pills(widget))

    def test_pill_has_remove_marker(self, qapp: QApplication) -> None:
        """Each pill button's text contains '×' to indicate it is removable."""
        widget = TagInput()
        widget.add_tag("alpha")
        assert any("×" in p.text() for p in _get_pills(widget))

    def test_clicking_pill_removes_tag(self, qapp: QApplication) -> None:
        """Clicking a pill button removes its tag."""
        widget = TagInput()
        widget.add_tag("alpha")
        _get_pills(widget)[0].click()
        assert widget.get_tags() == []

    def test_pills_cleared_on_set_tags(self, qapp: QApplication) -> None:
        """After set_tags, old pill buttons are removed and new ones are shown."""
        widget = TagInput()
        widget.set_tags(["old1", "old2"])
        widget.set_tags(["new"])
        pills = _get_pills(widget)
        assert len(pills) == 1
        assert "new" in pills[0].text()


# ---------------------------------------------------------------------------
# TestTagInputOptionsMode
# ---------------------------------------------------------------------------


class TestTagInputOptionsMode:
    """Tests for QMenu popup mode (available_options provided)."""

    def test_menu_populated_with_options(self, qapp: QApplication) -> None:
        """The menu contains all provided available_options when none are selected."""
        widget = TagInput(available_options=["Open Access", "CC BY"])
        widget._slot._populate_menu()
        texts = [a.text() for a in widget._slot._menu.actions()]  # type: ignore[union-attr]
        assert "Open Access" in texts
        assert "CC BY" in texts

    def test_selecting_option_adds_tag(self, qapp: QApplication) -> None:
        """Triggering a menu action adds the option as a tag."""
        widget = TagInput(available_options=["Open Access", "CC BY"])
        widget._slot._populate_menu()
        action = next(
            a
            for a in widget._slot._menu.actions()  # type: ignore[union-attr]
            if a.text() == "Open Access"
        )
        action.trigger()
        assert "Open Access" in widget.get_tags()

    def test_selected_option_excluded_from_menu(self, qapp: QApplication) -> None:
        """An already-selected tag does not appear in the menu."""
        widget = TagInput(available_options=["Open Access", "CC BY", "CC BY-SA"])
        widget.add_tag("Open Access")
        widget._slot._populate_menu()
        texts = [a.text() for a in widget._slot._menu.actions()]  # type: ignore[union-attr]
        assert "Open Access" not in texts
        assert "CC BY" in texts

    def test_removed_tag_reappears_in_menu(self, qapp: QApplication) -> None:
        """After removing a tag it reappears as an option in the menu."""
        widget = TagInput(available_options=["Open Access", "CC BY"])
        widget.add_tag("Open Access")
        widget.remove_tag("Open Access")
        widget._slot._populate_menu()
        texts = [a.text() for a in widget._slot._menu.actions()]  # type: ignore[union-attr]
        assert "Open Access" in texts

    def test_all_options_selected_menu_empty(self, qapp: QApplication) -> None:
        """When all options are selected the menu has no actions."""
        options = ["A", "B"]
        widget = TagInput(available_options=options)
        for opt in options:
            widget.add_tag(opt)
        widget._slot._populate_menu()
        assert len(widget._slot._menu.actions()) == 0  # type: ignore[union-attr]

    def test_add_button_hidden_when_all_options_selected(self, qapp: QApplication) -> None:
        """The add button is hidden when every available option is already a tag."""
        options = ["A", "B"]
        widget = TagInput(available_options=options)
        for opt in options:
            widget.add_tag(opt)
        assert widget._slot._add_btn.isHidden()

    def test_add_button_restored_after_option_removed(self, qapp: QApplication) -> None:
        """Removing a tag brings the add button back."""
        options = ["A", "B"]
        widget = TagInput(available_options=options)
        for opt in options:
            widget.add_tag(opt)
        widget.remove_tag("A")
        assert not widget._slot._add_btn.isHidden()


# ---------------------------------------------------------------------------
# TestTagInputStatus
# ---------------------------------------------------------------------------


class TestTagInputStatus:
    """Tests for set_tag_status and get_tags_by_status."""

    def test_new_tag_defaults_to_valid(self, qapp: QApplication) -> None:
        """Tags start with status 'valid' unless explicitly changed."""
        widget = TagInput()
        widget.add_tag("alpha")
        assert widget._tag_statuses.get("alpha") == "valid"

    def test_set_tag_status_updates_status(self, qapp: QApplication) -> None:
        """set_tag_status changes the stored status for an existing tag."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.set_tag_status("alpha", "invalid")
        assert widget._tag_statuses.get("alpha") == "invalid"

    def test_set_tag_status_noop_for_unknown_tag(self, qapp: QApplication) -> None:
        """set_tag_status on a non-existent tag does not raise and changes nothing."""
        widget = TagInput()
        widget.set_tag_status("missing", "invalid")  # must not raise
        assert "missing" not in widget._tag_statuses

    def test_get_tags_by_status_returns_matching(self, qapp: QApplication) -> None:
        """get_tags_by_status returns only tags whose status is in the given list."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.add_tag("beta")
        widget.set_tag_status("beta", "invalid")
        assert widget.get_tags_by_status(["valid"]) == ["alpha"]

    def test_get_tags_by_status_multiple_statuses(self, qapp: QApplication) -> None:
        """get_tags_by_status accepts multiple statuses and includes all matching tags."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.add_tag("beta")
        widget.add_tag("gamma")
        widget.set_tag_status("beta", "pending")
        widget.set_tag_status("gamma", "invalid")
        result = widget.get_tags_by_status(["valid", "pending"])
        assert result == ["alpha", "beta"]
        assert "gamma" not in result

    def test_get_tags_by_status_empty_when_no_match(self, qapp: QApplication) -> None:
        """get_tags_by_status returns an empty list when no tags match."""
        widget = TagInput()
        widget.add_tag("alpha")
        widget.set_tag_status("alpha", "invalid")
        assert widget.get_tags_by_status(["valid"]) == []

    def test_get_tags_by_status_preserves_insertion_order(self, qapp: QApplication) -> None:
        """get_tags_by_status preserves insertion order of matching tags."""
        widget = TagInput()
        for tag in ["c", "a", "b"]:
            widget.add_tag(tag)
        widget.set_tag_status("a", "invalid")
        assert widget.get_tags_by_status(["valid"]) == ["c", "b"]

    def test_get_tags_by_status_all_invalid(self, qapp: QApplication) -> None:
        """Excluding all invalid tags returns an empty list."""
        widget = TagInput()
        widget.add_tag("x")
        widget.add_tag("y")
        widget.set_tag_status("x", "invalid")
        widget.set_tag_status("y", "invalid")
        assert widget.get_tags_by_status(["valid", "pending"]) == []
