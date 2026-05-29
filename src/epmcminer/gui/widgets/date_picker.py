"""Styled date picker widget for the epmcminer dark theme."""

from PyQt6.QtCore import QDate, QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainterPath, QRegion, QResizeEvent, QTextCharFormat
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QFrame,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import epmcminer.gui.theme as theme

_DISPLAY_STYLE = f"""
    QPushButton {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 12px;
        padding: 14px 16px;
        font-size: 16px;
        text-align: left;
    }}
    QPushButton:hover {{
        background-color: rgba(255, 255, 255, 5);
    }}
    QPushButton:focus {{
        border-color: rgba(255, 122, 61, 140);
        outline: none;
    }}
"""

_CALENDAR_STYLE = f"""
    QCalendarWidget QAbstractItemView {{
        background-color: {theme.CARD_BG};
        color: {theme.TEXT_PRIMARY};
        gridline-color: transparent;
        alternate-background-color: {theme.CARD_BG};
        selection-background-color: transparent;
        border: none;
        outline: none;
    }}
    QCalendarWidget QAbstractItemView:disabled {{
        color: {theme.TEXT_MUTED};
    }}
    QCalendarWidget QAbstractItemView::item {{
        border: none;
        border-radius: 6px;
        margin: 1px;
    }}
    QCalendarWidget QAbstractItemView::item:selected {{
        background-color: {theme.ACCENT};
        color: #000000;
        border: none;
        border-radius: 6px;
    }}
    QCalendarWidget QAbstractItemView::item:hover {{
        background-color: rgba(255, 122, 61, 40);
        border: none;
        border-radius: 6px;
    }}
    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background-color: {theme.CARD_INNER};
        padding: 4px;
    }}
    QCalendarWidget QToolButton {{
        background-color: transparent;
        color: {theme.TEXT_PRIMARY};
        border: none;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 14px;
    }}
    QCalendarWidget QToolButton:hover {{
        background-color: rgba(255, 255, 255, 10);
    }}
    QCalendarWidget QMenu {{
        background-color: {theme.CARD_BG};
        border: 1px solid rgba(255, 255, 255, 46);
        border-radius: 10px;
        padding: 5px;
        font-size: 14px;
        color: {theme.TEXT_PRIMARY};
    }}
    QCalendarWidget QMenu::item {{
        padding: 9px 18px;
        border-radius: 6px;
        color: {theme.TEXT_PRIMARY};
        font-size: 14px;
        font-weight: 400;
    }}
    QCalendarWidget QMenu::item:selected {{
        background-color: rgba(255, 122, 61, 46);
        color: #ff9a6a;
    }}
    QCalendarWidget QSpinBox {{
        background-color: {theme.CARD_INNER};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.BORDER};
        border-radius: 4px;
        padding: 2px 4px;
    }}
    QCalendarWidget QSpinBox::up-button,
    QCalendarWidget QSpinBox::down-button {{
        width: 0px;
    }}
"""

_POPUP_STYLE = f"""
    QFrame {{
        background-color: {theme.CARD_BG};
        border: 1px solid {theme.BORDER_STRONG};
        border-radius: 12px;
    }}
"""

_CALENDAR_MIN_WIDTH = 300

_NAV_BUTTON_STYLE = (
    f"color: {theme.ACCENT}; font-size: 20px; font-weight: bold;"
    f"background-color: transparent; border: none; padding: 2px 8px;"
)


class _CalendarPopup(QFrame):
    """Floating popup containing a styled QCalendarWidget.

    Uses Qt.WindowType.Popup so Qt closes it automatically whenever the
    user clicks outside the popup.
    """

    date_selected = pyqtSignal(QDate)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_POPUP_STYLE)

        self._calendar = QCalendarWidget()
        self._calendar.setStyleSheet(_CALENDAR_STYLE)
        self._calendar.setStyle(theme.get_fusion_style())
        self._calendar.setGridVisible(False)
        self._calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader,
        )
        self._calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames,
        )
        self._calendar.setMinimumWidth(_CALENDAR_MIN_WIDTH)
        self._calendar.clicked.connect(self.date_selected)
        self._style_navigation_buttons()
        self._style_weekend_format()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        layout.addWidget(self._calendar)
        self.adjustSize()

    def calendar(self) -> QCalendarWidget:
        """Return the internal QCalendarWidget.

        Returns:
            The QCalendarWidget used inside this popup.

        """
        return self._calendar

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Clip the popup to its rounded-corner shape so no boxy corners bleed through."""
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12.0, 12.0)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _style_navigation_buttons(self) -> None:
        """Replace the default black arrows with accent-colored Unicode chevrons.

        In Qt 6 the buttons use setIcon() rather than setArrowType(), so both
        are cleared and the button is switched to text-only mode before setting
        the glyph and colour.
        """
        for name, glyph in (("qt_calendar_prevmonth", "‹"), ("qt_calendar_nextmonth", "›")):
            btn = self._calendar.findChild(QToolButton, name)
            if btn is not None:
                btn.setArrowType(Qt.ArrowType.NoArrow)
                btn.setIcon(QIcon())
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
                btn.setText(glyph)
                btn.setStyleSheet(_NAV_BUTTON_STYLE)

    def _style_weekend_format(self) -> None:
        """Use the accent colour for Saturday and Sunday instead of Qt's default red."""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(theme.ACCENT))
        self._calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, fmt)
        self._calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, fmt)


class DatePicker(QWidget):
    """A minimal date-picker widget styled for the epmcminer dark theme.

    Displays the selected date in a styled field. Clicking anywhere in the
    field opens a floating calendar popup. Optional minimum and maximum date
    bounds can be set via constructor arguments or setter methods.

    Signals:
        dateChanged: Emitted with the new QDate when the selected date changes.
    """

    dateChanged = pyqtSignal(QDate)

    def __init__(
        self,
        min_date: QDate | None = None,
        max_date: QDate | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the date picker with optional bounds.

        Args:
            min_date: Optional lower bound. Dates before this cannot be selected.
            max_date: Optional upper bound. Dates after this cannot be selected.
            parent: Optional parent widget.

        """
        super().__init__(parent)
        self._date: QDate = QDate.currentDate()
        self._min_date: QDate | None = min_date
        self._max_date: QDate | None = max_date
        self._build_ui()
        if min_date is not None:
            self._popup.calendar().setMinimumDate(min_date)
        if max_date is not None:
            self._popup.calendar().setMaximumDate(max_date)
        self._update_display()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def date(self) -> QDate:
        """Return the currently selected date.

        Returns:
            The selected QDate.

        """
        return self._date

    def setDate(self, date: QDate) -> None:
        """Set the selected date, clamping to [minimumDate, maximumDate].

        dateChanged is not emitted if the date is unchanged after clamping.

        Args:
            date: The desired QDate.

        """
        if self._min_date is not None and date < self._min_date:
            date = self._min_date
        if self._max_date is not None and date > self._max_date:
            date = self._max_date
        if date == self._date:
            return
        self._date = date
        self._update_display()
        self._popup.calendar().setSelectedDate(date)
        self.dateChanged.emit(date)

    def minimumDate(self) -> QDate | None:
        """Return the lower date bound, or None if no bound is set.

        Returns:
            The minimum QDate, or None.

        """
        return self._min_date

    def setMinimumDate(self, date: QDate) -> None:
        """Set the lower date bound, clamping the current date if needed.

        Args:
            date: The new minimum QDate.

        """
        self._min_date = date
        self._popup.calendar().setMinimumDate(date)
        if self._date < date:
            self.setDate(date)

    def maximumDate(self) -> QDate | None:
        """Return the upper date bound, or None if no bound is set.

        Returns:
            The maximum QDate, or None.

        """
        return self._max_date

    def setMaximumDate(self, date: QDate) -> None:
        """Set the upper date bound, clamping the current date if needed.

        Args:
            date: The new maximum QDate.

        """
        self._max_date = date
        self._popup.calendar().setMaximumDate(date)
        if self._date > date:
            self.setDate(date)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._display = QPushButton()
        self._display.setStyle(theme.get_fusion_style())
        self._display.setStyleSheet(_DISPLAY_STYLE)
        self._display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._display.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._display.clicked.connect(self._toggle_popup)
        layout.addWidget(self._display)

        self._popup = _CalendarPopup(self)
        self._popup.date_selected.connect(self._on_date_selected)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _toggle_popup(self) -> None:
        if self._popup.isVisible():
            self._popup.hide()
        else:
            pos = self._display.mapToGlobal(QPoint(0, self._display.height() + 4))
            self._popup.move(pos)
            self._popup.show()

    def _on_date_selected(self, date: QDate) -> None:
        self.setDate(date)

    def _update_display(self) -> None:
        self._display.setText(self._date.toString("d MMM yyyy"))
