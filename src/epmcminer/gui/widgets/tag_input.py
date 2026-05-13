"""Reusable tag input widget used on all filter fields."""

from PyQt6.QtWidgets import QWidget


class TagInput(QWidget):
    """Widget that allows users to add and remove text tags.

    Renders each tag as a removable chip and emits a signal whenever
    the set of tags changes. Used on all filter input fields across screens.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the tag input widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
