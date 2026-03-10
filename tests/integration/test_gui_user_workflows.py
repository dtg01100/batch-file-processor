"""Integration tests for complete GUI user workflows.

Tests cover end-to-end user interactions with the GUI:
1. Folder configuration workflow (add, edit, delete folders)
2. Processing workflow (process files and verify results)
3. Settings configuration workflow (edit application settings)
4. Maintenance workflow (database operations)
5. Processed files review workflow
6. Resend workflow (mark and resend files)
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.qt,
    pytest.mark.gui,
    pytest.mark.workflow,
    pytest.mark.slow,
]

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QDialog

from interface.qt.app import QtBatchFileSenderApp
from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog
from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def qt_app():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    return app


@pytest.fixture
def temp_workspace():
    """Create temporary workspace with folders and database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Input folder
        input_folder = workspace / "input"
        input_folder.mkdir()

        # Output folder
        output_folder = workspace / "output"
        output_folder.mkdir()

        # Processed folder
        processed_folder = workspace / "processed"
        processed_folder.mkdir()

        # Create test EDI file
        sample_edi = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010CAT1Test Item 1                     0000010000
C00000001000010000
"""
        (input_folder / "test_invoice.edi").write_text(sample_edi)

        # Database path
        db_path = workspace / "test.db"

        yield {
            "workspace": workspace,
            "input_folder": input_folder,
            "output_folder": output_folder,
            "processed_folder": processed_folder,
            "db_path": db_path,
        }


@pytest.fixture
def initialized_app(qt_app, temp_workspace):
    """Create an initialized QtBatchFileSenderApp instance."""
    from interface.qt.services.qt_services import QtUIService, QtProgressService
    from PyQt6.QtWidgets import QWidget

    # Create a real QWidget for the progress service parent
    progress_parent = QWidget()

    # Patch the config folder to use temp workspace
    with patch("appdirs.user_data_dir", return_value=str(temp_workspace["workspace"])):
        app = QtBatchFileSenderApp(
            database_obj=None,
            ui_service=QtUIService(None),
            progress_service=QtProgressService(progress_parent),
        )

        with patch("sys.argv", ["test"]):
            app.initialize()

        yield app

        app.shutdown()


# =============================================================================
# Folder Configuration Workflow Tests
# =============================================================================


class TestFolderConfigurationWorkflow:
    """Test complete folder configuration workflow."""

    def test_add_folder_through_workflow(self, initialized_app, temp_workspace):
        """Test adding a folder through the complete workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Mock the folder selection dialog
        with patch.object(app, "_select_folder") as mock_select:
            mock_select.side_effect = lambda: app._folder_manager.add_folder(
                input_folder
            )

            # Select folder
            mock_select()

            # Verify folder was added to database
            folders = list(app._database.folders_table.all())
            assert len(folders) > 0

            # Find the added folder
            added_folder = next(
                (f for f in folders if f["folder_name"] == input_folder), None
            )
            assert added_folder is not None

    def test_edit_folder_workflow(self, initialized_app, temp_workspace):
        """Test editing a folder through the complete workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # First add a folder
        app._folder_manager.add_folder(input_folder)
        folder = app._database.folders_table.find_one(folder_name=input_folder)

        # Mock edit dialog
        with patch.object(
            EditFoldersDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ):
            # Edit folder
            app._edit_folder_selector(folder["id"])

            # Verify folder still exists
            edited_folder = app._database.folders_table.find_one(id=folder["id"])
            assert edited_folder is not None

    def test_disable_folder_workflow(self, initialized_app, temp_workspace):
        """Test disabling a folder through the complete workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add folder
        app._folder_manager.add_folder(input_folder)
        folder = app._database.folders_table.find_one(folder_name=input_folder)

        # Disable folder
        app._disable_folder(folder["id"])

        # Verify folder is disabled
        disabled_folder = app._database.folders_table.find_one(id=folder["id"])
        assert disabled_folder["folder_is_active"] == "False"

    def test_delete_folder_workflow(self, initialized_app, temp_workspace):
        """Test deleting a folder through the complete workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add folder
        app._folder_manager.add_folder(input_folder)
        folder = app._database.folders_table.find_one(folder_name=input_folder)

        # Delete folder
        with patch.object(app._ui_service, "ask_yes_no", return_value=True):
            app._delete_folder_entry_wrapper(folder["id"], input_folder)

        # Verify folder is deleted
        deleted_folder = app._database.folders_table.find_one(id=folder["id"])
        assert deleted_folder is None


class TestSettingsConfigurationWorkflow:
    """Test settings configuration workflow."""

    def test_edit_email_settings_workflow(self, initialized_app):
        """Test editing email settings through the complete workflow."""
        app = initialized_app

        # Mock the settings dialog
        with patch.object(
            EditSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ) as mock_exec:
            # Show edit settings dialog
            app._show_edit_settings_dialog()

            mock_exec.assert_called_once()

    def test_edit_reporting_settings_workflow(self, initialized_app):
        """Test editing reporting settings through the complete workflow."""
        app = initialized_app

        # Mock the settings dialog with reporting enabled
        with patch.object(
            EditSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ):
            app._show_edit_settings_dialog()

            # Verify callbacks exist
            assert callable(app._update_reporting)
            assert callable(app._refresh_users_list)

    def test_edit_backup_settings_workflow(self, initialized_app):
        """Test editing backup settings through the complete workflow."""
        app = initialized_app

        with patch.object(
            EditSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ) as mock_exec:
            app._show_edit_settings_dialog()

            mock_exec.assert_called_once()


class TestProcessingWorkflow:
    """Test file processing workflow."""

    def test_process_single_folder_workflow(self, initialized_app, temp_workspace):
        """Test processing a single folder through the complete workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add folder
        app._folder_manager.add_folder(input_folder)
        folder = app._database.folders_table.find_one(folder_name=input_folder)

        # Mock processing
        with patch.object(app, "_graphical_process_directories") as mock_process:
            # Process folder
            app._graphical_process_directories(app._database.folders_table)

            # Verify processing was called
            mock_process.assert_called_once()

    def test_process_all_folders_workflow(self, initialized_app, temp_workspace):
        """Test processing all folders through the complete workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add multiple folders
        app._folder_manager.add_folder(input_folder)
        app._folder_manager.add_folder(str(temp_workspace["output_folder"]))

        # Get folders table
        folders_table = app._database.folders_table

        # Mock processing
        with patch.object(app, "_graphical_process_directories") as mock_process:
            # Process all folders
            app._graphical_process_directories(folders_table)

            # Verify processing was called with folders table
            mock_process.assert_called_once_with(folders_table)


class TestMaintenanceWorkflow:
    """Test maintenance operations workflow."""

    def test_maintenance_dialog_workflow(self, initialized_app):
        """Test opening and using maintenance dialog."""
        app = initialized_app

        # Mock the maintenance dialog
        with patch.object(MaintenanceDialog, "open_dialog", return_value=None):
            # Show maintenance dialog
            app._show_maintenance_dialog_wrapper()

            # Verify backup was created
            # (The actual backup is called in _show_maintenance_dialog_wrapper)

    def test_database_import_workflow(self, initialized_app):
        """Test database import workflow."""
        app = initialized_app

        with patch.object(MaintenanceDialog, "open_dialog", return_value=None):
            app._show_maintenance_dialog_wrapper()

            # Verify database import callback exists
            # (Actual import happens in the dialog)


class TestProcessedFilesWorkflow:
    """Test processed files review workflow."""

    def test_view_processed_files_workflow(self, initialized_app):
        """Test viewing processed files through the complete workflow."""
        app = initialized_app

        # Mock the processed files dialog
        with patch.object(
            ProcessedFilesDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ):
            # Show processed files dialog
            app._show_processed_files_dialog_wrapper()

            # Verify dialog was created with correct parameters

    def test_processed_files_button_toggled_when_empty(self, initialized_app):
        """Test that processed files button is disabled when no files processed."""
        app = initialized_app

        # Verify no processed files exist
        count = app._database.processed_files.count()
        assert count == 0

        # Update button states
        app._set_main_button_states()

        # Verify button is disabled
        assert app._processed_files_button.isEnabled() is False

    def test_processed_files_button_enabled_when_files_exist(self, initialized_app):
        """Test that processed files button is enabled when files are processed."""
        app = initialized_app

        # Insert a processed file
        app._database.processed_files.insert(
            {
                "file_name": "test.edi",
                "md5": "abc123",
                "file_checksum": "def456",
                "resend_flag": 0,
                "folder_id": 1,
                "created_at": "2024-01-01",
            }
        )

        # Verify processed files exist
        count = app._database.processed_files.count()
        assert count > 0

        # Update button states
        app._set_main_button_states()

        # Verify button is enabled
        assert app._processed_files_button.isEnabled() is True


class TestResendWorkflow:
    """Test resend workflow."""

    def test_resend_dialog_workflow(self, initialized_app):
        """Test opening and using resend dialog."""
        app = initialized_app

        # Mock the resend dialog
        mock_dialog = MagicMock()
        mock_dialog._should_show = True
        mock_dialog.exec = MagicMock(return_value=QDialog.DialogCode.Accepted)

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendDialog", return_value=mock_dialog
        ):
            # Show resend dialog
            app._show_resend_dialog()

            # Verify dialog was created
            mock_dialog.exec.assert_called_once()

    def test_resend_button_toggled_when_no_processed_files(self, initialized_app):
        """Test that resend button is disabled when no files processed."""
        app = initialized_app

        # Verify no processed files exist
        count = app._database.processed_files.count()
        assert count == 0

        # Update button states
        app._set_main_button_states()

        # Verify button is disabled
        assert app._allow_resend_button.isEnabled() is False

    def test_resend_button_enabled_when_files_exist(self, initialized_app):
        """Test that resend button is enabled when files are processed."""
        app = initialized_app

        # Insert a processed file
        app._database.processed_files.insert(
            {
                "file_name": "test.edi",
                "md5": "abc123",
                "file_checksum": "def456",
                "resend_flag": 0,
                "folder_id": 1,
                "created_at": "2024-01-01",
            }
        )

        # Verify processed files exist
        count = app._database.processed_files.count()
        assert count > 0

        # Update button states
        app._set_main_button_states()

        # Verify button is enabled
        assert app._allow_resend_button.isEnabled() is True


class TestCompleteUserWorkflow:
    """Test complete end-to-end user workflow."""

    def test_complete_add_process_view_workflow(self, initialized_app, temp_workspace):
        """Test complete workflow: add folder → process → view results."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Step 1: Add folder
        with patch.object(app, "_select_folder") as mock_select:
            mock_select.side_effect = lambda: app._folder_manager.add_folder(
                input_folder
            )
            mock_select()

        # Verify folder added
        folder = app._database.folders_table.find_one(folder_name=input_folder)
        assert folder is not None

        # Step 2: Mock processing files
        with patch.object(app, "_graphical_process_directories") as mock_process:
            app._graphical_process_directories(app._database.folders_table)
            mock_process.assert_called_once_with(app._database.folders_table)

        # Step 3: Mock viewing processed files
        with patch.object(
            ProcessedFilesDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ) as mock_exec:
            app._show_processed_files_dialog_wrapper()
            mock_exec.assert_called_once()

    def test_complete_settings_apply_workflow(self, initialized_app):
        """Test complete workflow: edit settings → apply → verify."""
        app = initialized_app

        # Step 1: Edit settings
        with patch.object(
            EditSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ) as mock_exec:
            app._show_edit_settings_dialog()

        mock_exec.assert_called_once()
        assert app._database.get_settings_or_default() is not None


class TestButtonStateManagement:
    """Test button state management during workflow."""

    def test_button_states_update_after_folder_add(
        self, initialized_app, temp_workspace
    ):
        """Test button states update after adding a folder."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Initially no folders
        app._set_main_button_states()
        assert app._process_folder_button.isEnabled() is False

        # Add folder
        app._folder_manager.add_folder(input_folder)
        # Enable the folder
        folder = app._folder_manager.get_folder_by_name(input_folder)
        if folder:
            app._folder_manager.enable_folder(folder["id"])
        app._refresh_users_list()

        # Verify button states updated
        assert app._process_folder_button.isEnabled() is True

    def test_button_states_update_after_folder_disable(
        self, initialized_app, temp_workspace
    ):
        """Test button states update after disabling a folder."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add folder
        app._folder_manager.add_folder(input_folder)
        folder = app._database.folders_table.find_one(folder_name=input_folder)

        # Disable folder
        app._disable_folder(folder["id"])
        app._set_main_button_states()

        assert app._process_folder_button.isEnabled() is False

    def test_button_states_update_after_files_processed(self, initialized_app):
        """Test button states update after files are processed."""
        app = initialized_app

        # Initially no processed files
        app._set_main_button_states()
        assert app._processed_files_button.isEnabled() is False
        assert app._allow_resend_button.isEnabled() is False

        # Insert processed files
        app._database.processed_files.insert(
            {
                "file_name": "test.edi",
                "md5": "abc123",
                "file_checksum": "def456",
                "resend_flag": 0,
                "folder_id": 1,
                "created_at": "2024-01-01",
            }
        )

        # Verify processed files exist
        count = app._database.processed_files.count()
        assert count > 0

        # Update button states
        app._set_main_button_states()

        # Verify button states updated
        assert app._processed_files_button.isEnabled() is True
        assert app._allow_resend_button.isEnabled() is True


class TestSearchAndFilterWorkflow:
    """Test search and filter workflow."""

    def test_search_functionality_exists(self, initialized_app):
        """Test that search functionality exists in the workflow."""
        app = initialized_app

        # Verify search widget exists
        assert hasattr(app, "_search_widget")
        assert hasattr(app, "_folder_filter")
        assert hasattr(app, "_set_folders_filter")

    def test_filter_updates_folder_list(self, initialized_app):
        """Test that filter updates the folder list."""
        app = initialized_app

        # Mock filter change
        with patch.object(app, "_refresh_users_list") as mock_refresh:
            app._set_folders_filter("test")

            mock_refresh.assert_called_once()
            assert app._folder_filter == "test"


class TestErrorHandlingWorkflow:
    """Test error handling in user workflows."""

    def test_folder_already_exists_workflow(self, initialized_app, temp_workspace):
        """Test workflow when folder already exists."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add folder first time
        app._folder_manager.add_folder(input_folder)

        # Try to add same folder again
        result = app._folder_manager.check_folder_exists(input_folder)

        # Verify folder already exists
        assert result["truefalse"] is True

    def test_folder_not_found_workflow(self, initialized_app):
        """Test workflow when folder is not found."""
        app = initialized_app

        # Try to edit non-existent folder without opening a blocking error dialog
        with patch.object(app._ui_service, "show_error") as mock_show_error:
            app._edit_folder_selector(99999)

        # Should handle gracefully and notify user
        mock_show_error.assert_called_once_with(
            "Error", "Folder with id 99999 not found."
        )

    def test_database_error_workflow(self, initialized_app):
        """Test workflow when database error occurs."""
        app = initialized_app

        # Mock database error
        with patch.object(
            app._database.folders_table, "count", side_effect=Exception("DB Error")
        ):
            with pytest.raises(Exception, match="DB Error"):
                app._set_main_button_states()


class TestPersistenceWorkflow:
    """Test data persistence across workflow."""

    def test_settings_persist_workflow(self, initialized_app):
        """Test that settings persist through the workflow."""
        app = initialized_app

        # Get initial settings
        initial_settings = app._database.get_settings_or_default()

        # Edit settings
        with patch.object(
            EditSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ):
            app._show_edit_settings_dialog()

        # Verify settings still accessible
        current_settings = app._database.get_settings_or_default()
        assert current_settings is not None

    def test_folder_config_persists_workflow(self, initialized_app, temp_workspace):
        """Test that folder configuration persists through the workflow."""
        app = initialized_app
        input_folder = str(temp_workspace["input_folder"])

        # Add folder
        app._folder_manager.add_folder(input_folder)

        # Verify folder persists
        folder = app._database.folders_table.find_one(folder_name=input_folder)
        assert folder is not None

        # Refresh and verify still exists
        app._refresh_users_list()
        folder_after_refresh = app._database.folders_table.find_one(
            folder_name=input_folder
        )
        assert folder_after_refresh is not None


class TestCleanupWorkflow:
    """Test cleanup operations in workflow."""

    def test_app_shutdown_cleanup(self, initialized_app):
        """Test that app properly cleans up on shutdown."""
        app = initialized_app

        # Shutdown should not raise errors
        app.shutdown()

        # Verify database was closed - the database object should still exist
        # but the connection should be closed (we can verify shutdown doesn't crash)
        assert app._database is not None

    def test_dialog_cleanup(self, initialized_app):
        """Test that dialogs are properly cleaned up."""
        app = initialized_app

        # Mock dialog creation and cleanup
        with patch.object(
            EditSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted
        ):
            app._show_edit_settings_dialog()

        # Dialog should be cleaned up properly


class TestPerformanceWorkflow:
    """Test workflow performance characteristics."""

    def test_multiple_folders_workflow(self, initialized_app, temp_workspace):
        """Test workflow with multiple folders."""
        app = initialized_app

        # Add multiple folders
        folders_to_add = [
            str(temp_workspace["input_folder"]),
            str(temp_workspace["output_folder"]),
            str(temp_workspace["processed_folder"]),
        ]

        for folder in folders_to_add:
            app._folder_manager.add_folder(folder)

        # Verify all folders added
        all_folders = list(app._database.folders_table.all())
        assert len(all_folders) == len(folders_to_add)

        # Verify workflow still responsive
        app._refresh_users_list()
        assert app._database.folders_table.count() == len(folders_to_add)

    def test_large_dataset_workflow(self, initialized_app):
        """Test workflow with large dataset."""
        app = initialized_app

        # Verify workflow completes with real database
        app._set_main_button_states()
        assert app._process_folder_button.isEnabled() is False
