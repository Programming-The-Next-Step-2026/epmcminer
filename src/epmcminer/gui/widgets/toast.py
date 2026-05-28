"""Reusable toast / snackbar overlay notification widget."""

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QPainter, QPaintEvent
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStyle,
    QStyleOption,
    QWidget,
)

import epmcminer.gui.theme as theme

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_FADE_MS: int = 200
"""Duration in milliseconds for each fade-in / fade-out animation."""

_HOLD_MS_SUCCESS: int = 10000
"""Duration in milliseconds the toast stays fully visible after a success."""

_HOLD_MS_ERROR: int = 10000
"""Duration in milliseconds the toast stays fully visible after an error."""

_MARGIN_BOTTOM: int = 96
"""Pixels above the bottom edge of the parent widget (clears the 72 px action bar)."""

# Elevated card background — clearly above APP_BG (#0b0b0d) and CARD_BG (#1c1c1f).
_TOAST_BG: str = "#252528"

# Vivid stripe colors used on the left/right border and the icon badge background.
_SUCCESS_STRIPE: str = "#22c55e"
_ERROR_STRIPE: str = "#ef4444"

# Icon badge: slightly deeper shade of the stripe color for visual depth.
_SUCCESS_BADGE_BG: str = "#16a34a"
_ERROR_BADGE_BG: str = "#dc2626"

# Dimensions for the colored icon badge (rounded-square label).
_BADGE_SIZE: int = 26
_BADGE_RADIUS: int = 7

# Stripe width on the left and right border edges.
_STRIPE_WIDTH: int = 5

# The top/bottom borders are omitted so the pill silhouette reads as side-bracketed
# by the stripe color.  A faint white opacity on top/bottom would also work but
# the clean edge looks better against the dark background.
_TOAST_STYLE_TMPL: str = """
    QWidget#toast {{
        background-color: {bg};
        border-left:  {sw}px solid {stripe};
        border-right: {sw}px solid {stripe};
        border-top:    0px;
        border-bottom: 0px;
        border-radius: 16px;
    }}
"""

_BADGE_STYLE_TMPL: str = (
    "background-color: {badge_bg};"
    f" border-radius: {_BADGE_RADIUS}px;"
    " color: #ffffff;"
    " font-size: 13px;"
    " font-weight: 700;"
)

_TEXT_STYLE: str = (
    f"color: {theme.TEXT_PRIMARY}; font-size: 14px; font-weight: 500;"
    " background: transparent;"
)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------


class Toast(QWidget):
    """A brief overlay notification that fades in, holds, then fades out.

    The toast must be a direct child of the widget it overlays.  It positions
    itself horizontally centred and ``_MARGIN_BOTTOM`` pixels above the bottom
    edge of its parent.  Calling :meth:`show_message` while a toast is already
    visible interrupts the current one and starts a fresh animation.

    Visual design: elevated dark pill (``_TOAST_BG``) with a vivid colored
    stripe on the left and right border edges, and a matching rounded-square
    icon badge on the left that holds a ✓ or ✗ in white.  The stripe color and
    badge color are green for success and red for errors.

    The widget is transparent to mouse events so it never blocks clicks on the
    content beneath it.

    Example::

        self._toast = Toast(self)
        self._toast.show_message("Saved to results.xlsx", success=True)
    """

    def __init__(self, parent: QWidget) -> None:
        """Initialise the toast widget.

        Args:
            parent: The parent widget this toast overlays.  Must not be None.
        """
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.setDuration(_FADE_MS)
        self._anim.finished.connect(self._on_anim_finished)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._start_fade_out)

        self._fading_out: bool = False

        self._build_ui()
        self.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_message(self, message: str, *, success: bool = True) -> None:
        """Display the toast with the given message.

        Interrupts any in-progress toast and starts a new fade-in sequence.

        Args:
            message: Text to display in the toast body.
            success: If ``True``, the toast uses green success styling and
                holds for ``_HOLD_MS_SUCCESS`` milliseconds.  If ``False``,
                red error styling is used and the hold extends to
                ``_HOLD_MS_ERROR`` milliseconds.
        """
        # Cancel any running animation / hold timer before starting fresh.
        self._hold_timer.stop()
        self._anim.stop()
        self._fading_out = False

        stripe = _SUCCESS_STRIPE if success else _ERROR_STRIPE
        badge_bg = _SUCCESS_BADGE_BG if success else _ERROR_BADGE_BG
        icon = "✓" if success else "✗"
        hold_ms = _HOLD_MS_SUCCESS if success else _HOLD_MS_ERROR

        self.setStyleSheet(
            _TOAST_STYLE_TMPL.format(bg=_TOAST_BG, stripe=stripe, sw=_STRIPE_WIDTH)
        )
        self._icon_lbl.setStyleSheet(_BADGE_STYLE_TMPL.format(badge_bg=badge_bg))
        self._icon_lbl.setText(icon)
        self._msg_lbl.setText(message)
        self._hold_timer.setInterval(hold_ms)

        self.adjustSize()
        self.reposition()
        self.raise_()
        self.show()

        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent | None) -> None:
        """Paint the stylesheet background explicitly.

        ``QGraphicsOpacityEffect`` renders the widget to an offscreen buffer
        and blends it back with reduced opacity.  Without this override the
        buffer is transparent because plain ``QWidget`` subclasses do not
        paint a background by default — the stylesheet ``background-color``
        rule is only honoured when the widget explicitly requests it via the
        style system.
        """
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)  # type: ignore[union-attr]

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(_BADGE_SIZE, _BADGE_SIZE)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_lbl)

        self._msg_lbl = QLabel()
        self._msg_lbl.setStyleSheet(_TEXT_STYLE)
        self._msg_lbl.setWordWrap(False)
        layout.addWidget(self._msg_lbl)

    def reposition(self) -> None:
        """Centre the toast horizontally above the bottom margin of its parent."""
        parent = self.parentWidget()
        if parent is None:
            return
        pw = parent.width()
        ph = parent.height()
        tw = self.width()
        th = self.height()
        x = (pw - tw) // 2
        y = ph - th - _MARGIN_BOTTOM
        self.move(x, y)

    def _start_fade_out(self) -> None:
        """Begin the fade-out animation."""
        self._fading_out = True
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        """Handle animation completion — either start the hold timer or hide."""
        if self._fading_out:
            self.hide()
            self._fading_out = False
        else:
            # Fade-in finished → start the hold timer.
            self._hold_timer.start()
