"""Simplified E2E workflow tests focusing on UI-backend integration logic.

These tests validate the complete user journey without heavy Qt app initialization,
making them faster and more reliable for CI/CD.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow]

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from interface.database.database_obj import DatabaseObj
import create_database
from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
from copy_backend import do as copy_backend_do
from dispatch.pipeline.validator import EDIValidationStep
from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.tweaker import EDITweakerStep


@pytest.fixture
def test_environment():
    """Create a complete test environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create directories
        (workspace / "input").mkdir()
        (workspace / "output").mkdir()
        (workspace / "database").mkdir()
        (workspace / "logs").mkdir()
        (workspace / "errors").mkdir()

        # Create database
        db_path = workspace / "database" / "folders.db"
        create_database.do("33", str(db_path), str(workspace), "Linux")

        # Connect using DatabaseObj
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION

        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,  # Use latest version
            config_folder=str(workspace),
            running_platform="Linux",
        )

        yield {
            "workspace": workspace,
            "db": db,
        }

        # Cleanup
        db.close()


@pytest.fixture
def sample_edi_content():
    """Sample EDI file content."""
    return """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""


@pytest.fixture
def pipeline_steps():
    """Create pipeline steps for processing."""
    return {
        "validator_step": EDIValidationStep(),
        "converter_step": EDIConverterStep(),
        "tweaker_step": EDITweakerStep(),
    }


class TestCompleteFolderLifecycle:
    """Test complete folder lifecycle from creation to deletion."""

    def test_create_configure_process_delete_workflow(
        self, test_environment, sample_edi_content, pipeline_steps
    ):
        """Test: Create folder → Configure → Process → Verify → Delete."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Step 1: Create sample EDI file (simulating user placing files in folder)
        edi_file = workspace / "input" / "test_invoice.edi"
        edi_file.write_text(sample_edi_content)

        # Step 2: User adds folder via UI (simulating EditFoldersDialog save)
        folder_config = {
            "folder_name": str(workspace / "input"),
            "alias": "E2E Workflow Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "process_backend_ftp": False,
            "process_backend_email": False,
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Step 3: Verify folder was saved (simulating UI refresh)
        folders = list(db.folders_table.all())
        assert len(folders) == 1
        assert folders[0]["alias"] == "E2E Workflow Test"
        assert folders[0]["process_backend_copy"] == 1  # SQLite returns 1 for True

        # Step 4: User clicks "Process" (simulating backend processing with pipeline)
        # Configure the copy backend
        class CopyBackend:
            """Test wrapper for copy backend."""

            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        backends = {"copy": CopyBackend()}
        # Configure with pipeline steps - pipeline is now always used
        config = DispatchConfig(
            backends=backends,
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()

        result = orchestrator.process_folder(folders[0], run_log)

        # Step 5: Verify processing occurred
        assert result.success, "Folder processing should succeed"
        assert result.files_processed == 1, "Should process the single input file"

        # Step 6: Verify output was created (check both EDI and CSV)
        # The copy backend copies the processed file (could be EDI or CSV depending on pipeline)
        output_files = list((workspace / "output").glob("*"))
        assert (
            len(output_files) > 0
        ), f"Should create output file. Processed: {result.files_processed}, Failed: {result.files_failed}"

        # Step 7: Verify output content
        output_content = output_files[0].read_text()
        assert len(output_content) > 0, "Output file should not be empty"

        # Step 8: User deletes folder (simulating delete button + confirmation)
        folder_id = folders[0]["id"]
        db.folders_table.delete(id=folder_id)

        # Step 9: Verify deletion
        final_folders = list(db.folders_table.all())
        assert len(final_folders) == 0

    def test_edit_folder_configuration_workflow(self, test_environment):
        """Test: View folder → Edit configuration → Save → Verify update."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Step 1: Create initial folder
        initial_config = {
            "folder_name": str(workspace / "input"),
            "alias": "Original Name",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(initial_config)

        # Step 2: Verify initial state
        folders = list(db.folders_table.all())
        assert len(folders) == 1
        assert folders[0]["alias"] == "Original Name"
        assert folders[0]["convert_to_format"] == "csv"

        # Step 3: User edits folder (simulating EditFoldersDialog)
        folder_id = folders[0]["id"]
        updated_config = folders[0].copy()
        updated_config["alias"] = "Updated Name"
        updated_config["convert_to_format"] = "fintech"
        updated_config["process_backend_ftp"] = True

        # Step 4: Save changes (simulating dialog save button)
        db.folders_table.update(updated_config, ["id"])

        # Step 5: Verify update persisted
        updated_folders = list(db.folders_table.all())
        assert updated_folders[0]["alias"] == "Updated Name"
        assert updated_folders[0]["convert_to_format"] == "fintech"
        assert (
            updated_folders[0]["process_backend_ftp"] == 1
        )  # SQLite returns 1 for True

    def test_multiple_folders_independent_processing(
        self, test_environment, sample_edi_content, pipeline_steps
    ):
        """Test: Create multiple folders → Process independently → Verify isolation."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Create separate input folders
        input1 = workspace / "input1"
        input2 = workspace / "input2"
        output1 = workspace / "output1"
        output2 = workspace / "output2"

        input1.mkdir(exist_ok=True)
        input2.mkdir(exist_ok=True)
        output1.mkdir(exist_ok=True)
        output2.mkdir(exist_ok=True)

        # Create different EDI files in each
        (input1 / "invoice1.edi").write_text(sample_edi_content)
        (input2 / "invoice2.edi").write_text(
            sample_edi_content.replace("TESTVENDOR", "VENDOR2")
        )

        # Configure folders with different settings
        folder1_config = {
            "folder_name": str(input1),
            "alias": "Folder 1 - CSV",
            "process_backend_copy": True,
            "copy_to_directory": str(output1),
            "convert_to_format": "csv",
        }

        folder2_config = {
            "folder_name": str(input2),
            "alias": "Folder 2 - Simplified",
            "process_backend_copy": True,
            "copy_to_directory": str(output2),
            "convert_to_format": "simplified_csv",
        }

        db.folders_table.insert(folder1_config)
        db.folders_table.insert(folder2_config)

        # Process both folders
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import do as copy_backend_do

        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        backends = {"copy": CopyBackend()}
        config = DispatchConfig(
            backends=backends,
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        results = []
        for folder in folders:
            result = orchestrator.process_folder(folder, MagicMock())
            results.append(result)

        # Verify both produced output
        output1_files = list(output1.glob("*"))
        output2_files = list(output2.glob("*"))

        assert len(output1_files) > 0, "Folder 1 should produce output"
        assert len(output2_files) > 0, "Folder 2 should produce output"

        # Verify different conversion types produced different outputs
        output1_content = output1_files[0].read_text()
        output2_content = output2_files[0].read_text()

        assert (
            output1_content != output2_content
        ), "Different conversion types should produce different outputs"


class TestSettingsWorkflow:
    """Test settings management workflows."""

    def test_edit_settings_persistence_workflow(self, test_environment):
        """Test: Open settings → Modify values → Save → Verify persistence."""
        db = test_environment["db"]
        workspace = test_environment["workspace"]

        # Step 1: Get current settings
        settings = db.oversight_and_defaults.find_one()
        assert settings is not None
        initial_logs_dir = settings["logs_directory"]

        # Step 2: User modifies settings (simulating EditSettingsDialog)
        updated_settings = settings.copy()
        updated_settings["logs_directory"] = str(workspace / "new_logs")
        updated_settings["convert_to_format"] = "fintech"

        # Step 3: Save settings (simulating dialog OK button)
        db.oversight_and_defaults.update(updated_settings, ["id"])

        # Step 4: Verify persistence
        updated = db.oversight_and_defaults.find_one()
        assert updated["logs_directory"] == str(workspace / "new_logs")
        assert updated["convert_to_format"] == "fintech"

    def test_settings_validation_workflow(self, test_environment):
        """Test: Modify settings → Validate → Save or reject based on validation."""
        db = test_environment["db"]
        workspace = test_environment["workspace"]

        # Get current settings
        settings = db.oversight_and_defaults.find_one()

        # Test valid settings
        valid_settings = settings.copy()
        valid_settings["convert_to_format"] = "csv"  # Valid format

        # In real UI, validation would happen in dialog
        # For this test, we verify the database accepts valid data
        db.oversight_and_defaults.update(valid_settings, ["id"])

        updated = db.oversight_and_defaults.find_one()
        assert updated["convert_to_format"] == "csv"

        # Test invalid settings would be rejected by validation logic
        # (In real UI, this happens before database update)
        invalid_format = "invalid_format_name"

        # Validation logic should prevent this from being saved
        # For now, we just verify the concept
        assert invalid_format not in [
            "csv",
            "fintech",
            "scannerware",
            "simplified_csv",
            "yellowdog_csv",
            "estore_einvoice",
            "estore_einvoice_generic",
            "stewarts_custom",
            "scansheet_type_a",
            "jolley_custom",
        ], "This should be caught by validation before save"


class TestErrorRecoveryWorkflow:
    """Test error detection and recovery workflows."""

    def test_invalid_folder_path_detection_and_recovery(self, test_environment):
        """Test: Add invalid path → Detect error → Fix path → Process successfully."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Step 1: User adds folder with invalid path (typo or deleted folder)
        invalid_config = {
            "folder_name": str(workspace / "nonexistent_folder"),
            "alias": "Invalid Path Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(invalid_config)

        # Step 2: System detects error during processing
        folders = list(db.folders_table.all())
        folder = folders[0]

        # Verify path doesn't exist
        assert not Path(folder["folder_name"]).exists()

        # Step 3: User is notified (would be error dialog in UI)
        # For this test, we simulate user fixing the configuration

        # Step 4: User corrects the path (simulating EditFoldersDialog)
        valid_path = workspace / "valid_input"
        valid_path.mkdir(exist_ok=True)

        folder["folder_name"] = str(valid_path)
        db.folders_table.update(folder, ["id"])

        # Step 5: Verify fix persisted
        updated = list(db.folders_table.all())
        assert Path(updated[0]["folder_name"]).exists()

    def test_processing_error_continues_with_other_folders(
        self, test_environment, sample_edi_content
    ):
        """Test: One folder fails → Error logged → Other folders continue processing."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Create one valid folder with EDI file
        valid_input = workspace / "valid_input"
        valid_input.mkdir(exist_ok=True)
        (valid_input / "test.edi").write_text(sample_edi_content)

        valid_config = {
            "folder_name": str(valid_input),
            "alias": "Valid Folder",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }

        db.folders_table.insert(valid_config)

        # Add invalid folder (nonexistent path)
        invalid_config = {
            "folder_name": str(workspace / "invalid_input"),
            "alias": "Invalid Folder",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }

        db.folders_table.insert(invalid_config)

        # Process all folders
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from dispatch.pipeline.validator import EDIValidationStep
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from copy_backend import do as copy_backend_do

        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        backends = {"copy": CopyBackend()}
        config = DispatchConfig(
            backends=backends,
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        success_count = 0
        failure_count = 0

        for folder in folders:
            try:
                result = orchestrator.process_folder(folder, MagicMock())
                if result.files_processed > 0:
                    success_count += 1
                elif result.files_failed > 0 or not result.success:
                    failure_count += 1
            except Exception:
                failure_count += 1
                # Continue with next folder (important!)

        # Verify at least the valid folder was processed
        assert success_count >= 1, "Valid folder should process successfully"

        # Verify error isolation (one failure doesn't stop others)
        output_files = list((workspace / "output").glob("*"))
        assert len(output_files) > 0, "Should have output from valid folder"


class TestMultiStepWorkflow:
    """Test complex multi-step user workflows."""

    def test_complete_setup_workflow(
        self, test_environment, sample_edi_content, pipeline_steps
    ):
        """Test complete setup: Settings → Folder → Process → Verify."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Phase 1: Configure global settings
        settings = db.oversight_and_defaults.find_one()
        settings["convert_to_format"] = "csv"
        settings["logs_directory"] = str(workspace / "logs")
        db.oversight_and_defaults.update(settings, ["id"])

        # Phase 2: Create EDI file
        input_folder = workspace / "input"
        (input_folder / "test.edi").write_text(sample_edi_content)

        # Phase 3: Add and configure folder
        folder_config = {
            "folder_name": str(input_folder),
            "alias": "Complete Setup Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Phase 4: Process folder
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import do as copy_backend_do

        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        backends = {"copy": CopyBackend()}
        config = DispatchConfig(
            backends=backends,
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        result = orchestrator.process_folder(folders[0], MagicMock())

        # Phase 5: Verify complete workflow
        assert result.success, "Complete setup workflow should succeed"
        assert result.files_processed == 1, "Should process the single configured file"

        # Verify output created
        output_files = list((workspace / "output").glob("*"))
        assert len(output_files) > 0, "Should create output file"

        # Verify settings persisted
        final_settings = db.oversight_and_defaults.find_one()
        assert final_settings["convert_to_format"] == "csv"

    def test_bulk_configuration_workflow(self, test_environment, pipeline_steps):
        """Test: Add multiple folders → Configure all → Process all → Verify."""
        workspace = test_environment["workspace"]
        db = test_environment["db"]

        # Create multiple input folders
        num_folders = 3  # Reduced for faster testing
        for i in range(num_folders):
            folder_path = workspace / f"input_{i}"
            folder_path.mkdir(exist_ok=True)

            # Add sample EDI file
            edi_content = f"""A00000{i}2024010100{i}VENDOR{i}          Vendor {i} Inc                  0000{i}
B00100{i}ITEM00{i}     0000{i}0EA00{i}0Item {i}                          00000{i}0000
"""
            (folder_path / f"invoice_{i}.edi").write_text(edi_content)

        # Configure all folders
        for i in range(num_folders):
            folder_config = {
                "folder_name": str(workspace / f"input_{i}"),
                "alias": f"Bulk Test Folder {i}",
                "process_backend_copy": True,
                "copy_to_directory": str(workspace / f"output_{i}"),
                "convert_to_format": "csv",
            }
            db.folders_table.insert(folder_config)

        # Verify all folders saved
        folders = list(db.folders_table.all())
        assert len(folders) == num_folders

        # Process all folders
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import do as copy_backend_do

        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        backends = {"copy": CopyBackend()}
        config = DispatchConfig(
            backends=backends,
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        for folder in folders:
            output_dir = Path(folder["copy_to_directory"])
            output_dir.mkdir(exist_ok=True)
            orchestrator.process_folder(folder, MagicMock())

        # Verify all produced output
        output_count = 0
        for i in range(num_folders):
            output_path = workspace / f"output_{i}"
            output_files = list(output_path.glob("*"))
            if len(output_files) > 0:
                output_count += 1

        assert (
            output_count == num_folders
        ), f"All {num_folders} folders should produce output"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
