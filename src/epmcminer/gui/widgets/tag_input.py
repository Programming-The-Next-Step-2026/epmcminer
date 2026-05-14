"""Reusable tag input widget used on all filter fields."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_PILL_STYLE = """
    QPushButton {{
        background-color: #FFF7ED;
        color: #C2410C;
        border: 1.5px solid #F97316;
        border-radius: 12px;
        padding: 2px 10px 2px 10px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: #FED7AA;
    }}
"""

_ADD_BUTTON_STYLE = """
    QPushButton {
        background-color: transparent;
        color: #F97316;
        border: 2px dashed #F97316;
        border-radius: 12px;
        padding: 2px 14px;
        font-size: 15px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #FFF7ED;
    }
"""

_INPUT_STYLE = """
    QLineEdit, QComboBox {
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 13px;
        min-width: 120px;
        max-width: 200px;
    }
"""


class _TagPill(QPushButton):
    """A removable pill button representing a single tag."""

    removed = pyqtSignal(str)

    def __init__(self, tag: str, parent: QWidget | None = None) -> None:
        super().__init__(f"{tag}  ×", parent)
        self._tag = tag
        self.setStyleSheet(_PILL_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.removed.emit(self._tag))


class TagInput(QWidget):
    """Widget that allows users to add and remove text tags.

    Renders each tag as a removable orange pill and emits a signal whenever
    the set of tags changes. Used on all filter input fields across screens.

    In free-text mode (default), a QLineEdit accepts arbitrary input.
    In options mode (pass ``available_options``), a QComboBox restricts input
    to the provided choices.

    Signals:
        tags_changed: Emitted with the current list of tags after any change.
    """

    tags_changed = pyqtSignal(list)

    def __init__(
        self,
        parent: QWidget | None = None,
        available_options: list[str] | None = None,
    ) -> None:
        """Initialise the tag input widget.

        Args:
            parent: Optional parent widget.
            available_options: If provided, a QComboBox is used instead of a
                free-text QLineEdit, restricting input to these choices.
        """
        super().__init__(parent)
        self._tags: list[str] = []
        self._available_options = available_options or []

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
        """Add a tag if it is non-blank and not already present.

        Args:
            tag: The tag string to add.
        """
        cleaned = tag.strip()
        if not cleaned or cleaned in self._tags:
            return
        self._tags.append(cleaned)
        self._add_pill(cleaned)
        self.tags_changed.emit(list(self._tags))

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present. No-op if the tag is not in the list.

        Args:
            tag: The tag string to remove.
        """
        if tag not in self._tags:
            return
        self._tags.remove(tag)
        self._rebuild_pills()
        self.tags_changed.emit(list(self._tags))

    def set_tags(self, tags: list[str]) -> None:
        """Replace the current tag list entirely.

        Blank strings are filtered out and duplicates are removed while
        preserving order. Emits ``tags_changed`` once with the final list.

        Args:
            tags: The new list of tag strings.
        """
        seen: list[str] = []
        for tag in tags:
            cleaned = tag.strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        self._tags = seen
        self._rebuild_pills()
        self.tags_changed.emit(list(self._tags))

    # ------------------------------------------------------------------
    # Internal UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        # --- pill container inside a horizontal scroll area ---
        self._pill_container = QWidget()
        self._pill_layout = QHBoxLayout(self._pill_container)
        self._pill_layout.setContentsMargins(4, 4, 4, 4)
        self._pill_layout.setSpacing(6)
        self._pill_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._pill_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(44)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        # --- input row ---
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(6)

        if self._available_options:
            self._input: QComboBox | QLineEdit = QComboBox()
            self._input.addItems(self._available_options)
        else:
            self._input = QLineEdit()
            self._input.setPlaceholderText("Add tag…")
            self._input.returnPressed.connect(self._on_add)

        self._input.setStyleSheet(_INPUT_STYLE)
        self._input.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        input_row.addWidget(self._input)

        self._add_btn = QPushButton("+")
        self._add_btn.setStyleSheet(_ADD_BUTTON_STYLE)
        self._add_btn.setFixedSize(32, 28)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._on_add)
        input_row.addWidget(self._add_btn)
        input_row.addStretch()

        outer.addLayout(input_row)

    def _on_add(self) -> None:
        if isinstance(self._input, QComboBox):
            text = self._input.currentText()
        else:
            text = self._input.text()
            self._input.clear()
        self.add_tag(text)

    def _add_pill(self, tag: str) -> None:
        pill = _TagPill(tag)
        pill.removed.connect(self.remove_tag)
        # Insert before the trailing stretch (last item).
        self._pill_layout.insertWidget(self._pill_layout.count() - 1, pill)

    def _rebuild_pills(self) -> None:
        # Remove all widgets except the trailing stretch.
        while self._pill_layout.count() > 1:
            item = self._pill_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)  # detach immediately so findChildren sees current state
        for tag in self._tags:
            self._add_pill(tag)
