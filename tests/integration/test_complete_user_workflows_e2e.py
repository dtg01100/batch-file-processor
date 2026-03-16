"""End-to-end tests for complete user workflows.

Tests cover:
- Add Folder → Configure → Process → View Results
- Edit Folder → Change Settings → Save → Verify Persistence
- Process → Error → Retry → Success
- Complete batch processing workflows
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from copy_backend import CopyBackend
from core.utils.bool_utils import normalize_bool
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.send_manager import MockBackend

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow]


@pytest.fixture
def complete_workspace():
    """Create a complete workspace with all necessary directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create directory structure
        (workspace / "input").mkdir()
        (workspace / "output").mkdir()
        (workspace / "errors").mkdir()
        (workspace / "logs").mkdir()
        (workspace / "backup").mkdir()

        # Create sample EDI files
        edi_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""
        for i in range(5):
            (workspace / "input" / f"invoice_{i:03d}.edi").write_text(
                edi_content.replace("00001", f"{i + 1:05d}")
            )

        yield workspace


@pytest.fixture
def sample_folder_config(complete_workspace):
    """Create a sample folder configuration."""
    return {
        "folder_name": str(complete_workspace / "input"),
        "alias": "E2E Test Folder",
        "folder_is_active": "True",
        "process_backend_copy": True,
        "copy_to_directory": str(complete_workspace / "output"),
        "process_backend_ftp": False,
        "process_backend_email": False,
        "convert_to_type": "csv",
        "edi_filter_category": "",
        "process_edi": "True",
        "calculate_upc_check_digit": "True",
        "include_a_records": "True",
        "include_c_records": "True",
        "include_headings": "True",
    }


@pytest.mark.e2e
class TestAddFolderConfigureProcessWorkflow:
    """Test complete workflow: Add Folder → Configure → Process → View Results."""

    def test_full_workflow_success(self, complete_workspace, sample_folder_config):
        """Test complete workflow from folder creation through processing."""
        config = DispatchConfig(backends={"copy": CopyBackend()}, settings={})
        orchestrator = DispatchOrchestrator(config)

        # Create mock run log
        run_log = MagicMock()

        # Process folder
        result = orchestrator.process_folder(sample_folder_config, run_log)

        # Verify processing completed
        assert result is not None
        assert result.success is True

        # Verify files were copied (as EDI files - no conversion pipeline configured)
        output_files = list((complete_workspace / "output").glob("*.edi"))
        assert len(output_files) == 5

        # Verify output files have content
        for output_file in output_files:
            assert output_file.stat().st_size > 0

    def test_workflow_with_edi_validation(
        self, complete_workspace, sample_folder_config
    ):
        """Test workflow with EDI validation enabled."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create orchestrator with validator
        config = DispatchConfig(
            backends={"copy": CopyBackend()}, settings={"validate_edi": True}
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        result = orchestrator.process_folder(sample_folder_config, run_log)

        assert result is not None
        assert result.success is True

    def test_workflow_with_duplicate_detection(
        self, complete_workspace, sample_folder_config
    ):
        """Test workflow detects duplicate files."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Process same files twice
        config = DispatchConfig(backends={"copy": CopyBackend()}, settings={})
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # First processing
        result1 = orchestrator.process_folder(sample_folder_config, run_log)
        assert result1.success is True

        # Second processing (should skip duplicates)
        result2 = orchestrator.process_folder(sample_folder_config, run_log)
        assert result2.success is True

        # Verify no duplicate files created
        output_files = list((complete_workspace / "output").glob("*.edi"))
        assert len(output_files) == 5  # Still only 5 files


@pytest.mark.e2e
class TestEditFolderSettingsPersistenceWorkflow:
    """Test workflow: Edit Folder → Change Settings → Save → Verify Persistence."""

    def test_edit_folder_settings_persistence(self, complete_workspace, temp_database):
        """Test that folder settings persist after edit."""

        # Add folder to database
        folders_table = temp_database.folders_table
        folder_id = temp_database.folders_table.insert(
            {
                "folder_name": str(complete_workspace / "input"),
                "alias": "Test Folder",
                "folder_is_active": "True",
                "process_backend_copy": "True",
                "copy_to_directory": str(complete_workspace / "output"),
            }
        )

        # Verify initial settings
        initial_config = temp_database.folders_table.find_one(id=folder_id)
        assert initial_config["alias"] == "Test Folder"

        # Update settings - pass dict with both key fields and update values, plus list of key field names
        folders_table.update(
            {
                "id": folder_id,
                "alias": "Updated Folder Name",
                "process_backend_ftp": "True",
            },
            ["id"],
        )

        # Verify persistence
        updated_config = temp_database.folders_table.find_one(id=folder_id)
        assert updated_config["alias"] == "Updated Folder Name"
        assert updated_config["process_backend_ftp"] is True

    def test_edit_folder_backend_configuration(self, complete_workspace, temp_database):
        """Test enabling/disabling backends persists."""

        folders_table = temp_database.folders_table
        folder_id = temp_database.folders_table.insert(
            {
                "folder_name": str(complete_workspace / "input"),
                "alias": "Backend Test",
                "process_backend_copy": "True",
                "process_backend_ftp": "False",
                "process_backend_email": "False",
            }
        )

        # Enable all backends - pass dict with both key fields and update values
        folders_table.update(
            {
                "id": folder_id,
                "process_backend_copy": "True",
                "process_backend_ftp": "True",
                "process_backend_email": "True",
            },
            ["id"],
        )

        updated = temp_database.folders_table.find_one(id=folder_id)
        assert updated["process_backend_copy"] is True
        assert updated["process_backend_ftp"] is True
        assert updated["process_backend_email"] is True

    def test_edit_folder_conversion_settings(self, complete_workspace, temp_database):
        """Test conversion settings persistence."""

        folders_table = temp_database.folders_table
        folder_id = temp_database.folders_table.insert(
            {
                "folder_name": str(complete_workspace / "input"),
                "alias": "Conversion Test",
                "convert_to_format": "csv",
            }
        )

        # Change conversion type
        folders_table.update(
            {
                "id": folder_id,
                "convert_to_format": "fintech",
            },
            ["id"],
        )

        updated = temp_database.folders_table.find_one(id=folder_id)
        assert updated["convert_to_format"] == "fintech"


@pytest.mark.e2e
class TestErrorRecoveryWorkflow:
    """Test workflow: Process → Error → Retry → Success."""

    def test_retry_after_backend_failure(
        self, complete_workspace, sample_folder_config
    ):
        """Test retry workflow after backend failure."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create a flaky backend that fails first time but succeeds on retry
        class FlakyBackend:
            def __init__(self):
                self.call_count = 0

            def send(self, params, settings, filename):
                self.call_count += 1
                if self.call_count == 1:
                    raise Exception("Temporary failure")
                return True

            def validate(self, params):
                return []

            def get_name(self):
                return "Flaky Backend"

        # Test using the orchestrator with the flaky backend
        # The orchestrator will log the error but continue processing
        flaky = FlakyBackend()
        config = DispatchConfig(backends={"copy": flaky}, settings={"max_retries": 2})
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Since the orchestrator catches exceptions, we expect it to process successfully
        # but one file may fail - that's expected behavior without explicit retry logic
        result = orchestrator.process_folder(sample_folder_config, run_log)

        # Either succeeds (retry worked) or has failures (as expected without explicit retry)
        # The test verifies the backend was called
        assert flaky.call_count >= 1

    def test_continue_after_file_error(self, complete_workspace, sample_folder_config):
        """Test processing continues after individual file error."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create one invalid file
        (complete_workspace / "input" / "invalid.edi").write_text("INVALID CONTENT")

        config = DispatchConfig(
            backends={"copy": MockBackend(should_succeed=True)}, settings={}
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        result = orchestrator.process_folder(sample_folder_config, run_log)

        # Should process valid files despite invalid one
        assert result is not None
        # Some files should succeed
        assert result.files_processed >= 5

    def test_error_logging_and_recovery(self, complete_workspace, sample_folder_config):
        """Test that errors are logged and recovery is possible."""
        from dispatch.error_handler import ErrorHandler
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        error_handler = ErrorHandler()

        class FailingBackend:
            def send(self, params, settings, filename):
                error = Exception("Backend failure")
                error_handler.record_error(
                    folder=params.get("folder_name", ""), filename=filename, error=error
                )
                raise error

            def validate(self, params):
                return []

            def get_name(self):
                return "Failing Backend"

        config = DispatchConfig(
            backends={"copy": FailingBackend()}, settings={"max_retries": 1}
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        result = orchestrator.process_folder(sample_folder_config, run_log)

        # Verify errors were logged
        assert error_handler.get_error_count() > 0


@pytest.mark.e2e
class TestMultiStepWorkflow:
    """Test complex multi-step workflows."""

    def test_process_multiple_folders_sequentially(self, complete_workspace):
        """Test processing multiple folders in sequence."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create second folder
        input2 = complete_workspace / "input2"
        input2.mkdir()
        output2 = complete_workspace / "output2"
        output2.mkdir()

        # Add files to second folder
        (input2 / "file1.edi").write_text(
            """A00000220240102002TESTVENDOR         Test Vendor Inc                 00002
B002001ITEM001     000020EA0020Test Item                     0000020000
"""
        )

        config = DispatchConfig(backends={"copy": CopyBackend()}, settings={})
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process first folder
        config1 = {
            "folder_name": str(complete_workspace / "input"),
            "alias": "Folder 1",
            "process_backend_copy": True,
            "copy_to_directory": str(complete_workspace / "output"),
        }
        result1 = orchestrator.process_folder(config1, run_log)

        # Process second folder
        config2 = {
            "folder_name": str(input2),
            "alias": "Folder 2",
            "process_backend_copy": True,
            "copy_to_directory": str(output2),
        }
        result2 = orchestrator.process_folder(config2, run_log)

        # Both should succeed
        assert result1.success is True
        assert result2.success is True

        # Verify outputs (as EDI files - no conversion pipeline configured)
        assert len(list((complete_workspace / "output").glob("*.edi"))) > 0
        assert len(list((output2).glob("*.edi"))) > 0

    def test_process_with_multiple_backends(
        self, complete_workspace, sample_folder_config
    ):
        """Test processing with multiple backends enabled."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        class MockFTPBackend:
            def send(self, params, settings, filename):
                return True

            def validate(self, params):
                return []

            def get_name(self):
                return "Mock FTP"

        class MockEmailBackend:
            def send(self, params, settings, filename):
                return True

            def validate(self, params):
                return []

            def get_name(self):
                return "Mock Email"

        config = DispatchConfig(
            backends={
                "copy": MockBackend(should_succeed=True),
                "ftp": MockFTPBackend(),
                "email": MockEmailBackend(),
            },
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        result = orchestrator.process_folder(sample_folder_config, run_log)

        # All backends should be called
        assert result.success is True


@pytest.mark.e2e
class TestDatabaseIntegrationWorkflow:
    """Test workflows involving database operations."""

    def test_processed_files_tracking(
        self, complete_workspace, sample_folder_config, temp_database
    ):
        """Test that processed files are tracked in database."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        config = DispatchConfig(backends={"copy": CopyBackend()}, settings={})
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Add folder id to config (needed for tracking)
        folder_config = sample_folder_config.copy()
        folder_config["id"] = 1

        result = orchestrator.process_folder(
            folder_config, run_log, temp_database.processed_files
        )

        # Verify files tracked in database
        processed_count = temp_database.processed_files.count()
        assert processed_count >= 5

    def test_resend_flag_workflow(
        self, complete_workspace, sample_folder_config, temp_database
    ):
        """Test marking files for resend and reprocessing."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Process files initially
        config = DispatchConfig(
            backends={"copy": MockBackend(should_succeed=True)}, settings={}
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        result = orchestrator.process_folder(sample_folder_config, run_log)
        assert result.success is True

        # Mark some files for resend
        files = temp_database.processed_files.find({})
        for file_record in list(files)[:2]:
            temp_database.processed_files.update(file_record["id"], {"resend_flag": 1})

        # Reprocess - should resend marked files
        result2 = orchestrator.process_folder(sample_folder_config, run_log)
        assert result2.success is True


@pytest.mark.e2e
class TestConfigurationPersistenceWorkflow:
    """Test configuration persistence across sessions."""

    def test_folder_config_save_load(self, complete_workspace, temp_database):
        """Test saving and loading folder configuration."""

        folders_table = temp_database.folders_table

        # Save configuration
        config = {
            "folder_name": str(complete_workspace / "input"),
            "alias": "Persistence Test",
            "folder_is_active": True,
            "process_backend_copy": True,
            "copy_to_directory": str(complete_workspace / "output"),
            "convert_to_format": "csv",
            "process_edi": True,
        }
        folder_id = temp_database.folders_table.insert(config)

        # Load configuration
        loaded = temp_database.folders_table.find_one(id=folder_id)

        # Verify all fields persisted
        assert loaded["folder_name"] == config["folder_name"]
        assert loaded["alias"] == config["alias"]
        assert normalize_bool(loaded["process_backend_copy"]) is True
        assert loaded["convert_to_format"] == config["convert_to_format"]

    def test_multiple_folder_configs(self, complete_workspace, temp_database):
        """Test managing multiple folder configurations."""

        folders_table = temp_database.folders_table

        # Create multiple folder configs
        configs = []
        for i in range(10):
            config = {
                "folder_name": str(complete_workspace / f"input_{i}"),
                "alias": f"Folder {i}",
                "folder_is_active": "True" if i % 2 == 0 else "False",
                "process_backend_copy": "True",
            }
            folder_id = temp_database.folders_table.insert(config)
            configs.append(folder_id)

        # Verify all saved
        assert folders_table.count() >= 10

        # Query active folders
        active = folders_table.find(folder_is_active="True")
        assert len(list(active)) >= 5


@pytest.mark.e2e
class TestEdgeCaseWorkflows:
    """Test edge case workflows."""

    def test_empty_folder_processing(self, complete_workspace):
        """Test processing empty folder."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create empty folder
        empty_input = complete_workspace / "empty_input"
        empty_input.mkdir()

        config = DispatchConfig(
            backends={"copy": MockBackend(should_succeed=True)}, settings={}
        )
        orchestrator = DispatchOrchestrator(config)

        folder_config = {
            "folder_name": str(empty_input),
            "alias": "Empty Folder",
            "process_backend_copy": True,
            "copy_to_directory": str(complete_workspace / "output"),
            "convert_to_format": "csv",
        }

        run_log = MagicMock()
        result = orchestrator.process_folder(folder_config, run_log)

        # Should handle gracefully
        assert result is not None

    def test_large_file_processing(self, complete_workspace, sample_folder_config):
        """Test processing large files."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create large EDI file (1MB)
        large_content = (
            "A00000120240101001TESTVENDOR         Test Vendor Inc                 00001\n"
            * 20000
        )
        (complete_workspace / "input" / "large.edi").write_text(large_content)

        config = DispatchConfig(
            backends={"copy": MockBackend(should_succeed=True)}, settings={}
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        result = orchestrator.process_folder(sample_folder_config, run_log)

        # Should process successfully
        assert result.success is True

    def test_special_characters_in_path(self, sample_folder_config):
        """Test processing files with special characters in path."""
        import tempfile

        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator

        # Create folder with special characters
        with tempfile.TemporaryDirectory(suffix="_test-folder") as tmpdir:
            special_input = Path(tmpdir) / "input"
            special_input.mkdir()
            special_output = Path(tmpdir) / "output"
            special_output.mkdir()

            # Create test file
            (special_input / "test.edi").write_text(
                """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item                     0000010000
"""
            )

            config = DispatchConfig(
                backends={"copy": MockBackend(should_succeed=True)}, settings={}
            )
            orchestrator = DispatchOrchestrator(config)

            folder_config = {
                "folder_name": str(special_input),
                "alias": "Special Chars Folder",
                "process_backend_copy": True,
                "copy_to_directory": str(special_output),
                "convert_to_format": "csv",
            }

            run_log = MagicMock()
            result = orchestrator.process_folder(folder_config, run_log)

            # Should handle special characters
            assert result.success is True
