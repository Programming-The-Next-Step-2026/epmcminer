"""Reusable animated progress/loading widget."""

from PyQt6.QtWidgets import QWidget


class ProgressWidget(QWidget):
    """Animated widget indicating an ongoing background operation.

    Wraps a progress bar and an optional status label. Can be switched
    between indeterminate (spinner) and determinate (percentage) modes.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the progress widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
