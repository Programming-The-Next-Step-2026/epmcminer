"""Screen 2 — results preview and download settings."""

from PyQt6.QtWidgets import QWidget


class ScreenPreview(QWidget):
    """Wizard screen for previewing search results and configuring the download.

    Displays a paginated table of matched papers returned by SearchService.
    Allows the user to set the output directory and confirm the download.
    Emits a signal carrying download configuration when the user proceeds.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the preview screen.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
