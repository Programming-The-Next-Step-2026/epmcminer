"""Screen 4 — download summary, skipped papers, and export."""

from PyQt6.QtWidgets import QWidget


class ScreenSummary(QWidget):
    """Wizard screen presenting a summary of the completed download.

    Shows total downloaded, skipped, and failed counts, lists skipped
    papers with reasons, and offers CSV/Excel/PDF export via ReportService.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the summary screen.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
