"""Entry point for the epmcminer application."""

import sys

from PyQt6.QtWidgets import QApplication

import epmcminer.gui.theme as theme
from epmcminer.gui.app import MainWindow


def main() -> None:
    """Create and launch the epmcminer desktop application.

    Creates a QApplication, instantiates the MainWindow, shows it,
    and enters the Qt event loop.

    Examples:
        >>> main()  # doctest: +SKIP

    """
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.SCROLLBAR_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
