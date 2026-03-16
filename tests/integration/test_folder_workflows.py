"""Integration workflow tests for FolderManager complex scenarios.

This module extends test_folder_management.py with comprehensive workflow tests
that simulate real-world usage patterns, state transitions, and complex scenarios.

Test coverage includes:
- Real-world folder registration and configuration workflows
- Complex state transitions (add -> configure -> enable/disable -> delete)
- Settings propagation through folder lifecycle
- Data consistency validation across operations
- Batch operations with mixed success/failure scenarios
- Error recovery and rollback patterns
- Concurrent-like patterns with multiple folders
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database, pytest.mark.workflow]
from pathlib import Path

from batch_file_processor.constants import CURRENT_DATABASE_VERSION
from core.utils.bool_utils import normalize_bool
from interface.database import sqlite_wrapper
from interface.database.database_obj import DatabaseObj
from interface.operations.folder_manager import FolderManager


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

    # Database setup – fresh_db already has schema + version record
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

        result2 = folder_manager.batch_add_folders(processing_path, skip_existing=False)

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
            result = folder_manager.add_folder(vendor_path, template_data=defaults)

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
        result1 = folder_manager.add_folder(vendor_path)
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

        result = folder_manager.batch_add_folders(batch_parent)
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
            result = folder_manager.add_folder(vendor_path, template_data=template)
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
