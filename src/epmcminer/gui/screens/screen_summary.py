"""Screen 4 — Download summary with stat cards and export options."""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QFileDialog,
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
from epmcminer.gui.widgets.toast import Toast
from epmcminer.services.models import DownloadResult, SearchParams
from epmcminer.services.report_service import ReportService
from epmcminer.utils.logger import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Screen-local constants
# ---------------------------------------------------------------------------
_DIVIDER = theme.BORDER_FAINT

_SKIPPED_LIST_MIN_HEIGHT = theme.EXPANDABLE_MIN_HEIGHT
_DOT_SIZE = 26
_DOT_RADIUS = _DOT_SIZE // 2
# License strings up to this many characters are placed inline on row 1;
# longer strings (many licenses selected) fall back to their own wrapping row.
_LICENSE_INLINE_MAX_CHARS = 40

_GHOST_BTN_STYLE = f"""
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
"""

_PRIMARY_BTN_STYLE = f"""
    QPushButton {{
        background-color: {theme.ACCENT};
        color: #000000;
        border: none;
        border-radius: 12px;
        padding: 12px 22px;
        font-size: 17px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: #ff9a6a;
    }}
"""


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class ExportWorker(QThread):
    """Background thread that calls a ReportService export method.

    Attributes:
        export_done: Emitted with the output file path string on success.
        export_error: Emitted with an error message string on failure.

    """

    export_done = pyqtSignal(str)
    export_error = pyqtSignal(str)

    def __init__(self, fn: Callable[[], None], path: str) -> None:
        """Initialise the worker.

        Args:
            fn: Zero-argument callable that performs the export (already bound
                with results, params, and output_path).
            path: Display path emitted with export_done on success.

        """
        super().__init__()
        self._fn = fn
        self._path = path

    def run(self) -> None:
        """Execute the export and emit the result signal."""
        try:
            self._fn()
            self.export_done.emit(self._path)
        except Exception as exc:  # noqa: BLE001
            _logger.exception("ExportWorker failed: %s", exc)
            self.export_error.emit(str(exc))


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


class ScreenSummary(QWidget):
    """Wizard screen showing a summary of the completed download run.

    Displays stat cards (downloaded, skipped, total found), the search
    parameters used, and a scrollable list of any skipped or failed papers.
    Provides Export Excel and Export PDF buttons that run in background workers.

    Signals:
        new_search_requested: Emitted when the user clicks "New search".
    """

    new_search_requested = pyqtSignal()

    def __init__(
        self,
        report_service: ReportService,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the summary screen.

        Args:
            report_service: Injected service used for Excel and PDF export.
            parent: Optional parent widget.

        """
        super().__init__(parent)
        self._report_service = report_service
        self._results: list[DownloadResult] = []
        self._params: SearchParams | None = None
        self._total_found: int = 0
        self._worker: ExportWorker | None = None
        self._param_query_lbl: QLabel | None = None
        self._param_sort_lbl: QLabel | None = None
        self._param_date_lbl: QLabel | None = None
        self._toast: Toast | None = None
        self.setStyleSheet(f"background-color: {theme.APP_BG};")
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(
        self,
        results: list[DownloadResult],
        params: SearchParams,
        total_found: int,
    ) -> None:
        """Populate the summary screen with download results.

        Args:
            results: List of DownloadResult objects from the download phase.
            params: The SearchParams used to produce the results.
            total_found: Total number of papers found in the API search.

        """
        self._results = results
        self._params = params
        self._total_found = total_found

        downloaded = sum(1 for r in results if r.status == DownloadResult.STATUS_DOWNLOADED)
        not_downloaded = len(results) - downloaded

        self._stat_downloaded_lbl.setText(str(downloaded))
        self._stat_skipped_lbl.setText(str(not_downloaded))
        self._stat_total_lbl.setText(f"{total_found:,}")
        self._stat_downloaded_sub.setText(f"of {len(results)} processed")

        self._populate_params(params)
        self._populate_skipped(results)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Reposition the toast whenever the screen is resized."""
        super().resizeEvent(event)
        if self._toast is not None and not self._toast.isHidden():
            self._toast.reposition()

    def _build_ui(self) -> None:
        """Construct the screen layout: scrollable stat and params cards, plus action bar."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.APP_BG}; border: none; }}",
        )

        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {theme.APP_BG};")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        layout.addLayout(self._make_stat_row())
        layout.addWidget(self._make_params_card())
        self._skipped_card = self._make_skipped_card()
        self._skipped_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._skipped_card, 1)
        self._skipped_card.setVisible(False)

        scroll.setWidget(content_widget)
        root.addWidget(scroll)
        root.addWidget(self._make_action_bar())

        self._toast = Toast(self)

    def _make_stat_card(
        self,
        label: str,
        initial_value: str,
        sub_text: str,
        value_color: str,
    ) -> tuple[QWidget, QLabel, QLabel]:
        """Build a single stat card with a label, large value, and sub-text.

        Args:
            label: The card's descriptive heading shown at the top.
            initial_value: The placeholder value displayed before data is loaded.
            sub_text: A short explanatory line shown below the value.
            value_color: CSS colour string applied to the value label.

        Returns:
            Tuple of (the card widget, the value QLabel, the sub-text QLabel).

        """
        card, layout = make_card()

        label_lbl = QLabel(label)
        label_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 15px; font-weight: 500;")
        layout.addWidget(label_lbl)

        value_lbl = QLabel(initial_value)
        value_lbl.setStyleSheet(
            f"color: {value_color}; font-size: 32px; font-weight: 600; line-height: 1;",
        )
        layout.addWidget(value_lbl)

        sub_lbl = QLabel(sub_text)
        sub_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(sub_lbl)

        return card, value_lbl, sub_lbl

    def _make_stat_row(self) -> QHBoxLayout:
        """Build the horizontal layout of three stat cards (downloaded, skipped, total found).

        Returns:
            A QHBoxLayout containing the three stat card widgets.

        """
        row = QHBoxLayout()
        row.setSpacing(16)

        card_dl, self._stat_downloaded_lbl, self._stat_downloaded_sub = self._make_stat_card(
            "Downloaded", "—", "of 0 processed", theme.ACCENT,
        )
        card_sk, self._stat_skipped_lbl, _ = self._make_stat_card(
            "Skipped", "—", "see reasons below", theme.DANGER,
        )
        card_tot, self._stat_total_lbl, _ = self._make_stat_card(
            "Total results", "—", "found in Europe PMC", theme.ACCENT,
        )

        row.addWidget(card_dl)
        row.addWidget(card_sk)
        row.addWidget(card_tot)
        return row

    def _make_params_card(self) -> QWidget:
        """Build the search parameters card with a container for populated param rows.

        Returns:
            The card QWidget whose interior is populated by _populate_params.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Search parameters"))

        params_container = QWidget()
        params_container.setStyleSheet(f"background-color: {theme.CARD_BG};")
        self._param_pairs_layout = QVBoxLayout(params_container)
        self._param_pairs_layout.setContentsMargins(0, 4, 0, 0)
        self._param_pairs_layout.setSpacing(14)

        layout.addWidget(params_container)
        return card

    def _make_skipped_card(self) -> QWidget:
        """Build the skipped papers card with a scrollable list container.

        Returns:
            The card QWidget whose list is populated by _populate_skipped. Hidden when
            there are no skipped papers.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Skipped papers"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(_SKIPPED_LIST_MIN_HEIGHT)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.CARD_BG}; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background-color: {theme.CARD_BG}; }}",
        )

        list_container = QWidget()
        list_container.setStyleSheet(f"background-color: {theme.CARD_BG};")
        self._skipped_list_layout = QVBoxLayout(list_container)
        self._skipped_list_layout.setContentsMargins(0, 0, 0, 0)
        self._skipped_list_layout.setSpacing(0)

        scroll.setWidget(list_container)
        layout.addWidget(scroll)
        return card

    def _make_action_bar(self) -> QWidget:
        """Build the fixed-height action bar with New search, Export Excel, and Export PDF buttons.

        Returns:
            A QWidget containing the three action buttons.

        """
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f"background-color: {theme.APP_BG}; border-top: 1px solid {theme.BORDER};",
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(22, 0, 22, 0)
        bar_layout.setSpacing(12)

        self._new_search_btn = QPushButton("＋  New search")
        self._new_search_btn.setStyle(theme.get_fusion_style())
        self._new_search_btn.setStyleSheet(_GHOST_BTN_STYLE)
        self._new_search_btn.clicked.connect(self._on_new_search)
        bar_layout.addWidget(self._new_search_btn)
        bar_layout.addStretch()

        self._export_excel_btn = QPushButton("Export Excel")
        self._export_excel_btn.setStyle(theme.get_fusion_style())
        self._export_excel_btn.setStyleSheet(_GHOST_BTN_STYLE)
        self._export_excel_btn.clicked.connect(self._on_export_excel)
        bar_layout.addWidget(self._export_excel_btn)

        self._export_pdf_btn = QPushButton("Export PDF")
        self._export_pdf_btn.setStyle(theme.get_fusion_style())
        self._export_pdf_btn.setStyleSheet(_PRIMARY_BTN_STYLE)
        self._export_pdf_btn.clicked.connect(self._on_export_pdf)
        bar_layout.addWidget(self._export_pdf_btn)

        return bar

    # ------------------------------------------------------------------
    # Population helpers
    # ------------------------------------------------------------------

    def _make_inline_pair(self, label: str, value: str) -> tuple[QWidget, QLabel]:
        """Build a compact inline label–value widget for the params card.

        Args:
            label: The parameter name displayed in muted colour.
            value: The parameter value displayed in primary colour.

        Returns:
            Tuple of (the containing widget, the value QLabel).

        """
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {theme.CARD_BG};")
        h = QHBoxLayout(widget)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        label_lbl = QLabel(label)
        label_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 15px;")
        h.addWidget(label_lbl)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 15px; font-weight: 600;",
        )
        h.addWidget(value_lbl)
        return widget, value_lbl

    def _make_param_line(self, label: str, value: str) -> QWidget:
        """Build a full-width label–value row where the value wraps across lines.

        The value label receives stretch factor 1 so it always fills the
        available card width, giving Qt the layout information it needs to
        reflow text as the window is resized.

        Args:
            label: The parameter name displayed in muted colour on the left.
            value: The parameter value; wraps to additional lines when needed.

        Returns:
            The containing row widget.

        """
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {theme.CARD_BG};")
        h = QHBoxLayout(widget)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.setAlignment(Qt.AlignmentFlag.AlignTop)

        label_lbl = QLabel(label)
        label_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 15px;")
        h.addWidget(label_lbl)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 15px; font-weight: 600;",
        )
        value_lbl.setWordWrap(True)
        h.addWidget(value_lbl, 1)
        return widget

    def _make_param_row(self, pairs: list[tuple[str, str]]) -> tuple[QWidget, list[QLabel]]:
        """Build a horizontal row of inline label–value pairs.

        Args:
            pairs: List of (label, value) tuples to display in one row.

        Returns:
            Tuple of (the row widget, list of value QLabels in order).

        """
        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.CARD_BG};")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(36)

        value_lbls: list[QLabel] = []
        for label, value in pairs:
            widget, value_lbl = self._make_inline_pair(label, value)
            h.addWidget(widget)
            value_lbls.append(value_lbl)
        h.addStretch()
        return row, value_lbls

    def _populate_params(self, params: SearchParams) -> None:
        """Clear and repopulate the params card with rows built from the given SearchParams.

        Args:
            params: The SearchParams whose fields are rendered as label–value rows.

        """
        while self._param_pairs_layout.count():
            item = self._param_pairs_layout.takeAt(0)
            if item.widget():  # type: ignore[union-attr]
                item.widget().deleteLater()  # type: ignore[union-attr]

        date_str = f"{params.date_from} → {params.date_to}"

        # Build row 1: Query, Sort, Date are always inline; License joins them
        # when its text is short enough to fit comfortably.
        license_str = ", ".join(params.licenses) if params.licenses else ""
        license_inline = bool(license_str) and len(license_str) <= _LICENSE_INLINE_MAX_CHARS
        row1_pairs: list[tuple[str, str]] = [
            ("Query", params.query),
            ("Sort", params.sort_order.capitalize()),
            ("Date", date_str),
        ]
        if license_inline:
            row1_pairs.append(("License", license_str))

        row1, row1_lbls = self._make_param_row(row1_pairs)
        self._param_query_lbl = row1_lbls[0]
        self._param_sort_lbl = row1_lbls[1]
        self._param_date_lbl = row1_lbls[2]
        self._param_pairs_layout.addWidget(row1)

        if license_str and not license_inline:
            self._param_pairs_layout.addWidget(
                self._make_param_line("License", license_str),
            )
        if params.publication_types:
            self._param_pairs_layout.addWidget(
                self._make_param_line("Publication types", ", ".join(params.publication_types)),
            )
        if params.author_orcids:
            self._param_pairs_layout.addWidget(
                self._make_param_line("Authors", f"{len(params.author_orcids)} ORCIDs"),
            )

    def _populate_skipped(self, results: list[DownloadResult]) -> None:
        """Clear and repopulate the skipped papers card from the given results.

        Shows the card when there are skipped or failed papers; hides it otherwise.

        Args:
            results: The full list of DownloadResult objects from the download phase.

        """
        not_downloaded = [r for r in results if r.status != DownloadResult.STATUS_DOWNLOADED]
        self._skipped_card.setVisible(bool(not_downloaded))

        while self._skipped_list_layout.count():
            item = self._skipped_list_layout.takeAt(0)
            if item.widget():  # type: ignore[union-attr]
                item.widget().deleteLater()  # type: ignore[union-attr]

        for i, result in enumerate(not_downloaded):
            last = i == len(not_downloaded) - 1
            self._skipped_list_layout.addWidget(self._make_skipped_row(result, last=last))

    def _make_skipped_row(self, result: DownloadResult, *, last: bool) -> QWidget:
        """Build a single row widget for a skipped or failed paper.

        Args:
            result: The DownloadResult to render (non-downloaded status expected).
            last: When True, the bottom separator is omitted to avoid a double border.

        Returns:
            A QWidget showing the paper title, metadata, and skip reason.

        """
        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.CARD_BG};")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 16, 0, 0)
        row_layout.setSpacing(16)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        dot = QLabel("✗")
        dot.setFixedSize(_DOT_SIZE, _DOT_SIZE)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet(
            f"background-color: {theme.DANGER_BG}; color: {theme.DANGER};"
            f" border-radius: {_DOT_RADIUS}px; font-size: 12px;"
            f" font-weight: 700; border: none;",
        )
        row_layout.addWidget(dot)

        text_col = QWidget()
        text_col.setStyleSheet(f"background-color: {theme.CARD_BG};")
        text_layout = QVBoxLayout(text_col)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        title_lbl = QLabel(result.paper.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;",
        )
        text_layout.addWidget(title_lbl)

        meta_parts = [result.paper.authors, result.paper.journal, result.paper.year]
        meta_str = " · ".join(p for p in meta_parts if p)
        meta_lbl = QLabel(meta_str)
        meta_lbl.setWordWrap(True)
        meta_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 14px;")
        text_layout.addWidget(meta_lbl)

        reason_lbl = QLabel(result.reason or "Unknown reason")
        reason_lbl.setStyleSheet(
            f"color: {theme.DANGER}; font-size: 14px; font-weight: 500;",
        )
        text_layout.addWidget(reason_lbl)

        if not last:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(
                f"background-color: {_DIVIDER}; border: none; max-height: 1px; margin-top: 8px;",
            )
            text_layout.addWidget(separator)

        row_layout.addWidget(text_col, 1)
        return row

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_new_search(self) -> None:
        """Emit new_search_requested to signal MainWindow to reset to Screen 1."""
        self.new_search_requested.emit()

    def _on_export_excel(self) -> None:
        """Open a save dialog and export the report as Excel in a background worker."""
        if self._params is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "results.xlsx", "Excel Files (*.xlsx)",
        )
        if not path:
            return
        output_path = Path(path)
        results, params = self._results, self._params
        self._start_export(
            lambda: self._report_service.export_excel(results, params, output_path),
            path,
        )

    def _on_export_pdf(self) -> None:
        """Open a save dialog and export the report as PDF in a background worker."""
        if self._params is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", "results.pdf", "PDF Files (*.pdf)",
        )
        if not path:
            return
        output_path = Path(path)
        results, params, total_found = self._results, self._params, self._total_found
        self._start_export(
            lambda: self._report_service.export_pdf(results, params, output_path, total_found),
            path,
        )

    def _start_export(self, fn: Callable[[], None], path: str) -> None:
        """Create and start an ExportWorker for the given callable.

        Args:
            fn: Zero-argument callable that performs the export.
            path: File path string to emit with export_done on success.

        """
        self._worker = ExportWorker(fn, path)
        self._worker.export_done.connect(self._on_export_done)
        self._worker.export_error.connect(self._on_export_error)
        self._worker.start()

    def _on_export_done(self, path: str) -> None:
        """Show a success toast after a successful export.

        Only the filename (not the full path) is shown so the toast fits
        without overflowing on long directory paths.
        """
        self._toast.show_message(f"Saved to {Path(path).name}", success=True)  # type: ignore[union-attr]

    def _on_export_error(self, message: str) -> None:
        """Log the error and show a failure toast."""
        _logger.error("Export failed: %s", message)
        self._toast.show_message(f"Export failed: {message}", success=False)  # type: ignore[union-attr]
