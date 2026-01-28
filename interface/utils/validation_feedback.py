"""
Visual feedback utilities for Qt validators.

Provides helper functions to add visual feedback for input validation states,
such as colored borders for valid/invalid fields.

Usage:
    from interface.utils.validation_feedback import setup_validation_feedback

    field = QLineEdit()
    field.setValidator(EMAIL_VALIDATOR)
    setup_validation_feedback(field)
"""

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QValidator


def setup_validation_feedback(line_edit: QLineEdit) -> None:
    """Setup visual feedback for QLineEdit with validator.

    Connects to textChanged signal to update styling based on validation state.
    Shows:
    - Green border for acceptable input
    - Red border for invalid input
    - Default border for intermediate or empty input

    Args:
        line_edit: QLineEdit instance with a validator
    """

    def update_styling():
        text = line_edit.text()

        if not text:
            line_edit.setStyleSheet("")
            return

        if line_edit.hasAcceptableInput():
            line_edit.setStyleSheet("QLineEdit { border: 2px solid #4CAF50; }")
        else:
            validator = line_edit.validator()
            if validator:
                state, _, _ = validator.validate(text, 0)
                if state == QValidator.State.Invalid:
                    line_edit.setStyleSheet("QLineEdit { border: 2px solid #f44336; }")
                else:
                    line_edit.setStyleSheet("")

    line_edit.textChanged.connect(update_styling)
    update_styling()


def add_validation_to_fields(*fields: QLineEdit) -> None:
    """Add validation feedback to multiple QLineEdit fields.

    Args:
        *fields: Variable number of QLineEdit instances with validators
    """
    for field in fields:
        if field.validator() is not None:
            setup_validation_feedback(field)
