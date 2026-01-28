"""
Tests for ApplicationController
"""

import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestApplicationControllerImport:
    """Test that ApplicationController can be imported."""

    def test_import(self):
        """Test ApplicationController can be imported."""
        from interface.application_controller import ApplicationController

        assert ApplicationController is not None


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db = Mock()
    db.oversight_and_defaults = Mock()
    db.folders_table = Mock()
    db.emails_table = Mock()
    db.processed_files = Mock()
    db.settings = Mock()
    db.session_database = {}
    return db


@pytest.fixture
def mock_main_window():
    """Create a mock main window."""
    window = Mock()
    window._button_panel = Mock()
    window.refresh_folder_list = Mock()

    # Mock signals
    window.process_directories_requested = Mock()
    window.add_folder_requested = Mock()
    window.batch_add_folders_requested = Mock()
    window.edit_settings_requested = Mock()
    window.maintenance_requested = Mock()
    window.processed_files_requested = Mock()
    window.exit_requested = Mock()
    window.edit_folder_requested = Mock()
    window.toggle_active_requested = Mock()
    window.delete_folder_requested = Mock()
    window.send_folder_requested = Mock()

    # Mock connect methods
    for attr in dir(window):
        if hasattr(getattr(window, attr), "connect"):
            getattr(window, attr).connect = Mock()

    return window


@pytest.fixture
def mock_app():
    """Create a mock application."""
    app = Mock()
    return app


@pytest.fixture
def controller_deps(mock_main_window, mock_db_manager, mock_app):
    """Create controller dependencies."""
    return {
        "main_window": mock_main_window,
        "db_manager": mock_db_manager,
        "app": mock_app,
        "database_path": "/tmp/test.db",
        "args": Mock(automatic=False),
        "version": "1.0.0",
    }


class TestApplicationControllerInit:
    """Test ApplicationController initialization."""

    def test_init_creates_operations(self, controller_deps):
        """Test that init creates operation objects."""
        with (
            patch(
                "interface.application_controller.FolderOperations"
            ) as mock_folder_ops,
            patch(
                "interface.application_controller.MaintenanceOperations"
            ) as mock_maint_ops,
            patch(
                "interface.application_controller.ProcessingOrchestrator"
            ) as mock_proc_orch,
        ):
            # Configure mock to return proper values
            mock_folder_ops.return_value.get_folder_count.return_value = 0

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)

            # Verify operations were created
            mock_folder_ops.assert_called_once_with(controller_deps["db_manager"])
            mock_maint_ops.assert_called_once_with(controller_deps["db_manager"])
            mock_proc_orch.assert_called_once()

    def test_init_connects_signals(self, controller_deps):
        """Test that init connects all signals."""
        with (
            patch(
                "interface.application_controller.FolderOperations"
            ) as mock_folder_ops,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops.return_value.get_folder_count.return_value = 0

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)

            # Verify signals were connected
            window = controller_deps["main_window"]
            window.process_directories_requested.connect.assert_called_once()
            window.add_folder_requested.connect.assert_called_once()
            window.batch_add_folders_requested.connect.assert_called_once()
            window.edit_settings_requested.connect.assert_called_once()
            window.maintenance_requested.connect.assert_called_once()
            window.processed_files_requested.connect.assert_called_once()
            window.exit_requested.connect.assert_called_once()
            window.edit_folder_requested.connect.assert_called_once()
            window.toggle_active_requested.connect.assert_called_once()
            window.delete_folder_requested.connect.assert_called_once()
            window.send_folder_requested.connect.assert_called_once()


class TestApplicationControllerFolderOperations:
    """Test folder operation handlers."""

    def test_handle_toggle_active_toggles_state(self, controller_deps):
        """Test toggle active changes folder state."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops = Mock()
            mock_folder_ops.get_folder_count.return_value = 0
            mock_folder_ops.get_folder.return_value = {
                "id": 1,
                "folder_is_active": "True",
            }
            mock_folder_ops.update_folder.return_value = True
            MockFolderOps.return_value = mock_folder_ops

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)
            controller._handle_toggle_active(1)

            # Should have toggled to False
            mock_folder_ops.get_folder.assert_called_with(1)
            mock_folder_ops.update_folder.assert_called_once()

            # Get the updated folder dict
            call_args = mock_folder_ops.update_folder.call_args
            updated_folder = call_args[0][1]
            assert updated_folder["folder_is_active"] == "False"

    def test_handle_delete_folder(self, controller_deps):
        """Test delete folder removes folder."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops = Mock()
            mock_folder_ops.get_folder_count.return_value = 0
            mock_folder_ops.delete_folder.return_value = True
            MockFolderOps.return_value = mock_folder_ops

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)
            controller._handle_delete_folder(1)

            mock_folder_ops.delete_folder.assert_called_once_with(1)
            controller_deps["main_window"].refresh_folder_list.assert_called_once()


class TestApplicationControllerButtonStates:
    """Test button state management."""

    def test_update_button_states_no_folders(self, controller_deps):
        """Test button states when no folders exist."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops = Mock()
            mock_folder_ops.get_folder_count.side_effect = [0, 0, 0, 0]
            MockFolderOps.return_value = mock_folder_ops

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)
            controller._update_button_states()

            # Process button should be disabled
            button_panel = controller_deps["main_window"]._button_panel
            button_panel.set_process_enabled.assert_called_with(
                enabled=False, has_active_folders=False
            )

    def test_update_button_states_with_active_folders(self, controller_deps):
        """Test button states when active folders exist."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops = Mock()
            mock_folder_ops.get_folder_count.side_effect = [5, 3, 5, 3]
            MockFolderOps.return_value = mock_folder_ops

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)
            controller._update_button_states()

            # Process button should be enabled
            button_panel = controller_deps["main_window"]._button_panel
            button_panel.set_process_enabled.assert_called_with(
                enabled=True, has_active_folders=True
            )


class TestApplicationControllerDialogs:
    """Test dialog operations."""

    @patch("interface.application_controller.QMessageBox")
    def test_handle_edit_folder_not_found(self, mock_qmsg, controller_deps):
        """Test edit folder when folder not found."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops = Mock()
            mock_folder_ops.get_folder_count.return_value = 0
            mock_folder_ops.get_folder.return_value = None
            MockFolderOps.return_value = mock_folder_ops

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)
            controller._handle_edit_folder(999)

            # Should show warning
            mock_qmsg.warning.assert_called_once()


class TestApplicationControllerProcessing:
    """Test processing operations."""

    @patch("interface.application_controller.QMessageBox")
    def test_handle_process_no_active_folders(self, mock_qmsg, controller_deps):
        """Test process directories with no active folders."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            mock_folder_ops = Mock()
            mock_folder_ops.get_folder_count.return_value = 0
            mock_folder_ops.get_active_folders.return_value = []
            MockFolderOps.return_value = mock_folder_ops

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_deps)
            controller._handle_process_directories()

            # Should show error
            mock_qmsg.critical.assert_called_once()
            assert "No Active Folders" in str(mock_qmsg.critical.call_args)
