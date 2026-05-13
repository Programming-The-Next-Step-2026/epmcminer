"""Screen 3 — download progress bar and live log."""

from PyQt6.QtWidgets import QWidget


class ScreenDownload(QWidget):
    """Wizard screen that shows download progress and a live activity log.

    Starts DownloadService in a QThread worker and updates the progress bar
    and log view via Qt signals as each paper is processed.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the download screen.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
