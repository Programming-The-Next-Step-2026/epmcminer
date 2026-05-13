"""Entry point for the epmcminer application."""

import sys

from PyQt6.QtWidgets import QApplication

from epmcminer.gui.app import MainWindow


def main() -> None:
    """Create and launch the epmcminer desktop application.

    Creates a QApplication, instantiates the MainWindow, shows it,
    and enters the Qt event loop.
    """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
