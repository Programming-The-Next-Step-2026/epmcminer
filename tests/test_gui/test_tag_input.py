"""Tests for epmcminer.gui.widgets.tag_input."""

import sys
from collections.abc import Generator

import pytest
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
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

    def test_has_scroll_area(self, qapp: QApplication) -> None:
        """TagInput contains a QScrollArea for the pill container."""
        widget = TagInput()
        scroll_areas = widget.findChildren(QScrollArea)
        assert len(scroll_areas) == 1

    def test_has_add_button(self, qapp: QApplication) -> None:
        """TagInput contains an add ('+') button."""
        widget = TagInput()
        buttons = widget.findChildren(QPushButton)
        add_buttons = [b for b in buttons if "+" in b.text()]
        assert len(add_buttons) == 1

    def test_free_text_mode_has_line_edit(self, qapp: QApplication) -> None:
        """Without available_options, a QLineEdit is present for free-text input."""
        widget = TagInput()
        assert len(widget.findChildren(QLineEdit)) >= 1

    def test_options_mode_has_combo_box(self, qapp: QApplication) -> None:
        """With available_options, a QComboBox replaces the QLineEdit."""
        widget = TagInput(available_options=["A", "B", "C"])
        assert len(widget.findChildren(QComboBox)) >= 1

    def test_options_mode_no_line_edit(self, qapp: QApplication) -> None:
        """With available_options, there is no free-text QLineEdit."""
        widget = TagInput(available_options=["A", "B", "C"])
        assert len(widget.findChildren(QLineEdit)) == 0


# ---------------------------------------------------------------------------
# TestTagInputAddTag
# ---------------------------------------------------------------------------


class TestTagInputAddTag:
    """Tests for the add_tag method and the add-button interaction."""

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
        received: list[list[str]] = []
        widget.add_tag("alpha")
        widget.tags_changed.connect(lambda tags: received.append(tags))
        widget.add_tag("alpha")
        assert received == []

    def test_add_button_click_adds_tag_from_line_edit(self, qapp: QApplication) -> None:
        """Clicking the + button adds text from the QLineEdit."""
        widget = TagInput()
        line_edit = widget.findChildren(QLineEdit)[0]
        line_edit.setText("gamma")
        add_button = next(b for b in widget.findChildren(QPushButton) if "+" in b.text())
        add_button.click()
        assert "gamma" in widget.get_tags()

    def test_add_button_clears_line_edit(self, qapp: QApplication) -> None:
        """Clicking + clears the QLineEdit after adding the tag."""
        widget = TagInput()
        line_edit = widget.findChildren(QLineEdit)[0]
        line_edit.setText("delta")
        add_button = next(b for b in widget.findChildren(QPushButton) if "+" in b.text())
        add_button.click()
        assert line_edit.text() == ""

    def test_return_key_adds_tag(self, qapp: QApplication) -> None:
        """Pressing Return/Enter in the QLineEdit adds the tag."""
        widget = TagInput()
        line_edit = widget.findChildren(QLineEdit)[0]
        line_edit.setText("epsilon")
        line_edit.returnPressed.emit()
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
    """Tests for pill rendering in the scroll area."""

    def test_pill_count_matches_tags(self, qapp: QApplication) -> None:
        """The number of pill buttons equals the number of tags."""
        widget = TagInput()
        widget.set_tags(["a", "b", "c"])
        pills = _get_pills(widget)
        assert len(pills) == 3

    def test_pill_text_contains_tag(self, qapp: QApplication) -> None:
        """Each pill button's text contains the tag value."""
        widget = TagInput()
        widget.add_tag("my-tag")
        pills = _get_pills(widget)
        assert any("my-tag" in p.text() for p in pills)

    def test_pill_has_remove_marker(self, qapp: QApplication) -> None:
        """Each pill button's text contains '×' to indicate it is removable."""
        widget = TagInput()
        widget.add_tag("alpha")
        pills = _get_pills(widget)
        assert any("×" in p.text() for p in pills)

    def test_clicking_pill_removes_tag(self, qapp: QApplication) -> None:
        """Clicking a pill button removes its tag."""
        widget = TagInput()
        widget.add_tag("alpha")
        pills = _get_pills(widget)
        assert len(pills) == 1
        pills[0].click()
        assert widget.get_tags() == []

    def test_pills_cleared_on_set_tags(self, qapp: QApplication) -> None:
        """After set_tags, old pill buttons are removed from the scroll area."""
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
    """Tests for QComboBox mode (available_options provided)."""

    def test_combo_populated_with_options(self, qapp: QApplication) -> None:
        """The QComboBox contains the provided available_options."""
        widget = TagInput(available_options=["Open Access", "CC BY"])
        combo = widget.findChildren(QComboBox)[0]
        items = [combo.itemText(i) for i in range(combo.count())]
        assert "Open Access" in items
        assert "CC BY" in items

    def test_add_button_adds_selected_option(self, qapp: QApplication) -> None:
        """Clicking + adds the currently selected combo item as a tag."""
        widget = TagInput(available_options=["Open Access", "CC BY"])
        combo = widget.findChildren(QComboBox)[0]
        combo.setCurrentIndex(0)
        selected = combo.currentText()
        add_button = next(b for b in widget.findChildren(QPushButton) if "+" in b.text())
        add_button.click()
        assert selected in widget.get_tags()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pills(widget: TagInput) -> list[QPushButton]:
    """Return all pill QPushButtons inside the TagInput's scroll area."""
    scroll = widget.findChildren(QScrollArea)[0]
    return scroll.widget().findChildren(QPushButton)
