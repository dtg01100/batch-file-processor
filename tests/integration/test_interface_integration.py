"""
Integration Tests for Interface Module

These tests verify that components work together correctly.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEndToEndFolderManagement:
    """Test end-to-end folder management workflows."""

    @pytest.fixture
    def integrated_setup(self):
        """Create integrated components for testing."""
        # Mock database manager
        db = Mock()
        db.oversight_and_defaults = Mock()
        db.folders_table = Mock()
        db.emails_table = Mock()
        db.processed_files = Mock()
        db.settings = Mock()
        db.session_database = {}
        db.database_connection = Mock()

        # Setup default returns
        db.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "single_add_folder_prior": "/home",
            "batch_add_folder_prior": "/home",
        }

        return {"db_manager": db}

    def test_add_folder_workflow(self, integrated_setup):
        """Test complete add folder workflow."""
        from interface.operations.folder_operations import FolderOperations

        db = integrated_setup["db_manager"]
        db.folders_table.find_one.side_effect = [None, {"id": 1}]
        db.folders_table.insert.return_value = None

        ops = FolderOperations(db)
        folder_id = ops.add_folder("/test/folder")

        assert folder_id == 1
        db.folders_table.insert.assert_called_once()

    def test_edit_and_toggle_workflow(self, integrated_setup):
        """Test edit folder then toggle active workflow."""
        from interface.operations.folder_operations import FolderOperations

        db = integrated_setup["db_manager"]

        # First get folder
        db.folders_table.find_one.return_value = {
            "id": 1,
            "alias": "test",
            "folder_is_active": "True",
        }
        db.folders_table.update.return_value = None

        ops = FolderOperations(db)

        # Update folder
        folder = ops.get_folder(1)
        folder["alias"] = "updated"
        result = ops.update_folder(1, folder)
        assert result is True

        # Toggle active
        result = ops.set_folder_active(1, False)
        assert result is True

    def test_mark_as_processed_then_delete_workflow(self, integrated_setup):
        """Test mark files as processed then delete folder workflow."""
        from interface.operations.folder_operations import FolderOperations
        from interface.operations.maintenance import MaintenanceOperations

        db = integrated_setup["db_manager"]
        db.folders_table.find_one.return_value = {
            "id": 1,
            "alias": "test",
            "folder_name": "/test",
        }
        db.folders_table.delete.return_value = None
        db.processed_files.delete.return_value = None
        db.emails_table.delete.return_value = None

        with (
            patch("os.chdir"),
            patch("os.getcwd", return_value="/test"),
            patch("os.listdir", return_value=[]),
            patch("os.path.isfile", return_value=True),
        ):
            maint_ops = MaintenanceOperations(db)
            folder_ops = FolderOperations(db)

            # Mark as processed
            count = maint_ops.mark_all_as_processed(folder_id=1)

            # Delete folder
            result = folder_ops.delete_folder(1)
            assert result is True


class TestApplicationControllerIntegration:
    """Test ApplicationController integration with operations."""

    @pytest.fixture
    def controller_setup(self):
        """Setup controller with mock dependencies."""
        main_window = Mock()
        main_window._button_panel = Mock()
        main_window.refresh_folder_list = Mock()

        # Mock all signal connections
        for signal_name in [
            "process_directories_requested",
            "add_folder_requested",
            "batch_add_folders_requested",
            "edit_settings_requested",
            "maintenance_requested",
            "processed_files_requested",
            "exit_requested",
            "edit_folder_requested",
            "toggle_active_requested",
            "delete_folder_requested",
            "send_folder_requested",
        ]:
            signal = Mock()
            signal.connect = Mock()
            setattr(main_window, signal_name, signal)

        db = Mock()
        db.oversight_and_defaults = Mock()
        db.folders_table = Mock()
        db.emails_table = Mock()
        db.processed_files = Mock()
        db.settings = Mock()
        db.session_database = {}

        app = Mock()

        return {
            "main_window": main_window,
            "db_manager": db,
            "app": app,
            "database_path": "/tmp/test.db",
            "args": Mock(automatic=False),
            "version": "1.0.0",
        }

    def test_controller_wires_operations(self, controller_setup):
        """Test controller properly wires operations to UI."""
        with (
            patch("interface.application_controller.FolderOperations") as MockFolderOps,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            MockFolderOps.return_value.get_folder_count.return_value = 0

            from interface.application_controller import ApplicationController

            controller = ApplicationController(**controller_setup)

            main_window = controller_setup["main_window"]
            assert main_window.add_folder_requested.connect.called
            assert main_window.process_directories_requested.connect.called
            assert main_window.edit_folder_requested.connect.called


class TestDatabaseIntegration:
    """Test database operations integration."""

    def test_folder_operations_use_correct_tables(self):
        """Test FolderOperations uses correct database tables."""
        from interface.operations.folder_operations import FolderOperations

        db = Mock()
        db.oversight_and_defaults = Mock()
        db.folders_table = Mock()
        db.emails_table = Mock()
        db.processed_files = Mock()

        ops = FolderOperations(db)

        # Verify it has references to correct tables
        assert ops.db_manager == db

    def test_maintenance_operations_use_correct_tables(self):
        """Test MaintenanceOperations uses correct database tables."""
        from interface.operations.maintenance import MaintenanceOperations

        db = Mock()
        db.folders_table = Mock()
        db.processed_files = Mock()
        db.emails_table = Mock()
        db.database_connection = Mock()

        ops = MaintenanceOperations(db)

        # Verify it has reference to database
        assert ops.db_manager == db


class TestProcessingIntegration:
    """Test processing orchestrator integration."""

    def test_processing_orchestrator_init(self):
        """Test ProcessingOrchestrator can be initialized."""
        from interface.operations.processing import ProcessingOrchestrator

        db = Mock()
        db.settings = Mock()
        db.oversight_and_defaults = Mock()
        db.folders_table = Mock()
        db.emails_table = Mock()
        db.emails_table_batch = Mock()
        db.sent_emails_removal_queue = Mock()
        db.processed_files = Mock()
        db.database_connection = Mock()

        orchestrator = ProcessingOrchestrator(
            db_manager=db,
            database_path="/tmp/test.db",
            args=Mock(automatic=False),
            version="1.0.0",
        )

        assert orchestrator is not None
        assert orchestrator.db_manager == db
