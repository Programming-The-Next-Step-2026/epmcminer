"""Reusable tag input widget used on all filter fields."""

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QWidget,
)

import epmcminer.gui.theme as theme

# Colour tokens from ui.jsx / handoff.jsx.
# Qt QSS uses 0-255 integer alpha in rgba(), not CSS 0.0-1.0 floats.
# 0.18×255≈46, 0.06×255≈15, 0.55×255≈140.

_PILL_STYLE = """
    QPushButton {
        background-color: #3a2218;
        color: #ff9a6a;
        border: 1px solid #5a3424;
        border-radius: 14px;
        padding: 6px 12px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #4a2c20;
    }
"""

_PILL_PENDING_STYLE = """
    QPushButton {
        background-color: #28282c;
        color: #8a8a90;
        border: 1px solid #3c3c42;
        border-radius: 14px;
        padding: 6px 12px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #303036;
    }
"""

_PILL_INVALID_STYLE = """
    QPushButton {
        background-color: #2e1a1a;
        color: #f87171;
        border: 1px solid #5a2424;
        border-radius: 14px;
        padding: 6px 12px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #3a2020;
    }
"""

_PILL_STYLES: dict[str, str] = {
    "valid": _PILL_STYLE,
    "pending": _PILL_PENDING_STYLE,
    "invalid": _PILL_INVALID_STYLE,
}

_ADD_BUTTON_STYLE = """
    QPushButton {
        background-color: #1c1c1f;
        color: #ededed;
        border: 1px solid rgba(255, 255, 255, 46);
        border-radius: 14px;
        padding: 6px 14px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #2a2a2d;
    }
"""

# Same height as chips: 6px top + 14px font + 6px bottom + 2px border = 28px
_INLINE_INPUT_STYLE = """
    QLineEdit {
        background-color: #242427;
        color: #ededed;
        border: 1px solid rgba(255, 255, 255, 46);
        border-radius: 14px;
        padding: 6px 10px;
        font-size: 14px;
        min-width: 100px;
        max-width: 220px;
    }
    QLineEdit:focus {
        border-color: rgba(255, 122, 61, 140);
    }
"""

_INLINE_CONFIRM_STYLE = """
    QPushButton {
        background-color: #ff7a3d;
        color: #1a0e07;
        border: 1px solid #ff7a3d;
        border-radius: 14px;
        padding: 6px 12px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #e8662a;
        border-color: #e8662a;
    }
"""

_MENU_STYLE = """
    QMenu {
        background-color: #1c1c1f;
        border: 1px solid rgba(255, 255, 255, 46);
        border-radius: 10px;
        padding: 5px;
        font-size: 14px;
        color: #ededed;
    }
    QMenu::item {
        padding: 9px 18px;
        border-radius: 6px;
        color: #ededed;
        font-size: 14px;
        font-weight: 400;
    }
    QMenu::item:selected {
        background-color: rgba(255, 122, 61, 46);
        color: #ff9a6a;
    }
"""


class _FlowLayout(QLayout):
    """Arranges child widgets in a wrapping row, like words in a paragraph."""

    def __init__(
        self,
        parent: QWidget | None = None,
        h_spacing: int = 10,
        v_spacing: int = 10,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def addItem(self, item) -> None:  # type: ignore[override]
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # type: ignore[override]
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # type: ignore[override]
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        line_h = 0
        right = rect.right() - m.right()

        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > right and line_h > 0:
                x = rect.x() + m.left()
                y += line_h + self._v_spacing
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._h_spacing
            line_h = max(line_h, hint.height())

        return y + line_h - rect.y() + m.bottom()


class _TagPill(QPushButton):
    """A removable pill button representing a single tag.

    The visual appearance is controlled by the ``status`` argument:

    * ``"valid"``   — default orange accent style
    * ``"pending"`` — muted grey; existence check is in flight
    * ``"invalid"`` — red; bad format or ORCID not found in registry
    """

    removed = pyqtSignal(str)

    def __init__(
        self,
        tag: str,
        status: str = "valid",
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the pill button.

        Args:
            tag: The tag string displayed on the pill.
            status: Visual state — ``"valid"``, ``"pending"``, or ``"invalid"``.
            parent: Optional parent widget.
        """
        super().__init__(f"{tag}  ×", parent)
        self._tag = tag
        self.setStyle(theme.get_fusion_style())
        self.setStyleSheet(_PILL_STYLES.get(status, _PILL_STYLE))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clicked.connect(lambda: self.removed.emit(self._tag))


class _InputSlot(QWidget):
    """Inline slot that switches between the add button and an input.

    **Free-text mode** (no ``available_options``): clicking the add button
    hides it and reveals an inline QLineEdit plus an accent-orange confirm
    button at chip height. Confirming emits ``tag_confirmed``.

    **Options mode** (``available_options`` provided): clicking the add button
    pops up a QMenu positioned directly below the button. Selecting an item
    emits ``tag_confirmed`` immediately — no separate confirm step. Already-
    selected options are excluded from the menu automatically.

    Signals:
        tag_confirmed: Emitted with the entered/selected string.
    """

    tag_confirmed = pyqtSignal(str)

    def __init__(
        self,
        add_label: str = "+ Add tag",
        available_options: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the input slot.

        Args:
            add_label: Text shown on the idle add button.
            available_options: If provided, a QMenu is used instead of QLineEdit.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._available_options = list(available_options or [])
        self._excluded: set[str] = set()

        # All three attributes exist in both modes; unused ones are None.
        self._input: QLineEdit | None = None
        self._confirm_btn: QPushButton | None = None
        self._menu: QMenu | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._add_btn = QPushButton(add_label)
        self._add_btn.setStyle(theme.get_fusion_style())
        self._add_btn.setStyleSheet(_ADD_BUTTON_STYLE)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._add_btn)

        if self._available_options:
            self._menu = QMenu(self)
            self._menu.setStyleSheet(_MENU_STYLE)
            self._add_btn.clicked.connect(self._show_menu)
        else:
            self._input = QLineEdit()
            self._input.setStyle(theme.get_fusion_style())
            self._input.setPlaceholderText("Add…")
            self._input.setStyleSheet(_INLINE_INPUT_STYLE)
            self._input.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            self._input.setVisible(False)
            self._input.returnPressed.connect(self._confirm)
            layout.addWidget(self._input)

            self._confirm_btn = QPushButton("✓")
            self._confirm_btn.setStyle(theme.get_fusion_style())
            self._confirm_btn.setStyleSheet(_INLINE_CONFIRM_STYLE)
            self._confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._confirm_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._confirm_btn.setVisible(False)
            self._confirm_btn.clicked.connect(self._confirm)
            layout.addWidget(self._confirm_btn)

            self._add_btn.clicked.connect(self._show_input)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_excluded(self, tags: list[str]) -> None:
        """Update the set of tags excluded from the options menu.

        Args:
            tags: Currently selected tags to omit from the popup menu.
        """
        self._excluded = set(tags)
        self._update_add_btn_visibility()

    def _update_add_btn_visibility(self) -> None:
        """Hide the add button when all options are already selected."""
        if not self._available_options:
            return
        all_taken = all(o in self._excluded for o in self._available_options)
        self._add_btn.setVisible(not all_taken)

    def reset(self) -> None:
        """Return to idle state without emitting a signal."""
        if self._input is not None:
            self._add_btn.setVisible(True)
            self._input.setVisible(False)
            self._input.clear()
            if self._confirm_btn is not None:
                self._confirm_btn.setVisible(False)
            self._relayout()

    # ------------------------------------------------------------------
    # Options mode
    # ------------------------------------------------------------------

    def _populate_menu(self) -> None:
        """Rebuild menu actions, omitting already-selected options."""
        if self._menu is None:
            return
        self._menu.clear()
        for option in self._available_options:
            if option not in self._excluded:
                action = self._menu.addAction(option)
                action.triggered.connect(
                    lambda checked, o=option: self.tag_confirmed.emit(o)
                )

    def _show_menu(self) -> None:
        self._populate_menu()
        pos = self._add_btn.mapToGlobal(QPoint(0, self._add_btn.height() + 4))
        self._menu.exec(pos)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Free-text mode
    # ------------------------------------------------------------------

    def _show_input(self) -> None:
        self._add_btn.setVisible(False)
        if self._input is not None:
            self._input.setVisible(True)
        if self._confirm_btn is not None:
            self._confirm_btn.setVisible(True)
        self._relayout()
        if self._input is not None:
            self._input.setFocus()

    def _confirm(self) -> None:
        text = self._input.text() if self._input is not None else ""
        if self._input is not None:
            self._input.clear()
        self._add_btn.setVisible(True)
        if self._input is not None:
            self._input.setVisible(False)
        if self._confirm_btn is not None:
            self._confirm_btn.setVisible(False)
        self._relayout()
        self.tag_confirmed.emit(text)

    def _relayout(self) -> None:
        """Resize to new sizeHint and force parent flow layout to reposition."""
        self.layout().invalidate()
        self.layout().activate()
        self.resize(self.sizeHint())
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            if parent.layout() is not None:
                parent.layout().invalidate()
                parent.layout().activate()
            parent.updateGeometry()


class TagInput(QWidget):
    """Widget that allows users to add and remove text tags.

    Renders tags as removable orange pills in a wrapping flow layout.

    In free-text mode (default) clicking the add button reveals an inline
    QLineEdit. In options mode (pass ``available_options``) a popup QMenu
    is shown instead — one click selects and confirms.

    Signals:
        tags_changed: Emitted with the current list of tags after any change.
    """

    tags_changed = pyqtSignal(list)

    def __init__(
        self,
        parent: QWidget | None = None,
        available_options: list[str] | None = None,
        add_label: str = "+ Add tag",
    ) -> None:
        """Initialise the tag input widget.

        Args:
            parent: Optional parent widget.
            available_options: If provided, restricts input to these choices.
            add_label: Label on the add button, e.g. '+ Add ORCID'.
        """
        super().__init__(parent)
        self._tags: list[str] = []
        self._tag_statuses: dict[str, str] = {}
        self._available_options = available_options or []
        self._add_label = add_label
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_tags(self) -> list[str]:
        """Return a copy of the current tag list.

        Returns:
            A list of tag strings in insertion order.
        """
        return list(self._tags)

    def add_tag(self, tag: str) -> None:
        """Add a tag if non-blank and not already present.

        The tag is given a default status of ``"valid"``; call
        :meth:`set_tag_status` afterwards to change it.

        Args:
            tag: The tag string to add.
        """
        cleaned = tag.strip()
        if not cleaned or cleaned in self._tags:
            return
        self._tags.append(cleaned)
        self._tag_statuses.setdefault(cleaned, "valid")
        self._rebuild_pills()
        self._slot.set_excluded(self._tags)
        self.tags_changed.emit(list(self._tags))

    def remove_tag(self, tag: str) -> None:
        """Remove a tag. No-op if not present.

        Args:
            tag: The tag string to remove.
        """
        if tag not in self._tags:
            return
        self._tags.remove(tag)
        self._tag_statuses.pop(tag, None)
        self._rebuild_pills()
        self._slot.set_excluded(self._tags)
        self.tags_changed.emit(list(self._tags))

    def set_tags(self, tags: list[str]) -> None:
        """Replace the tag list. Filters blanks, deduplicates, emits once.

        Existing statuses are preserved for tags that appear in both the old
        and new lists. New tags start with status ``"valid"``.

        Args:
            tags: The new list of tag strings.
        """
        seen: list[str] = []
        for tag in tags:
            cleaned = tag.strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        self._tags = seen
        # Remove statuses for tags no longer present; keep existing ones.
        self._tag_statuses = {t: self._tag_statuses.get(t, "valid") for t in self._tags}
        self._rebuild_pills()
        self._slot.set_excluded(self._tags)
        self.tags_changed.emit(list(self._tags))

    def set_tag_status(self, tag: str, status: str) -> None:
        """Update the visual status of an existing tag pill.

        If ``tag`` is not currently in the tag list this is a no-op.

        Args:
            tag: The tag string to update.
            status: One of ``"valid"``, ``"pending"``, or ``"invalid"``.
        """
        if tag not in self._tags:
            return
        self._tag_statuses[tag] = status
        self._rebuild_pills()

    # ------------------------------------------------------------------
    # Internal UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._flow = _FlowLayout(self)
        self._flow.setContentsMargins(0, 0, 0, 0)

        self._slot = _InputSlot(self._add_label, self._available_options)
        self._slot.tag_confirmed.connect(self.add_tag)
        self._flow.addWidget(self._slot)

    def _rebuild_pills(self) -> None:
        # Remove all items except _slot; hide before deparenting so that Qt
        # does not promote visible widgets to top-level windows.
        while self._flow.count() > 0:
            item = self._flow.takeAt(0)
            widget = item.widget() if item else None
            if widget and widget is not self._slot:
                widget.hide()
                widget.setParent(None)
        # Re-add pills in order, then the input slot.
        for tag in self._tags:
            status = self._tag_statuses.get(tag, "valid")
            pill = _TagPill(tag, status=status)
            pill.removed.connect(self.remove_tag)
            self._flow.addWidget(pill)
        self._flow.addWidget(self._slot)
        self.updateGeometry()
