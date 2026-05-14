"""Main application window managing screen navigation and the step indicator."""

from PyQt6.QtWidgets import QMainWindow

APP_TITLE = "epmcminer"
DEFAULT_WIDTH = 900
DEFAULT_HEIGHT = 640


class MainWindow(QMainWindow):
    """Top-level window for epmcminer.

    Owns the four wizard screens, the step indicator widget, and all
    screen-transition logic. Screens never navigate themselves; they emit
    signals that MainWindow connects to its navigation slots.
    """

    def __init__(self) -> None:
        """Initialise the main window with a default title and size."""
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
