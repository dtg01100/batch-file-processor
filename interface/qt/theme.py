"""Modern Material Design 3 inspired theme system for PyQt6 applications.

This theme system implements contemporary design principles including:
- Material Design 3 color palette with accessible colors
- Enhanced typography with proper visual hierarchy
- Smooth animations and transitions
- Card-based layouts with subtle shadows
- Improved focus states and accessibility
- Modern button and input styling
"""

import re
from pathlib import Path

from PyQt6.QtWidgets import QApplication


class Theme:
    # Material Design 3 Color Palette
    PRIMARY = "#6750A4"
    PRIMARY_CONTAINER = "#EADDFF"
    ON_PRIMARY = "#FFFFFF"
    ON_PRIMARY_CONTAINER = "#21005D"

    SECONDARY = "#625B71"
    SECONDARY_CONTAINER = "#E8DEF8"
    ON_SECONDARY = "#FFFFFF"
    ON_SECONDARY_CONTAINER = "#1D192B"

    TERTIARY = "#7D5260"
    TERTIARY_CONTAINER = "#FFD8E4"
    ON_TERTIARY = "#FFFFFF"
    ON_TERTIARY_CONTAINER = "#31111D"

    ERROR = "#B3261E"
    ERROR_CONTAINER = "#F9DEDC"
    ON_ERROR = "#FFFFFF"
    ON_ERROR_CONTAINER = "#410E0B"

    SUCCESS = "#386A20"
    SUCCESS_CONTAINER = "#C7F0B6"
    ON_SUCCESS = "#FFFFFF"
    ON_SUCCESS_CONTAINER = "#072100"

    WARNING = "#9C6500"
    WARNING_CONTAINER = "#FFDEA8"
    ON_WARNING = "#FFFFFF"
    ON_WARNING_CONTAINER = "#2E1D00"

    # Background Colors
    BACKGROUND = "#FFFBFE"
    ON_BACKGROUND = "#1C1B1F"
    SURFACE = "#FFFBFE"
    ON_SURFACE = "#1C1B1F"
    SURFACE_VARIANT = "#E7E0EC"
    ON_SURFACE_VARIANT = "#49454F"
    OUTLINE = "#79747E"
    OUTLINE_VARIANT = "#CAC4D0"

    # Sidebar Colors (Dark theme for sidebar)
    SIDEBAR_BACKGROUND = "#1C1B1F"
    SIDEBAR_SURFACE = "#2B2930"
    SIDEBAR_ON_SURFACE = "#E6E1E5"
    SIDEBAR_ON_SURFACE_VARIANT = "#CAC4D0"
    SIDEBAR_OUTLINE = "#49454F"

    # Card Colors
    CARD_BACKGROUND = "#FFFFFF"
    CARD_SURFACE = "#F3EDF7"
    CARD_BORDER = "#E8DEF8"
    CARD_SHADOW = "rgba(29, 27, 32, 0.08)"

    # Input Colors
    INPUT_BACKGROUND = "#F7F2FA"
    INPUT_BORDER = "#D9D2E9"
    INPUT_FOCUS_BORDER = "#6750A4"
    INPUT_HOVER_BORDER = "#E8DEF8"

    # Text Colors
    TEXT_PRIMARY = "#1C1B1F"
    TEXT_SECONDARY = "#49454F"
    TEXT_TERTIARY = "#605D62"
    TEXT_DISABLED = "#938F99"
    TEXT_ON_PRIMARY = "#FFFFFF"
    TEXT_ON_SIDEBAR = "#E6E1E5"
    TEXT_ON_SIDEBAR_HOVER = "#FFFFFF"
    TEXT_ON_OVERLAY = "#FFFFFF"
    TEXT_ON_OVERLAY_SECONDARY = "#CCCCCC"
    TEXT_ON_OVERLAY_TERTIARY = "#999999"

    # Border Colors
    BORDER = "#D9D2E9"
    BORDER_FOCUS = "#6750A4"
    BORDER_HOVER = "#C4B5E0"

    # Overlay Colors
    OVERLAY_BACKGROUND = "rgba(0, 0, 0, 230)"
    PROGRESS_BAR_BORDER = "#666666"
    PROGRESS_BAR_CHUNK = "#4CAF50"

    # Typography System
    FONT_FAMILY = '"Segoe UI", "SF Pro Display", -apple-system, BlinkMacSystemFont, Roboto, sans-serif'
    FONT_SIZE_XS = "11px"
    FONT_SIZE_SM = "12px"
    FONT_SIZE_BASE = "14px"
    FONT_SIZE_MD = "16px"
    FONT_SIZE_LG = "18px"
    FONT_SIZE_XL = "20px"
    FONT_SIZE_XXL = "24px"
    FONT_SIZE_TITLE = "28px"
    FONT_SIZE_DISPLAY = "32px"

    # Spacing System
    SPACING_XS = "2px"
    SPACING_SM = "4px"
    SPACING_MD = "6px"
    SPACING_LG = "8px"
    SPACING_XL = "10px"
    SPACING_XXL = "12px"
    SPACING_XXXL = "16px"
    SPACING_XXXXL = "20px"

    # Border Radius
    RADIUS_XS = "4px"
    RADIUS_SM = "8px"
    RADIUS_MD = "12px"
    RADIUS_LG = "16px"
    RADIUS_XL = "24px"
    RADIUS_XXL = "28px"
    RADIUS_FULL = "9999px"

    # Shadows
    SHADOW_SM = "0 1px 2px rgba(0, 0, 0, 0.05)"
    SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
    SHADOW_LG = (
        "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
    )
    SHADOW_XL = (
        "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
    )

    # Transitions
    TRANSITION_FAST = "150ms cubic-bezier(0.4, 0.0, 0.2, 1)"
    TRANSITION_BASE = "200ms cubic-bezier(0.4, 0.0, 0.2, 1)"
    TRANSITION_SLOW = "300ms cubic-bezier(0.4, 0.0, 0.2, 1)"

    # Spacing Integer Values (for Qt layout methods that require integers)
    SPACING_XS_INT = 2
    SPACING_SM_INT = 4
    SPACING_MD_INT = 6
    SPACING_LG_INT = 8
    SPACING_XL_INT = 10
    SPACING_XXL_INT = 12
    SPACING_XXXL_INT = 16
    SPACING_XXXXL_INT = 20

    @staticmethod
    def get_spacing_int(spacing_str: str) -> int:
        """Convert a spacing string (e.g., '16px') to integer value."""
        if isinstance(spacing_str, int):
            return spacing_str
        return int(spacing_str.replace("px", ""))

    @staticmethod
    def _asset_uri(filename: str) -> str:
        """Return an absolute path for a theme asset located under interface/qt/assets."""
        return str((Path(__file__).resolve().parent / "assets" / filename).resolve())

    @staticmethod
    def get_button_stylesheet(variant="default"):
        base = f"""
            QPushButton {{
                background-color: {Theme.INPUT_BACKGROUND};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius: {Theme.RADIUS_MD};
                padding: {Theme.SPACING_SM} {Theme.SPACING_XL};
                font-size: {Theme.FONT_SIZE_BASE};
                font-family: {Theme.FONT_FAMILY};
                font-weight: 500;
                min-height: 28px;
                min-width: 64px;
            }}
            QPushButton:hover {{
                background-color: {Theme.SURFACE_VARIANT};
                border-color: {Theme.BORDER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Theme.SURFACE_VARIANT};
                border-color: {Theme.PRIMARY};
            }}
            QPushButton:focus {{
                border: 2px solid {Theme.BORDER_FOCUS};
                padding: 3px 9px;
            }}
            QPushButton:disabled {{
                background-color: {Theme.INPUT_BACKGROUND};
                color: {Theme.TEXT_DISABLED};
                border-color: {Theme.OUTLINE_VARIANT};
            }}
        """
        # Variant-specific additions
        if variant == "primary":
            styles = f"""
                QPushButton {{
                    background-color: {Theme.PRIMARY};
                    color: {Theme.ON_PRIMARY};
                    border: none;
                    border-radius: {Theme.RADIUS_MD};
                    padding: {Theme.SPACING_SM} {Theme.SPACING_XL};
                    font-size: {Theme.FONT_SIZE_BASE};
                    font-family: {Theme.FONT_FAMILY};
                    font-weight: 500;
                    min-height: 28px;
                    min-width: 64px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.ON_PRIMARY_CONTAINER};
                    box-shadow: {Theme.SHADOW_MD};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.ON_PRIMARY_CONTAINER};
                    box-shadow: {Theme.SHADOW_SM};
                }}
                QPushButton:focus {{
                    border: 2px solid {Theme.ON_PRIMARY};
                    padding: 2px 8px;
                }}
                QPushButton:disabled {{
                    background-color: {Theme.OUTLINE_VARIANT};
                    color: {Theme.TEXT_DISABLED};
                }}
            """
        elif variant == "danger":
            styles = f"""
                QPushButton {{
                    background-color: {Theme.ERROR};
                    color: {Theme.ON_ERROR};
                    border: none;
                    border-radius: {Theme.RADIUS_MD};
                    padding: {Theme.SPACING_SM} {Theme.SPACING_XL};
                    font-size: {Theme.FONT_SIZE_BASE};
                    font-family: {Theme.FONT_FAMILY};
                    font-weight: 500;
                    min-height: 28px;
                    min-width: 64px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.ON_ERROR_CONTAINER};
                    box-shadow: {Theme.SHADOW_MD};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.ON_ERROR_CONTAINER};
                    box-shadow: {Theme.SHADOW_SM};
                }}
                QPushButton:focus {{
                    border: 2px solid {Theme.ON_ERROR};
                    padding: 2px 8px;
                }}
                QPushButton:disabled {{
                    background-color: {Theme.OUTLINE_VARIANT};
                    color: {Theme.TEXT_DISABLED};
                }}
            """
        elif variant == "success":
            styles = f"""
                QPushButton {{
                    background-color: {Theme.SUCCESS};
                    color: {Theme.ON_SUCCESS};
                    border: none;
                    border-radius: {Theme.RADIUS_MD};
                    padding: {Theme.SPACING_SM} {Theme.SPACING_XL};
                    font-size: {Theme.FONT_SIZE_BASE};
                    font-family: {Theme.FONT_FAMILY};
                    font-weight: 500;
                    min-height: 28px;
                    min-width: 64px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.ON_SUCCESS_CONTAINER};
                    box-shadow: {Theme.SHADOW_MD};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.ON_SUCCESS_CONTAINER};
                    box-shadow: {Theme.SHADOW_SM};
                }}
                QPushButton:focus {{
                    border: 2px solid {Theme.ON_SUCCESS};
                    padding: 2px 8px;
                }}
                QPushButton:disabled {{
                    background-color: {Theme.OUTLINE_VARIANT};
                    color: {Theme.TEXT_DISABLED};
                }}
            """
        elif variant == "sidebar":
            styles = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Theme.TEXT_ON_SIDEBAR};
                    border: none;
                    border-radius: {Theme.RADIUS_MD};
                    padding: {Theme.SPACING_SM} {Theme.SPACING_MD};
                    font-size: {Theme.FONT_SIZE_BASE};
                    font-family: {Theme.FONT_FAMILY};
                    font-weight: 400;
                    text-align: left;
                    min-height: 28px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.SIDEBAR_SURFACE};
                    color: {Theme.TEXT_ON_SIDEBAR_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.SIDEBAR_SURFACE};
                }}
                QPushButton:focus {{
                    background-color: {Theme.SIDEBAR_SURFACE};
                    border: 1px solid {Theme.SIDEBAR_OUTLINE};
                }}
                QPushButton:disabled {{
                    color: {Theme.SIDEBAR_ON_SURFACE_VARIANT};
                }}
            """
        elif variant == "text":
            styles = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Theme.PRIMARY};
                    border: none;
                    border-radius: {Theme.RADIUS_MD};
                    padding: {Theme.SPACING_SM} {Theme.SPACING_MD};
                    font-size: {Theme.FONT_SIZE_BASE};
                    font-family: {Theme.FONT_FAMILY};
                    font-weight: 500;
                    min-height: 28px;
                }}
                QPushButton:hover {{
                    background-color: {Theme.PRIMARY_CONTAINER};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.PRIMARY_CONTAINER};
                }}
                QPushButton:focus {{
                    border: 2px solid {Theme.BORDER_FOCUS};
                    padding: 2px 4px;
                }}
                QPushButton:disabled {{
                    color: {Theme.TEXT_DISABLED};
                }}
            """
        else:
            styles = base

        # Sanitize stylesheet to remove properties unsupported by Qt (e.g., box-shadow)
        return Theme._sanitize_stylesheet(styles)

    @staticmethod
    def get_input_stylesheet():
        styles = f"""
            QLineEdit, QTextEdit {{
                background-color: {Theme.INPUT_BACKGROUND};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.INPUT_BORDER};
                border-radius: {Theme.RADIUS_MD};
                padding: {Theme.SPACING_SM} {Theme.SPACING_MD};
                font-size: {Theme.FONT_SIZE_BASE};
                font-family: {Theme.FONT_FAMILY};
                selection-background-color: {Theme.PRIMARY_CONTAINER};
                selection-color: {Theme.ON_PRIMARY_CONTAINER};
            }}
            QLineEdit:hover, QTextEdit:hover {{
                border-color: {Theme.INPUT_HOVER_BORDER};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {Theme.INPUT_FOCUS_BORDER};
                padding: 3px 5px;
                background-color: {Theme.BACKGROUND};
            }}
            QLineEdit:disabled, QTextEdit:disabled {{
                background-color: {Theme.SURFACE_VARIANT};
                color: {Theme.TEXT_DISABLED};
                border-color: {Theme.OUTLINE_VARIANT};
            }}
        """
        return Theme._sanitize_stylesheet(styles)

    @classmethod
    def get_stylesheet(cls):
        raw = f"""
            * {{
                font-family: {cls.FONT_FAMILY};
                font-size: {cls.FONT_SIZE_BASE};
                color: {cls.TEXT_PRIMARY};
            }}

            /* Default Button */
            QPushButton {{
                background-color: {cls.INPUT_BACKGROUND};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_XL};
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 500;
                min-height: 28px;
                min-width: 64px;
            }}
            QPushButton:hover {{
                background-color: {cls.SURFACE_VARIANT};
                border-color: {cls.BORDER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {cls.SURFACE_VARIANT};
                border-color: {cls.PRIMARY};
            }}
            QPushButton:focus {{
                border: 2px solid {cls.BORDER_FOCUS};
                padding: 3px 9px;
            }}
            QPushButton:disabled {{
                background-color: {cls.INPUT_BACKGROUND};
                color: {cls.TEXT_DISABLED};
                border-color: {cls.OUTLINE_VARIANT};
            }}

            /* Primary Button */
            QPushButton[class="primary"] {{
                background-color: {cls.PRIMARY};
                color: {cls.ON_PRIMARY};
                border: none;
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_XL};
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 500;
                min-height: 28px;
                min-width: 64px;
            }}
            QPushButton[class="primary"]:hover {{
                background-color: {cls.ON_PRIMARY_CONTAINER};
                box-shadow: {cls.SHADOW_MD};
            }}
            QPushButton[class="primary"]:pressed {{
                background-color: {cls.ON_PRIMARY_CONTAINER};
                box-shadow: {cls.SHADOW_SM};
            }}
            QPushButton[class="primary"]:focus {{
                border: 2px solid {cls.ON_PRIMARY};
                padding: 2px 8px;
            }}
            QPushButton[class="primary"]:disabled {{
                background-color: {cls.OUTLINE_VARIANT};
                color: {cls.TEXT_DISABLED};
            }}

            /* Danger Button */
            QPushButton[class="danger"] {{
                background-color: {cls.ERROR};
                color: {cls.ON_ERROR};
                border: none;
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_XL};
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 500;
                min-height: 28px;
                min-width: 64px;
            }}
            QPushButton[class="danger"]:hover {{
                background-color: {cls.ON_ERROR_CONTAINER};
                box-shadow: {cls.SHADOW_MD};
            }}
            QPushButton[class="danger"]:pressed {{
                background-color: {cls.ON_ERROR_CONTAINER};
                box-shadow: {cls.SHADOW_SM};
            }}
            QPushButton[class="danger"]:focus {{
                border: 2px solid {cls.ON_ERROR};
                padding: 2px 8px;
            }}
            QPushButton[class="danger"]:disabled {{
                background-color: {cls.OUTLINE_VARIANT};
                color: {cls.TEXT_DISABLED};
            }}

            /* Success Button */
            QPushButton[class="success"] {{
                background-color: {cls.SUCCESS};
                color: {cls.ON_SUCCESS};
                border: none;
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_XL};
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 500;
                min-height: 28px;
                min-width: 64px;
            }}
            QPushButton[class="success"]:hover {{
                background-color: {cls.ON_SUCCESS_CONTAINER};
                box-shadow: {cls.SHADOW_MD};
            }}
            QPushButton[class="success"]:pressed {{
                background-color: {cls.ON_SUCCESS_CONTAINER};
                box-shadow: {cls.SHADOW_SM};
            }}
            QPushButton[class="success"]:focus {{
                border: 2px solid {cls.ON_SUCCESS};
                padding: 2px 8px;
            }}
            QPushButton[class="success"]:disabled {{
                background-color: {cls.OUTLINE_VARIANT};
                color: {cls.TEXT_DISABLED};
            }}

            /* Sidebar Button */
            QPushButton[class="sidebar"] {{
                background-color: transparent;
                color: {cls.TEXT_ON_SIDEBAR};
                border: none;
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 400;
                text-align: left;
                min-height: 28px;
            }}
            QPushButton[class="sidebar"]:hover {{
                background-color: {cls.SIDEBAR_SURFACE};
                color: {cls.TEXT_ON_SIDEBAR_HOVER};
            }}
            QPushButton[class="sidebar"]:pressed {{
                background-color: {cls.SIDEBAR_SURFACE};
            }}
            QPushButton[class="sidebar"]:focus {{
                background-color: {cls.SIDEBAR_SURFACE};
                border: 1px solid {cls.SIDEBAR_OUTLINE};
            }}
            QPushButton[class="sidebar"]:disabled {{
                color: {cls.SIDEBAR_ON_SURFACE_VARIANT};
            }}

            /* Text Button */
            QPushButton[class="text"] {{
                background-color: transparent;
                color: {cls.PRIMARY};
                border: none;
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                font-size: {cls.FONT_SIZE_BASE};
                font-weight: 500;
                min-height: 28px;
            }}
            QPushButton[class="text"]:hover {{
                background-color: {cls.PRIMARY_CONTAINER};
            }}
            QPushButton[class="text"]:pressed {{
                background-color: {cls.PRIMARY_CONTAINER};
            }}
            QPushButton[class="text"]:focus {{
                border: 2px solid {cls.BORDER_FOCUS};
                padding: 2px 4px;
            }}
            QPushButton[class="text"]:disabled {{
                color: {cls.TEXT_DISABLED};
            }}

            /* Line Edit */
            QLineEdit {{
                background-color: {cls.INPUT_BACKGROUND};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.INPUT_BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                selection-background-color: {cls.PRIMARY_CONTAINER};
                selection-color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QLineEdit:hover {{
                border-color: {cls.INPUT_HOVER_BORDER};
            }}
            QLineEdit:focus {{
                border: 2px solid {cls.INPUT_FOCUS_BORDER};
                padding: 3px 5px;
                background-color: {cls.BACKGROUND};
            }}
            QLineEdit:disabled {{
                background-color: {cls.SURFACE_VARIANT};
                color: {cls.TEXT_DISABLED};
                border-color: {cls.OUTLINE_VARIANT};
            }}

            /* Text Edit */
            QTextEdit {{
                background-color: {cls.INPUT_BACKGROUND};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.INPUT_BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM};
                selection-background-color: {cls.PRIMARY_CONTAINER};
                selection-color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QTextEdit:hover {{
                border-color: {cls.INPUT_HOVER_BORDER};
            }}
            QTextEdit:focus {{
                border: 2px solid {cls.INPUT_FOCUS_BORDER};
                padding: 3px;
                background-color: {cls.BACKGROUND};
            }}
            QTextEdit:disabled {{
                background-color: {cls.SURFACE_VARIANT};
                color: {cls.TEXT_DISABLED};
                border-color: {cls.OUTLINE_VARIANT};
            }}

            /* Combo Box */
            QComboBox {{
                background-color: {cls.INPUT_BACKGROUND};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.INPUT_BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                font-size: {cls.FONT_SIZE_BASE};
            }}
            QComboBox:hover {{
                border-color: {cls.INPUT_HOVER_BORDER};
            }}
            QComboBox:focus {{
                border: 2px solid {cls.INPUT_FOCUS_BORDER};
                padding: 3px 5px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 32px;
                padding-right: {cls.SPACING_SM};
            }}
            QComboBox::down-arrow {{
                image: url({cls._asset_uri("dropdown_arrow.svg")});
                width: 16px;
                height: 16px;
            }}
            QComboBox::down-arrow:disabled {{
                image: url({cls._asset_uri("dropdown_arrow_disabled.svg")});
            }}
            QComboBox QAbstractItemView {{
                background-color: {cls.BACKGROUND};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_XS};
                selection-background-color: {cls.PRIMARY_CONTAINER};
                color: {cls.TEXT_PRIMARY};
                selection-color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QComboBox::item:selected {{
                background-color: {cls.PRIMARY_CONTAINER};
                color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QComboBox::item:hover {{
                background-color: {cls.SURFACE_VARIANT};
            }}

            /* Check Box */
            QCheckBox {{
                color: {cls.TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                padding: 0;
                spacing: {cls.SPACING_SM};
                font-size: {cls.FONT_SIZE_BASE};
            }}
            QCheckBox:hover,
            QCheckBox:checked,
            QCheckBox:unchecked,
            QCheckBox:focus {{
                background-color: transparent;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {cls.OUTLINE};
                border-radius: {cls.RADIUS_XS};
                background-color: transparent;
                margin-right: {cls.SPACING_XS};
                image: none;
            }}
            QCheckBox::indicator:hover {{
                border-color: {cls.TEXT_SECONDARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.PRIMARY};
                border-color: {cls.PRIMARY};
                image: url({cls._asset_uri("checkbox_checked.svg")});
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {cls.PRIMARY};
                border-color: {cls.PRIMARY};
                image: url({cls._asset_uri("checkbox_checked.svg")});
            }}
            QCheckBox::indicator:unchecked {{
                background-color: transparent;
                border: 2px solid {cls.OUTLINE};
                image: none;
            }}
            QCheckBox:disabled {{
                color: {cls.TEXT_DISABLED};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {cls.SURFACE_VARIANT};
                border-color: {cls.OUTLINE_VARIANT};
                image: none;
            }}
            QCheckBox::indicator:disabled:checked {{
                background-color: {cls.SURFACE_VARIANT};
                border-color: {cls.OUTLINE_VARIANT};
                image: url({cls._asset_uri("checkbox_checked.svg")});
            }}

            /* Label */
            QLabel {{
                color: {cls.TEXT_PRIMARY};
                background-color: transparent;
                font-size: {cls.FONT_SIZE_BASE};
            }}
            QLabel[heading="true"] {{
                font-size: {cls.FONT_SIZE_TITLE};
                font-weight: 600;
                color: {cls.TEXT_PRIMARY};
            }}
            QLabel[subheading="true"] {{
                font-size: {cls.FONT_SIZE_LG};
                font-weight: 500;
                color: {cls.TEXT_PRIMARY};
            }}
            QLabel[secondary="true"] {{
                color: {cls.TEXT_SECONDARY};
            }}
            QLabel[tertiary="true"] {{
                color: {cls.TEXT_TERTIARY};
            }}

            /* Frame */
            QFrame {{
                background-color: transparent;
            }}
            QFrame[frame="card"] {{
                background-color: {cls.CARD_BACKGROUND};
                border: 1px solid {cls.CARD_BORDER};
                border-radius: {cls.RADIUS_LG};
                padding: {cls.SPACING_LG};
            }}
            QFrame#separator {{
                background-color: {cls.OUTLINE_VARIANT};
                border: none;
            }}

            /* Scroll Area */
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.OUTLINE_VARIANT};
                border-radius: 6px;
                min-height: 30px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.OUTLINE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background-color: transparent;
                height: 12px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {cls.OUTLINE_VARIANT};
                border-radius: 6px;
                min-width: 30px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {cls.OUTLINE};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}

            /* List Widget */
            QListWidget {{
                background-color: {cls.BACKGROUND};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_XS};
            }}
            QListWidget::item {{
                background-color: transparent;
                border-radius: {cls.RADIUS_SM};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                margin: 1px;
            }}
            QListWidget::item:selected {{
                background-color: {cls.PRIMARY_CONTAINER};
                color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {cls.SURFACE_VARIANT};
            }}

            /* Table Widget */
            QTableWidget {{
                background-color: {cls.BACKGROUND};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MD};
                gridline-color: {cls.BORDER};
                alternate-background-color: {cls.CARD_SURFACE};
            }}
            QTableWidget::item {{
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {cls.PRIMARY_CONTAINER};
                color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QTableWidget::item:hover:!selected {{
                background-color: {cls.SURFACE_VARIANT};
            }}
            QHeaderView::section {{
                background-color: {cls.CARD_SURFACE};
                color: {cls.TEXT_PRIMARY};
                border: none;
                border-bottom: 2px solid {cls.BORDER};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                font-weight: 600;
                text-align: left;
            }}

            /* Spin Box */
            QSpinBox, QDoubleSpinBox {{
                background-color: {cls.INPUT_BACKGROUND};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.INPUT_BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
            }}
            QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {cls.INPUT_HOVER_BORDER};
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {cls.INPUT_FOCUS_BORDER};
                padding: 3px 5px;
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                border-left: 1px solid {cls.BORDER};
                background-color: transparent;
                width: 24px;
                border-top-right-radius: {cls.RADIUS_SM};
                border-bottom-right-radius: {cls.RADIUS_SM};
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                border-left: 1px solid {cls.BORDER};
                background-color: transparent;
                width: 24px;
                border-top-right-radius: {cls.RADIUS_SM};
                border-bottom-right-radius: {cls.RADIUS_SM};
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {cls.SURFACE_VARIANT};
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                image: url({cls._asset_uri("spinbox_up.svg")});
                width: 12px;
                height: 8px;
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                image: url({cls._asset_uri("spinbox_down.svg")});
                width: 12px;
                height: 8px;
            }}
            QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
            QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
                width: 12px;
                height: 8px;
            }}
            QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{
                image: url({cls._asset_uri("spinbox_up_disabled.svg")});
            }}
            QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
                image: url({cls._asset_uri("spinbox_down_disabled.svg")});
            }}

            /* Dialog */
            QDialog {{
                background-color: {cls.BACKGROUND};
            }}

            /* Main Window */
            QMainWindow {{
                background-color: {cls.BACKGROUND};
            }}

            /* Progress Bar */
            QProgressBar {{
                background-color: {cls.SURFACE_VARIANT};
                border: none;
                border-radius: {cls.RADIUS_FULL};
                height: 6px;
                text-align: center;
                color: {cls.TEXT_SECONDARY};
            }}
            QProgressBar::chunk {{
                background-color: {cls.PRIMARY};
                border-radius: {cls.RADIUS_FULL};
            }}

            /* Tab Widget */
            QTabWidget::pane {{
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MD};
                background-color: {cls.BACKGROUND};
            }}
            QTabBar::tab {{
                background-color: {cls.CARD_SURFACE};
                color: {cls.TEXT_SECONDARY};
                border: 1px solid {cls.BORDER};
                border-bottom: none;
                border-top-left-radius: {cls.RADIUS_MD};
                border-top-right-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_SM} {cls.SPACING_XL};
                margin-right: 2px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{
                background-color: {cls.BACKGROUND};
                color: {cls.PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {cls.SURFACE_VARIANT};
            }}

            /* Group Box */
            QGroupBox {{
                background-color: transparent;
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_LG};
                margin-top: {cls.SPACING_LG};
                padding-top: {cls.SPACING_LG};
                font-weight: 500;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {cls.SPACING_MD};
                padding: 0 {cls.SPACING_SM};
                color: {cls.TEXT_PRIMARY};
                font-weight: 600;
            }}

            /* Menu */
            QMenu {{
                background-color: {cls.BACKGROUND};
                border: 1px solid {cls.BORDER};
                border-radius: {cls.RADIUS_MD};
                padding: {cls.SPACING_XS};
            }}
            QMenu::item {{
                background-color: transparent;
                border-radius: {cls.RADIUS_SM};
                padding: {cls.SPACING_SM} {cls.SPACING_XL};
                color: {cls.TEXT_PRIMARY};
            }}
            QMenu::item:selected {{
                background-color: {cls.PRIMARY_CONTAINER};
                color: {cls.ON_PRIMARY_CONTAINER};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {cls.OUTLINE_VARIANT};
                margin: {cls.SPACING_XS} 0;
            }}

            /* Tool Tip */
            QToolTip {{
                background-color: {cls.SIDEBAR_BACKGROUND};
                color: {cls.TEXT_ON_SIDEBAR};
                border: 1px solid {cls.SIDEBAR_OUTLINE};
                border-radius: {cls.RADIUS_SM};
                padding: {cls.SPACING_SM} {cls.SPACING_MD};
                font-size: {cls.FONT_SIZE_SM};
            }}
        """
        # Strip unsupported CSS properties before returning
        return cls._sanitize_stylesheet(raw)

    @staticmethod
    def apply_theme(widget):
        app = QApplication.instance()
        if app:
            # Apply a sanitized stylesheet to avoid Qt warnings about unsupported properties
            app.setStyleSheet(Theme.get_stylesheet())

    @staticmethod
    def _sanitize_stylesheet(css: str) -> str:
        """Remove or neutralize CSS properties unsupported by Qt stylesheets.

        Currently strips vendor-prefixed and standard `box-shadow` declarations which
        Qt's stylesheet parser does not recognize and causes console warnings.
        """
        if not isinstance(css, str):
            return css
        # Remove -webkit- and -moz- vendor prefixed and standard box-shadow declarations
        pattern = r"(?:-webkit-|-moz-)?box-shadow\s*:[^;]+;"
        return re.sub(pattern, "", css, flags=re.IGNORECASE)
