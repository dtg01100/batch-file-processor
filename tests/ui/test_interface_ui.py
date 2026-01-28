"""
UI Interface Tests

Tests for the interface module to prevent regressions.
These tests verify that all UI components can be imported and initialized.
"""

import pytest
import os
import sys

# Add the project root to the path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class TestInterfaceImport:
    """Test that the interface module can be imported."""

    def test_interface_import(self):
        """Test that the interface module can be imported."""
        import interface

        assert interface is not None

    def test_interface_main_import(self):
        """Test that interface.main module can be imported."""
        from interface.main import main

        assert main is not None


class TestDatabaseManager:
    """Test that the database manager works correctly."""

    def test_database_manager_import(self):
        """Test that DatabaseManager can be imported."""
        from interface.database.database_manager import DatabaseManager

        assert DatabaseManager is not None

    def test_database_manager_has_init_signature(self):
        """Test DatabaseManager has the expected init signature."""
        from interface.database.database_manager import DatabaseManager
        import inspect

        sig = inspect.signature(DatabaseManager.__init__)
        params = list(sig.parameters.keys())
        # Should have: self, database_path, config_folder, platform, app_version, database_version
        assert "database_path" in params
        assert "config_folder" in params
        assert "platform" in params
        assert "app_version" in params
        assert "database_version" in params


class TestUIComponents:
    """Test that UI components can be imported."""

    def test_button_panel_import(self):
        """Test that ButtonPanel can be imported."""
        from interface.ui.widgets.button_panel import ButtonPanel

        assert ButtonPanel is not None

    def test_folder_list_import(self):
        """Test that FolderListWidget can be imported."""
        from interface.ui.widgets.folder_list import FolderListWidget

        assert FolderListWidget is not None


class TestDialogImports:
    """Test that dialog modules can be imported with correct class names."""

    def test_edit_folder_dialog_import(self):
        """Test that EditFolderDialog can be imported."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        assert EditFolderDialog is not None

    def test_edit_settings_dialog_import(self):
        """Test that EditSettingsDialog can be imported."""
        from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog

        assert EditSettingsDialog is not None

    def test_maintenance_dialog_import(self):
        """Test that MaintenanceDialog can be imported."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog

        assert MaintenanceDialog is not None

    def test_processed_files_dialog_import(self):
        """Test that ProcessedFilesDialog can be imported."""
        from interface.ui.dialogs.processed_files_dialog import ProcessedFilesDialog

        assert ProcessedFilesDialog is not None


class TestModels:
    """Test that data models can be imported."""

    def test_folder_model_import(self):
        """Test that Folder model can be imported."""
        from interface.models.folder import Folder

        assert Folder is not None

    def test_settings_model_import(self):
        """Test that Settings model can be imported."""
        from interface.models.settings import Settings

        assert Settings is not None

    def test_processed_file_model_import(self):
        """Test that ProcessedFile model can be imported."""
        from interface.models.processed_file import ProcessedFile

        assert ProcessedFile is not None


class TestOperations:
    """Test that operations modules can be imported."""

    def test_folder_operations_import(self):
        """Test that folder operations module can be imported."""
        from interface.operations.folder_operations import FolderOperations

        assert FolderOperations is not None

    def test_maintenance_operations_import(self):
        """Test that maintenance operations module can be imported."""
        from interface.operations.maintenance import MaintenanceOperations

        assert MaintenanceOperations is not None

    def test_processing_operations_import(self):
        """Test that ProcessingOrchestrator can be imported."""
        from interface.operations.processing import ProcessingOrchestrator

        assert ProcessingOrchestrator is not None


class TestUtilities:
    """Test that utility modules can be imported."""

    def test_validation_import(self):
        """Test that validation functions can be imported."""
        from interface.utils.validation import (
            validate_email,
            validate_folder_path,
            validate_ftp_host,
            validate_port,
        )

        assert validate_email is not None
        assert validate_folder_path is not None
        assert validate_ftp_host is not None
        assert validate_port is not None
