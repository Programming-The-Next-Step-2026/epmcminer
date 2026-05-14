"""Screen 1 — search query and filter inputs."""

from PyQt6.QtWidgets import QWidget


class ScreenSearch(QWidget):
    """Wizard screen for composing a Europe PMC search query.

    Provides keyword inputs, active filter controls, sort-order selection,
    and a result-count selector. Emits a signal carrying SearchParams when
    the user submits the query.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the search screen.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
