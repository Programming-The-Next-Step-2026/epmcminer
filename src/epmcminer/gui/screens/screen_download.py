"""Screen 3 — download progress bar and live log."""

import threading
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme
from epmcminer.gui.widgets.card import make_card, make_section_label
from epmcminer.gui.widgets.progress_widget import ProgressWidget
from epmcminer.gui.widgets.toast import Toast
from epmcminer.services.download_service import DownloadService
from epmcminer.services.models import DownloadResult, SearchParams
from epmcminer.services.report_service import ReportService
from epmcminer.utils.logger import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Screen-local constants
# ---------------------------------------------------------------------------
_SUCCESS_BG = "#1a3d1a"
_SUCCESS = "#4ade80"
_DANGER_BG = "#3a1a1a"
_DANGER = "#f87171"
_SKIPPED_BG = "rgba(255, 122, 61, 20)"
_DIVIDER = theme.BORDER_FAINT

_LOG_MIN_HEIGHT = theme.EXPANDABLE_MIN_HEIGHT
_DOT_SIZE = 26
_DOT_RADIUS = _DOT_SIZE // 2
_BYTES_PER_MB = 1_000_000
_BYTES_PER_KB = 1_000

_CANCEL_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_STRONG};
        border-radius: 12px;
        padding: 12px 22px;
        font-size: 17px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 10);
    }}
    QPushButton:disabled {{
        color: {theme.TEXT_MUTED};
        border-color: {theme.BORDER};
    }}
"""


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class DownloadWorker(QThread):
    """Background thread that calls DownloadService.download().

    Attributes:
        progress_updated: Emitted with each DownloadResult as it completes.
        download_finished: Emitted with the full list of results on completion.
        error_occurred: Emitted with an error message string on failure.
        cancel_event: Set this to request cancellation of the download loop.
    """

    progress_updated = pyqtSignal(DownloadResult)
    download_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, service: DownloadService, params: SearchParams) -> None:
        """Initialise the worker.

        Args:
            service: The DownloadService to use.
            params: The search/download parameters.
        """
        super().__init__()
        self._service = service
        self._params = params
        self.cancel_event = threading.Event()

    def run(self) -> None:
        """Execute the download and emit signals for each result and on completion."""
        try:
            results = self._service.download(
                self._params,
                progress_callback=self.progress_updated.emit,
                cancel_event=self.cancel_event,
            )
            self.download_finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


class ScreenDownload(QWidget):
    """Wizard screen showing download progress and a live activity log.

    Starts DownloadService in a DownloadWorker QThread and updates the
    ProgressWidget and log view via Qt signals as each paper is processed.
    Saves report.csv automatically on completion via ReportService.

    Signals:
        download_complete: Emitted with the full list[DownloadResult] when done.
    """

    download_complete = pyqtSignal(list)

    def __init__(
        self,
        download_service: DownloadService,
        report_service: ReportService,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the download screen.

        Args:
            download_service: Injected service that performs the downloads.
            report_service: Injected service that writes report.csv.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._service = download_service
        self._report_service = report_service
        self._params: SearchParams | None = None
        self._worker: DownloadWorker | None = None
        self._results: list[DownloadResult] = []
        self._completed: int = 0
        self._total: int = 0
        self._start_time: float = 0.0
        self._toast: Toast | None = None
        self.setStyleSheet(f"background-color: {theme.APP_BG};")
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, params: SearchParams) -> None:
        """Begin the download for the given params.

        Resets the UI, stores params, and starts a DownloadWorker.

        Args:
            params: SearchParams including query, count, and output_folder.
        """
        self._params = params
        self._results = []
        self._completed = 0
        self._total = params.count
        self._start_time = time.time()

        self._clear_log()
        self._cancel_btn.setEnabled(True)
        self._folder_label.setText(f"Saving to {params.output_folder}")
        self._progress.set_loading("Preparing download…")

        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel_event.set()
            self._worker.quit()
            self._worker.wait()

        self._worker = DownloadWorker(self._service, params)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.download_finished.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Reposition the toast whenever the screen is resized."""
        super().resizeEvent(event)
        if self._toast is not None and not self._toast.isHidden():
            self._toast.reposition()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.APP_BG}; border: none; }}"
        )

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {theme.APP_BG};")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        layout.addWidget(self._make_progress_card())
        log_card = self._make_log_card()
        log_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(log_card, 1)

        scroll.setWidget(content_widget)
        root.addWidget(scroll)
        root.addWidget(self._make_action_bar())

        self._toast = Toast(self)

    def _make_progress_card(self) -> QWidget:
        card, layout = make_card(padding=26)
        layout.addWidget(make_section_label("Download progress"))
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)
        return card

    def _make_log_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Live status"))

        self._log_scroll = QScrollArea()
        self._log_scroll.setWidgetResizable(True)
        self._log_scroll.setMinimumHeight(_LOG_MIN_HEIGHT)
        self._log_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._log_scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.CARD_BG}; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background-color: {theme.CARD_BG}; }}"
        )
        self._log_scroll.verticalScrollBar().rangeChanged.connect(
            lambda _, max_val: self._log_scroll.verticalScrollBar().setValue(max_val)
        )

        log_container = QWidget()
        log_container.setStyleSheet(f"background-color: {theme.CARD_BG};")
        self._log_layout = QVBoxLayout(log_container)
        self._log_layout.setContentsMargins(0, 0, 0, 0)
        self._log_layout.setSpacing(0)
        self._log_layout.addStretch()

        self._log_scroll.setWidget(log_container)
        layout.addWidget(self._log_scroll)
        return card

    def _make_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f"background-color: {theme.APP_BG}; border-top: 1px solid {theme.BORDER};"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(22, 0, 22, 0)

        self._folder_label = QLabel("")
        self._folder_label.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 15px;")
        bar_layout.addWidget(self._folder_label)
        bar_layout.addStretch()

        self._cancel_btn = QPushButton("✕  Cancel")
        self._cancel_btn.setStyle(theme.get_fusion_style())
        self._cancel_btn.setStyleSheet(_CANCEL_BTN_STYLE)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        bar_layout.addWidget(self._cancel_btn)

        return bar

    # ------------------------------------------------------------------
    # Log row construction
    # ------------------------------------------------------------------

    def _make_status_dot(self, status: str) -> QLabel:
        """Return a circular status indicator for a download row."""
        if status == DownloadResult.STATUS_DOWNLOADED:
            bg, fg, symbol = _SUCCESS_BG, _SUCCESS, "✓"
        elif status == DownloadResult.STATUS_FAILED:
            bg, fg, symbol = _DANGER_BG, _DANGER, "✗"
        else:
            bg, fg, symbol = _SKIPPED_BG, theme.ACCENT, "–"

        dot = QLabel(symbol)
        dot.setFixedSize(_DOT_SIZE, _DOT_SIZE)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: {_DOT_RADIUS}px;"
            f" font-size: 13px; font-weight: 700; border: none;"
        )
        return dot

    def _filename_for(self, result: DownloadResult) -> str:
        """Return the display filename for a log row."""
        if result.file_path is not None:
            return result.file_path.name
        if result.paper.doi:
            return result.paper.doi
        return result.paper.title[:70]

    def _sub_text_for(self, result: DownloadResult) -> tuple[str, str]:
        """Return (text, css_color) for the sub-label of a log row."""
        if result.status == DownloadResult.STATUS_DOWNLOADED and result.file_path is not None:
            try:
                size = result.file_path.stat().st_size
                size_str = (
                    f"{size / _BYTES_PER_MB:.1f} MB" if size >= _BYTES_PER_MB
                    else f"{size / _BYTES_PER_KB:.0f} KB"
                )
            except OSError:
                size_str = ""
            return f"Saved · {size_str}".rstrip(" ·"), theme.TEXT_MUTED
        if result.status == DownloadResult.STATUS_FAILED:
            return result.reason or "Download failed", _DANGER
        return result.reason or "Skipped", theme.TEXT_MUTED

    def _make_log_row(self, result: DownloadResult) -> QWidget:
        """Build one row widget for the live log."""
        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.CARD_BG};")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._make_status_dot(result.status))

        text_col = QWidget()
        text_col.setStyleSheet(f"background-color: {theme.CARD_BG};")
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        filename_lbl = QLabel(self._filename_for(result))
        filename_lbl.setWordWrap(True)
        filename_lbl.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 14px; font-weight: 600;"
            f" font-family: monospace; letter-spacing: -0.2px;"
        )
        text_layout.addWidget(filename_lbl)

        sub_text, sub_color = self._sub_text_for(result)
        sub_lbl = QLabel(sub_text)
        sub_lbl.setStyleSheet(f"color: {sub_color}; font-size: 13px;")
        text_layout.addWidget(sub_lbl)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(
            f"background-color: {_DIVIDER}; border: none; max-height: 1px; margin-top: 8px;"
        )
        text_layout.addWidget(separator)

        layout.addWidget(text_col, 1)
        return row

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _clear_log(self) -> None:
        """Remove all rows from the log layout and restore the trailing stretch."""
        while self._log_layout.count():
            item = self._log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._log_layout.addStretch()

    def _add_log_row(self, result: DownloadResult) -> None:
        """Prepend a completed-download row before the trailing stretch."""
        self._log_layout.insertWidget(self._log_layout.count() - 1, self._make_log_row(result))

    def _downloaded_count(self) -> int:
        """Return the number of successfully downloaded papers so far."""
        return sum(1 for r in self._results if r.status == DownloadResult.STATUS_DOWNLOADED)

    def _eta_seconds(self) -> int | None:
        """Estimate seconds remaining based on average time per successful download."""
        downloaded = self._downloaded_count()
        if downloaded == 0:
            return None
        elapsed = time.time() - self._start_time
        avg = elapsed / downloaded
        remaining = max(0, self._total - downloaded)
        return round(avg * remaining) if remaining > 0 else None

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_progress(self, result: DownloadResult) -> None:
        """Handle one completed download attempt from the worker."""
        self._results.append(result)
        self._completed += 1
        cancelling = self._worker is not None and self._worker.cancel_event.is_set()
        self._progress.set_progress(
            self._downloaded_count(),
            self._total,
            eta_seconds=self._eta_seconds(),
            thread_count=result.active_threads or None,
            processed=self._completed,
            cancelling=cancelling,
        )
        self._add_log_row(result)

    def _on_finished(self, results: list[DownloadResult]) -> None:
        """Handle completion of the full download run."""
        self._cancel_btn.setEnabled(False)
        downloaded = sum(1 for r in results if r.status == DownloadResult.STATUS_DOWNLOADED)
        self._progress.set_progress(downloaded, max(self._total, 1), processed=self._completed)
        if self._params is not None:
            try:
                self._report_service.save_csv(
                    results, self._params, self._params.output_folder
                )
            except Exception:  # noqa: BLE001
                _logger.exception("Failed to save report.csv")
        self.download_complete.emit(results)

    def _on_error(self, message: str) -> None:
        """Handle an unrecoverable error from the worker.

        Resets the progress display (hiding the thread row and ETA) before
        showing the error toast, so the UI does not freeze on a stale thread
        count if the worker exits via an exception rather than a normal finish.
        """
        _logger.error("Download worker error: %s", message)
        self._cancel_btn.setEnabled(False)
        self._progress.set_progress(
            self._downloaded_count(), max(self._total, 1), processed=self._completed
        )
        self._toast.show_message(f"Download error: {message}", success=False)

    def _on_cancel(self) -> None:
        """Request cancellation and disable the cancel button."""
        if self._worker is not None:
            self._worker.cancel_event.set()
        self._cancel_btn.setEnabled(False)
