"""Contrast testing utilities for Qt widgets.

Provides functions to test that UI elements have sufficient color contrast
for accessibility compliance.
"""

from typing import Tuple

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QWidget


def get_widget_colors(widget: QWidget, role: int) -> Tuple[QColor, QColor]:
    """Get the foreground and background colors for a widget.

    Args:
        widget: The widget to get colors from
        role: The palette role to check (e.g., QPalette.Text)

    Returns:
        Tuple of (foreground_color, background_color)
    """
    palette = widget.palette()
    fg = palette.color(role)
    bg = palette.color(QPalette.Base)
    return fg, bg


def luminance(color: QColor) -> float:
    """Calculate relative luminance of a color.

    Based on WCAG 2.0 formula.
    """
    r = color.red() / 255.0
    g = color.green() / 255.0
    b = color.blue() / 255.0

    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: QColor, bg: QColor) -> float:
    """Calculate WCAG contrast ratio between two colors.

    Returns:
        Contrast ratio (1-21). WCAG AA requires 4.5:1 for normal text.
    """
    l1 = luminance(fg)
    l2 = luminance(bg)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    return (lighter + 0.05) / (darker + 0.05)


def assert_contrast_ratio(
    widget: QWidget, role: int = None, min_ratio: float = 4.5, message: str = None
) -> None:
    """Assert that a widget has sufficient color contrast.

    Args:
        widget: The widget to test
        role: The palette role to check (defaults to QPalette.Text)
        min_ratio: Minimum contrast ratio (WCAG AA = 4.5, AAA = 7.0)
        message: Custom error message

    Raises:
        AssertionError: If contrast is insufficient
    """
    if role is None:
        role = QPalette.Text

    fg, bg = get_widget_colors(widget, role)
    ratio = contrast_ratio(fg, bg)

    if message is None:
        message = f"Contrast ratio {ratio:.2f}:1 is below minimum {min_ratio}:1 (fg={fg.name()}, bg={bg.name()})"

    assert ratio >= min_ratio, message
