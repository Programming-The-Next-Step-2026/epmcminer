"""Reusable progress and loading widget used on the Preview and Download screens."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

# Colour tokens from ui.jsx / handoff.jsx.
# Qt QSS rgba() uses 0-255 integer alpha; 0.06×255≈15.
_PROGRESS_BAR_STYLE = """
    QProgressBar {
        background-color: rgba(255, 255, 255, 15);
        border-radius: 5px;
        border: none;
        min-height: 10px;
        max-height: 10px;
    }
    QProgressBar::chunk {
        background-color: #ff7a3d;
        border-radius: 5px;
    }
"""

_PCT_LABEL_STYLE = "color: #ff7a3d; font-size: 22px; font-weight: 700;"
_COUNT_LABEL_STYLE = "color: #ededed; font-size: 18px;"
_THREAD_LABEL_STYLE = "color: #8a8a8d; font-size: 14px;"
_MSG_LABEL_STYLE = "color: #cfcfcf; font-size: 15px;"
_ETA_VALUE_STYLE = "color: #ededed; font-size: 26px; font-weight: 700;"
_ETA_SUB_STYLE = "color: #8a8a8d; font-size: 13px;"

# Loading dot styles: one bright, two dim; cycled by the animation timer.
_DOT_BRIGHT = "background-color: #ff7a3d; border-radius: 3px;"
_DOT_DIM = "background-color: rgba(255, 122, 61, 46); border-radius: 3px;"

# Thread dot styles: static decreasing opacity (0.85, 0.67, 0.49, 0.31 × 255).
_THREAD_DOT_STYLES = [
    "background-color: rgba(255, 122, 61, 217); border-radius: 3px;",
    "background-color: rgba(255, 122, 61, 171); border-radius: 3px;",
    "background-color: rgba(255, 122, 61, 125); border-radius: 3px;",
    "background-color: rgba(255, 122, 61, 79);  border-radius: 3px;",
]

_DOT_SIZE = 6
_LOADING_DOT_COUNT = 3
_MAX_THREAD_DOTS = len(_THREAD_DOT_STYLES)
_ANIM_INTERVAL_MS = 500

_FUSION = QStyleFactory.create("Fusion")


class ProgressWidget(QWidget):
    """Dual-mode progress widget for loading and download states.

    In loading mode (``set_loading``) shows an indeterminate progress bar
    and an animated pulsing-dot row with a status message. In progress mode
    (``set_progress``) shows a determinate orange-filled bar with percentage,
    count, optional ETA, and optional thread-count dots. ``reset`` returns
    the widget to its blank initial state.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the widget in its blank reset state.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._dot_phase: int = 0
        self._build_ui()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(_ANIM_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._tick_loading_dots)
        self.reset()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_loading(self, message: str = "Loading...") -> None:
        """Show an indeterminate loading animation with a message.

        Stops any prior animation, switches the progress bar to
        indeterminate mode, and starts the pulsing dot animation.

        Args:
            message: Status text displayed beside the animated dots.
        """
        self._anim_timer.stop()
        self._bar.setRange(0, 0)
        self._bar.setVisible(True)
        self._msg_label.setText(message)
        self._loading_row.setVisible(True)
        self._stats_row.setVisible(False)
        self._dot_phase = 0
        self._update_loading_dots()
        self._anim_timer.start()

    def set_progress(
        self,
        current: int,
        total: int,
        eta_seconds: int | None = None,
        thread_count: int | None = None,
    ) -> None:
        """Show a determinate progress bar with download statistics.

        Args:
            current: Number of papers successfully downloaded so far.
            total: Total number of papers requested.
            eta_seconds: Estimated seconds remaining, or ``None`` to hide
                the ETA display.
            thread_count: Number of active download threads, or ``None``
                to hide the thread dot indicators.
        """
        self._anim_timer.stop()
        self._bar.setRange(0, max(total, 1))
        self._bar.setValue(current)
        self._bar.setVisible(True)

        pct = round(100 * current / total) if total > 0 else 0
        self._pct_label.setText(f"{pct}%")
        self._count_label.setText(f"{current} of {total} downloaded")

        self._update_eta(eta_seconds)
        self._update_thread_dots(thread_count)

        self._loading_row.setVisible(False)
        self._stats_row.setVisible(True)

    def reset(self) -> None:
        """Clear the widget back to its blank initial state."""
        self._anim_timer.stop()
        self._bar.setVisible(False)
        self._loading_row.setVisible(False)
        self._stats_row.setVisible(False)

    # ------------------------------------------------------------------
    # Internal UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self._bar = self._make_bar()
        layout.addWidget(self._bar)

        self._loading_row, self._loading_dot_frames, self._msg_label = (
            self._make_loading_row()
        )
        layout.addWidget(self._loading_row)

        (
            self._stats_row,
            self._pct_label,
            self._count_label,
            self._thread_row,
            self._thread_dots,
            self._thread_label,
            self._eta_col,
            self._eta_value,
        ) = self._make_stats_row()
        layout.addWidget(self._stats_row)

    def _make_bar(self) -> QProgressBar:
        bar = QProgressBar()
        bar.setStyle(_FUSION)
        bar.setStyleSheet(_PROGRESS_BAR_STYLE)
        bar.setTextVisible(False)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return bar

    def _make_loading_row(self) -> tuple[QWidget, list[QFrame], QLabel]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        dot_frames: list[QFrame] = []
        for _ in range(_LOADING_DOT_COUNT):
            dot = QFrame()
            dot.setFixedSize(_DOT_SIZE, _DOT_SIZE)
            dot.setStyleSheet(_DOT_DIM)
            layout.addWidget(dot)
            dot_frames.append(dot)

        msg = QLabel("Loading...")
        msg.setStyleSheet(_MSG_LABEL_STYLE)
        layout.addWidget(msg)
        layout.addStretch()
        return row, dot_frames, msg

    def _make_stats_row(
        self,
    ) -> tuple[
        QWidget, QLabel, QLabel, QWidget, list[QFrame], QLabel, QWidget, QLabel
    ]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(14)
        pct_label = QLabel("0%")
        pct_label.setStyleSheet(_PCT_LABEL_STYLE)
        count_label = QLabel("")
        count_label.setStyleSheet(_COUNT_LABEL_STYLE)
        top_layout.addWidget(pct_label)
        top_layout.addWidget(count_label)
        top_layout.addStretch()
        left_layout.addWidget(top)

        thread_row, thread_dots, thread_label = self._make_thread_row()
        left_layout.addWidget(thread_row)

        layout.addWidget(left, 1)

        eta_col, eta_value = self._make_eta_col()
        layout.addWidget(eta_col)

        return (
            row, pct_label, count_label, thread_row, thread_dots, thread_label, eta_col, eta_value
        )

    def _make_thread_row(self) -> tuple[QWidget, list[QFrame], QLabel]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        dot_group = QWidget()
        dot_layout = QHBoxLayout(dot_group)
        dot_layout.setContentsMargins(0, 0, 0, 0)
        dot_layout.setSpacing(5)

        dots: list[QFrame] = []
        for style in _THREAD_DOT_STYLES:
            dot = QFrame()
            dot.setFixedSize(_DOT_SIZE, _DOT_SIZE)
            dot.setStyleSheet(style)
            dot_layout.addWidget(dot)
            dots.append(dot)

        layout.addWidget(dot_group)
        label = QLabel("")
        label.setStyleSheet(_THREAD_LABEL_STYLE)
        layout.addWidget(label)
        layout.addStretch()
        return row, dots, label

    def _make_eta_col(self) -> tuple[QWidget, QLabel]:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        value = QLabel("~-- min")
        value.setStyleSheet(_ETA_VALUE_STYLE)
        value.setAlignment(Qt.AlignmentFlag.AlignRight)

        sub = QLabel("remaining")
        sub.setStyleSheet(_ETA_SUB_STYLE)
        sub.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(value)
        layout.addWidget(sub)
        return col, value

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _update_eta(self, eta_seconds: int | None) -> None:
        if eta_seconds is None:
            self._eta_col.setVisible(False)
            return
        self._eta_col.setVisible(True)
        if eta_seconds >= 60:
            self._eta_value.setText(f"~{round(eta_seconds / 60)} min")
        else:
            self._eta_value.setText(f"~{eta_seconds}s")

    def _update_thread_dots(self, thread_count: int | None) -> None:
        if thread_count is None:
            self._thread_row.setVisible(False)
            return
        self._thread_row.setVisible(True)
        n = min(thread_count, _MAX_THREAD_DOTS)
        for i, dot in enumerate(self._thread_dots):
            dot.setVisible(i < n)
        self._thread_label.setText(
            "1 thread running" if thread_count == 1 else f"{thread_count} threads running"
        )

    def _tick_loading_dots(self) -> None:
        self._dot_phase = (self._dot_phase + 1) % _LOADING_DOT_COUNT
        self._update_loading_dots()

    def _update_loading_dots(self) -> None:
        for i, dot in enumerate(self._loading_dot_frames):
            dot.setStyleSheet(_DOT_BRIGHT if i == self._dot_phase else _DOT_DIM)
