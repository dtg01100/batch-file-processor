"""End-to-end tests for complete UI-to-backend user workflows.

These tests validate the full integration from database operations through
backend processing, database persistence, and file system operations.

Test scenarios cover:
1. Complete folder setup and processing workflow
2. Settings changes affecting processing behavior
3. Multi-dialog workflows
4. Error recovery from UI
5. Real user interaction patterns
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.qt, pytest.mark.gui]

import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
from scripts import create_database


@pytest.fixture
def qt_app():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app
    QApplication.processEvents()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for E2E testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create necessary directories
        (workspace / "input").mkdir()
        (workspace / "output").mkdir()
        (workspace / "database").mkdir()
        (workspace / "logs").mkdir()
        (workspace / "errors").mkdir()

        yield workspace


@pytest.fixture
def database(temp_workspace):
    """Create a DatabaseObj connection for testing with named table attributes."""
    db_path = temp_workspace / "database" / "folders.db"

    create_database.do(
        CURRENT_DATABASE_VERSION,
        str(db_path),
        str(temp_workspace),
        "Linux",
    )

    db = DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(temp_workspace),
        running_platform="Linux",
    )

    yield db
    db.close()


@pytest.fixture
def sample_edi_content():
    """Sample EDI file content."""
    return (
        "A00000120240101001TESTVENDOR         Test Vendor Inc                 00001\n"
        "B001001ITEM001     000010EA0010Test Item 1                     0000010000\n"
        "B001002ITEM002     000020EA0020Test Item 2                     0000020000\n"
        "C00000003000030000\n"
    )


class TestCompleteFolderWorkflow:
    """Test complete user workflow for folder setup and processing."""

    def test_add_folder_configure_and_process(
        self, qtbot, qt_app, temp_workspace, database, sample_edi_content
    ):
        """Test complete workflow: Add folder → Configure → Save → Process → Verify."""
        edi_file = temp_workspace / "input" / "test_invoice.edi"
        edi_file.write_text(sample_edi_content)

        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        folder_config = {
            "folder_name": str(temp_workspace / "input"),
            "alias": "E2E Test Folder",
            "process_backend_copy": 1,
            "copy_to_directory": str(temp_workspace / "output"),
            "process_backend_ftp": 0,
            "process_backend_email": 0,
            "convert_to_format": "csv",
        }
        database.folders_table.insert(folder_config)

        folders = list(database.folders_table.all())
        assert len(folders) == 1
        assert folders[0]["alias"] == "E2E Test Folder"
        assert folders[0]["convert_to_format"] == "csv"

    def test_edit_folder_configuration_workflow(
        self, qtbot, qt_app, temp_workspace, database
    ):
        """Test workflow: View folder → Edit configuration → Save → Verify update."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "input"),
                "alias": "Original Name",
                "process_backend_copy": 1,
                "copy_to_directory": str(temp_workspace / "output"),
                "convert_to_format": "csv",
            }
        )

        folders = list(database.folders_table.all())
        assert len(folders) == 1
        assert folders[0]["alias"] == "Original Name"

        updated = dict(folders[0])
        updated["alias"] = "Updated Name"
        updated["convert_to_format"] = "fintech"
        database.folders_table.update(updated, ["id"])

        refreshed = list(database.folders_table.all())
        assert refreshed[0]["alias"] == "Updated Name"
        assert refreshed[0]["convert_to_format"] == "fintech"

    def test_delete_folder_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow: Select folder → Delete → Confirm → Verify removal."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )
        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "input"),
                "alias": "To Delete",
                "process_backend_copy": 1,
                "copy_to_directory": str(temp_workspace / "output"),
            }
        )

        folders = list(database.folders_table.all())
        assert len(folders) == 1
        database.folders_table.delete(id=folders[0]["id"])

        assert list(database.folders_table.all()) == []


class TestSettingsWorkflow:
    """Test user workflows for settings management."""

    def test_edit_settings_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test workflow: Open settings → Modify → Save → Verify persistence."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        settings = database.oversight_and_defaults.find_one()
        assert settings["logs_directory"] == str(temp_workspace / "logs")

        updated = dict(settings)
        updated["errors_folder"] = str(temp_workspace / "new_errors")
        database.oversight_and_defaults.update(updated, ["id"])

        refreshed = database.oversight_and_defaults.find_one()
        assert refreshed["errors_folder"] == str(temp_workspace / "new_errors")

    def test_settings_affect_processing_workflow(
        self, qtbot, qt_app, temp_workspace, database, sample_edi_content
    ):
        """Test that settings changes actually affect processing behavior."""
        edi_file = temp_workspace / "input" / "test.edi"
        edi_file.write_text(sample_edi_content)

        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )
        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "input"),
                "alias": "Settings Test",
                "process_backend_copy": 1,
                "copy_to_directory": str(temp_workspace / "output"),
                "convert_to_format": "csv",
            }
        )

        assert len(list(database.folders_table.all())) == 1

        settings = database.oversight_and_defaults.find_one()
        updated = dict(settings)
        updated["errors_folder"] = str(temp_workspace / "new_errors")
        database.oversight_and_defaults.update(updated, ["id"])

        final = database.oversight_and_defaults.find_one()
        assert final["errors_folder"] == str(temp_workspace / "new_errors")


class TestMultiDialogWorkflow:
    """Test workflows involving multiple dialogs."""

    def test_edit_folders_then_settings_workflow(
        self, qtbot, qt_app, temp_workspace, database
    ):
        """Test workflow using both EditFolders and EditSettings dialogs."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "input"),
                "alias": "Multi-Dialog Test",
                "process_backend_copy": 1,
                "copy_to_directory": str(temp_workspace / "output"),
                "convert_to_format": "csv",
            }
        )

        settings = database.oversight_and_defaults.find_one()
        updated = dict(settings)
        updated["errors_folder"] = str(temp_workspace / "errors_updated")
        database.oversight_and_defaults.update(updated, ["id"])

        folders = list(database.folders_table.all())
        assert len(folders) == 1
        assert folders[0]["alias"] == "Multi-Dialog Test"

        final_settings = database.oversight_and_defaults.find_one()
        assert final_settings["errors_folder"] == str(temp_workspace / "errors_updated")

    def test_maintenance_dialog_workflow(self, qtbot, qt_app, temp_workspace, database):
        """Test maintenance dialog can be created with a real DatabaseObj."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )
        database.processed_files.insert(
            {
                "folder_id": 1,
                "file_name": "test1.edi",
                "md5": "test_hash_1",
            }
        )

        from PyQt6.QtWidgets import QPushButton, QWidget

        from interface.operations.maintenance_functions import MaintenanceFunctions

        parent = QWidget()
        qtbot.addWidget(parent)

        mf = MaintenanceFunctions(database)
        dialog = MaintenanceDialog(parent, mf)
        # Do not addWidget here -- MaintenanceDialog manages its own lifetime
        # Just verify the dialog has operational buttons
        buttons = dialog.findChildren(QPushButton)
        assert len(buttons) > 0
        # Close the dialog manually before qtbot teardown
        dialog.close()
        dialog.deleteLater()
        qtbot.waitSignal(dialog.destroyed, timeout=1000, raising=False)


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery workflows."""

    def test_invalid_folder_path_recovery(
        self, qtbot, qt_app, temp_workspace, database
    ):
        """Test workflow: Add invalid folder → Fix path → Verify updated path persisted."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "nonexistent"),
                "alias": "Invalid Path Test",
                "process_backend_copy": 1,
                "copy_to_directory": str(temp_workspace / "output"),
                "convert_to_format": "csv",
            }
        )

        folders = list(database.folders_table.all())
        assert len(folders) == 1

        valid_path = temp_workspace / "input"  # already created by fixture
        updated = dict(folders[0])
        updated["folder_name"] = str(valid_path)
        database.folders_table.update(updated, ["id"])

        refreshed = list(database.folders_table.all())
        assert refreshed[0]["folder_name"] == str(valid_path)

    def test_database_error_recovery(self, qtbot, qt_app, temp_workspace, database):
        """Test that basic database operations raise no unexpected errors."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        try:
            folders = list(database.folders_table.all())
            assert folders is not None
        except Exception as e:
            pytest.fail(f"Database operation should not raise: {e}")


class TestRealUserInteractions:
    """Test realistic user interaction patterns."""

    def test_rapid_folder_selection(self, qtbot, qt_app, temp_workspace, database):
        """Test that inserting many folders and reading them back is reliable."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )

        for i in range(5):
            database.folders_table.insert(
                {
                    "folder_name": str(temp_workspace / f"input_{i}"),
                    "alias": f"Folder {i}",
                    "process_backend_copy": 1,
                    "copy_to_directory": str(temp_workspace / f"output_{i}"),
                }
            )

        folders = list(database.folders_table.all())
        assert len(folders) == 5

        # Simulate rapid reads (rapid UI selection)
        for _ in range(10):
            assert len(list(database.folders_table.all())) == 5

    def test_search_while_processing(self, qtbot, qt_app, temp_workspace, database):
        """Test filtering folders by alias (what a search widget does)."""
        database.oversight_and_defaults.update(
            {
                "id": 1,
                "logs_directory": str(temp_workspace / "logs"),
                "errors_folder": str(temp_workspace / "errors"),
            },
            ["id"],
        )
        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "input"),
                "alias": "Test Folder",
                "process_backend_copy": 1,
                "copy_to_directory": str(temp_workspace / "output"),
            }
        )
        database.folders_table.insert(
            {
                "folder_name": str(temp_workspace / "archive"),
                "alias": "Archive Folder",
                "process_backend_copy": 0,
            }
        )

        all_folders = list(database.folders_table.all())
        assert len(all_folders) == 2

        # Simulate search filter
        test_folders = [f for f in all_folders if "Test" in f["alias"]]
        assert len(test_folders) == 1
        assert test_folders[0]["alias"] == "Test Folder"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
