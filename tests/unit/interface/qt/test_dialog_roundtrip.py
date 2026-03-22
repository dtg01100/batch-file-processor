"""Tests for dialog lifecycle and roundtripping.

These tests verify that all dialogs can be opened, used, and closed
properly without crashes or resource leaks.
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import Mock

import pytest
from PyQt5.QtWidgets import QApplication

from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog
from interface.qt.dialogs.resend_dialog import ResendDialog


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DatabaseObj(
            database_path=db_path,
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=tmpdir,
            running_platform="Linux",
        )
        yield db
        db.close()


class TestDialogLifecycle:
    """Test dialog creation, opening, and closing."""

    def test_resend_dialog_with_no_processed_files(self, qapp, temp_db):
        """Test ResendDialog when no processed files exist."""
        from unittest.mock import patch

        # Mock QMessageBox to prevent GUI interaction during test
        with patch("PyQt5.QtWidgets.QMessageBox.information") as mock_msg_box:
            # ResendDialog should handle empty database gracefully
            dialog = ResendDialog(None, temp_db.database_connection)

            # Dialog should not crash during construction
            assert dialog is not None

            # _should_show flag should be False (nothing to show)
            assert dialog._should_show is False

            # Verify that the info message was shown
            mock_msg_box.assert_called_once()

        # Clean up
        dialog.close()
        dialog.deleteLater()

    def test_resend_dialog_with_processed_files(self, qapp, temp_db):
        """Test ResendDialog when processed files exist."""
        from unittest.mock import patch

        from interface.services.resend_service import ResendService

        # Add a folder and processed file
        temp_db.folders_table.insert(
            {
                "id": 1,
                "folder_name": "/test/path",
                "alias": "test_folder",
                "folder_is_active": "True",
            }
        )

        temp_db.processed_files.insert(
            {
                "folder_id": 1,
                "file_name": "test.txt",
                "file_checksum": "abc123",
                "resend_flag": False,
                "processed_at": datetime.now().isoformat(),
            }
        )

        # Mock get_folder_list to avoid .distinct() issues
        with patch.object(
            ResendService, "get_folder_list", return_value=[(1, "test_folder")]
        ):
            # Create dialog
            dialog = ResendDialog(None, temp_db.database_connection)

            # Dialog should be ready to show
            assert dialog._should_show is True
            assert dialog._service is not None

            # Clean up
            dialog.close()
            dialog.deleteLater()

    def test_processed_files_dialog_creation(self, qapp, temp_db):
        """Test ProcessedFilesDialog can be created."""
        from unittest.mock import patch

        # Mock _get_folder_tuples to avoid .distinct() issues
        with patch.object(ProcessedFilesDialog, "_get_folder_tuples", return_value=[]):
            dialog = ProcessedFilesDialog(
                parent=None, database_obj=temp_db, ui_service=None
            )

            assert dialog is not None
            assert dialog._database_obj is temp_db

            # Clean up
            dialog.close()
            dialog.deleteLater()

    def test_maintenance_dialog_creation(self, qapp, temp_db):
        """Test MaintenanceDialog can be created."""
        from interface.operations.maintenance_functions import MaintenanceFunctions

        # Create mock functions
        progress_callback = Mock()
        refresh_callback = Mock()
        set_button_states_callback = Mock()
        delete_folder_callback = Mock()

        maintenance = MaintenanceFunctions(
            database_obj=temp_db,
            refresh_callback=refresh_callback,
            set_button_states_callback=set_button_states_callback,
            delete_folder_callback=delete_folder_callback,
            database_path=temp_db._database_path,
            running_platform="Linux",
            database_version=CURRENT_DATABASE_VERSION,
            progress_callback=progress_callback,
        )

        dialog = MaintenanceDialog(
            parent=None, maintenance_functions=maintenance, ui_service=None
        )

        assert dialog is not None
        assert dialog._mf is maintenance

        # Clean up
        dialog.close()
        dialog.deleteLater()


class TestDatabaseInitialization:
    """Test database initialization and singleton records."""

    def test_database_creates_singleton_records(self):
        """Test that database automatically creates singleton records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseObj(
                database_path=db_path,
                database_version=CURRENT_DATABASE_VERSION,
                config_folder=tmpdir,
                running_platform="Linux",
            )

            # Settings singleton should exist
            settings = db.settings.find_one(id=1)
            assert settings is not None
            assert "enable_email" in settings

            # Oversight singleton should exist
            oversight = db.oversight_and_defaults.find_one(id=1)
            assert oversight is not None
            assert "logs_directory" in oversight

            db.close()

    def test_database_integrity_check(self):
        """Test database integrity verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseObj(
                database_path=db_path,
                database_version=CURRENT_DATABASE_VERSION,
                config_folder=tmpdir,
                running_platform="Linux",
            )

            # Database should be valid
            is_valid, errors = db.verify_database_integrity()
            assert is_valid, f"Database integrity check failed: {errors}"
            assert len(errors) == 0

            db.close()

    def test_get_settings_or_default_after_init(self):
        """Test safe accessor works after initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseObj(
                database_path=db_path,
                database_version=CURRENT_DATABASE_VERSION,
                config_folder=tmpdir,
                running_platform="Linux",
            )

            # Safe accessor should work
            settings = db.get_settings_or_default()
            assert settings is not None
            assert settings["id"] == 1

            oversight = db.get_oversight_or_default()
            assert oversight is not None
            assert oversight["id"] == 1

            db.close()

    def test_database_survives_singleton_deletion(self):
        """Test that safe accessors recreate deleted singleton records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db = DatabaseObj(
                database_path=db_path,
                database_version=CURRENT_DATABASE_VERSION,
                config_folder=tmpdir,
                running_platform="Linux",
            )

            # Delete settings
            db.settings.delete(id=1)

            # Safe accessor should recreate it
            settings = db.get_settings_or_default()
            assert settings is not None
            assert settings["id"] == 1

            # Delete oversight
            db.oversight_and_defaults.delete(id=1)

            # Safe accessor should recreate it
            oversight = db.get_oversight_or_default()
            assert oversight is not None
            assert oversight["id"] == 1

            db.close()


class TestDialogRoundtrip:
    """Test full roundtrip scenarios for dialogs."""

    def test_resend_dialog_full_cycle(self, qapp, temp_db):
        """Test complete ResendDialog open-use-close cycle."""
        from unittest.mock import patch

        from interface.services.resend_service import ResendService

        # Setup: Add folder and processed files
        temp_db.folders_table.insert(
            {
                "id": 1,
                "folder_name": "/test/path",
                "alias": "test_folder",
                "folder_is_active": "True",
            }
        )

        for i in range(5):
            temp_db.processed_files.insert(
                {
                    "folder_id": 1,
                    "file_name": f"test{i}.txt",
                    "file_checksum": f"abc{i}",
                    "resend_flag": False,
                    "processed_at": datetime.now().isoformat(),
                }
            )

        # Mock get_folder_list to avoid .distinct() issues
        with patch.object(
            ResendService, "get_folder_list", return_value=[(1, "test_folder")]
        ):
            # Open dialog
            dialog = ResendDialog(None, temp_db.database_connection)
            assert dialog._should_show is True

            # Close dialog
            dialog.close()
            dialog.deleteLater()

        # Verify database is still healthy
        is_valid, errors = temp_db.verify_database_integrity()
        assert is_valid, f"Database integrity check failed after dialog: {errors}"

    def test_multiple_dialogs_sequentially(self, qapp, temp_db):
        """Test opening multiple dialogs in sequence."""
        from unittest.mock import patch

        from interface.services.resend_service import ResendService

        # Add test data
        temp_db.folders_table.insert(
            {
                "id": 1,
                "folder_name": "/test/path",
                "alias": "test_folder",
                "folder_is_active": "True",
            }
        )

        temp_db.processed_files.insert(
            {
                "folder_id": 1,
                "file_name": "test.txt",
                "file_checksum": "abc123",
                "resend_flag": False,
                "processed_at": datetime.now().isoformat(),
            }
        )

        # Mock get_folder_list to avoid .distinct() issues
        with patch.object(
            ResendService, "get_folder_list", return_value=[(1, "test_folder")]
        ):
            # Mock _get_folder_tuples for ProcessedFilesDialog
            with patch.object(
                ProcessedFilesDialog, "_get_folder_tuples", return_value=[]
            ):
                # Open and close multiple dialogs
                for _ in range(3):
                    dialog1 = ResendDialog(None, temp_db.database_connection)
                    dialog1.close()
                    dialog1.deleteLater()

                    dialog2 = ProcessedFilesDialog(None, temp_db, None)
                    dialog2.close()
                    dialog2.deleteLater()

        # Database should still be healthy
        is_valid, errors = temp_db.verify_database_integrity()
        assert is_valid, f"Database integrity check failed: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
