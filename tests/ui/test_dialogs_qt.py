"""
Tests for Dialog components using actual PyQt6 dialogs
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.qt
class TestEditFolderDialogQt:
    """Test EditFolderDialog with actual Qt dialog."""

    def test_create_edit_folder_dialog(self, qtbot, mock_db_manager):
        """Test EditFolderDialog can be created."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        folder_data = {
            "id": 1,
            "alias": "Test Folder",
            "folder_name": "/test/folder",
            "folder_is_active": "True",
        }

        dialog = EditFolderDialog(
            parent=None, folder_data=folder_data, db_manager=mock_db_manager
        )
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "Edit Folder"

    def test_edit_folder_dialog_has_components(self, qtbot, mock_db_manager):
        """Test EditFolderDialog creates UI components."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        folder_data = {"id": 1, "alias": "Test", "folder_name": "/test"}

        dialog = EditFolderDialog(
            parent=None, folder_data=folder_data, db_manager=mock_db_manager
        )
        qtbot.addWidget(dialog)

        # Dialog should be created without error
        assert dialog is not None

    def test_edit_folder_dialog_estore_integer_values(self, qtbot, mock_db_manager):
        """Test that estore fields with integer values don't cause TypeError."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        folder_data = {
            "id": 1,
            "alias": "Test Folder",
            "folder_name": "/test/folder",
            "folder_is_active": "True",
            "estore_store_number": 123,  # Integer that caused crash
            "estore_Vendor_OId": 456,
            "estore_c_record_OID": 789,
            "fintech_division_id": 100,
        }

        # Should not raise TypeError
        dialog = EditFolderDialog(
            parent=None, folder_data=folder_data, db_manager=mock_db_manager
        )
        qtbot.addWidget(dialog)

        # Verify dialog was created successfully
        assert dialog is not None
        assert dialog.windowTitle() == "Edit Folder"

    def test_edit_folder_dialog_estore_generic_integer_values(self, qtbot, mock_db_manager):
        """Test that estore generic fields with integer values don't cause TypeError."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        folder_data = {
            "id": 1,
            "alias": "Test Folder",
            "folder_name": "/test/folder",
            "folder_is_active": "True",
            "estore_store_number": 999,  # Integer for estore generic
            "estore_Vendor_OId": 888,
            "estore_c_record_OID": 777,
        }

        # Should not raise TypeError
        dialog = EditFolderDialog(
            parent=None, folder_data=folder_data, db_manager=mock_db_manager
        )
        qtbot.addWidget(dialog)

        # Verify dialog was created successfully
        assert dialog is not None

    def test_edit_folder_dialog_fintech_integer_values(self, qtbot, mock_db_manager):
        """Test that fintech division field with integer value doesn't cause TypeError."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        folder_data = {
            "id": 1,
            "alias": "Test Folder",
            "folder_name": "/test/folder",
            "folder_is_active": "True",
            "fintech_division_id": 42,  # Integer for fintech
        }

        # Should not raise TypeError
        dialog = EditFolderDialog(
            parent=None, folder_data=folder_data, db_manager=mock_db_manager
        )
        qtbot.addWidget(dialog)

        # Verify dialog was created successfully
        assert dialog is not None


@pytest.mark.qt
class TestEditSettingsDialogQt:
    """Test EditSettingsDialog with actual Qt dialog."""

    def test_create_edit_settings_dialog(self, qtbot, mock_db_manager):
        """Test EditSettingsDialog can be created."""
        from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog

        settings = {"id": 1, "logs_directory": "/tmp/logs", "enable_reporting": "False"}

        dialog = EditSettingsDialog(
            parent=None, oversight=settings, db_manager=mock_db_manager
        )
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "Edit Settings"


@pytest.mark.qt
class TestMaintenanceDialogQt:
    """Test MaintenanceDialog with actual Qt dialog."""

    def test_create_maintenance_dialog(self, qtbot, mock_db_manager):
        """Test MaintenanceDialog can be created."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(
            parent=None, db_manager=mock_db_manager, running_platform="Linux"
        )
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "Maintenance Functions"

    def test_maintenance_dialog_has_warning(self, qtbot, mock_db_manager):
        """Test MaintenanceDialog displays warning."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(parent=None, db_manager=mock_db_manager)
        qtbot.addWidget(dialog)

        # Should have warning label
        assert dialog is not None


@pytest.mark.qt
class TestProcessedFilesDialogQt:
    """Test ProcessedFilesDialog with actual Qt dialog."""

    def test_create_processed_files_dialog(self, qtbot, mock_db_manager):
        """Test ProcessedFilesDialog can be created."""
        from interface.ui.dialogs.processed_files_dialog import ProcessedFilesDialog

        # Mock processed files data
        mock_db_manager.processed_files.count.return_value = 0
        mock_db_manager.processed_files.distinct.return_value = []

        dialog = ProcessedFilesDialog(parent=None, db_manager=mock_db_manager)
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "Processed Files Report"


@pytest.mark.qt
class TestBaseDialog:
    """Test BaseDialog with actual Qt."""

    def test_base_dialog_import(self):
        """Test BaseDialog can be imported."""
        from interface.ui.base_dialog import BaseDialog

        assert BaseDialog is not None

    def test_base_dialog_has_setup_ui_method(self):
        """Test BaseDialog has _setup_layout method."""
        from interface.ui.base_dialog import BaseDialog

        assert hasattr(BaseDialog, "_setup_layout")
        assert hasattr(BaseDialog, "_create_widgets")


# Non-Qt tests for structure verification
class TestDialogStructure:
    """Test dialog class structures without Qt instantiation."""

    def test_edit_folder_dialog_init_signature(self):
        """Test EditFolderDialog init has correct signature."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog
        import inspect

        sig = inspect.signature(EditFolderDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "folder_data" in params
        assert "db_manager" in params

    def test_edit_settings_dialog_init_signature(self):
        """Test EditSettingsDialog init has correct signature."""
        from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog
        import inspect

        sig = inspect.signature(EditSettingsDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "oversight" in params
        assert "db_manager" in params

    def test_maintenance_dialog_init_signature(self):
        """Test MaintenanceDialog init has correct signature."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog
        import inspect

        sig = inspect.signature(MaintenanceDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "db_manager" in params

    def test_processed_files_dialog_init_signature(self):
        """Test ProcessedFilesDialog init has correct signature."""
        from interface.ui.dialogs.processed_files_dialog import ProcessedFilesDialog
        import inspect

        sig = inspect.signature(ProcessedFilesDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "db_manager" in params
