"""Screen 2 — results preview and download settings."""

import dataclasses
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme
from epmcminer.gui.widgets.card import make_card, make_section_label
from epmcminer.gui.widgets.progress_widget import ProgressWidget
from epmcminer.services.models import Paper, SearchParams, SearchResult
from epmcminer.services.search_service import SORT_ORDER_MAP, SearchService

# ---------------------------------------------------------------------------
# Screen-local constants
# ---------------------------------------------------------------------------
_SORT_OPTIONS: list[str] = list(SORT_ORDER_MAP.keys())  # ["relevance", "date", "citations"]
_SORT_LABELS: dict[str, str] = {"relevance": "Relevance", "date": "Date", "citations": "Citations"}
_DEFAULT_COUNT = 50
_COUNT_MIN = 1
_COUNT_MAX = 10_000
_PAPER_LIST_HEIGHT = 380
_DIVIDER = theme.BORDER_FAINT

_ACTION_BTN_STYLE = f"""
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

_SORT_BTN_STYLE = f"""
    QPushButton {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_STRONG};
        border-radius: 14px;
        padding: 6px 14px;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 10);
    }}
"""

_SORT_MENU_STYLE = f"""
    QMenu {{
        background-color: {theme.CARD_BG};
        border: 1px solid rgba(255, 255, 255, 46);
        border-radius: 10px;
        padding: 5px;
        font-size: 14px;
        color: {theme.TEXT_PRIMARY};
    }}
    QMenu::item {{
        padding: 9px 18px;
        border-radius: 6px;
        color: {theme.TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 400;
    }}
    QMenu::item:selected {{
        background-color: rgba(255, 122, 61, 46);
        color: #ff9a6a;
    }}
"""

_SPIN_STYLE = f"""
    QSpinBox {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 16px;
        text-align: center;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        width: 0px; border: none;
    }}
"""

_FOLDER_INPUT_STYLE = f"""
    QLineEdit {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 15px;
    }}
"""

_BROWSE_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_STRONG};
        border-radius: 12px;
        padding: 12px 18px;
        font-size: 15px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 10);
    }}
"""


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class PreviewWorker(QThread):
    """Background thread that calls SearchService.preview().

    Attributes:
        result_ready: Emitted with the SearchResult on success.
        error_occurred: Emitted with an error message string on failure.
    """

    result_ready = pyqtSignal(SearchResult)
    error_occurred = pyqtSignal(str)

    def __init__(self, service: SearchService, params: SearchParams) -> None:
        """Initialise the worker.

        Args:
            service: The SearchService to query.
            params: The search parameters to pass to preview().
        """
        super().__init__()
        self._service = service
        self._params = params

    def run(self) -> None:
        """Execute the preview call and emit the appropriate signal."""
        try:
            result = self._service.preview(self._params)
            self.result_ready.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.error_occurred.emit(str(exc))


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


class ScreenPreview(QWidget):
    """Wizard screen for previewing search results and configuring the download.

    Shows a loading state while querying the API, then displays stat cards,
    a paper list, and download settings. Emits back_requested or
    download_requested depending on the user's action.

    Signals:
        back_requested: Emitted when the user clicks "Back".
        download_requested: Emitted with a fully populated SearchParams when
            "Start download" is clicked.
        result_loaded: Emitted with ``total_found`` (int) when a search result
            arrives successfully. Used by MainWindow to pass the count to
            ScreenSummary.
    """

    back_requested = pyqtSignal()
    download_requested = pyqtSignal(SearchParams)
    result_loaded = pyqtSignal(int)  # emits total_found when a search result arrives

    def __init__(self, search_service: SearchService, parent: QWidget | None = None) -> None:
        """Initialise the preview screen.

        Args:
            search_service: Injected SearchService used to fetch preview results.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._service = search_service
        self._params: SearchParams | None = None
        self._worker: PreviewWorker | None = None
        self._sort_index: int = 0
        self.setStyleSheet(f"background-color: {theme.APP_BG};")
        self._build_ui()
        self._connect_signals()
        self._validate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, params: SearchParams) -> None:
        """Trigger an API query for the given params and update the UI.

        Shows the loading animation immediately, stops any running worker,
        and starts a new PreviewWorker.

        Args:
            params: Search parameters to pass to the service.
        """
        self._params = params
        sort_idx = (
            _SORT_OPTIONS.index(params.sort_order) if params.sort_order in _SORT_OPTIONS else 0
        )
        self._sort_index = sort_idx
        self._sort_btn.setText(_SORT_LABELS[_SORT_OPTIONS[sort_idx]] + "  ▾")

        if params.output_folder.is_absolute():
            self._folder_edit.setText(str(params.output_folder))

        self._show_loading()

        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()

        self._worker = PreviewWorker(self._service, params)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

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

        self._progress = ProgressWidget()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._error_widget = self._make_error_widget()
        self._error_widget.setVisible(False)
        layout.addWidget(self._error_widget)

        self._content = self._make_content()
        self._content.setVisible(False)
        layout.addWidget(self._content)

        layout.addStretch()

        scroll.setWidget(content_widget)
        root.addWidget(scroll)
        root.addWidget(self._make_action_bar())

    def _make_error_widget(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {theme.APP_BG};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 40, 0, 0)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self._error_label = QLabel("")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 15px;")
        layout.addWidget(self._error_label)

        self._try_again_btn = QPushButton("Try again")
        self._try_again_btn.setStyle(theme.get_fusion_style())
        self._try_again_btn.setStyleSheet(_ACTION_BTN_STYLE)
        self._try_again_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._try_again_btn.clicked.connect(self._on_try_again)
        layout.addWidget(self._try_again_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        return widget

    def _make_content(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {theme.APP_BG};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        layout.addWidget(self._make_stat_row())
        layout.addWidget(self._make_results_card())
        layout.addWidget(self._make_download_settings_card())

        return widget

    def _make_stat_tile(self, label: str, sub: str) -> tuple[QWidget, QLabel]:
        """Build a single stat tile. Returns (frame, value_label)."""
        card, layout = make_card(padding=22)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 15px; font-weight: 500;")
        layout.addWidget(lbl)

        value_lbl = QLabel("—")
        value_lbl.setStyleSheet(
            f"color: {theme.ACCENT}; font-size: 32px; font-weight: 600; line-height: 1;"
        )
        layout.addWidget(value_lbl)

        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(sub_lbl)

        return card, value_lbl

    def _make_stat_row(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.APP_BG}; border: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        tile_total, self._stat_total_value = self._make_stat_tile(
            "Total results", "matching your query"
        )
        tile_pdf, self._stat_pdf_value = self._make_stat_tile(
            "PDF available", "open-access full text"
        )
        tile_prev, self._stat_previewing_value = self._make_stat_tile(
            "Previewing", "top results shown below"
        )

        layout.addWidget(tile_total)
        layout.addWidget(tile_pdf)
        layout.addWidget(tile_prev)
        return row

    def _make_results_card(self) -> QWidget:
        card, layout = make_card()

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        header_layout.addWidget(make_section_label("Results preview"))

        sort_group = QWidget()
        sort_layout = QHBoxLayout(sort_group)
        sort_layout.setContentsMargins(0, 0, 0, 0)
        sort_layout.setSpacing(10)

        sort_lbl = QLabel("Sort by")
        sort_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 14px;")
        sort_layout.addWidget(sort_lbl)

        self._sort_btn = QPushButton(_SORT_LABELS[_SORT_OPTIONS[0]] + "  ▾")
        self._sort_btn.setStyle(theme.get_fusion_style())
        self._sort_btn.setStyleSheet(_SORT_BTN_STYLE)
        self._sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._sort_btn.clicked.connect(self._show_sort_menu)

        self._sort_menu = QMenu(self)
        self._sort_menu.setStyleSheet(_SORT_MENU_STYLE)
        for key in _SORT_OPTIONS:
            action = self._sort_menu.addAction(_SORT_LABELS[key])
            action.triggered.connect(lambda checked, k=key: self._on_sort_menu_selected(k))

        sort_layout.addWidget(self._sort_btn)

        header_layout.addStretch()
        header_layout.addWidget(sort_group)
        layout.addWidget(header_row)

        paper_scroll = QScrollArea()
        paper_scroll.setWidgetResizable(True)
        paper_scroll.setFixedHeight(_PAPER_LIST_HEIGHT)
        paper_scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.CARD_BG}; border: none; }}"
            f"QScrollArea > QWidget > QWidget {{ background-color: {theme.CARD_BG}; }}"
        )

        paper_container = QWidget()
        paper_container.setStyleSheet(f"background-color: {theme.CARD_BG};")
        self._paper_list_layout = QVBoxLayout(paper_container)
        self._paper_list_layout.setContentsMargins(0, 0, 0, 0)
        self._paper_list_layout.setSpacing(0)
        self._paper_list_layout.addStretch()

        paper_scroll.setWidget(paper_container)
        layout.addWidget(paper_scroll)

        return card

    def _make_paper_row(self, paper: Paper) -> QWidget:
        from PyQt6.QtWidgets import QFrame

        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.CARD_BG};")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(6)

        title_lbl = QLabel(paper.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;"
        )
        layout.addWidget(title_lbl)

        authors_lbl = QLabel(paper.authors)
        authors_lbl.setWordWrap(True)
        authors_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 13px;")
        layout.addWidget(authors_lbl)

        meta_lbl = QLabel(f"{paper.journal}  ·  {paper.year}  ·  {paper.doi}")
        meta_lbl.setWordWrap(True)
        meta_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(meta_lbl)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(
            f"background-color: {_DIVIDER}; border: none; max-height: 1px; margin-top: 10px;"
        )
        layout.addWidget(separator)

        return row

    def _make_download_settings_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Download settings"))

        fields_row = QWidget()
        fields_layout = QHBoxLayout(fields_row)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(14)

        count_col = QWidget()
        count_layout = QVBoxLayout(count_col)
        count_layout.setContentsMargins(0, 0, 0, 0)
        count_layout.setSpacing(8)
        count_lbl = QLabel("Count")
        count_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 14px; font-weight: 500;")
        count_layout.addWidget(count_lbl)
        self._count_spin = QSpinBox()
        self._count_spin.setStyle(theme.get_fusion_style())
        self._count_spin.setStyleSheet(_SPIN_STYLE)
        self._count_spin.setRange(_COUNT_MIN, _COUNT_MAX)
        self._count_spin.setValue(_DEFAULT_COUNT)
        self._count_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_spin.setFixedWidth(160)
        count_layout.addWidget(self._count_spin)
        fields_layout.addWidget(count_col)

        folder_col = QWidget()
        folder_layout = QVBoxLayout(folder_col)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)
        folder_lbl = QLabel("Output folder")
        folder_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 14px; font-weight: 500;")
        folder_layout.addWidget(folder_lbl)
        self._folder_edit = QLineEdit()
        self._folder_edit.setStyle(theme.get_fusion_style())
        self._folder_edit.setStyleSheet(_FOLDER_INPUT_STYLE)
        self._folder_edit.setPlaceholderText("/path/to/output")
        self._folder_edit.setReadOnly(True)
        folder_layout.addWidget(self._folder_edit)
        fields_layout.addWidget(folder_col, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.setStyle(theme.get_fusion_style())
        browse_btn.setStyleSheet(_BROWSE_BTN_STYLE)
        browse_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        browse_btn.clicked.connect(self._browse_folder)
        fields_layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(fields_row)

        hint = QLabel("Skipped papers and reasons will be shown on the summary screen")
        hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(hint)

        return card

    def _make_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f"background-color: {theme.APP_BG}; border-top: 1px solid {theme.BORDER};"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(22, 0, 22, 0)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setStyle(theme.get_fusion_style())
        self._back_btn.setStyleSheet(_ACTION_BTN_STYLE)
        self._back_btn.clicked.connect(self.back_requested.emit)
        bar_layout.addWidget(self._back_btn)

        bar_layout.addStretch()

        self._start_btn = QPushButton("Start download  →")
        self._start_btn.setStyle(theme.get_fusion_style())
        self._start_btn.setStyleSheet(_ACTION_BTN_STYLE)
        self._start_btn.clicked.connect(self._on_start_download)
        bar_layout.addWidget(self._start_btn)

        return bar

    def _connect_signals(self) -> None:
        """Wire validation signals after all widgets are built."""
        self._folder_edit.textChanged.connect(self._validate)
        self._count_spin.valueChanged.connect(self._validate)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _show_loading(self) -> None:
        self._progress.set_loading("Searching…")
        self._progress.setVisible(True)
        self._error_widget.setVisible(False)
        self._content.setVisible(False)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Enable Start download when count >= 1 and folder is non-empty."""
        ok = self._count_spin.value() >= 1 and bool(self._folder_edit.text().strip())
        self._start_btn.setEnabled(ok)

    def _on_result(self, result: SearchResult) -> None:
        """Handle a successful preview result from the worker."""
        self._stat_total_value.setText(f"{result.total_found:,}")
        self._stat_pdf_value.setText(f"{result.estimated_downloadable:,}")
        self._stat_previewing_value.setText(str(len(result.papers)))
        self._populate_paper_list(result.papers)
        self._progress.setVisible(False)
        self._error_widget.setVisible(False)
        self._content.setVisible(True)
        self.result_loaded.emit(result.total_found)

    def _on_error(self, message: str) -> None:
        """Handle an error emitted by the worker."""
        self._error_label.setText(message)
        self._progress.setVisible(False)
        self._content.setVisible(False)
        self._error_widget.setVisible(True)

    def _on_try_again(self) -> None:
        """Re-run the last load() call."""
        if self._params is not None:
            self.load(self._params)

    def _show_sort_menu(self) -> None:
        """Pop up the sort menu positioned below the sort button."""
        pos = self._sort_btn.mapToGlobal(QPoint(0, self._sort_btn.height() + 4))
        self._sort_menu.exec(pos)

    def _on_sort_menu_selected(self, sort_key: str) -> None:
        """Handle sort option selection: update button label and re-query."""
        self._sort_index = _SORT_OPTIONS.index(sort_key)
        self._sort_btn.setText(_SORT_LABELS[sort_key] + "  ▾")
        if self._params is None:
            return
        self._params = dataclasses.replace(self._params, sort_order=sort_key)
        self.load(self._params)

    def _on_start_download(self) -> None:
        """Emit download_requested with merged count, folder, and sort order."""
        if self._params is None:
            return
        sort_key = _SORT_OPTIONS[self._sort_index]
        params = dataclasses.replace(
            self._params,
            count=self._count_spin.value(),
            output_folder=Path(self._folder_edit.text().strip()),
            sort_order=sort_key,
        )
        self.download_requested.emit(params)

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self._folder_edit.setText(folder)

    def _populate_paper_list(self, papers: list[Paper]) -> None:
        # Remove all items including the trailing stretch
        while self._paper_list_layout.count():
            item = self._paper_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for paper in papers:
            self._paper_list_layout.addWidget(self._make_paper_row(paper))
        self._paper_list_layout.addStretch()
