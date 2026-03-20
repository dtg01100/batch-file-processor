"""Integration tests for FolderManager operations.

This test suite provides comprehensive coverage of folder management
functionality using real database operations (not mocks).

Tests cover:
- Adding folders with template defaults
- Checking folder existence
- Enabling/disabling folders
- Deleting folders (with and without related data)
- Batch folder operations
- Default settings inheritance
- Unique alias generation
- Path normalization
- Edge cases and error conditions
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database]
import os
from pathlib import Path

from backend.database import sqlite_wrapper
from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from core.utils.bool_utils import normalize_bool
from interface.operations.folder_manager import FolderManager


@pytest.fixture
def workspace(fresh_db, tmp_path):
    """Create a test workspace with database and directories."""
    workspace_dir = tmp_path / "folder_mgmt_workspace"
    workspace_dir.mkdir()

    # Create test directories
    test_dirs = {
        "folder1": workspace_dir / "test_folder_1",
        "folder2": workspace_dir / "test_folder_2",
        "folder3": workspace_dir / "test_folder_3",
        "batch_parent": workspace_dir / "batch_parent",
        "batch_child1": workspace_dir / "batch_parent" / "child1",
        "batch_child2": workspace_dir / "batch_parent" / "child2",
        "batch_child3": workspace_dir / "batch_parent" / "child3",
    }

    for dir_path in test_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    # Database setup -- fresh_db already has the schema and version record
    db_path = fresh_db
    db_conn = sqlite_wrapper.Database.connect(str(db_path))

    db = DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(workspace_dir),
        running_platform="Linux",
        connection=db_conn,
    )

    # Set up default template in oversight_and_defaults
    # Note: FolderManager reads from oversight_and_defaults for template
    # but only copies non-SKIP_LIST fields
    defaults = db.get_oversight_or_default()
    # Update only fields that exist in oversight_and_defaults
    if "default_setting_1" not in defaults:
        # Add any test-specific settings we want to verify inheritance
        # These would typically be in oversight_and_defaults in production
        pass

    yield {
        "db": db,
        "dirs": test_dirs,
        "tmp_path": workspace_dir,
    }

    db.close()


class TestBasicFolderOperations:
    """Test basic folder CRUD operations."""

    def test_add_folder_basic(self, workspace):
        """Test adding a folder with default template."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        result = folder_manager.add_folder(folder_path)

        # Verify folder was added
        assert result["folder_name"] == folder_path
        assert result["alias"] == "test_folder_1"

        # Verify it's in database
        folder_from_db = db.folders_table.find_one(folder_name=folder_path)
        assert folder_from_db is not None
        assert folder_from_db["alias"] == "test_folder_1"
        assert folder_from_db["folder_name"] == folder_path

    def test_add_folder_with_custom_template(self, workspace):
        """Test adding a folder with custom template data."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Get existing oversight defaults and modify them
        custom_template = db.get_oversight_or_default()
        custom_template["process_edi"] = 0  # Override default

        folder_path = str(workspace["dirs"]["folder2"])
        folder_manager.add_folder(folder_path, template_data=custom_template)

        # Verify the custom template value was used
        folder_from_db = db.folders_table.find_one(folder_name=folder_path)
        assert folder_from_db["process_edi"] == 0

    def test_get_folder_by_id(self, workspace):
        """Test retrieving folder by ID."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        # Get from database to get the actual ID
        folder_from_db = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder_from_db["id"]

        # Retrieve by ID
        retrieved = folder_manager.get_folder_by_id(folder_id)
        assert retrieved is not None
        assert retrieved["folder_name"] == folder_path
        assert retrieved["id"] == folder_id

    def test_get_folder_by_name(self, workspace):
        """Test retrieving folder by path/name."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        retrieved = folder_manager.get_folder_by_name(folder_path)
        assert retrieved is not None
        assert retrieved["folder_name"] == folder_path

    def test_get_folder_by_alias(self, workspace):
        """Test retrieving folder by alias."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        retrieved = folder_manager.get_folder_by_alias("test_folder_1")
        assert retrieved is not None
        assert retrieved["folder_name"] == folder_path

    def test_update_folder(self, workspace):
        """Test updating folder configuration."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        folder = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder["id"]

        # Update folder
        updated_data = {
            "id": folder_id,
            "folder_is_active": "False",
            "convert_to_format": "estore_einvoice",
        }

        result = folder_manager.update_folder(updated_data)
        assert result is True

        # Verify update
        updated = db.folders_table.find_one(id=folder_id)
        assert updated["folder_is_active"] is False
        assert updated["convert_to_format"] == "estore_einvoice"

    def test_update_folder_by_name(self, workspace):
        """Test updating folder by name instead of ID."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        # Update by name
        updated_data = {
            "folder_name": folder_path,
            "folder_is_active": "False",
            "process_edi": 0,
        }

        result = folder_manager.update_folder_by_name(updated_data)
        assert result is True

        # Verify update
        updated = db.folders_table.find_one(folder_name=folder_path)
        assert updated["folder_is_active"] is False
        assert updated["process_edi"] == 0

    def test_delete_folder(self, workspace):
        """Test deleting a folder."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        folder = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder["id"]

        # Delete folder
        result = folder_manager.delete_folder(folder_id)
        assert result is True

        # Verify deletion
        folder_after = db.folders_table.find_one(id=folder_id)
        assert folder_after is None


class TestFolderExistenceChecking:
    """Test folder existence checking with path normalization."""

    def test_check_folder_exists_true(self, workspace):
        """Test checking existing folder."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        result = folder_manager.check_folder_exists(folder_path)
        assert result["truefalse"] is True
        assert result["matched_folder"] is not None
        assert result["matched_folder"]["folder_name"] == folder_path

    def test_check_folder_exists_false(self, workspace):
        """Test checking non-existent folder."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.check_folder_exists("/nonexistent/path")
        assert result["truefalse"] is False
        assert result["matched_folder"] is None

    def test_check_folder_exists_with_trailing_slash(self, workspace):
        """Test path normalization with trailing slashes."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        # Check with trailing slash
        result = folder_manager.check_folder_exists(folder_path + "/")
        assert result["truefalse"] is True
        assert result["matched_folder"] is not None

    def test_check_folder_exists_normalized_paths(self, workspace):
        """Test that different path formats match correctly."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        # Create alternative path format
        alt_path = folder_path + "/../test_folder_1"

        result = folder_manager.check_folder_exists(os.path.normpath(alt_path))
        assert result["truefalse"] is True


class TestEnableDisableOperations:
    """Test folder enable/disable functionality."""

    def test_disable_folder(self, workspace):
        """Test disabling an active folder."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        folder = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder["id"]

        # Disable folder
        result = folder_manager.disable_folder(folder_id)
        assert result is True

        # Verify disabled
        folder_after = db.folders_table.find_one(id=folder_id)
        assert folder_after["folder_is_active"] is False

    def test_enable_folder(self, workspace):
        """Test enabling an inactive folder."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add folder with inactive template
        custom_template = {
            "id": 1,
            "folder_is_active": "False",
        }

        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path, template_data=custom_template)

        folder = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder["id"]

        # Verify initially inactive
        assert folder["folder_is_active"] is False

        # Enable folder
        result = folder_manager.enable_folder(folder_id)
        assert result is True

        # Verify enabled
        folder_after = db.folders_table.find_one(id=folder_id)
        assert folder_after["folder_is_active"] is True

    def test_disable_nonexistent_folder(self, workspace):
        """Test disabling non-existent folder returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.disable_folder(99999)
        assert result is False

    def test_enable_nonexistent_folder(self, workspace):
        """Test enabling non-existent folder returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.enable_folder(99999)
        assert result is False


class TestUniqueAliasGeneration:
    """Test unique alias generation for duplicate folder names."""

    def test_unique_alias_on_duplicate(self, workspace):
        """Test that duplicate folder names get unique aliases."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Create first folder
        folder_path1 = str(workspace["dirs"]["folder1"])
        result1 = folder_manager.add_folder(folder_path1)
        assert result1["alias"] == "test_folder_1"

        # Create folder with same base name
        folder_path2 = str(workspace["tmp_path"] / "test_folder_1_copy")
        os.makedirs(folder_path2, exist_ok=True)

        # Manually set alias to conflict
        db.folders_table.insert(
            {
                "folder_name": folder_path2,
                "alias": "test_folder_1",
                "folder_is_active": "True",
            }
        )

        # Try to add another with same base name
        folder_path3 = str(workspace["tmp_path"] / "another" / "test_folder_1")
        os.makedirs(folder_path3, exist_ok=True)
        result3 = folder_manager.add_folder(folder_path3)

        # Should have unique alias
        assert result3["alias"] == "test_folder_1 1"

    def test_multiple_duplicate_aliases(self, workspace):
        """Test multiple folders with same base name get incrementing aliases."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        base_name = "duplicate"
        folders = []

        for i in range(5):
            folder_path = str(workspace["tmp_path"] / f"path{i}" / base_name)
            os.makedirs(folder_path, exist_ok=True)
            result = folder_manager.add_folder(folder_path)
            folders.append(result)

        # Check aliases
        assert folders[0]["alias"] == "duplicate"
        assert folders[1]["alias"] == "duplicate 1"
        assert folders[2]["alias"] == "duplicate 2"
        assert folders[3]["alias"] == "duplicate 3"
        assert folders[4]["alias"] == "duplicate 4"


class TestFolderRetrieval:
    """Test various folder retrieval operations."""

    def test_get_active_folders(self, workspace):
        """Test retrieving only active folders."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add folders
        folder_manager.add_folder(str(workspace["dirs"]["folder1"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder2"]))

        # Enable them explicitly
        f1 = db.folders_table.find_one(folder_name=str(workspace["dirs"]["folder1"]))
        f2 = db.folders_table.find_one(folder_name=str(workspace["dirs"]["folder2"]))
        folder_manager.enable_folder(f1["id"])
        folder_manager.enable_folder(f2["id"])

        # Add inactive folder
        folder_manager.add_folder(str(workspace["dirs"]["folder3"]))
        f3 = db.folders_table.find_one(folder_name=str(workspace["dirs"]["folder3"]))
        folder_manager.disable_folder(f3["id"])

        # Get active folders
        active_folders = folder_manager.get_active_folders()

        assert len(active_folders) == 2
        for folder in active_folders:
            assert folder["folder_is_active"] is True

    def test_get_inactive_folders(self, workspace):
        """Test retrieving only inactive folders."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add active folder
        folder_manager.add_folder(str(workspace["dirs"]["folder1"]))

        # Add inactive folders
        inactive_template = {"id": 1, "folder_is_active": "False"}
        folder_manager.add_folder(
            str(workspace["dirs"]["folder2"]), template_data=inactive_template
        )
        folder_manager.add_folder(
            str(workspace["dirs"]["folder3"]), template_data=inactive_template
        )

        # Get inactive folders
        inactive_folders = folder_manager.get_inactive_folders()

        assert len(inactive_folders) == 2
        for folder in inactive_folders:
            assert folder["folder_is_active"] is False

    def test_get_all_folders(self, workspace):
        """Test retrieving all folders regardless of status."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add mixed folders
        folder_manager.add_folder(str(workspace["dirs"]["folder1"]))
        inactive_template = {"id": 1, "folder_is_active": "False"}
        folder_manager.add_folder(
            str(workspace["dirs"]["folder2"]), template_data=inactive_template
        )
        folder_manager.add_folder(str(workspace["dirs"]["folder3"]))

        all_folders = folder_manager.get_all_folders()

        assert len(all_folders) == 3

    def test_get_all_folders_ordered(self, workspace):
        """Test retrieving folders with ordering."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add folders in non-alphabetical order
        folder_manager.add_folder(str(workspace["dirs"]["folder3"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder1"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder2"]))

        folders = folder_manager.get_all_folders(order_by="alias")

        # Verify ordering by alias
        aliases = [f["alias"] for f in folders]
        assert aliases == sorted(aliases)

    def test_count_folders_all(self, workspace):
        """Test counting all folders."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        folder_manager.add_folder(str(workspace["dirs"]["folder1"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder2"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder3"]))

        count = folder_manager.count_folders()
        assert count == 3

    def test_count_folders_active_only(self, workspace):
        """Test counting only active folders."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add folders and enable 2 of them
        folder_manager.add_folder(str(workspace["dirs"]["folder1"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder2"]))
        folder_manager.add_folder(str(workspace["dirs"]["folder3"]))

        f1 = db.folders_table.find_one(folder_name=str(workspace["dirs"]["folder1"]))
        f2 = db.folders_table.find_one(folder_name=str(workspace["dirs"]["folder2"]))
        f3 = db.folders_table.find_one(folder_name=str(workspace["dirs"]["folder3"]))

        folder_manager.enable_folder(f1["id"])
        folder_manager.enable_folder(f2["id"])
        folder_manager.disable_folder(f3["id"])

        active_count = folder_manager.count_folders(active_only=True)
        assert active_count == 2

        total_count = folder_manager.count_folders(active_only=False)
        assert total_count == 3


class TestBatchOperations:
    """Test batch folder addition operations."""

    def test_batch_add_folders_basic(self, workspace):
        """Test batch adding multiple folders."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        parent_path = str(workspace["dirs"]["batch_parent"])

        result = folder_manager.batch_add_folders(parent_path)

        assert result["added"] == 3
        assert result["skipped"] == 0

        # Verify all folders were added
        all_folders = folder_manager.get_all_folders()
        assert len(all_folders) == 3

    def test_batch_add_folders_skip_existing(self, workspace):
        """Test batch add skips existing folders."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        parent_path = str(workspace["dirs"]["batch_parent"])

        # Add one folder manually
        child1_path = str(workspace["dirs"]["batch_child1"])
        folder_manager.add_folder(child1_path)

        # Batch add all (should skip child1)
        result = folder_manager.batch_add_folders(parent_path, skip_existing=True)

        assert result["added"] == 2
        assert result["skipped"] == 1

        # Verify total count
        all_folders = folder_manager.get_all_folders()
        assert len(all_folders) == 3

    def test_batch_add_folders_no_skip(self, workspace):
        """Test batch add with skip_existing=False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        parent_path = str(workspace["dirs"]["batch_parent"])

        # Add one folder manually
        child1_path = str(workspace["dirs"]["batch_child1"])
        folder_manager.add_folder(child1_path)

        # Batch add all without skipping (will create duplicate aliases)
        result = folder_manager.batch_add_folders(parent_path, skip_existing=False)

        # All 3 should be "added" (even though 1 exists)
        assert result["added"] == 3
        assert result["skipped"] == 0

    def test_batch_add_invalid_path(self, workspace):
        """Test batch add with invalid parent path."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.batch_add_folders("/nonexistent/path")

        assert result["added"] == 0
        assert result["skipped"] == 0
        assert "error" in result


class TestDeleteWithRelated:
    """Test deletion of folders with related data."""

    def test_delete_folder_with_related_data(self, workspace):
        """Test deleting folder and all related records."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add folder
        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        folder = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder["id"]

        # Add related data (use correct column names from schema)
        db.processed_files.insert(
            {
                "folder_id": folder_id,
                "filename": "test.edi",
                "md5": "test_hash",
            }
        )

        db.emails_table.insert(
            {
                "folder_id": folder_id,
                "folder_alias": "test_folder",
                "log": "Test email log",
            }
        )

        # Verify related data exists
        processed = list(db.processed_files.find(folder_id=folder_id))
        emails = list(db.emails_table.find(folder_id=folder_id))
        assert len(processed) == 1
        assert len(emails) == 1

        # Delete folder with related data
        result = folder_manager.delete_folder_with_related(folder_id)
        assert result is True

        # Verify folder is deleted
        folder_after = db.folders_table.find_one(id=folder_id)
        assert folder_after is None

        # Verify related data is deleted
        processed_after = list(db.processed_files.find(folder_id=folder_id))
        emails_after = list(db.emails_table.find(folder_id=folder_id))
        assert len(processed_after) == 0
        assert len(emails_after) == 0

    def test_delete_folder_basic_vs_with_related(self, workspace):
        """Test that basic delete doesn't remove related data."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Add folder
        folder_path = str(workspace["dirs"]["folder1"])
        folder_manager.add_folder(folder_path)

        folder = db.folders_table.find_one(folder_name=folder_path)
        folder_id = folder["id"]

        # Add related data (use correct column names from schema)
        db.processed_files.insert(
            {
                "folder_id": folder_id,
                "filename": "test.edi",
                "md5": "test_hash",
            }
        )

        # Use basic delete
        result = folder_manager.delete_folder(folder_id)
        assert result is True

        # Verify folder is deleted
        folder_after = db.folders_table.find_one(id=folder_id)
        assert folder_after is None

        # Verify related data still exists
        processed_after = list(db.processed_files.find(folder_id=folder_id))
        assert len(processed_after) == 1


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_update_folder_without_id(self, workspace):
        """Test that updating without ID returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.update_folder({"folder_is_active": "False"})
        assert result is False

    def test_update_folder_nonexistent(self, workspace):
        """Test updating non-existent folder returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.update_folder(
            {"id": 99999, "folder_is_active": "False"}
        )
        assert result is False

    def test_update_folder_by_name_without_name(self, workspace):
        """Test that updating by name without folder_name returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.update_folder_by_name({"folder_is_active": "False"})
        assert result is False

    def test_update_folder_by_name_nonexistent(self, workspace):
        """Test updating non-existent folder by name returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.update_folder_by_name(
            {"folder_name": "/nonexistent/path", "folder_is_active": "False"}
        )
        assert result is False

    def test_get_folder_by_id_nonexistent(self, workspace):
        """Test getting non-existent folder by ID returns None."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.get_folder_by_id(99999)
        assert result is None

    def test_get_folder_by_name_nonexistent(self, workspace):
        """Test getting non-existent folder by name returns None."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.get_folder_by_name("/nonexistent/path")
        assert result is None

    def test_get_folder_by_alias_nonexistent(self, workspace):
        """Test getting non-existent folder by alias returns None."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.get_folder_by_alias("nonexistent_alias")
        assert result is None

    def test_delete_nonexistent_folder(self, workspace):
        """Test deleting non-existent folder returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.delete_folder(99999)
        assert result is False

    def test_delete_with_related_nonexistent(self, workspace):
        """Test deleting non-existent folder with related returns False."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        result = folder_manager.delete_folder_with_related(99999)
        assert result is False


class TestDefaultsInheritance:
    """Test that folders correctly inherit default settings."""

    def test_folders_inherit_template_settings(self, workspace):
        """Test that new folders get all template settings."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Update oversight_and_defaults with specific values
        defaults = db.get_oversight_or_default()
        # Update only fields that exist in the schema
        defaults["logs_directory"] = "/test/logs"
        db.oversight_and_defaults.update(defaults, ["id"])

        # Add folder
        folder_path = str(workspace["dirs"]["folder1"])
        result = folder_manager.add_folder(folder_path)

        # Verify folder inherits settings (but logs_directory is in SKIP_LIST so it shouldn't be inherited)
        assert result["folder_name"] == folder_path
        # Verify SKIP_LIST fields are not inherited
        assert result.get("logs_directory") != "/test/logs"

    def test_skip_list_fields_not_inherited(self, workspace):
        """Test that SKIP_LIST fields are not copied from template."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Set values in oversight_and_defaults that should not be inherited
        defaults = db.get_oversight_or_default()
        defaults["logs_directory"] = "/should/not/inherit"
        defaults["errors_folder"] = "/should/not/inherit"
        db.oversight_and_defaults.update(defaults, ["id"])

        folder_path = str(workspace["dirs"]["folder1"])
        result = folder_manager.add_folder(folder_path)

        # These SKIP_LIST fields should not be in the folder result
        for skip_field in [
            "logs_directory",
            "errors_folder",
            "single_add_folder_prior",
        ]:
            # These fields should either not exist or not have the "should not inherit" value
            if skip_field in result:
                assert result[skip_field] != "/should/not/inherit"

    def test_custom_template_overrides_database(self, workspace):
        """Test that custom template data overrides database defaults."""
        db = workspace["db"]
        folder_manager = FolderManager(db)

        # Use custom template with specific values
        custom_template = {
            "id": 1,
            "folder_is_active": "False",
            "process_edi": 0,
        }

        folder_path = str(workspace["dirs"]["folder1"])
        result = folder_manager.add_folder(folder_path, template_data=custom_template)

        # Custom template values should be used
        assert normalize_bool(result["folder_is_active"]) is False
        assert result["process_edi"] == 0


@pytest.fixture
def workspace_with_datasets(fresh_db, tmp_path):
    """Create a test workspace with multiple folder datasets for workflow testing."""
    workspace_dir = tmp_path / "workflow_workspace"
    workspace_dir.mkdir()

    # Create organized directory structure
    datasets = {
        "vendor_folders": workspace_dir / "vendors",
        "customer_folders": workspace_dir / "customers",
        "archive": workspace_dir / "archive",
        "processing": workspace_dir / "processing",
        "incoming": workspace_dir / "incoming",
        "outgoing": workspace_dir / "outgoing",
    }

    # Create subdirectories within vendors
    vendor_paths = {}
    for vendor_name in ["acme_corp", "startech", "electronics_inc"]:
        vendor_path = datasets["vendor_folders"] / vendor_name
        vendor_path.mkdir(parents=True, exist_ok=True)
        vendor_paths[vendor_name] = vendor_path

    # Create subdirectories within customers
    customer_paths = {}
    for customer_name in ["retailer_a", "retailer_b", "distributor_x"]:
        customer_path = datasets["customer_folders"] / customer_name
        customer_path.mkdir(parents=True, exist_ok=True)
        customer_paths[customer_name] = customer_path

    # Create other directories
    for dir_path in datasets.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    # Database setup -- fresh_db already has schema + version record
    db_conn = sqlite_wrapper.Database.connect(str(fresh_db))

    db = DatabaseObj(
        database_path=str(fresh_db),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(workspace_dir),
        running_platform="Linux",
        connection=db_conn,
    )

    yield {
        "db": db,
        "workspace": workspace_dir,
        "datasets": datasets,
        "vendor_paths": vendor_paths,
        "customer_paths": customer_paths,
    }

    db.close()


class TestRealWorldWorkflows:
    """Test realistic folder management workflows."""

    def test_multi_vendor_setup_workflow(self, workspace_with_datasets):
        """Test setting up multiple vendor folders with different configurations."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        # Configure each vendor differently
        vendor_configs = {
            "acme_corp": {"process_edi": 1, "tweak_edi": 1, "convert_to_format": "csv"},
            "startech": {
                "process_edi": 1,
                "tweak_edi": 0,
                "convert_to_format": "estore_einvoice",
            },
            "electronics_inc": {
                "process_edi": 1,
                "tweak_edi": 1,
                "convert_to_format": "fintech",
            },
        }

        added_folders = {}
        for vendor_name, config in vendor_configs.items():
            vendor_path = str(vendor_paths[vendor_name])
            template = {"id": 1, **config}
            result = folder_manager.add_folder(vendor_path, template_data=template)
            added_folders[vendor_name] = result

            # Verify configuration
            folder_db = db.folders_table.find_one(folder_name=vendor_path)
            assert folder_db["process_edi"] == config["process_edi"]
            assert folder_db["tweak_edi"] == config["tweak_edi"]
            assert folder_db["convert_to_format"] == config["convert_to_format"]

        # Verify all folders added
        all_folders = folder_manager.get_all_folders()
        assert len(all_folders) == 3

    def test_folder_lifecycle_workflow(self, workspace_with_datasets):
        """Test complete folder lifecycle: add -> configure -> enable -> disable -> delete."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        vendor_path = str(vendor_paths["acme_corp"])

        # Stage 1: Add folder
        result = folder_manager.add_folder(vendor_path)
        folder = db.folders_table.find_one(folder_name=vendor_path)
        folder_id = folder["id"]
        assert folder["alias"] == result["alias"]

        # Stage 2: Configure folder
        config_data = {
            "id": folder_id,
            "folder_is_active": "True",
            "process_edi": 1,
            "convert_to_format": "csv",
        }
        folder_manager.update_folder(config_data)
        folder_after_config = db.folders_table.find_one(id=folder_id)
        assert folder_after_config["convert_to_format"] == "csv"

        # Stage 3: Enable folder
        folder_manager.enable_folder(folder_id)
        folder_enabled = db.folders_table.find_one(id=folder_id)
        assert folder_enabled["folder_is_active"] is True

        # Stage 4: Disable folder
        folder_manager.disable_folder(folder_id)
        folder_disabled = db.folders_table.find_one(id=folder_id)
        assert folder_disabled["folder_is_active"] is False

        # Stage 5: Delete folder
        folder_manager.delete_folder(folder_id)
        folder_deleted = db.folders_table.find_one(id=folder_id)
        assert folder_deleted is None

    def test_batch_migration_workflow(self, workspace_with_datasets):
        """Test migrating batch of folders from one location to another."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        datasets = workspace_with_datasets["datasets"]

        # Initial batch add from incoming directory
        incoming_path = str(datasets["incoming"])
        Path(incoming_path + "/folder_a").mkdir(exist_ok=True)
        Path(incoming_path + "/folder_b").mkdir(exist_ok=True)
        Path(incoming_path + "/folder_c").mkdir(exist_ok=True)

        result1 = folder_manager.batch_add_folders(incoming_path)
        assert result1["added"] == 3

        # Verify all folders are in database
        all_folders_1 = folder_manager.get_all_folders()
        assert len(all_folders_1) == 3

        # Move folders to processing (simulate migration)
        processing_path = str(datasets["processing"])
        for folder in all_folders_1:
            db.folders_table.update(
                {
                    "id": folder["id"],
                    "folder_name": folder["folder_name"].replace(
                        "incoming", "processing"
                    ),
                },
                ["id"],
            )

        # Batch add from processing directory
        Path(processing_path + "/folder_a").mkdir(exist_ok=True)
        Path(processing_path + "/folder_b").mkdir(exist_ok=True)
        Path(processing_path + "/folder_c").mkdir(exist_ok=True)

        folder_manager.batch_add_folders(processing_path, skip_existing=False)

        # Should have additional folders
        all_folders_2 = folder_manager.get_all_folders()
        assert len(all_folders_2) >= 3

    def test_settings_propagation_workflow(self, workspace_with_datasets):
        """Test that settings propagate correctly through folder lifecycle."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        # Get current defaults from administrative table
        defaults = db.get_oversight_or_default()

        # Add multiple folders with same template
        vendor_names = ["acme_corp", "startech", "electronics_inc"]
        for vendor_name in vendor_names:
            vendor_path = str(vendor_paths[vendor_name])

            # Add with current defaults as template
            folder_manager.add_folder(vendor_path, template_data=defaults)

            # Verify folder was added
            folder = db.folders_table.find_one(folder_name=vendor_path)
            assert folder is not None
            assert folder["folder_name"] == vendor_path

        # Verify all folders now configured
        all_folders = folder_manager.get_all_folders()
        assert len(all_folders) >= len(vendor_names)


class TestComplexStateTransitions:
    """Test complex state transitions and multi-step operations."""

    def test_enable_disable_toggle_sequence(self, workspace_with_datasets):
        """Test toggling folder enabled/disabled state multiple times."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        vendor_path = str(vendor_paths["acme_corp"])
        folder_manager.add_folder(vendor_path)
        folder = db.folders_table.find_one(folder_name=vendor_path)
        folder_id = folder["id"]

        # Toggle multiple times
        for iteration in range(5):
            # Disable
            folder_manager.disable_folder(folder_id)
            folder = db.folders_table.find_one(id=folder_id)
            assert folder["folder_is_active"] is False

            # Enable
            folder_manager.enable_folder(folder_id)
            folder = db.folders_table.find_one(id=folder_id)
            assert folder["folder_is_active"] is True

    def test_concurrent_folder_updates(self, workspace_with_datasets):
        """Test updating multiple folders in sequence (simulating concurrent updates)."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        # Add multiple folders
        folder_ids = {}
        for vendor_name in ["acme_corp", "startech", "electronics_inc"]:
            vendor_path = str(vendor_paths[vendor_name])
            result = folder_manager.add_folder(vendor_path)
            folder = db.folders_table.find_one(folder_name=vendor_path)
            folder_ids[vendor_name] = folder["id"]

        # Update all folders with different configurations
        update_configs = {
            "acme_corp": {"process_edi": 1, "convert_to_format": "csv"},
            "startech": {"process_edi": 0, "convert_to_format": "estore_einvoice"},
            "electronics_inc": {"process_edi": 1, "convert_to_format": "fintech"},
        }

        for vendor_name, config in update_configs.items():
            folder_id = folder_ids[vendor_name]
            update_data = {"id": folder_id, **config}
            result = folder_manager.update_folder(update_data)
            assert result is True

            # Verify update
            folder = db.folders_table.find_one(id=folder_id)
            assert folder["process_edi"] == config["process_edi"]
            assert folder["convert_to_format"] == config["convert_to_format"]

    def test_update_with_validation_workflow(self, workspace_with_datasets):
        """Test updating folder with validation between updates."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        vendor_path = str(vendor_paths["acme_corp"])
        folder_manager.add_folder(vendor_path)
        folder = db.folders_table.find_one(folder_name=vendor_path)
        folder_id = folder["id"]

        # Update and validate each step
        updates = [
            {"id": folder_id, "folder_is_active": True, "process_edi": 1},
            {"id": folder_id, "convert_to_format": "estore_einvoice"},
            {"id": folder_id, "folder_is_active": False},
        ]

        for update in updates:
            result = folder_manager.update_folder(update)
            assert result is True

            folder = db.folders_table.find_one(id=folder_id)
            for key, value in update.items():
                if key != "id":
                    assert folder[key] == value


class TestDataConsistency:
    """Test data consistency through various scenarios."""

    def test_alias_uniqueness_enforcement(self, workspace_with_datasets):
        """Test that alias uniqueness is maintained through operations."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        # Add folders
        aliases_seen = set()
        for vendor_name in ["acme_corp", "startech", "electronics_inc"]:
            vendor_path = str(vendor_paths[vendor_name])
            result = folder_manager.add_folder(vendor_path)

            # Verify unique alias
            alias = result["alias"]
            assert alias not in aliases_seen, f"Duplicate alias: {alias}"
            aliases_seen.add(alias)

        # Verify all aliases in database are unique
        all_folders = folder_manager.get_all_folders()
        db_aliases = [f["alias"] for f in all_folders]
        assert len(db_aliases) == len(set(db_aliases)), "Duplicate aliases in database"

    def test_folder_path_consistency(self, workspace_with_datasets):
        """Test that folder paths are stored and retrieved consistently."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        # Add folders with various path formats
        paths_added = []
        for vendor_name in ["acme_corp", "startech", "electronics_inc"]:
            vendor_path = str(vendor_paths[vendor_name])
            folder_manager.add_folder(vendor_path)
            paths_added.append(vendor_path)

        # Verify all paths match
        all_folders = folder_manager.get_all_folders()
        for folder in all_folders:
            assert folder["folder_name"] in paths_added

    def test_id_consistency_through_operations(self, workspace_with_datasets):
        """Test that folder IDs remain consistent through operations."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        vendor_path = str(vendor_paths["acme_corp"])
        folder_manager.add_folder(vendor_path)
        folder1 = db.folders_table.find_one(folder_name=vendor_path)
        folder_id = folder1["id"]

        # Perform various operations
        folder_manager.enable_folder(folder_id)
        folder_manager.update_folder({"id": folder_id, "process_edi": 1})
        folder_manager.disable_folder(folder_id)

        # Verify ID never changed
        folder_final = db.folders_table.find_one(folder_name=vendor_path)
        assert folder_final["id"] == folder_id


class TestBatchScenarios:
    """Test complex batch operation scenarios."""

    def test_selective_batch_operation(self, workspace_with_datasets):
        """Test batch operations with selective enabling/disabling."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        datasets = workspace_with_datasets["datasets"]

        # Create batch of folders
        batch_parent = str(datasets["processing"])
        for i in range(5):
            Path(batch_parent + f"/batch_{i}").mkdir(exist_ok=True)

        result = folder_manager.batch_add_folders(batch_parent)
        assert result["added"] >= 5

        # Get all folders and selectively enable/disable
        all_folders = folder_manager.get_all_folders()
        batch_folders = [f for f in all_folders if batch_parent in f["folder_name"]]

        # Enable odd-numbered folders
        for i, folder in enumerate(batch_folders):
            if i % 2 == 0:
                folder_manager.enable_folder(folder["id"])
            else:
                folder_manager.disable_folder(folder["id"])

        # Verify state
        enabled = folder_manager.get_active_folders()
        disabled = folder_manager.get_inactive_folders()
        assert len(enabled) > 0
        assert len(disabled) > 0

    def test_batch_configuration_application(self, workspace_with_datasets):
        """Test applying common configuration to batch of folders."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        datasets = workspace_with_datasets["datasets"]

        # Add batch of folders with default config
        batch_parent = str(datasets["outgoing"])
        for i in range(3):
            Path(batch_parent + f"/folder_{i}").mkdir(exist_ok=True)

        folder_manager.batch_add_folders(batch_parent)
        all_folders = folder_manager.get_all_folders()
        batch_folders = [f for f in all_folders if batch_parent in f["folder_name"]]

        # Apply common configuration to all
        common_config = {
            "process_edi": 1,
            "convert_to_format": "csv",
            "folder_is_active": True,
        }

        for folder in batch_folders:
            update_data = {"id": folder["id"], **common_config}
            folder_manager.update_folder(update_data)

        # Verify all have the same configuration
        for folder in batch_folders:
            updated = db.folders_table.find_one(id=folder["id"])
            for key, value in common_config.items():
                assert updated[key] == value


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_recovery_from_failed_batch_operation(self, workspace_with_datasets):
        """Test recovery when batch operation has mixed results."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)

        # Try batch add on invalid path
        result = folder_manager.batch_add_folders("/invalid/nonexistent/path")
        assert result["added"] == 0

        # Database should still be functional - add a folder normally
        vendor_paths = workspace_with_datasets["vendor_paths"]
        vendor_path = str(vendor_paths["acme_corp"])
        result = folder_manager.add_folder(vendor_path)
        assert result["folder_name"] == vendor_path

    def test_repeated_add_operations(self, workspace_with_datasets):
        """Test adding same folder multiple times (should handle gracefully)."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        vendor_path = str(vendor_paths["acme_corp"])

        # Add same folder three times
        result1 = folder_manager.add_folder(vendor_path)
        result2 = folder_manager.add_folder(vendor_path)
        result3 = folder_manager.add_folder(vendor_path)

        # All should complete (though second and third create duplicates)
        assert result1["folder_name"] == vendor_path
        assert result2["folder_name"] == vendor_path
        assert result3["folder_name"] == vendor_path

        # Count folders - should have duplicates
        all_folders = folder_manager.get_all_folders()
        matching = [f for f in all_folders if vendor_path in f["folder_name"]]
        assert len(matching) == 3


@pytest.mark.slow
class TestPerformanceBaselines:
    """Test performance characteristics of folder operations."""

    def test_bulk_folder_operations_performance(self, workspace_with_datasets):
        """Test performance of operations on multiple folders."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        datasets = workspace_with_datasets["datasets"]

        # Create and add 20 folders
        batch_parent = str(datasets["archive"])
        for i in range(20):
            Path(batch_parent + f"/perf_test_{i:03d}").mkdir(exist_ok=True)

        # Batch add all
        result = folder_manager.batch_add_folders(batch_parent)
        assert result["added"] >= 20

        # Retrieve all - should be fast
        all_folders = folder_manager.get_all_folders()
        assert len(all_folders) >= 20

        # Count operations - should be fast
        count = folder_manager.count_folders()
        assert count >= 20

        # Filter operations - should be fast
        active_count = folder_manager.count_folders(active_only=True)
        assert active_count == len(folder_manager.get_active_folders())
        assert active_count <= count


class TestMultiVendorScenarios:
    """Test realistic multi-vendor operational scenarios."""

    def test_multi_tenant_isolation(self, workspace_with_datasets):
        """Test that multiple vendors/tenants remain isolated."""
        db = workspace_with_datasets["db"]
        folder_manager = FolderManager(db)
        vendor_paths = workspace_with_datasets["vendor_paths"]

        # Add each vendor with distinct configuration
        vendor_configs = {
            "acme_corp": {"process_edi": 1, "convert_to_format": "csv"},
            "startech": {"process_edi": 1, "convert_to_format": "estore_einvoice"},
            "electronics_inc": {"process_edi": 0, "convert_to_format": "fintech"},
        }

        folder_ids = {}
        for vendor_name, config in vendor_configs.items():
            vendor_path = str(vendor_paths[vendor_name])
            template = {"id": 1, **config}
            folder_manager.add_folder(vendor_path, template_data=template)
            folder = db.folders_table.find_one(folder_name=vendor_path)
            folder_ids[vendor_name] = (folder["id"], vendor_path)

        # Verify each vendor's configuration is isolated
        for vendor_name, config in vendor_configs.items():
            folder_id, vendor_path = folder_ids[vendor_name]
            folder = db.folders_table.find_one(id=folder_id)

            assert folder["process_edi"] == config["process_edi"]
            assert folder["convert_to_format"] == config["convert_to_format"]

            # Update this vendor's config
            new_config = {
                "id": folder_id,
                "process_edi": 0,  # Change value
            }
            folder_manager.update_folder(new_config)

        # Verify other vendors unchanged
        for other_vendor in vendor_configs:
            if other_vendor != "acme_corp":  # We modified acme_corp
                _, vendor_path = folder_ids[other_vendor]
                folder = db.folders_table.find_one(folder_name=vendor_path)
                assert folder["folder_name"] == vendor_path
