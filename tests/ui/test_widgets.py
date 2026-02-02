"""
Tests for UI Widgets (ButtonPanel, FolderListWidget)
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestButtonPanelImport:
    """Test ButtonPanel can be imported."""

    def test_import(self):
        """Test ButtonPanel can be imported."""
        from interface.ui.widgets.button_panel import ButtonPanel

        assert ButtonPanel is not None


class TestButtonPanelSignals:
    """Test ButtonPanel signal definitions."""

    @pytest.fixture
    def button_panel_class(self):
        """Get ButtonPanel class."""
        from interface.ui.widgets.button_panel import ButtonPanel

        return ButtonPanel

    def test_has_process_signal(self, button_panel_class):
        """Test ButtonPanel has process_clicked signal."""
        # Check class has signal attribute
        assert hasattr(button_panel_class, "process_clicked")

    def test_has_add_folder_signal(self, button_panel_class):
        """Test ButtonPanel has add_folder_clicked signal."""
        assert hasattr(button_panel_class, "add_folder_clicked")

    def test_has_batch_add_signal(self, button_panel_class):
        """Test ButtonPanel has batch_add_clicked signal."""
        assert hasattr(button_panel_class, "batch_add_clicked")

    def test_has_settings_signal(self, button_panel_class):
        """Test ButtonPanel has edit_settings_clicked signal."""
        assert hasattr(button_panel_class, "edit_settings_clicked")

    def test_has_maintenance_signal(self, button_panel_class):
        """Test ButtonPanel has maintenance_clicked signal."""
        assert hasattr(button_panel_class, "maintenance_clicked")

    def test_has_processed_files_signal(self, button_panel_class):
        """Test ButtonPanel has processed_files_clicked signal."""
        assert hasattr(button_panel_class, "processed_files_clicked")

    def test_has_set_defaults_signal(self, button_panel_class):
        """Test ButtonPanel has set_defaults_clicked signal."""
        assert hasattr(button_panel_class, "set_defaults_clicked")

    def test_has_enable_resend_signal(self, button_panel_class):
        """Test ButtonPanel has enable_resend_clicked signal."""
        assert hasattr(button_panel_class, "enable_resend_clicked")


class TestButtonPanelMethods:
    """Test ButtonPanel methods."""

    def test_has_set_button_enabled_method(self):
        """Test ButtonPanel has set_button_enabled method."""
        from interface.ui.widgets.button_panel import ButtonPanel

        assert hasattr(ButtonPanel, "set_button_enabled")
        assert callable(getattr(ButtonPanel, "set_button_enabled"))

    def test_has_set_process_enabled_method(self):
        """Test ButtonPanel has set_process_enabled method."""
        from interface.ui.widgets.button_panel import ButtonPanel

        assert hasattr(ButtonPanel, "set_process_enabled")
        assert callable(getattr(ButtonPanel, "set_process_enabled"))


class TestFolderListWidgetImport:
    """Test FolderListWidget can be imported."""

    def test_import(self):
        """Test FolderListWidget can be imported."""
        from interface.ui.widgets.folder_list import FolderListWidget

        assert FolderListWidget is not None


class TestFolderListWidgetSignals:
    """Test FolderListWidget signal definitions."""

    @pytest.fixture
    def folder_list_class(self):
        """Get FolderListWidget class."""
        from interface.ui.widgets.folder_list import FolderListWidget

        return FolderListWidget

    def test_has_edit_signal(self, folder_list_class):
        """Test has folder_edit_requested signal."""
        assert hasattr(folder_list_class, "folder_edit_requested")

    def test_has_toggle_signal(self, folder_list_class):
        """Test has folder_toggle_active signal."""
        assert hasattr(folder_list_class, "folder_toggle_active")

    def test_has_delete_signal(self, folder_list_class):
        """Test has folder_delete_requested signal."""
        assert hasattr(folder_list_class, "folder_delete_requested")

    def test_has_send_signal(self, folder_list_class):
        """Test has folder_send_requested signal."""
        assert hasattr(folder_list_class, "folder_send_requested")


class TestFolderListWidgetMethods:
    """Test FolderListWidget methods."""

    def test_has_refresh_method(self):
        """Test has refresh method."""
        from interface.ui.widgets.folder_list import FolderListWidget

        assert hasattr(FolderListWidget, "refresh")
        assert callable(getattr(FolderListWidget, "refresh"))

    def test_has_set_filter_method(self):
        """Test has set_filter method."""
        from interface.ui.widgets.folder_list import FolderListWidget

        assert hasattr(FolderListWidget, "set_filter")
        assert callable(getattr(FolderListWidget, "set_filter"))


class TestFolderListWidgetLogic:
    """Test FolderListWidget filtering logic."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db = Mock()
        db.folders_table = Mock()
        db.folders_table.find.return_value = [
            {"id": 1, "alias": "Test Folder 1", "folder_is_active": "True"},
            {"id": 2, "alias": "Test Folder 2", "folder_is_active": "False"},
            {"id": 3, "alias": "Another Folder", "folder_is_active": "True"},
        ]
        return db

    def test_load_folders_separates_active_inactive(self, mock_db_manager):
        """Test _load_folders separates active and inactive folders."""
        from interface.ui.widgets.folder_list import FolderListWidget

        # We can't instantiate without Qt, but we can test the logic separately
        # by creating a partial mock
        widget = Mock(spec=FolderListWidget)
        widget._db_manager = mock_db_manager

        # Call the actual method
        all_folders, active, inactive = FolderListWidget._load_folders(widget)

        assert len(all_folders) == 3
        assert len(active) == 2
        assert len(inactive) == 1
        assert active[0]["alias"] == "Test Folder 1"
        assert inactive[0]["alias"] == "Test Folder 2"
