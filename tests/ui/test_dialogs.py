"""
Tests for Dialog components
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEditFolderDialog:
    """Test EditFolderDialog."""

    def test_import(self):
        """Test EditFolderDialog can be imported."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog

        assert EditFolderDialog is not None

    def test_init_signature(self):
        """Test EditFolderDialog init has correct signature."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog
        import inspect

        sig = inspect.signature(EditFolderDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "folder_data" in params
        assert "db_manager" in params
        assert "settings" in params


class TestEditSettingsDialog:
    """Test EditSettingsDialog."""

    def test_import(self):
        """Test EditSettingsDialog can be imported."""
        from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog

        assert EditSettingsDialog is not None

    def test_init_signature(self):
        """Test EditSettingsDialog init has correct signature."""
        from interface.ui.dialogs.edit_settings_dialog import EditSettingsDialog
        import inspect

        sig = inspect.signature(EditSettingsDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "settings" in params
        assert "oversight" in params
        assert "db_manager" in params


class TestMaintenanceDialog:
    """Test MaintenanceDialog."""

    def test_import(self):
        """Test MaintenanceDialog can be imported."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog

        assert MaintenanceDialog is not None

    def test_init_signature(self):
        """Test MaintenanceDialog init has correct signature."""
        from interface.ui.dialogs.maintenance_dialog import MaintenanceDialog
        import inspect

        sig = inspect.signature(MaintenanceDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "db_manager" in params
        assert "running_platform" in params


class TestProcessedFilesDialog:
    """Test ProcessedFilesDialog."""

    def test_import(self):
        """Test ProcessedFilesDialog can be imported."""
        from interface.ui.dialogs.processed_files_dialog import ProcessedFilesDialog

        assert ProcessedFilesDialog is not None

    def test_init_signature(self):
        """Test ProcessedFilesDialog init has correct signature."""
        from interface.ui.dialogs.processed_files_dialog import ProcessedFilesDialog
        import inspect

        sig = inspect.signature(ProcessedFilesDialog.__init__)
        params = list(sig.parameters.keys())

        assert "parent" in params
        assert "db_manager" in params


class TestBaseDialog:
    """Test BaseDialog."""

    def test_import(self):
        """Test BaseDialog can be imported."""
        from interface.ui.base_dialog import BaseDialog

        assert BaseDialog is not None

    def test_has_setup_ui_method(self):
        """Test BaseDialog has _setup_layout method."""
        from interface.ui.base_dialog import BaseDialog

        assert hasattr(BaseDialog, "_setup_layout")
        assert hasattr(BaseDialog, "_create_widgets")
