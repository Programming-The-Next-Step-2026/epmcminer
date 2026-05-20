"""Screen 1 — search query and filter inputs."""

from pathlib import Path

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme
from epmcminer.gui.widgets.card import make_card, make_section_label
from epmcminer.gui.widgets.tag_input import TagInput
from epmcminer.services.models import SearchParams

DEFAULT_PUBLICATION_TYPES: list[str] = [
    "Review",
    "Meta analysis",
    "Clinical trial",
    "Systematic review",
    "Comparative study",
    "Observational study",
    "Randomized controlled trial",
    "Twin study",
    "Validation study",
    "Case reports",
    "Dataset",
    "Corrected and republished article",
    "Clinical study",
    "Evaluation study",
    "Multicenter study",
    "Observational study (veterinary)",
]

_AVAILABLE_LICENSES: list[str] = [
    "CC-BY",
    "CC-BY-NC",
    "CC-BY-SA",
    "CC0",
    "CC-BY-ND",
    "CC-BY-NC-SA",
    "CC-BY-NC-ND",
]

_QUERY_INPUT_STYLE = f"""
    QLineEdit {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 18px;
    }}
    QLineEdit:focus {{
        border-color: rgba(255, 122, 61, 140);
    }}
"""

_FOLDER_INPUT_STYLE = f"""
    QLineEdit {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 15px;
    }}
"""

_DATE_EDIT_STYLE = f"""
    QDateEdit {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 16px;
    }}
    QDateEdit:focus {{
        border-color: rgba(255, 122, 61, 140);
    }}
    QDateEdit::drop-down {{
        border: none;
        width: 0px;
    }}
"""

_CONTINUE_BTN_STYLE = f"""
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

_BROWSE_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER_STRONG};
        border-radius: 12px;
        padding: 14px 18px;
        font-size: 15px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 10);
    }}
"""

_HINT_STYLE = f"color: {theme.TEXT_MUTED}; font-size: 13px;"


class ScreenSearch(QWidget):
    """Wizard screen for composing a Europe PMC search query.

    Collects a keyword query, date range, publication types, license, author
    ORCIDs, and an output folder. Emits ``search_requested`` carrying a
    ``SearchParams`` when the user clicks "Continue to preview". The button
    is disabled until the query is non-empty and at least one publication
    type is selected.

    Signals:
        search_requested: Emitted with a fully populated ``SearchParams``
            when the user confirms the query.
    """

    search_requested = pyqtSignal(SearchParams)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the search screen.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {theme.APP_BG};")
        self._build_ui()
        self._connect_signals()
        self._validate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_params(self) -> SearchParams:
        """Collect and return the current form values as a SearchParams.

        Returns:
            A SearchParams built from the current widget state.
        """
        folder_text = self._folder_edit.text().strip()
        return SearchParams(
            query=self._query_edit.text().strip(),
            date_from=self._date_from.date().toString("yyyy-MM-dd"),
            date_to=self._date_to.date().toString("yyyy-MM-dd"),
            publication_types=self._pub_types.get_tags(),
            licenses=self._license.get_tags(),
            author_orcids=self._orcids.get_tags(),
            output_folder=Path(folder_text) if folder_text else Path(),
        )

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

        content = QWidget()
        content.setStyleSheet(f"background-color: {theme.APP_BG};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        layout.addWidget(self._make_query_card())
        layout.addWidget(self._make_orcids_card())
        layout.addWidget(self._make_pub_types_card())
        layout.addWidget(self._make_two_col_row())
        layout.addWidget(self._make_folder_card())
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
        root.addWidget(self._make_action_bar())

    def _connect_signals(self) -> None:
        """Wire validation signals after all widgets are constructed."""
        self._query_edit.textChanged.connect(self._validate)
        self._pub_types.tags_changed.connect(self._validate)

    def _make_query_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Search query"))

        self._query_edit = QLineEdit()
        self._query_edit.setStyle(theme.get_fusion_style())
        self._query_edit.setStyleSheet(_QUERY_INPUT_STYLE)
        self._query_edit.setPlaceholderText("e.g. depression AND therapy")
        layout.addWidget(self._query_edit)

        hint = QLabel("Defaults to AND if no operator specified")
        hint.setStyleSheet(_HINT_STYLE)
        layout.addWidget(hint)
        return card

    def _make_orcids_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Author ORCIDs"))

        self._orcids = TagInput(add_label="+ Add ORCID")
        layout.addWidget(self._orcids)

        hint = QLabel("Multiple ORCIDs use OR logic — leave empty to search all authors")
        hint.setStyleSheet(_HINT_STYLE)
        layout.addWidget(hint)
        return card

    def _make_pub_types_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Publication types"))

        self._pub_types = TagInput(
            available_options=DEFAULT_PUBLICATION_TYPES, add_label="+ Add type"
        )
        self._pub_types.set_tags(list(DEFAULT_PUBLICATION_TYPES))
        layout.addWidget(self._pub_types)
        return card

    def _make_two_col_row(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.APP_BG}; border: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self._make_license_card())
        layout.addWidget(self._make_date_card())
        return row

    def _make_license_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("License"))

        self._license = TagInput(available_options=_AVAILABLE_LICENSES, add_label="+ Add")
        self._license.set_tags(["CC-BY"])
        layout.addWidget(self._license)
        return card

    def _make_date_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Date range"))

        today = QDate.currentDate()
        five_years_ago = today.addYears(-5)

        date_row = QWidget()
        date_layout = QHBoxLayout(date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(10)

        self._date_from = QDateEdit()
        self._date_from.setStyle(theme.get_fusion_style())
        self._date_from.setStyleSheet(_DATE_EDIT_STYLE)
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(five_years_ago)
        self._date_from.setMinimumDate(QDate(2000, 1, 1))
        self._date_from.setMaximumDate(today)
        self._date_from.dateChanged.connect(self._on_date_from_changed)
        date_layout.addWidget(self._date_from)

        arrow = QLabel("→")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 16px;")
        date_layout.addWidget(arrow)

        self._date_to = QDateEdit()
        self._date_to.setStyle(theme.get_fusion_style())
        self._date_to.setStyleSheet(_DATE_EDIT_STYLE)
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(today)
        self._date_to.setMinimumDate(five_years_ago)
        self._date_to.setMaximumDate(today)
        date_layout.addWidget(self._date_to)

        layout.addWidget(date_row)
        return card

    def _make_folder_card(self) -> QWidget:
        card, layout = make_card()
        layout.addWidget(make_section_label("Output folder"))

        folder_row = QWidget()
        folder_layout = QHBoxLayout(folder_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(10)

        self._folder_edit = QLineEdit()
        self._folder_edit.setStyle(theme.get_fusion_style())
        self._folder_edit.setStyleSheet(_FOLDER_INPUT_STYLE)
        self._folder_edit.setPlaceholderText("/path/to/output")
        self._folder_edit.setReadOnly(True)
        folder_layout.addWidget(self._folder_edit, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.setStyle(theme.get_fusion_style())
        browse_btn.setStyleSheet(_BROWSE_BTN_STYLE)
        browse_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_btn)

        layout.addWidget(folder_row)
        return card

    def _make_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f"background-color: {theme.APP_BG}; border-top: 1px solid {theme.BORDER};"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(22, 0, 22, 0)

        lock_lbl = QLabel("🔒  Open-access papers only")
        lock_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 15px;")
        bar_layout.addWidget(lock_lbl)
        bar_layout.addStretch()

        self._continue_btn = QPushButton("Continue to preview  →")
        self._continue_btn.setStyle(theme.get_fusion_style())
        self._continue_btn.setStyleSheet(_CONTINUE_BTN_STYLE)
        self._continue_btn.clicked.connect(self._on_continue)
        bar_layout.addWidget(self._continue_btn)
        return bar

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Enable the continue button when query is non-empty and pub types selected."""
        ok = bool(self._query_edit.text().strip()) and bool(self._pub_types.get_tags())
        self._continue_btn.setEnabled(ok)

    def _on_date_from_changed(self, new_from: QDate) -> None:
        """Enforce start ≤ end by updating the end date minimum and value."""
        if self._date_to.date() < new_from:
            self._date_to.setDate(new_from)
        self._date_to.setMinimumDate(new_from)

    def _on_continue(self) -> None:
        self.search_requested.emit(self.get_params())

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self._folder_edit.setText(folder)
