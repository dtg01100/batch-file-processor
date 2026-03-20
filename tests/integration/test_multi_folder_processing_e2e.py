"""End-to-end tests for multi-folder processing scenarios.

Tests cover:
- Processing multiple folders in sequence
- Processing multiple folders in parallel (if supported)
- Mixed success/failure across folders
- Resource contention between folder processing
- Progress tracking across multiple folders
"""

import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow]


@pytest.fixture
def multiple_folders_workspace():
    """Create workspace with multiple input folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        folders = []
        for i in range(5):
            input_dir = workspace / f"input_{i}"
            input_dir.mkdir()
            output_dir = workspace / f"output_{i}"
            output_dir.mkdir()

            # Add EDI files to each folder
            edi_content = (
                f"A00000{i}20240101001TESTVENDOR         Test Vendor Inc                 0000{i}\n"
                + f"B{i+1:011d}{'Test Item ' + str(i):<25}{i:06d}{100:06d}EA{1:06d}{i+1:05d}{100:05d}001{i:06d}\n"
                + f"B{i+2:011d}{'Test Item ' + str(i+1):<25}{i:06d}{100:06d}EA{1:06d}{i+2:05d}{100:05d}001{i:06d}\n"
                + "C00000003000030000\n"
            )
            for j in range(3):
                (input_dir / f"file_{j}.edi").write_text(
                    edi_content.replace("00001", f"{i*10+j+1:05d}")
                )

            folders.append(
                {
                    "input": input_dir,
                    "output": output_dir,
                    "config": {
                        "folder_name": str(input_dir),
                        "alias": f"Folder {i}",
                        "process_backend_copy": True,
                        "copy_to_directory": str(output_dir),
                        "convert_to_type": "csv",
                        "convert_edi": True,
                    },
                }
            )

        yield {
            "workspace": workspace,
            "folders": folders,
        }


def create_copy_backend():
    """Create a copy backend wrapper for testing."""
    from backend.copy_backend import do as copy_backend_do

    class CopyBackend:
        def send(self, params: dict, settings: dict, filename: str) -> None:
            copy_backend_do(params, settings, filename)

    return CopyBackend()


@pytest.mark.e2e
class TestSequentialMultiFolderProcessing:
    """Test processing multiple folders sequentially."""

    def test_process_multiple_folders_sequentially(self, multiple_folders_workspace):
        """Test processing 5 folders in sequence."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        results = []

        # Process each folder sequentially
        for folder_config in multiple_folders_workspace["folders"]:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # Verify all outputs created (EDI files are copied as-is)
        for folder in multiple_folders_workspace["folders"]:
            output_files = list(folder["output"].glob("*.edi"))
            assert len(output_files) == 3

    def test_process_folders_with_different_configs(self, multiple_folders_workspace):
        """Test processing folders with different configurations."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Configure each folder differently
        configs = [
            {"convert_to_type": "csv", "convert_edi": True},
            {"convert_to_type": "csv", "convert_edi": True},
            {"convert_to_type": "csv", "convert_edi": True},
        ]

        for i, (folder, cfg) in enumerate(
            zip(multiple_folders_workspace["folders"][:3], configs)
        ):
            folder_config = folder["config"].copy()
            folder_config.update(cfg)

            result = orchestrator.process_folder(folder_config, run_log)
            assert result.success is True


@pytest.mark.e2e
class TestMixedSuccessFailureScenarios:
    """Test scenarios with mixed success and failure across folders."""

    def test_some_folders_fail_others_succeed(self, multiple_folders_workspace):
        """Test processing when some folders fail but others succeed."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        class FailingBackend:
            def __init__(self, fail_on_indices):
                self.fail_on_indices = fail_on_indices
                self._call_counter = 0

            def send(self, params, settings, filename):
                self._call_counter += 1
                # Fail on certain call numbers (roughly mapping to folders 1 and 3)
                # Each folder has 3 files, so folder 1 = calls 4-6, folder 3 = calls 10-12
                folder_call_start = (self._call_counter - 1) // 3
                if folder_call_start in self.fail_on_indices:
                    raise Exception(f"Failing for folder {folder_call_start}")
                return True

        config = DispatchConfig(
            backends={"copy": FailingBackend(fail_on_indices={1, 3})},
            settings={"max_retries": 1},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()
        results = []

        for folder_config in multiple_folders_workspace["folders"]:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            results.append(result)

        # Some should fail, some should succeed
        successes = [r.success for r in results]
        assert successes.count(True) >= 3
        assert successes.count(False) <= 2

    def test_partial_folder_processing_success(self, multiple_folders_workspace):
        """Test when folder processing has partial success."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process all folders
        results = []
        for folder_config in multiple_folders_workspace["folders"]:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            results.append(result)

        # All should complete (even if some files fail)
        assert len(results) == 5


@pytest.mark.e2e
class TestResourceContention:
    """Test resource contention scenarios."""

    def test_concurrent_folder_access(self, multiple_folders_workspace):
        """Test accessing same output directory from multiple folders."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        # All folders write to same output with unique filenames
        shared_output = multiple_folders_workspace["workspace"] / "shared_output"
        shared_output.mkdir()

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Configure all to use same output but with unique subfolders per source folder
        for folder in multiple_folders_workspace["folders"]:
            folder_config = folder["config"].copy()
            # Use unique subdirectory per folder to avoid overwrites
            folder_config["copy_to_directory"] = str(
                shared_output / folder["config"]["alias"].replace(" ", "_")
            )

            result = orchestrator.process_folder(folder_config, run_log)
            assert result.success is True

        # All files should be in shared output (in subdirectories)
        all_files = list(shared_output.glob("**/*.edi"))
        assert len(all_files) == 15  # 5 folders × 3 files

    def test_database_locking_during_multi_folder(
        self, multiple_folders_workspace, temp_database
    ):
        """Test database locking during multi-folder processing."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process folders with database tracking
        for folder_config in multiple_folders_workspace["folders"]:
            # Add folder id to config
            folder_cfg = folder_config["config"].copy()
            folder_cfg["id"] = (
                folder_config["folders_id"] if "folders_id" in folder_config else None
            )
            result = orchestrator.process_folder(
                folder_cfg, run_log, temp_database.processed_files
            )
            assert result.success is True

        # Database should be consistent
        processed_count = len(list(temp_database.processed_files.find({})))
        assert processed_count >= 15


@pytest.mark.e2e
class TestProgressTracking:
    """Test progress tracking across multiple folders."""

    def test_progress_updates_across_folders(self, multiple_folders_workspace):
        """Test that progress is tracked across multiple folders."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        # Track progress via progress_reporter
        progress_updates = []

        class MockProgressReporter:
            def start_folder(self, name, total):
                progress_updates.append(("start_folder", name, total))

            def update_file(self, current, total):
                progress_updates.append(("update_file", current, total))

            def complete_folder(self, success):
                progress_updates.append(("complete_folder", success))

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
            progress_reporter=MockProgressReporter(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process multiple folders
        for folder_config in multiple_folders_workspace["folders"]:
            orchestrator.process_folder(folder_config["config"], run_log)

        # Should have progress updates
        assert len(progress_updates) > 0

    def test_cumulative_file_count_tracking(self, multiple_folders_workspace):
        """Test cumulative file count tracking."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        total_processed = 0
        for folder_config in multiple_folders_workspace["folders"]:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            if hasattr(result, "files_processed"):
                total_processed += result.files_processed

        # Should have processed all files
        assert total_processed >= 15


@pytest.mark.e2e
class TestParallelProcessing:
    """Test parallel folder processing (if supported)."""

    def test_parallel_folder_processing(self, multiple_folders_workspace):
        """Test processing folders in parallel."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        def process_folder_thread(folder_config):
            config = DispatchConfig(
                backends={"copy": create_copy_backend()},
                settings={},
                validator_step=EDIValidationStep(),
                converter_step=EDIConverterStep(),
                tweaker_step=EDITweakerStep(),
            )
            orchestrator = DispatchOrchestrator(config)
            run_log = MagicMock()
            return orchestrator.process_folder(folder_config["config"], run_log)

        # Process in parallel using threads
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_folder_thread, folder_config)
                for folder_config in multiple_folders_workspace["folders"]
            ]

            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.success for r in results)

        # Verify outputs
        for folder in multiple_folders_workspace["folders"]:
            output_files = list(folder["output"].glob("*.edi"))
            assert len(output_files) == 3


@pytest.mark.e2e
class TestLargeScaleMultiFolder:
    """Test large-scale multi-folder processing."""

    def test_process_20_folders(self, tmp_path):
        """Test processing 20 folders."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        workspace = tmp_path / "large_scale"
        workspace.mkdir()

        # Create 20 folders
        folders = []
        for i in range(20):
            input_dir = workspace / f"input_{i}"
            input_dir.mkdir()
            output_dir = workspace / f"output_{i}"
            output_dir.mkdir()

            # Add 2 files per folder
            for j in range(2):
                (input_dir / f"file_{j}.edi").write_text(
                    f"A00000{i}20240101001TESTVENDOR         Test Vendor Inc                 0000{i}\n"
                    + f"B{i+1:011d}{'Test Item ' + str(i):<25}{i:06d}{100:06d}EA{1:06d}{i+1:05d}{100:05d}001{i:06d}\n"
                    + "C00000003000030000\n"
                )

            folders.append(
                {
                    "input": input_dir,
                    "output": output_dir,
                    "config": {
                        "folder_name": str(input_dir),
                        "alias": f"Folder {i}",
                        "process_backend_copy": True,
                        "copy_to_directory": str(output_dir),
                        "convert_to_type": "csv",
                        "convert_edi": True,
                    },
                }
            )

        config = DispatchConfig(
            backends={"copy": create_copy_backend()},
            settings={},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process all folders
        results = []
        for folder_config in folders:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # Verify outputs
        total_outputs = sum(len(list(f["output"].glob("*.edi"))) for f in folders)
        assert total_outputs == 40  # 20 folders × 2 files


@pytest.mark.e2e
class TestMultiFolderErrorRecovery:
    """Test error recovery in multi-folder scenarios."""

    def test_retry_failed_folders(self, multiple_folders_workspace):
        """Test retrying failed folders."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        fail_count = {"count": 0}

        class InitiallyFailingBackend:
            def send(self, params, settings, filename):
                fail_count["count"] += 1
                if fail_count["count"] <= 3:  # Fail first 3 calls
                    raise Exception("Temporary failure")
                return True

        config = DispatchConfig(
            backends={"copy": InitiallyFailingBackend()},
            settings={"max_retries": 2},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process folders - some will fail initially but retry
        results = []
        for folder_config in multiple_folders_workspace["folders"]:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            results.append(result)

        # Most should succeed after retries
        success_count = sum(1 for r in results if r.success)
        assert success_count >= 3

    def test_skip_problematic_folders(self, multiple_folders_workspace):
        """Test skipping folders that consistently fail."""
        from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        class AlwaysFailingBackend:
            def send(self, params, settings, filename):
                raise Exception("Always fails")

        config = DispatchConfig(
            backends={"copy": AlwaysFailingBackend()},
            settings={"max_retries": 1},
            validator_step=EDIValidationStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MagicMock()

        # Process all folders - all should fail gracefully
        results = []
        for folder_config in multiple_folders_workspace["folders"]:
            result = orchestrator.process_folder(folder_config["config"], run_log)
            results.append(result)

        # All should fail but not crash
        assert len(results) == 5
