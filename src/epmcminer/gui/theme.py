"""Shared design tokens and helpers for the epmcminer GUI.

Import this module as ``import epmcminer.gui.theme as theme`` in all GUI modules
to avoid duplicating colour constants and to enable lazy QStyle initialisation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QStyle

# Colour palette — single source of truth for all screen QSS.
# Qt rgba() uses 0-255 integer alpha; 0.07×255≈18, 0.16×255≈41, 0.04×255≈10.
APP_BG = "#0b0b0d"
TITLE_BAR_BG = "#111114"
CARD_BG = "#1c1c1f"
CARD_INNER = "#242427"
ACCENT = "#ff7a3d"
TEXT_PRIMARY = "#ededed"
TEXT_BODY = "#cfcfcf"
TEXT_MUTED = "#8a8a8d"
BORDER = "rgba(255, 255, 255, 18)"         # card borders
BORDER_STRONG = "rgba(255, 255, 255, 41)"  # button and menu borders
BORDER_FAINT = "rgba(255, 255, 255, 10)"   # title-bar border + dividers

CARD_STYLE = f"""
    QFrame#card {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 16px;
    }}
    QFrame#card QWidget {{
        background-color: {CARD_BG};
    }}
"""

# ACCENT rgb components for use in rgba() expressions (ACCENT = #ff7a3d = 255, 122, 61).
_A_R, _A_G, _A_B = 255, 122, 61

SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px 2px 2px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba({_A_R}, {_A_G}, {_A_B}, 70);
        border-radius: 4px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba({_A_R}, {_A_G}, {_A_B}, 150);
    }}
    QScrollBar::handle:vertical:pressed {{
        background: rgba({_A_R}, {_A_G}, {_A_B}, 210);
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0px 2px 2px 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba({_A_R}, {_A_G}, {_A_B}, 70);
        border-radius: 4px;
        min-width: 28px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba({_A_R}, {_A_G}, {_A_B}, 150);
    }}
    QScrollBar::handle:horizontal:pressed {{
        background: rgba({_A_R}, {_A_G}, {_A_B}, 210);
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
"""

# Minimum height for vertically-expanding list sections (results preview on Screen 2,
# live log on Screen 3, and skipped papers on Screen 4).  All three sections share
# this constant so resizing behaviour feels consistent across screens.  Raise it if
# the default window height changes significantly; keep it well below DEFAULT_HEIGHT
# minus the fixed chrome (action bar 72 px, cards ~200 px) so the section is useful
# at the minimum window size too.
EXPANDABLE_MIN_HEIGHT: int = 200

_fusion_style: QStyle | None = None


def get_fusion_style() -> QStyle | None:
    """Return the Fusion QStyle instance, creating it lazily on first call.

    The style is created on demand so this module is safe to import before
    a QApplication instance exists (e.g. in non-GUI tests or at module load
    time).

    Returns:
        The Fusion QStyle, or ``None`` if the style is unavailable.
    """
    global _fusion_style
    if _fusion_style is None:
        from PyQt6.QtWidgets import QStyleFactory

        _fusion_style = QStyleFactory.create("Fusion")
    return _fusion_style
