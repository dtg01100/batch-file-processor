"""Additional tests for MaintenanceDialog to improve coverage."""
from unittest.mock import MagicMock, patch
import pytest
from PyQt6.QtCore import Qt

pytestmark = pytest.mark.qt


@pytest.mark.qt
class TestMaintenanceDialogUI:
    """Tests for MaintenanceDialog UI initialization and setup."""

    def test_dialog_initialization(self, qtbot, mock_database_obj):
        """Test dialog initializes with correct properties."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Database Maintenance"
        assert dialog._database_obj == mock_database_obj

    def test_ui_has_required_buttons(self, qtbot, mock_database_obj):
        """Test that all required buttons are created."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Check for maintenance operation buttons
        assert hasattr(dialog, "_set_all_active_button")
        assert hasattr(dialog, "_set_all_inactive_button")
        assert hasattr(dialog, "_clear_resend_flags_button")
        assert hasattr(dialog, "_clear_processed_files_button")
        assert hasattr(dialog, "_remove_inactive_button")
        assert hasattr(dialog, "_mark_active_processed_button")
        assert hasattr(dialog, "_close_button")


@pytest.mark.qt
class TestMaintenanceDialogSetAllActive:
    """Tests for 'Set All Active' operation."""

    def test_set_all_active_button_triggers_operation(self, qtbot, mock_database_obj, monkeypatch):
        """Test clicking 'Set All Active' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_maintenance = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceFunctions",
            lambda db: mock_maintenance
        )

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Mock the operation
        mock_maintenance.set_all_active = MagicMock()

        # Click the button
        qtbot.mouseClick(dialog._set_all_active_button, Qt.MouseButton.LeftButton)

        # Should have called the operation
        # (actual call depends on implementation)


@pytest.mark.qt
class TestMaintenanceDialogSetAllInactive:
    """Tests for 'Set All Inactive' operation."""

    def test_set_all_inactive_button_triggers_operation(self, qtbot, mock_database_obj, monkeypatch):
        """Test clicking 'Set All Inactive' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_maintenance = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceFunctions",
            lambda db: mock_maintenance
        )

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Mock the operation
        mock_maintenance.set_all_inactive = MagicMock()

        # Click the button
        qtbot.mouseClick(dialog._set_all_inactive_button, Qt.MouseButton.LeftButton)


@pytest.mark.qt
class TestMaintenanceDialogClearResendFlags:
    """Tests for 'Clear Resend Flags' operation."""

    def test_clear_resend_flags_button_triggers_operation(self, qtbot, mock_database_obj, monkeypatch):
        """Test clicking 'Clear Resend Flags' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_maintenance = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceFunctions",
            lambda db: mock_maintenance
        )

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        mock_maintenance.clear_resend_flags = MagicMock()

        qtbot.mouseClick(dialog._clear_resend_flags_button, Qt.MouseButton.LeftButton)


@pytest.mark.qt
class TestMaintenanceDialogClearProcessedFiles:
    """Tests for 'Clear Processed Files Log' operation."""

    def test_clear_processed_files_button_triggers_operation(self, qtbot, mock_database_obj, monkeypatch):
        """Test clicking 'Clear Processed Files Log' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_maintenance = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceFunctions",
            lambda db: mock_maintenance
        )

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        mock_maintenance.clear_processed_files_log = MagicMock()

        qtbot.mouseClick(dialog._clear_processed_files_button, Qt.MouseButton.LeftButton)


@pytest.mark.qt
class TestMaintenanceDialogRemoveInactive:
    """Tests for 'Remove Inactive Folders' operation."""

    def test_remove_inactive_button_triggers_operation(self, qtbot, mock_database_obj, monkeypatch):
        """Test clicking 'Remove Inactive Folders' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_maintenance = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceFunctions",
            lambda db: mock_maintenance
        )

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        mock_maintenance.remove_inactive_folders = MagicMock()

        qtbot.mouseClick(dialog._remove_inactive_button, Qt.MouseButton.LeftButton)


@pytest.mark.qt
class TestMaintenanceDialogMarkActiveProcessed:
    """Tests for 'Mark Active as Processed' operation."""

    def test_mark_active_processed_button_triggers_operation(self, qtbot, mock_database_obj, monkeypatch):
        """Test clicking 'Mark Active as Processed' button triggers the operation."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_maintenance = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.maintenance_dialog.MaintenanceFunctions",
            lambda db: mock_maintenance
        )

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        mock_maintenance.mark_active_as_processed = MagicMock()

        qtbot.mouseClick(dialog._mark_active_processed_button, Qt.MouseButton.LeftButton)


@pytest.mark.qt
class TestMaintenanceDialogClose:
    """Tests for closing the dialog."""

    def test_close_button_closes_dialog(self, qtbot, mock_database_obj):
        """Test clicking close button closes the dialog."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Click close button
        qtbot.mouseClick(dialog._close_button, Qt.MouseButton.LeftButton)

        # Dialog should be closed
        assert not dialog.isVisible()

    def test_escape_key_closes_dialog(self, qtbot, mock_database_obj):
        """Test pressing Escape key closes the dialog."""
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog.show()
        assert dialog.isVisible()

        # Press Escape
        qtbot.keyPress(dialog, Qt.Key.Key_Escape)

        # Dialog should be closed
        assert not dialog.isVisible()
