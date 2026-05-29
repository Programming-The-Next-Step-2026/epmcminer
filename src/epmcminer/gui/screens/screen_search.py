"""Screen 1 — search query and filter inputs."""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme
from epmcminer.gui.widgets.card import make_card, make_section_label
from epmcminer.gui.widgets.date_picker import DatePicker
from epmcminer.gui.widgets.tag_input import TagInput
from epmcminer.gui.widgets.toast import Toast
from epmcminer.services.models import SearchParams
from epmcminer.services.orcid_validation_service import OrcidValidationService

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

_HINT_STYLE = f"color: {theme.TEXT_MUTED}; font-size: 13px;"


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


class OrcidExistenceWorker(QThread):
    """QThread worker that checks whether an ORCID exists in the public registry.

    Emits :attr:`validation_done` on success/failure, or :attr:`network_error`
    when a network-level failure prevents the request from completing. The
    latter leaves the pill in ``"pending"`` state — non-blocking fail-open
    behaviour so the user can still submit the form.

    Signals:
        validation_done: Emitted with ``(orcid, exists)`` on HTTP response.
        network_error: Emitted with ``orcid`` on :class:`ConnectionError`.
    """

    validation_done = pyqtSignal(str, bool)
    network_error = pyqtSignal(str)

    def __init__(
        self,
        orcid: str,
        service: OrcidValidationService,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the worker.

        Args:
            orcid: The bare ORCID identifier to look up.
            service: The validation service used to perform the HTTP check.
            parent: Optional parent for ownership / lifetime management.

        """
        super().__init__(parent)
        self._orcid = orcid
        self._service = service

    def run(self) -> None:
        """Perform the existence check and emit the result signal."""
        try:
            exists = self._service.check_exists(self._orcid)
            self.validation_done.emit(self._orcid, exists)
        except ConnectionError:
            self.network_error.emit(self._orcid)


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


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

    def __init__(
        self,
        orcid_service: OrcidValidationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the search screen.

        Args:
            orcid_service: Optional service used to validate ORCID identifiers.
                When ``None``, ORCIDs are accepted without validation (useful
                in tests that do not need the validation feature).
            parent: Optional parent widget.

        """
        super().__init__(parent)
        self._orcid_service = orcid_service
        # Track which ORCID tags have already been processed so the handler is
        # idempotent — we only launch a new worker for newly added tags.
        self._validated_orcids: set[str] = set()
        # Keep worker references alive until Qt delivers the signals.
        self._workers: list[OrcidExistenceWorker] = []
        self._toast: Toast | None = None
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
        return SearchParams(
            query=self._query_edit.text().strip(),
            date_from=self._date_from.date().toString("yyyy-MM-dd"),
            date_to=self._date_to.date().toString("yyyy-MM-dd"),
            publication_types=self._pub_types.get_tags(),
            licenses=self._license.get_tags(),
            author_orcids=self._orcids.get_tags_by_status(["valid", "pending"]),
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Construct the screen layout: scrollable form cards and fixed action bar."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {theme.APP_BG}; border: none; }}",
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
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
        root.addWidget(self._make_action_bar())

        self._toast = Toast(self)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Reposition the toast whenever the screen is resized."""
        super().resizeEvent(event)
        if self._toast is not None and not self._toast.isHidden():
            self._toast.reposition()

    def _connect_signals(self) -> None:
        """Wire validation signals after all widgets are constructed."""
        self._query_edit.textChanged.connect(self._validate)
        self._pub_types.tags_changed.connect(self._validate)
        self._license.tags_changed.connect(self._validate)

    def _make_query_card(self) -> QWidget:
        """Build the search query card with a text input and a usage hint.

        Returns:
            The card QWidget containing the query input.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Search query"))

        self._query_edit = QLineEdit()
        self._query_edit.setStyle(theme.get_fusion_style())
        self._query_edit.setStyleSheet(_QUERY_INPUT_STYLE)
        self._query_edit.setPlaceholderText("e.g. depression AND therapy")
        self._query_edit.setMaxLength(500)
        layout.addWidget(self._query_edit)

        hint = QLabel("Use AND / OR to combine keywords. Defaults to AND if no operator is specified")
        hint.setStyleSheet(_HINT_STYLE)
        layout.addWidget(hint)
        return card

    def _make_orcids_card(self) -> QWidget:
        """Build the Author ORCIDs card with a tag input and a format hint.

        Returns:
            The card QWidget containing the ORCID tag input.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Author ORCIDs"))

        self._orcids = TagInput(add_label="+ Add ORCID")
        self._orcids.tags_changed.connect(self._on_orcid_tags_changed)
        layout.addWidget(self._orcids)

        hint = QLabel("Format: 0000-0000-0000-0000 · Multiple ORCIDs use OR logic")
        hint.setStyleSheet(_HINT_STYLE)
        layout.addWidget(hint)
        return card

    def _make_pub_types_card(self) -> QWidget:
        """Build the publication types card pre-populated with all default types.

        Returns:
            The card QWidget containing the publication type tag input.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Publication types"))

        self._pub_types = TagInput(
            available_options=DEFAULT_PUBLICATION_TYPES, add_label="+ Add type",
        )
        self._pub_types.set_tags(list(DEFAULT_PUBLICATION_TYPES))
        layout.addWidget(self._pub_types)
        return card

    def _make_two_col_row(self) -> QWidget:
        """Build a two-column row containing the license and date range cards side by side.

        Returns:
            A QWidget laying out the license card and date card horizontally.

        """
        row = QWidget()
        row.setStyleSheet(f"background-color: {theme.APP_BG}; border: none;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self._make_license_card())
        layout.addWidget(self._make_date_card())
        return row

    def _make_license_card(self) -> QWidget:
        """Build the license card pre-populated with CC-BY.

        Returns:
            The card QWidget containing the license tag input.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Licenses"))

        self._license = TagInput(available_options=_AVAILABLE_LICENSES, add_label="+ Add")
        self._license.set_tags(["CC-BY"])
        layout.addWidget(self._license)
        return card

    def _make_date_card(self) -> QWidget:
        """Build the date range card with from/to DatePicker widgets.

        Returns:
            The card QWidget containing the date range pickers.

        """
        card, layout = make_card()
        layout.addWidget(make_section_label("Date range"))

        today = QDate.currentDate()
        five_years_ago = today.addYears(-5)

        date_row = QWidget()
        date_layout = QHBoxLayout(date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(10)

        self._date_from = DatePicker()
        self._date_from.setDate(five_years_ago)
        self._date_from.setMinimumDate(QDate(1900, 1, 1))
        self._date_from.setMaximumDate(today)
        self._date_from.dateChanged.connect(self._on_date_from_changed)
        date_layout.addWidget(self._date_from)

        arrow = QLabel("→")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 16px;")
        date_layout.addWidget(arrow)

        self._date_to = DatePicker()
        self._date_to.setDate(today)
        self._date_to.setMinimumDate(five_years_ago)
        self._date_to.setMaximumDate(today)
        self._date_to.dateChanged.connect(self._on_date_to_changed)
        date_layout.addWidget(self._date_to)

        layout.addWidget(date_row)
        return card

    def _make_action_bar(self) -> QWidget:
        """Build the fixed-height action bar with the open-access label and Continue button.

        Returns:
            A QWidget containing the status label, hint label, and continue button.

        """
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f"background-color: {theme.APP_BG}; border-top: 1px solid {theme.BORDER};",
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(22, 0, 22, 0)

        lock_lbl = QLabel("🔒  Open-access papers only")
        lock_lbl.setStyleSheet(f"color: {theme.TEXT_BODY}; font-size: 15px;")
        bar_layout.addWidget(lock_lbl)
        bar_layout.addStretch()

        self._hint_lbl = QLabel()
        self._hint_lbl.setStyleSheet(_HINT_STYLE)
        self._hint_lbl.setVisible(False)
        bar_layout.addWidget(self._hint_lbl)
        bar_layout.addSpacing(16)

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
        """Enable the continue button when all required fields are satisfied."""
        has_query = bool(self._query_edit.text().strip())
        has_pub_types = bool(self._pub_types.get_tags())
        has_license = bool(self._license.get_tags())
        ok = has_query and has_pub_types and has_license
        self._continue_btn.setEnabled(ok)

        if not ok:
            parts: list[str] = []
            if not has_query:
                parts.append("Enter a search keyword")
            elif not has_pub_types:
                parts.append("Select a publication type")
            elif not has_license:
                parts.append("Select a license")
            self._hint_lbl.setText("  ·  ".join(parts))
            self._hint_lbl.setVisible(True)
        else:
            self._hint_lbl.setVisible(False)

    def _on_date_from_changed(self, new_from: QDate) -> None:
        """Enforce start ≤ end by updating the end date minimum and value."""
        if self._date_to.date() < new_from:
            self._date_to.setDate(new_from)
        self._date_to.setMinimumDate(new_from)

    def _on_date_to_changed(self, new_to: QDate) -> None:
        """Enforce start ≤ end by constraining the start date maximum."""
        self._date_from.setMaximumDate(new_to)

    def _on_continue(self) -> None:
        """Emit search_requested with the current form values when Continue is clicked."""
        self.search_requested.emit(self.get_params())

    def _on_orcid_tags_changed(self, tags: list[str]) -> None:
        """Handle additions and removals on the ORCID tag input.

        For each newly added tag:

        1. Normalise it — if the user pasted a URL-prefixed form, replace the
           tag in the widget with its bare form and return (the signal will
           re-fire with the normalised value).
        2. Run a format check synchronously. Invalid format → mark red.
        3. If format is valid, mark pending and launch an
           :class:`OrcidExistenceWorker` for the async registry check.

        When the service is ``None`` (tests / no-service mode) tags are
        accepted as-is without any validation styling.
        """
        if self._orcid_service is None:
            return

        current_set = set(tags)

        # Clean up stale state for removed tags.
        removed = self._validated_orcids - current_set
        self._validated_orcids -= removed

        for tag in tags:
            if tag in self._validated_orcids:
                continue  # already processed

            # Step 1: normalise URL-prefixed ORCIDs.
            normalised = self._orcid_service.normalise(tag)
            if normalised != tag:
                # Replace the raw tag with the bare form. The subsequent
                # tags_changed signal will re-enter this handler with the
                # normalised value, so we return early.
                self._validated_orcids.add(tag)  # prevent infinite loop
                self._orcids.remove_tag(tag)
                self._orcids.add_tag(normalised)
                return

            # Step 2: format validation (synchronous, local).
            self._validated_orcids.add(tag)
            if not self._orcid_service.validate_format(tag):
                self._orcids.set_tag_status(tag, "invalid")
                continue

            # Step 3: existence check (async, HTTP).
            self._orcids.set_tag_status(tag, "pending")
            worker = OrcidExistenceWorker(tag, self._orcid_service)
            worker.validation_done.connect(self._on_orcid_existence_checked)
            worker.network_error.connect(self._on_orcid_network_error)
            self._workers.append(worker)
            worker.start()

    def _on_orcid_existence_checked(self, orcid: str, exists: bool) -> None:
        """Update the pill status once the registry check completes.

        Args:
            orcid: The ORCID that was checked.
            exists: ``True`` if the registry returned HTTP 200.

        """
        self._orcids.set_tag_status(orcid, "valid" if exists else "invalid")
        # Discard completed workers to avoid unbounded growth.
        self._workers = [w for w in self._workers if w.isRunning()]

    def _on_orcid_network_error(self, orcid: str) -> None:
        """Keep the pill in ``"pending"`` state when the network is unreachable.

        This is a deliberate fail-open: the user can still submit the form
        with a pending ORCID; the tag simply has not been confirmed.

        Args:
            orcid: The ORCID whose existence check failed due to a network error.

        """
        # Pill already shows "pending" — no style change needed. Just clean up.
        self._workers = [w for w in self._workers if w.isRunning()]
        if self._toast is not None:
            self._toast.show_message(
                f"Could not verify ORCID {orcid} — network unreachable. Accepted as pending.",
                success=False,
            )
