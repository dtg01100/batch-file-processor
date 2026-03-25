"""Additional tests for MaintenanceDialog to improve coverage."""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel

from interface.qt.theme import Theme

pytestmark = pytest.mark.qt


def luminance(color: QColor) -> float:
    """Calculate relative luminance of a color. Based on WCAG 2.0."""
    r = color.red() / 255.0
    g = color.green() / 255.0
    b = color.blue() / 255.0
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: QColor, bg: QColor) -> float:
    """Calculate WCAG contrast ratio between two colors (1-21)."""
    l1 = luminance(fg)
    l2 = luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.qt
class TestMaintenanceDialogUI:
    """Tests for MaintenanceDialog UI initialization and setup."""

    def test_dialog_initialization(self, qtbot, mock_maintenance_functions):
        """Test dialog initializes with correct properties."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Maintenance Functions"
        assert dialog._mf is mock_maintenance_functions

    def test_ui_has_required_buttons(self, qtbot, mock_maintenance_functions):
        """Test that all required buttons are created."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Check that buttons list exists and has the expected number of buttons
        assert hasattr(dialog, "_buttons")
        assert len(dialog._buttons) == 8  # 8 maintenance operation buttons


@pytest.mark.qt
class TestMaintenanceDialogSetAllActive:
    """Tests for 'Set All Active' operation."""

    def test_set_all_active_button_triggers_operation(
        self, qtbot, mock_maintenance_functions
    ):
        """Test clicking 'Set All Active' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Click the first button (Set All Active)
        qtbot.mouseClick(dialog._buttons[0], Qt.MouseButton.LeftButton)

        # Should have called the operation
        assert mock_maintenance_functions.was_called("set_all_active")


@pytest.mark.qt
class TestMaintenanceDialogSetAllInactive:
    """Tests for 'Set All Inactive' operation."""

    def test_set_all_inactive_button_triggers_operation(
        self, qtbot, mock_maintenance_functions
    ):
        """Test clicking 'Set All Inactive' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Click the second button (Set All Inactive)
        qtbot.mouseClick(dialog._buttons[1], Qt.MouseButton.LeftButton)

        assert mock_maintenance_functions.was_called("set_all_inactive")


@pytest.mark.qt
class TestMaintenanceDialogClearResendFlags:
    """Tests for 'Clear Resend Flags' operation."""

    def test_clear_resend_flags_button_triggers_operation(
        self, qtbot, mock_maintenance_functions
    ):
        """Test clicking 'Clear Resend Flags' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Click the third button (Clear Resend Flags)
        qtbot.mouseClick(dialog._buttons[2], Qt.MouseButton.LeftButton)

        assert mock_maintenance_functions.was_called("clear_resend_flags")


@pytest.mark.qt
class TestMaintenanceDialogClearProcessedFiles:
    """Tests for 'Clear Processed Files Log' operation."""

    def test_clear_processed_files_button_triggers_operation(
        self, qtbot, mock_maintenance_functions
    ):
        """Test clicking 'Clear Processed Files Log' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Click the "Clear sent file records" button (index 6)
        qtbot.mouseClick(dialog._buttons[6], Qt.MouseButton.LeftButton)

        assert mock_maintenance_functions.was_called("clear_processed_files_log")


@pytest.mark.qt
class TestMaintenanceDialogRemoveInactive:
    """Tests for 'Remove Inactive Folders' operation."""

    def test_remove_inactive_button_triggers_operation(
        self, qtbot, mock_maintenance_functions
    ):
        """Test clicking 'Remove Inactive Folders' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Click the "Remove all inactive configurations" button (index 5)
        qtbot.mouseClick(dialog._buttons[5], Qt.MouseButton.LeftButton)

        assert mock_maintenance_functions.was_called("remove_inactive_folders")


@pytest.mark.qt
class TestMaintenanceDialogMarkActiveProcessed:
    """Tests for 'Mark Active as Processed' operation."""

    def test_mark_active_processed_button_triggers_operation(
        self, qtbot, mock_maintenance_functions
    ):
        """Test clicking 'Mark Active as Processed' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        # Click the "Mark all in active as processed" button (index 4)
        qtbot.mouseClick(dialog._buttons[4], Qt.MouseButton.LeftButton)

        assert mock_maintenance_functions.was_called("mark_active_as_processed")


@pytest.mark.qt
class TestMaintenanceDialogClose:
    """Tests for closing the dialog."""

    def test_escape_key_closes_dialog(self, qtbot, mock_maintenance_functions):
        """Test pressing Escape key closes the dialog."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

        dialog.show()
        assert dialog.isVisible()

        # Press Escape
        qtbot.keyPress(dialog, Qt.Key.Key_Escape)

        # Dialog should be closed
        assert not dialog.isVisible()


@pytest.mark.qt
class TestMaintenanceDialogContrast:
    """Contrast tests for MaintenanceDialog."""

    def test_warning_label_contrast(self, qtbot, mock_maintenance_functions):
        """Test that the warning label has sufficient contrast."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog.show()

        warning_labels = [
            lbl for lbl in dialog.findChildren(QLabel) if "WARNING" in lbl.text()
        ]
        assert warning_labels, "Warning label not found"

        fg_color = QColor(Theme.ERROR)
        bg_color = QColor(Theme.BACKGROUND)
        ratio = contrast_ratio(fg_color, bg_color)

        assert ratio >= 4.5, (
            f"Warning label contrast {ratio:.2f}:1 is below WCAG AA 4.5:1 "
            f"(text={Theme.ERROR}, bg={Theme.BACKGROUND})"
        )

    def test_button_text_contrast(self, qtbot, mock_maintenance_functions):
        """Test that dialog buttons have sufficient contrast."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog.show()

        for btn in dialog._buttons:
            fg_color = QColor(Theme.TEXT_PRIMARY)
            bg_color = QColor(Theme.INPUT_BACKGROUND)
            ratio = contrast_ratio(fg_color, bg_color)

            assert ratio >= 4.5, (
                f"Button '{btn.text()}' contrast {ratio:.2f}:1 is below WCAG AA 4.5:1 "
                f"(text={Theme.TEXT_PRIMARY}, bg={Theme.INPUT_BACKGROUND})"
            )
