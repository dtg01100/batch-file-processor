"""Tests for dispatch.services.folder_processor module."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import Mock

from dispatch.services.folder_processor import (
    FolderPipelineExecutor,
    FolderProcessingDependencies,
    FolderProcessingRequest,
)


class TestFolderProcessingRequest:
    """Tests for FolderProcessingRequest dataclass."""

    def test_default_values(self):
        """Test default values for request."""
        request = FolderProcessingRequest(
            folder={"folder_name": "/test"},
            run_log=Mock(),
        )

        assert request.processed_files is None
        assert request.upc_dict is None
        assert request.pre_discovered_files is None
        assert request.folder_num is None
        assert request.folder_total is None

    def test_all_values_specified(self):
        """Test specifying all values."""
        request = FolderProcessingRequest(
            folder={"folder_name": "/test", "alias": "Test"},
            run_log=Mock(),
            processed_files=Mock(),
            upc_dict={"upc": "123"},
            pre_discovered_files=["/file1.txt", "/file2.txt"],
            folder_num=1,
            folder_total=5,
        )

        assert request.folder["alias"] == "Test"
        assert request.upc_dict == {"upc": "123"}
        assert len(request.pre_discovered_files) == 2
        assert request.folder_num == 1
        assert request.folder_total == 5


class TestFolderProcessingDependencies:
    """Tests for FolderProcessingDependencies dataclass."""

    def test_default_values(self):
        """Test default values for dependencies."""
        deps = FolderProcessingDependencies()

        assert deps.file_processor is None
        assert deps.progress_reporter is None
        assert deps.get_upc_dictionary is None

    def test_with_values(self):
        """Test specifying dependencies."""
        mock_processor = Mock()
        mock_reporter = Mock()
        mock_upc_func = Mock(return_value={"upc": "123"})

        deps = FolderProcessingDependencies(
            file_processor=mock_processor,
            progress_reporter=mock_reporter,
            get_upc_dictionary=mock_upc_func,
        )

        assert deps.file_processor is mock_processor
        assert deps.progress_reporter is mock_reporter
        assert deps.get_upc_dictionary is mock_upc_func


class MockFileProcessor:
    """Mock file processor for testing."""

    def __init__(self, results: list | None = None):
        self.results = results or []
        self.call_count = 0

    def _build_context(self, folder, upc_dict, effective_folder=None):
        """Build a mock processing context."""
        from dispatch.services.file_processor import ProcessingContext

        return ProcessingContext(
            folder=folder,
            effective_folder=effective_folder if effective_folder else folder,
            settings={},
            upc_dict=upc_dict,
        )

    def process_file(self, **kwargs):
        if self.results and self.call_count < len(self.results):
            result = self.results[self.call_count]
            self.call_count += 1
            return result
        return Mock(sent=True, file_name="/test.txt", checksum="abc123")


class TestFolderPipelineExecutor:
    """Tests for FolderPipelineExecutor class."""

    def test_folder_exists_check(self):
        """Test _folder_exists returns correct result."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        with tempfile.TemporaryDirectory() as tmpdir:
            assert executor._folder_exists(tmpdir) is True
            assert executor._folder_exists("/nonexistent/path") is False

    def test_get_files_in_folder(self):
        """Test _get_files_in_folder returns files."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            open(test_file, "w").close()

            files = executor._get_files_in_folder(tmpdir)

            assert len(files) == 1
            assert files[0] == test_file

    def test_get_files_in_empty_folder(self):
        """Test _get_files_in_folder with empty directory."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        with tempfile.TemporaryDirectory() as tmpdir:
            files = executor._get_files_in_folder(tmpdir)
            assert files == []

    def test_calculate_file_checksum(self):
        """Test _calculate_file_checksum computes MD5."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()
            filepath = f.name

        try:
            checksum = executor._calculate_file_checksum(filepath)
            assert len(checksum) == 32
            assert checksum.isalnum()
        finally:
            os.unlink(filepath)

    def test_process_folder_nonexistent_folder(self):
        """Test processing a nonexistent folder returns error."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        request = FolderProcessingRequest(
            folder={"folder_name": "/nonexistent/path"},
            run_log=Mock(),
        )

        result = executor.process_folder(request)

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
        assert result.files_failed == 1

    def test_process_folder_empty_folder(self):
        """Test processing an empty folder returns success with zero files."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        with tempfile.TemporaryDirectory() as tmpdir:
            request = FolderProcessingRequest(
                folder={"folder_name": tmpdir},
                run_log=Mock(),
            )

            result = executor.process_folder(request)

            assert result.success is True
            assert result.files_processed == 0
            assert result.files_failed == 0

    def test_process_folder_with_files(self):
        """Test processing folder with files uses file processor."""
        mock_processor = MockFileProcessor(
            [
                Mock(sent=True, file_name="/test1.txt", checksum="abc"),
                Mock(sent=True, file_name="/test2.txt", checksum="def"),
            ]
        )
        deps = FolderProcessingDependencies(file_processor=mock_processor)
        executor = FolderPipelineExecutor(deps)

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "test1.txt")
            file2 = os.path.join(tmpdir, "test2.txt")
            open(file1, "w").close()
            open(file2, "w").close()

            request = FolderProcessingRequest(
                folder={"folder_name": tmpdir, "id": 1},
                run_log=Mock(),
            )

            result = executor.process_folder(request)

            assert result.files_processed == 2
            assert mock_processor.call_count == 2

    def test_process_folder_no_file_processor(self):
        """Test processing without file processor returns error."""
        deps = FolderProcessingDependencies(file_processor=None)
        executor = FolderPipelineExecutor(deps)

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "test.txt")
            open(file1, "w").close()

            request = FolderProcessingRequest(
                folder={"folder_name": tmpdir},
                run_log=Mock(),
            )

            result = executor.process_folder(request)

            assert result.files_failed == 1
            assert "No file processor" in result.errors[0]

    def test_filter_processed_files(self):
        """Test _filter_processed_files excludes already processed."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content")
            f.flush()
            filepath = f.name

        try:
            import hashlib

            with open(filepath, "rb") as f:
                actual_checksum = hashlib.md5(f.read()).hexdigest()

            # Mock processed_files to return a record with the ACTUAL file checksum
            mock_processed = Mock()
            mock_processed.find.return_value = [{"file_checksum": actual_checksum}]

            files = [filepath]
            result = executor._filter_processed_files(files, mock_processed, {"id": 1})
            assert len(result) == 0
        finally:
            os.unlink(filepath)

    def test_filter_processed_files_with_new_files(self):
        """Test _filter_processed_files keeps unprocessed files."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        mock_processed = Mock()
        mock_processed.find.return_value = []

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content")
            f.flush()
            filepath = f.name

        try:
            files = [filepath]
            result = executor._filter_processed_files(files, mock_processed, {"id": 1})
            assert len(result) == 1
        finally:
            os.unlink(filepath)

    def test_log_message_writes_to_run_log(self):
        """Test _log_message writes to run_log."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        mock_log = Mock()
        mock_log.write = Mock()

        executor._log_message(mock_log, "test message")

        assert len(executor._log_messages) == 1
        assert executor._log_messages[0] == "test message"

    def test_log_message_handles_non_writable(self):
        """Test _log_message handles non-writable run_log."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        executor._log_message(None, "test message")

        assert len(executor._log_messages) == 1

    def test_get_upc_dictionary_from_deps(self):
        """Test _get_upc_dictionary uses configured function."""
        mock_func = Mock(return_value={"upc": "123"})
        deps = FolderProcessingDependencies(get_upc_dictionary=mock_func)
        executor = FolderPipelineExecutor(deps)

        result = executor._get_upc_dictionary()

        mock_func.assert_called_once()
        assert result == {"upc": "123"}

    def test_get_upc_dictionary_no_function(self):
        """Test _get_upc_dictionary returns empty dict when not configured."""
        deps = FolderProcessingDependencies(get_upc_dictionary=None)
        executor = FolderPipelineExecutor(deps)

        result = executor._get_upc_dictionary()

        assert result == {}

    def test_record_processed_file(self):
        """Test _record_processed_file calls insert."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        mock_processed = Mock()
        # find_one returns None so insert is called (not update for resend)
        mock_processed.find_one.return_value = None

        mock_file_result = Mock(
            file_name="/test.txt",
            checksum="abc123",
        )

        executor._record_processed_file(
            mock_processed,
            {"id": 1},
            mock_file_result,
        )

        mock_processed.insert.assert_called_once()
        call_args = mock_processed.insert.call_args[0][0]
        assert call_args["file_name"] == "/test.txt"
        assert call_args["file_checksum"] == "abc123"
        assert call_args["folder_id"] == 1

    def test_record_processed_file_handles_error(self):
        """Test _record_processed_file handles insert errors gracefully."""
        deps = FolderProcessingDependencies()
        executor = FolderPipelineExecutor(deps)

        mock_processed = Mock()
        mock_processed.insert.side_effect = Exception("Insert failed")

        mock_file_result = Mock(
            file_name="/test.txt",
            checksum="abc123",
        )

        executor._record_processed_file(
            mock_processed,
            {"id": 1},
            mock_file_result,
        )
