"""Shared card and section-label builder functions for epmcminer screens."""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

import epmcminer.gui.theme as theme


def make_card(padding: int = 22) -> tuple[QFrame, QVBoxLayout]:
    """Create a standard dark card frame with an inner layout.

    Args:
        padding: Uniform padding in pixels around the card's contents.

    Returns:
        A tuple of (QFrame with ``objectName='card'``, QVBoxLayout inside it).
    """
    frame = QFrame()
    frame.setObjectName("card")
    frame.setStyleSheet(theme.CARD_STYLE)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(14)
    return frame, layout


def make_section_label(text: str) -> QWidget:
    """Create an all-caps section header with a leading accent bar.

    Args:
        text: Label text; converted to uppercase with letter-spacing applied.

    Returns:
        A QWidget containing a 3 × 14 px accent bar and a styled QLabel.
    """
    row = QWidget()
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(10)

    bar = QFrame()
    bar.setFixedSize(3, 14)
    bar.setStyleSheet(
        f"background-color: {theme.ACCENT}; border-radius: 2px; border: none;"
    )
    row_layout.addWidget(bar)

    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {theme.TEXT_PRIMARY}; font-size: 11px;"
        f" letter-spacing: 1.6px; font-weight: 600;"
    )
    row_layout.addWidget(lbl)
    row_layout.addStretch()
    return row
