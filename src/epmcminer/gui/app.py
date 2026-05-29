"""Main application window managing screen navigation and the step indicator."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme
from epmcminer.gui.screens.screen_download import ScreenDownload
from epmcminer.gui.screens.screen_preview import ScreenPreview
from epmcminer.gui.screens.screen_search import ScreenSearch
from epmcminer.gui.screens.screen_summary import ScreenSummary
from epmcminer.services import create_application_services
from epmcminer.services.download_result import DownloadResult
from epmcminer.services.models import SearchParams

try:
    APP_VERSION = _pkg_version("epmcminer")
except PackageNotFoundError:
    APP_VERSION = "dev"

APP_TITLE = f"epmcminer v{APP_VERSION}"
MINIMUM_WIDTH = 820
MINIMUM_HEIGHT = 600
# Increased from 960×700 to 1000×900 to give expandable list sections (results,
# log, skipped papers) enough vertical room to be usable at their minimum height.
DEFAULT_WIDTH = 1000
DEFAULT_HEIGHT = 900


# Step indicator geometry
_STEP_LABELS = ["Search", "Preview", "Download", "Summary"]
_STEP_COUNT = len(_STEP_LABELS)
_STEP_FONT_SIZE = 11
_STEP_TOP_MARGIN = 20  # vertical padding above circles inside each step widget

_TITLE_BAR_HEIGHT = 74
_CIRCLE_SIZE = 26
_CIRCLE_RADIUS = _CIRCLE_SIZE // 2
_LINE_HEIGHT = 2
# Vertical offset so the connector lines are centred on the circles
_LINE_SPACER = _STEP_TOP_MARGIN + _CIRCLE_RADIUS - _LINE_HEIGHT // 2

# Traffic-light button colours and geometry
_CLOSE_COLOR = "#ff5f57"
_MINIMIZE_COLOR = "#febc2e"
_ZOOM_COLOR = "#28c840"
_TRAFFIC_LIGHT_SIZE = 12
_TRAFFIC_LIGHT_RADIUS = _TRAFFIC_LIGHT_SIZE // 2
_TRAFFIC_LIGHT_SPACING = 8
_TRAFFIC_LIGHTS_LEFT_MARGIN = 16


# ---------------------------------------------------------------------------
# Internal title bar
# ---------------------------------------------------------------------------


class _TitleBar(QWidget):
    """Custom title bar with macOS-style traffic-light buttons and a step indicator.

    Handles window dragging when the user clicks and drags the bar.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the title bar layout."""
        super().__init__(parent)
        self.setFixedHeight(_TITLE_BAR_HEIGHT)
        self.setStyleSheet(
            f"background-color: {theme.TITLE_BAR_BG};"
            f" border-bottom: 1px solid {theme.BORDER_FAINT};",
        )
        self._drag_pos: QPoint | None = None

        self._circles: list[QLabel] = []
        self._step_texts: list[QLabel] = []
        self._connector_lines: list[QFrame] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(_TRAFFIC_LIGHTS_LEFT_MARGIN, 0, _TRAFFIC_LIGHTS_LEFT_MARGIN, 0)
        layout.setSpacing(0)

        layout.addLayout(self._make_traffic_lights())
        layout.addStretch(1)
        layout.addLayout(self._make_steps())
        layout.addStretch(1)
        layout.addLayout(self._make_app_title())

    def _make_app_title(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, _TRAFFIC_LIGHTS_LEFT_MARGIN, 0)
        lay.setSpacing(0)
        lbl = QLabel(f"epmcminer  v{APP_VERSION}")
        lbl.setStyleSheet(
            f"color: {theme.ACCENT}; font-size: 12px; background-color: transparent;",
        )
        lay.addWidget(lbl)
        return lay

    def _make_traffic_lights(self) -> QHBoxLayout:
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(_TRAFFIC_LIGHT_SPACING)

        for color, action in [
            (_CLOSE_COLOR, lambda: self.window().close()),  # type: ignore[union-attr]
            (_MINIMIZE_COLOR, lambda: self.window().showMinimized()),  # type: ignore[union-attr]
            (_ZOOM_COLOR, lambda: (
                self.window().showNormal()  # type: ignore[union-attr]
                if self.window().isMaximized()  # type: ignore[union-attr]
                else self.window().showMaximized()  # type: ignore[union-attr]
            )),
        ]:
            btn = QPushButton()
            btn.setFixedSize(_TRAFFIC_LIGHT_SIZE, _TRAFFIC_LIGHT_SIZE)
            btn.setStyleSheet(
                f"QPushButton {{"
                f" background-color: {color};"
                f" border-radius: {_TRAFFIC_LIGHT_RADIUS}px;"
                f" border: none;"
                f"}}",
            )
            btn.clicked.connect(action)
            btn_layout.addWidget(btn)

        return btn_layout

    def _make_steps(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i, label in enumerate(_STEP_LABELS):
            step_w = QWidget()
            step_w.setStyleSheet(f"background-color: {theme.TITLE_BAR_BG};")
            step_layout = QVBoxLayout(step_w)
            step_layout.setContentsMargins(0, _STEP_TOP_MARGIN, 0, 0)
            step_layout.setSpacing(5)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

            circle = QLabel(str(i + 1))
            circle.setFixedSize(_CIRCLE_SIZE, _CIRCLE_SIZE)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._circles.append(circle)
            step_layout.addWidget(circle, 0, Qt.AlignmentFlag.AlignHCenter)

            text_lbl = QLabel(label)
            text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._step_texts.append(text_lbl)
            step_layout.addWidget(text_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

            layout.addWidget(step_w)

            if i < _STEP_COUNT - 1:
                line_w = QWidget()
                line_w.setStyleSheet(f"background-color: {theme.TITLE_BAR_BG};")
                line_layout = QVBoxLayout(line_w)
                line_layout.setContentsMargins(0, 0, 0, 0)
                line_layout.setSpacing(0)
                line_layout.addSpacing(_LINE_SPACER)

                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(_LINE_HEIGHT)
                line.setMinimumWidth(40)
                self._connector_lines.append(line)
                line_layout.addWidget(line)
                line_layout.addStretch()

                layout.addWidget(line_w, 1)

        return layout

    def update_steps(self, active: int) -> None:
        """Update circle and text styles to reflect the given active step index.

        Args:
            active: Zero-based index of the currently active step (0–3).

        """
        for i, (circle, text) in enumerate(zip(self._circles, self._step_texts, strict=False)):
            if i < active:
                circle.setText("✓")
                circle.setStyleSheet(
                    f"background-color: rgba(255,122,61,20);"
                    f" color: {theme.ACCENT};"
                    f" border-radius: {_CIRCLE_RADIUS}px;"
                    f" font-size: 13px; font-weight: 700;"
                    f" border: 1.5px solid {theme.ACCENT};",
                )
                text.setStyleSheet(
                    f"color: {theme.TEXT_MUTED}; font-size: {_STEP_FONT_SIZE}px;",
                )
            elif i == active:
                circle.setText(str(i + 1))
                circle.setStyleSheet(
                    f"background-color: {theme.ACCENT};"
                    f" color: white;"
                    f" border-radius: {_CIRCLE_RADIUS}px;"
                    f" font-size: 13px; font-weight: 700;"
                    f" border: none;",
                )
                text.setStyleSheet(
                    f"color: {theme.ACCENT};"
                    f" font-size: {_STEP_FONT_SIZE}px; font-weight: 600;",
                )
            else:
                circle.setText(str(i + 1))
                circle.setStyleSheet(
                    f"background-color: transparent;"
                    f" color: {theme.TEXT_MUTED};"
                    f" border-radius: {_CIRCLE_RADIUS}px;"
                    f" font-size: 13px;"
                    f" border: 1.5px solid {theme.TEXT_MUTED};",
                )
                text.setStyleSheet(
                    f"color: {theme.TEXT_MUTED}; font-size: {_STEP_FONT_SIZE}px;",
                )

        for i, line in enumerate(self._connector_lines):
            if i < active:
                line.setStyleSheet(f"background-color: {theme.ACCENT}; border: none;")
            else:
                line.setStyleSheet("background-color: rgba(255,255,255,15); border: none;")

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()  # type: ignore[union-attr]
            )
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)  # type: ignore[union-attr]
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        self._drag_pos = None


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    """Top-level window for epmcminer.

    Owns the four wizard screens, the step indicator, and all screen-transition
    logic. Services are instantiated once in ``__init__`` and injected into the
    screens that need them. Screens communicate back exclusively via Qt signals.
    """

    def __init__(self) -> None:
        """Instantiate services, screens, layout, and wire all signals."""
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(MINIMUM_WIDTH, MINIMUM_HEIGHT)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        # Services — created once and injected; never re-created on navigation
        search_service, download_service, report_service, orcid_service = (
            create_application_services()
        )

        # Screens
        self._screen_search = ScreenSearch(orcid_service=orcid_service)
        self._screen_preview = ScreenPreview(search_service)
        self._screen_download = ScreenDownload(download_service, report_service)
        self._screen_summary = ScreenSummary(report_service)

        # State threaded through the wizard flow
        self._last_params: SearchParams | None = None
        self._total_found: int = 0

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def navigate_to(self, screen_index: int) -> None:
        """Switch to the given screen and update the step indicator.

        Args:
            screen_index: Zero-based index of the target screen (0–3).

        """
        self._stack.setCurrentIndex(screen_index)
        self._title_bar.update_steps(screen_index)

    def update_step_indicator(self, active_step: int) -> None:
        """Update only the step indicator without switching screens.

        Args:
            active_step: Zero-based index of the currently active step (0–3).

        """
        self._title_bar.update_steps(active_step)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        central.setStyleSheet(f"background-color: {theme.APP_BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = _TitleBar()
        root.addWidget(self._title_bar)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._screen_search)
        self._stack.addWidget(self._screen_preview)
        self._stack.addWidget(self._screen_download)
        self._stack.addWidget(self._screen_summary)
        root.addWidget(self._stack)

        self._title_bar.update_steps(0)

    def _connect_signals(self) -> None:
        self._screen_search.search_requested.connect(self._on_search_requested)
        self._screen_preview.back_requested.connect(self._on_back_requested)
        self._screen_preview.download_requested.connect(self._on_download_requested)
        self._screen_preview.result_loaded.connect(self._on_result_loaded)
        self._screen_download.download_complete.connect(self._on_download_complete)
        self._screen_summary.new_search_requested.connect(self._on_new_search_requested)

    # ------------------------------------------------------------------
    # Navigation slots
    # ------------------------------------------------------------------

    def _on_search_requested(self, params: SearchParams) -> None:
        self._screen_preview.load(params)
        self.navigate_to(1)

    def _on_back_requested(self) -> None:
        self.navigate_to(0)

    def _on_download_requested(self, params: SearchParams) -> None:
        self._last_params = params
        self._screen_download.start(params)
        self.navigate_to(2)

    def _on_result_loaded(self, total_found: int) -> None:
        self._total_found = total_found

    def _on_download_complete(self, results: list[DownloadResult]) -> None:
        if self._last_params is not None:
            self._screen_summary.load(results, self._last_params, self._total_found)
            self.navigate_to(3)

    def _on_new_search_requested(self) -> None:
        self.navigate_to(0)
