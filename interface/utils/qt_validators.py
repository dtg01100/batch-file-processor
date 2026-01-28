"""
Qt validators module for interface.py refactoring.

This module provides centralized Qt validators for common input patterns,
replacing manual validation functions with Qt's built-in validation framework.

Usage:
    from interface.utils.qt_validators import PORT_VALIDATOR, EMAIL_VALIDATOR

    port_field = QLineEdit()
    port_field.setValidator(PORT_VALIDATOR)
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QIntValidator, QDoubleValidator, QRegularExpressionValidator


# === Integer Range Validators ===

PORT_VALIDATOR = QIntValidator(1, 65535)
"""Validator for network port numbers (1-65535)."""

POSITIVE_INT_VALIDATOR = QIntValidator(1, 999999)
"""Validator for positive integers."""

NON_NEGATIVE_INT_VALIDATOR = QIntValidator(0, 999999)
"""Validator for non-negative integers."""


# === Regular Expression Validators ===

EMAIL_VALIDATOR = QRegularExpressionValidator(
    QRegularExpression(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
)
"""Validator for email addresses."""

IP_ADDRESS_VALIDATOR = QRegularExpressionValidator(
    QRegularExpression(
        r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
)
"""Validator for IPv4 addresses."""

FTP_HOST_VALIDATOR = QRegularExpressionValidator(
    QRegularExpression(
        r"^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$|^(\d{1,3}\.){3}\d{1,3}$"
    )
)
"""Validator for FTP hostnames or IP addresses."""

HEX_COLOR_VALIDATOR = QRegularExpressionValidator(
    QRegularExpression(r"^#[0-9a-fA-F]{6}$")
)
"""Validator for hex color codes (#RRGGBB)."""


# === Double/Float Validators ===

POSITIVE_DOUBLE_VALIDATOR = QDoubleValidator(0.0, 999999.9999, 4)
"""Validator for positive floating point numbers (up to 4 decimal places)."""


def create_range_validator(minimum: int, maximum: int) -> QIntValidator:
    """Create a custom integer range validator.

    Args:
        minimum: Minimum allowed value
        maximum: Maximum allowed value

    Returns:
        QIntValidator configured for the specified range
    """
    return QIntValidator(minimum, maximum)


def create_regex_validator(pattern: str) -> QRegularExpressionValidator:
    """Create a custom regular expression validator.

    Args:
        pattern: Regular expression pattern string

    Returns:
        QRegularExpressionValidator configured with the pattern
    """
    return QRegularExpressionValidator(QRegularExpression(pattern))
