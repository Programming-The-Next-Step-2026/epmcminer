"""Reusable progress and loading widget used on the Preview and Download screens."""

from typing import NamedTuple

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme


class _StatsWidgets(NamedTuple):
    """Named container for the widgets returned by :meth:`ProgressWidget._make_stats_row`."""

    row: QWidget
    pct_label: QLabel
    count_label: QLabel
    thread_row: QWidget
    thread_dots: list[QFrame]
    thread_label: QLabel
    eta_col: QWidget
    eta_value: QLabel


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

_DOT_SIZE = 6
_LOADING_DOT_COUNT = 3
_THREAD_DOT_COUNT = 3
_MAX_THREAD_DOTS = 4
_ANIM_INTERVAL_MS = 500


class ProgressWidget(QWidget):
    """Dual-mode progress widget for loading and download states.

    In loading mode (``set_loading``) shows an indeterminate progress bar
    and an animated pulsing-dot row with a status message. In progress mode
    (``set_progress``) shows a determinate orange-filled bar with percentage,
    count, optional ETA, and optional thread-count dots. ``reset`` returns
    the widget to its blank initial state.

    Examples:
        >>> widget = ProgressWidget()  # doctest: +SKIP
        >>> widget.set_loading("Searching Europe PMC…")  # doctest: +SKIP
        >>> widget.set_progress(23, 50, eta_seconds=90, processed=31)  # doctest: +SKIP
        >>> widget.reset()  # doctest: +SKIP

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
        self._anim_timer.timeout.connect(self._tick_dots)
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

        Examples:
            >>> widget = ProgressWidget()  # doctest: +SKIP
            >>> widget.set_loading("Searching Europe PMC…")  # doctest: +SKIP
            >>> widget.set_loading()  # doctest: +SKIP  — default message "Loading..."

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
        processed: int | None = None,
        cancelling: bool = False,
    ) -> None:
        """Show a determinate progress bar with download statistics.

        Args:
            current: Number of papers successfully downloaded so far.
            total: Total number of papers requested (used for percentage).
            eta_seconds: Estimated seconds remaining, or ``None`` to hide
                the ETA display.
            thread_count: Number of active download threads, or ``None``
                to hide the thread dot indicators.
            processed: Total papers processed (attempted) so far, or
                ``None`` to omit the processed count from the label.
            cancelling: When ``True``, the thread label reads
                "cancelling, waiting for N thread(s)" instead of
                "N thread(s) running".

        Examples:
            >>> widget = ProgressWidget()  # doctest: +SKIP
            >>> widget.set_progress(  # doctest: +SKIP
            ...     23, 50, eta_seconds=90, thread_count=2, processed=31
            ... )

        """
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self._bar.setRange(0, max(total, 1))
        self._bar.setValue(current)
        self._bar.setVisible(True)

        pct = round(100 * current / total) if total > 0 else 0
        self._pct_label.setText(f"{pct}%")
        if processed is not None:
            self._count_label.setText(
                f"downloaded {current} out of {total}  –  processed {processed} results",
            )
        else:
            self._count_label.setText(f"downloaded {current} out of {total}")

        self._update_eta(eta_seconds)
        self._update_thread_dots(thread_count, cancelling)

        self._loading_row.setVisible(False)
        self._stats_row.setVisible(True)

    def reset(self) -> None:
        """Clear the widget back to its blank initial state.

        Examples:
            >>> widget = ProgressWidget()  # doctest: +SKIP
            >>> widget.set_loading("Loading...")  # doctest: +SKIP
            >>> widget.reset()  # doctest: +SKIP  — hides all content

        """
        self._anim_timer.stop()
        self._bar.setVisible(False)
        self._loading_row.setVisible(False)
        self._stats_row.setVisible(False)

    # ------------------------------------------------------------------
    # Internal UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the three-section layout: progress bar, loading row, stats row."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self._bar = self._make_bar()
        layout.addWidget(self._bar)

        self._loading_row, self._loading_dot_frames, self._msg_label = self._make_loading_row()
        layout.addWidget(self._loading_row)

        stats = self._make_stats_row()
        self._stats_row = stats.row
        self._pct_label = stats.pct_label
        self._count_label = stats.count_label
        self._thread_row = stats.thread_row
        self._thread_dots = stats.thread_dots
        self._thread_label = stats.thread_label
        self._eta_col = stats.eta_col
        self._eta_value = stats.eta_value
        layout.addWidget(self._stats_row)

    def _make_bar(self) -> QProgressBar:
        """Create and return the styled progress bar shared by both widget modes.

        Returns:
            A horizontally expanding :class:`QProgressBar` with the app's
            dark orange theme applied via stylesheet.

        """
        bar = QProgressBar()
        bar.setStyle(theme.get_fusion_style())
        bar.setStyleSheet(_PROGRESS_BAR_STYLE)
        bar.setTextVisible(False)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return bar

    def _make_loading_row(self) -> tuple[QWidget, list[QFrame], QLabel]:
        """Build the indeterminate loading row shown while a preview or download starts.

        Contains three animated dot indicators followed by a status message label.
        Dots are styled via :meth:`_update_loading_dots` on each timer tick.

        Returns:
            A tuple of ``(row_widget, dot_frame_list, message_label)``.

        """
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

    def _make_stats_row(self) -> _StatsWidgets:
        """Build the determinate progress stats row shown during an active download.

        The row is split into a left column (percentage, count label, thread dots)
        and a right column (ETA). All child widgets are returned via
        :class:`_StatsWidgets` so :meth:`set_progress` can update them directly.

        Returns:
            A :class:`_StatsWidgets` NamedTuple containing the row widget and
            all mutable child labels and dot frames.

        """
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

        return _StatsWidgets(
            row=row,
            pct_label=pct_label,
            count_label=count_label,
            thread_row=thread_row,
            thread_dots=thread_dots,
            thread_label=thread_label,
            eta_col=eta_col,
            eta_value=eta_value,
        )

    def _make_thread_row(self) -> tuple[QWidget, list[QFrame], QLabel]:
        """Build the active-thread indicator row containing dot frames and a text label.

        The dots are cycled by :meth:`_tick_dots` on each timer tick to show
        download activity. The label is updated by :meth:`_update_thread_dots`
        with the current thread count or a cancellation message.

        Returns:
            A tuple of ``(row_widget, dot_frame_list, thread_label)``.

        """
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        dot_group = QWidget()
        dot_layout = QHBoxLayout(dot_group)
        dot_layout.setContentsMargins(0, 0, 0, 0)
        dot_layout.setSpacing(5)

        dots: list[QFrame] = []
        for _ in range(_THREAD_DOT_COUNT):
            dot = QFrame()
            dot.setFixedSize(_DOT_SIZE, _DOT_SIZE)
            dot.setStyleSheet(_DOT_DIM)
            dot_layout.addWidget(dot)
            dots.append(dot)

        layout.addWidget(dot_group)
        label = QLabel("")
        label.setStyleSheet(_THREAD_LABEL_STYLE)
        layout.addWidget(label)
        layout.addStretch()
        return row, dots, label

    def _make_eta_col(self) -> tuple[QWidget, QLabel]:
        """Build the right-aligned ETA column with a large value and a sub-label.

        The column is hidden when no ETA is available and shown by
        :meth:`_update_eta` when a valid estimate exists.

        Returns:
            A tuple of ``(column_widget, eta_value_label)``.

        """
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
        """Show or hide the ETA column and format the value as minutes or seconds.

        Values under 60 seconds are shown as ``~Ns``; values of 60 or more are
        rounded to the nearest minute and shown as ``~N min``.

        Args:
            eta_seconds: Estimated seconds remaining, or ``None`` to hide the column.

        """
        if eta_seconds is None:
            self._eta_col.setVisible(False)
            return
        self._eta_col.setVisible(True)
        if eta_seconds >= 60:
            self._eta_value.setText(f"~{round(eta_seconds / 60)} min")
        else:
            self._eta_value.setText(f"~{eta_seconds}s")

    def _update_thread_dots(self, thread_count: int | None, cancelling: bool = False) -> None:
        """Show or hide the thread row and update its label text.

        Hides the row when ``thread_count`` is ``None``. On the first call that
        makes the row visible, resets ``_dot_phase`` to 0 so the animation
        always starts from the first dot.

        Args:
            thread_count: Number of currently active download threads, or ``None``
                to hide the thread row entirely.
            cancelling: When ``True``, the label reads "cancelling, waiting for N
                thread(s)" instead of "N thread(s) running".

        """
        if thread_count is None:
            self._thread_row.setVisible(False)
            return
        if not self._thread_row.isVisible():
            self._dot_phase = 0
        self._thread_row.setVisible(True)
        if cancelling:
            noun = "thread" if thread_count == 1 else "threads"
            if thread_count:
                self._thread_label.setText(f"cancelling, waiting for {thread_count} {noun}")
            else:
                self._thread_label.setText("cancelling, waiting for threads to finish")
        else:
            self._thread_label.setText(
                "1 thread running" if thread_count == 1 else f"{thread_count} threads running",
            )

    def _tick_dots(self) -> None:
        """Advance the dot animation by one step. Called every 500 ms by the timer.

        Checks which row is currently visible and updates the appropriate set of
        dots. Only one set is ever active at a time: loading dots in loading mode,
        thread dots in progress mode.

        """
        if self._loading_row.isVisible():
            self._dot_phase = (self._dot_phase + 1) % _LOADING_DOT_COUNT
            self._update_loading_dots()
        elif self._thread_row.isVisible():
            self._dot_phase = (self._dot_phase + 1) % _THREAD_DOT_COUNT
            for i, dot in enumerate(self._thread_dots):
                dot.setStyleSheet(_DOT_BRIGHT if i == self._dot_phase else _DOT_DIM)

    def _update_loading_dots(self) -> None:
        """Apply bright or dim styles to the loading dots based on the current phase.

        Exactly one dot is bright (the one at index ``_dot_phase``); the others
        are dim. Called once immediately in :meth:`set_loading` to set the initial
        state, then on every subsequent timer tick via :meth:`_tick_dots`.

        """
        for i, dot in enumerate(self._loading_dot_frames):
            dot.setStyleSheet(_DOT_BRIGHT if i == self._dot_phase else _DOT_DIM)
