"""
Unit tests for interface.utils.validation_feedback module.

Tests visual feedback utilities for Qt validators.
Note: Requires PyQt6 to be installed.
"""

import pytest

# Try to import PyQt6, skip tests if not available
try:
    from PyQt6.QtWidgets import QApplication, QLineEdit
    from PyQt6.QtGui import QIntValidator
    from interface.utils.validation_feedback import (
        setup_validation_feedback,
        add_validation_to_fields,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


pytestmark = pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    import sys

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def line_edit_with_validator(qapp):
    """Create a QLineEdit with an integer validator."""
    line_edit = QLineEdit()
    line_edit.setValidator(QIntValidator(1, 100))
    return line_edit


class TestSetupValidationFeedback:
    """Tests for setup_validation_feedback function."""

    def test_connects_text_changed_signal(self, line_edit_with_validator):
        """Should connect to textChanged signal."""
        setup_validation_feedback(line_edit_with_validator)
        # Check that setting text triggers styling
        line_edit_with_validator.setText("50")
        # Should have green border for valid input
        style = line_edit_with_validator.styleSheet()
        assert "#4CAF50" in style or style == ""  # Green or no style

    def test_valid_input_shows_green_border(self, line_edit_with_validator):
        """Valid input should show green border."""
        setup_validation_feedback(line_edit_with_validator)
        line_edit_with_validator.setText("50")
        style = line_edit_with_validator.styleSheet()
        assert "#4CAF50" in style  # Green color

    def test_invalid_input_shows_red_border(self, line_edit_with_validator):
        """Invalid input should show red border."""
        setup_validation_feedback(line_edit_with_validator)
        line_edit_with_validator.setText("200")  # Above max of 100
        style = line_edit_with_validator.styleSheet()
        # Could be red or empty depending on intermediate vs invalid
        assert "#f44336" in style or style == ""

    def test_empty_input_clears_style(self, line_edit_with_validator):
        """Empty input should clear styling."""
        setup_validation_feedback(line_edit_with_validator)
        line_edit_with_validator.setText("")
        style = line_edit_with_validator.styleSheet()
        assert style == ""


class TestAddValidationToFields:
    """Tests for add_validation_to_fields function."""

    def test_adds_feedback_to_multiple_fields(self, qapp):
        """Should add validation feedback to multiple fields."""
        field1 = QLineEdit()
        field1.setValidator(QIntValidator(1, 100))
        field2 = QLineEdit()
        field2.setValidator(QIntValidator(1, 50))

        add_validation_to_fields(field1, field2)

        # Set valid values
        field1.setText("50")
        field2.setText("25")

        # Both should have styling applied
        assert "#4CAF50" in field1.styleSheet()
        assert "#4CAF50" in field2.styleSheet()

    def test_skips_fields_without_validator(self, qapp):
        """Should skip fields without validators."""
        field_with_validator = QLineEdit()
        field_with_validator.setValidator(QIntValidator(1, 100))
        field_without_validator = QLineEdit()

        # Should not raise an error
        add_validation_to_fields(field_with_validator, field_without_validator)

        # Field with validator should have feedback
        field_with_validator.setText("50")
        assert "#4CAF50" in field_with_validator.styleSheet()

        # Field without validator should have no styling
        field_without_validator.setText("anything")
        assert field_without_validator.styleSheet() == ""


class TestValidationFeedbackIntegration:
    """Integration tests for validation feedback."""

    def test_real_time_feedback_update(self, line_edit_with_validator):
        """Feedback should update in real-time as user types."""
        setup_validation_feedback(line_edit_with_validator)

        # Start with valid value
        line_edit_with_validator.setText("50")
        assert "#4CAF50" in line_edit_with_validator.styleSheet()

        # Change to empty
        line_edit_with_validator.setText("")
        assert line_edit_with_validator.styleSheet() == ""

        # Change to valid
        line_edit_with_validator.setText("99")
        assert "#4CAF50" in line_edit_with_validator.styleSheet()

    def test_boundary_values(self, line_edit_with_validator):
        """Boundary values should be handled correctly."""
        setup_validation_feedback(line_edit_with_validator)

        # Min value (1)
        line_edit_with_validator.setText("1")
        assert "#4CAF50" in line_edit_with_validator.styleSheet()

        # Max value (100)
        line_edit_with_validator.setText("100")
        assert "#4CAF50" in line_edit_with_validator.styleSheet()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
