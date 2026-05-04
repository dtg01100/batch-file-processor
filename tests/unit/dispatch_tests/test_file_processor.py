"""Unit tests for FileProcessor service.

Tests:
- FileResult dataclass
- ProcessingContext dataclass
- FileProcessor initialization
- process_file method
- Pipeline execution (validation, splitting, conversion, tweaks)
- Temporary file management
- Send operations
"""

import hashlib
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from dispatch.services.file_processor import (
    FileProcessor,
    FileResult,
    ProcessingContext,
)

pytestmark = [pytest.mark.unit, pytest.mark.dispatch]


class TestFileResult:
    """Tests for FileResult dataclass."""

    def test_default_values(self):
        """Test FileResult default values."""
        result = FileResult(file_name="test.edi", checksum="abc123")

        assert result.file_name == "test.edi"
        assert result.checksum == "abc123"
        assert result.sent is False
        assert result.validated is True
        assert result.converted is False
        assert result.errors == []

    def test_with_errors(self):
        """Test FileResult with errors."""
        result = FileResult(file_name="test.edi", checksum="")
        result.errors.append("Error 1")
        result.errors.append("Error 2")

        assert len(result.errors) == 2

    def test_immutable_fields(self):
        """Test that certain fields are set at initialization."""
        result = FileResult(file_name="test.edi", checksum="abc")

        assert result.file_name == "test.edi"
        assert result.checksum == "abc"


class TestProcessingContext:
    """Tests for ProcessingContext dataclass."""

    def test_default_values(self):
        """Test ProcessingContext default values."""
        context = ProcessingContext(
            folder={"folder_name": "/test"},
            effective_folder={"folder_name": "/test"},
            settings={},
            upc_dict={},
        )

        assert context.folder == {"folder_name": "/test"}
        assert context.effective_folder == {"folder_name": "/test"}
        assert context.settings == {}
        assert context.upc_dict == {}
        assert context.temp_dirs == []
        assert context.temp_files == []

    def test_with_temp_artifacts(self):
        """Test ProcessingContext with temp artifacts."""
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
            temp_dirs=["/tmp/dir1", "/tmp/dir2"],
            temp_files=["/tmp/file1"],
        )

        assert len(context.temp_dirs) == 2
        assert len(context.temp_files) == 1


class TestFileProcessorInitialization:
    """Tests for FileProcessor initialization."""

    def test_init_with_all_steps(self):
        """Test initialization with all pipeline steps."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        validator = MagicMock()
        splitter = MagicMock()
        converter = MagicMock()
        file_system = MagicMock()

        processor = FileProcessor(
            send_manager=send_manager,
            error_handler=error_handler,
            validator_step=validator,
            splitter_step=splitter,
            converter_step=converter,
            file_system=file_system,
        )

        assert processor.send_manager is send_manager
        assert processor.error_handler is error_handler
        assert processor.validator_step is validator
        assert processor.splitter_step is splitter
        assert processor.converter_step is converter
        assert processor.file_system is file_system

    def test_init_with_minimal_args(self):
        """Test initialization with minimal arguments."""
        send_manager = MagicMock()
        error_handler = MagicMock()

        processor = FileProcessor(
            send_manager=send_manager,
            error_handler=error_handler,
        )

        assert processor.send_manager is send_manager
        assert processor.error_handler is error_handler
        assert processor.validator_step is None
        assert processor.splitter_step is None
        assert processor.converter_step is None
        assert processor.converter_step is None
        assert processor.file_system is None


class TestBuildContext:
    """Tests for _build_context method."""

    def test_build_context_simple(self):
        """Test building context with simple folder dict."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = processor._build_context(
            folder={"folder_name": "/test"},
            upc_dict={"key": "value"},
            effective_folder=None,
        )

        assert context.folder == {"folder_name": "/test"}
        assert context.effective_folder == {"folder_name": "/test"}
        assert context.upc_dict == {"key": "value"}
        assert context.settings == {}

    def test_build_context_with_effective_folder(self):
        """Test building context with effective folder."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = processor._build_context(
            folder={"folder_name": "/test"},
            upc_dict={},
            effective_folder={"process_edi": True, "settings": {"key": "val"}},
        )

        assert context.effective_folder == {
            "process_edi": True,
            "settings": {"key": "val"},
        }
        assert context.settings == {"key": "val"}

    def test_build_context_reuses_processing_context(self):
        """Test that passing ProcessingContext returns it unchanged."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        existing_context = ProcessingContext(
            folder={"folder_name": "/original"},
            effective_folder={"folder_name": "/effective"},
            settings={"setting": "value"},
            upc_dict={},
            temp_dirs=["/tmp/dir"],
        )

        result = processor._build_context(
            folder={},
            upc_dict={},
            effective_folder=existing_context,
        )

        assert result is existing_context


class TestCalculateChecksum:
    """Tests for _calculate_checksum method."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file with content."""
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("test content for checksum")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)

    def test_calculate_checksum_default(self, temp_file):
        """Test checksum calculation uses default MD5."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        checksum = processor._calculate_checksum(temp_file)

        expected = hashlib.md5(b"test content for checksum").hexdigest()
        assert checksum == expected

    def test_calculate_checksum_with_file_system(self, temp_file):
        """Test checksum calculation with injected file system."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        mock_fs = MagicMock()
        mock_fs.read_file.return_value = b"test content for checksum"

        processor = FileProcessor(send_manager, error_handler, file_system=mock_fs)

        checksum = processor._calculate_checksum(temp_file)

        mock_fs.read_file.assert_called_once_with(temp_file)
        expected = hashlib.md5(b"test content for checksum").hexdigest()
        assert checksum == expected


class TestApplyRename:
    """Tests for _apply_rename method."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file."""
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("content")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_apply_rename_no_template(self, temp_file):
        """Test rename with empty template returns original."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = ProcessingContext(
            folder={},
            effective_folder={"rename_file": ""},
            settings={},
            upc_dict={},
        )

        result = processor._apply_rename(temp_file, context)

        assert result == temp_file

    def test_apply_rename_with_datetime(self, temp_file):
        """Test rename with %datetime% placeholder."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = ProcessingContext(
            folder={},
            effective_folder={"rename_file": "renamed_%datetime%"},
            settings={},
            upc_dict={},
        )

        result = processor._apply_rename(temp_file, context)

        assert result != temp_file
        assert "renamed_" in os.path.basename(result)
        # Verify temp dir was added
        assert len(context.temp_dirs) > 0

    def test_apply_rename_invalid_path(self, temp_file):
        """Test rename with invalid path raises."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = ProcessingContext(
            folder={},
            effective_folder={"rename_file": ".."},
            settings={},
            upc_dict={},
        )

        with pytest.raises(ValueError, match="Invalid filename"):
            processor._apply_rename(temp_file, context)

    def test_apply_rename_sanitizes_special_chars(self, temp_file):
        """Test rename sanitizes special characters."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = ProcessingContext(
            folder={},
            effective_folder={"rename_file": "test@#$%file"},
            settings={},
            upc_dict={},
        )

        result = processor._apply_rename(temp_file, context)

        assert result != temp_file
        # Special characters should be removed
        assert "@" not in os.path.basename(result)
        assert "#" not in os.path.basename(result)
        assert "$" not in os.path.basename(result)


class TestCleanupTempArtifacts:
    """Tests for _cleanup_temp_artifacts method."""

    def test_cleanup_empty_context(self):
        """Test cleanup with no temp artifacts."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        processor._cleanup_temp_artifacts(context)

        assert context.temp_dirs == []
        assert context.temp_files == []

    @patch("dispatch.services.file_processor.os.path.exists")
    @patch("dispatch.services.file_processor.shutil.rmtree")
    def test_cleanup_removes_dirs(self, mock_rmtree, mock_exists):
        """Test cleanup removes temp directories."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        mock_exists.return_value = True

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
            temp_dirs=["/tmp/dir1", "/tmp/dir2"],
        )

        processor._cleanup_temp_artifacts(context)

        assert mock_rmtree.call_count == 2

    @patch("dispatch.services.file_processor.os.path.exists")
    @patch("dispatch.services.file_processor.os.remove")
    def test_cleanup_removes_files(self, mock_remove, mock_exists):
        """Test cleanup removes temp files."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        mock_exists.return_value = True

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
            temp_files=["/tmp/file1", "/tmp/file2"],
        )

        processor._cleanup_temp_artifacts(context)

        assert mock_remove.call_count == 2


class TestRunValidation:
    """Tests for _run_validation method."""

    def test_validation_no_step(self):
        """Test validation with no validator step returns True."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        continue_processing, current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            run_log=None,
            file_basename="file.edi",
        )

        assert continue_processing is True
        assert result.validated is True

    def test_validation_success(self):
        """Test validation with successful result."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        validator = MagicMock()
        validator.execute.return_value = (True, "/path/to/validated.edi")

        processor = FileProcessor(send_manager, error_handler, validator_step=validator)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={"force_edi_validation": True},
            settings={},
            upc_dict={},
        )

        continue_processing, current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            run_log=None,
            file_basename="file.edi",
        )

        assert continue_processing is True
        assert result.validated is True
        assert current_file == "/path/to/validated.edi"

    def test_validation_failure(self):
        """Test validation with failed result."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        validator = MagicMock()
        validator.execute.return_value = (False, "Validation error message")

        processor = FileProcessor(send_manager, error_handler, validator_step=validator)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={"process_edi": True},
            settings={},
            upc_dict={},
        )

        continue_processing, current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            run_log=None,
            file_basename="file.edi",
        )

        assert continue_processing is False
        assert result.validated is False
        assert "Validation error message" in result.errors[0]

    def test_validation_exception(self):
        """Test validation with exception."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        validator = MagicMock()
        validator.execute.side_effect = Exception("Validation exception")

        processor = FileProcessor(send_manager, error_handler, validator_step=validator)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={"force_edi_validation": True},
            settings={},
            upc_dict={},
        )

        continue_processing, current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            run_log=None,
            file_basename="file.edi",
        )

        assert continue_processing is False
        assert result.validated is False


class TestRunSplitting:
    """Tests for _run_splitting method."""

    def test_splitting_no_step(self):
        """Test splitting with no splitter step returns False."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        was_split = processor._run_splitting(
            current_file="/path/to/file.edi",
            file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            run_log=None,
        )

        assert was_split is False

    def test_splitting_no_output(self):
        """Test splitting with no output returns False."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        splitter = MagicMock()
        splitter.execute.return_value = []

        processor = FileProcessor(send_manager, error_handler, splitter_step=splitter)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        was_split = processor._run_splitting(
            current_file="/path/to/file.edi",
            file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            run_log=None,
        )

        assert was_split is False

    def test_splitting_with_output(self):
        """Test splitting with output returns True."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        splitter = MagicMock()
        splitter.execute.return_value = ["/path/to/output1.edi", "/path/to/output2.edi"]

        processor = FileProcessor(send_manager, error_handler, splitter_step=splitter)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        was_split = processor._run_splitting(
            current_file="/path/to/file.edi",
            file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            run_log=None,
        )

        assert was_split is True


class TestRunConversion:
    """Tests for the unified conversion execution path."""

    def test_conversion_no_step(self):
        """Test conversion with no converter step."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        new_file, did_convert, conversion_failed = processor._run_conversion(
            current_file="/path/to/file.edi",
            file_basename="file.edi",
            original_file_path="/path/to/file.edi",
            context=context,
            run_log=None,
            validation_passed=True,
        )

        assert new_file == "/path/to/file.edi"
        assert did_convert is False
        assert conversion_failed is False

    def test_conversion_success(self):
        """Test conversion with successful result."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        converter = MagicMock()
        converter.execute.return_value = "/path/to/converted.edi"

        processor = FileProcessor(send_manager, error_handler, converter_step=converter)

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        new_file, did_convert, conversion_failed = processor._run_conversion(
            current_file="/path/to/file.edi",
            file_basename="file.edi",
            original_file_path="/path/to/file.edi",
            context=context,
            run_log=None,
            validation_passed=True,
        )

        assert new_file == "/path/to/converted.edi"
        assert did_convert is True
        assert conversion_failed is False

    def test_conversion_no_output(self):
        """Test conversion with no output treats as failure."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        converter = MagicMock()
        converter.execute.return_value = None

        processor = FileProcessor(send_manager, error_handler, converter_step=converter)

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        new_file, did_convert, conversion_failed = processor._run_conversion(
            current_file="/path/to/file.edi",
            file_basename="file.edi",
            original_file_path="/path/to/file.edi",
            context=context,
            run_log=None,
            validation_passed=True,
        )

        assert conversion_failed is True

    def test_conversion_skipped_when_validation_failed(self):
        """Test conversion is skipped when validation failed."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        converter = MagicMock()

        processor = FileProcessor(send_manager, error_handler, converter_step=converter)

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        new_file, did_convert, conversion_failed = processor._run_conversion(
            current_file="/path/to/file.edi",
            file_basename="file.edi",
            original_file_path="/path/to/file.edi",
            context=context,
            run_log=None,
            validation_passed=False,
        )

        converter.execute.assert_not_called()
        assert did_convert is False

    def test_conversion_step_output_is_accepted(self):
        """Test converter_step output is accepted as converted output."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        tweaker = MagicMock()
        tweaker.execute.return_value = "/path/to/tweaked.edi"

        processor = FileProcessor(send_manager, error_handler, converter_step=tweaker)

        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        new_file, did_convert, conversion_failed = processor._run_conversion(
            current_file="/path/to/file.edi",
            file_basename="file.edi",
            original_file_path="/path/to/file.edi",
            context=context,
            run_log=None,
            validation_passed=True,
        )

        assert new_file == "/path/to/tweaked.edi"
        assert did_convert is True
        assert conversion_failed is False


class TestSendFile:
    """Tests for _send_file method."""

    def test_send_no_backends_enabled(self):
        """Test send with no enabled backends."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.return_value = set()

        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        processor._send_file(
            current_file="/path/to/file.edi",
            file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            run_log=None,
        )

        assert result.sent is False
        assert "No backends enabled" in result.errors[0]

    def test_send_success(self):
        """Test successful send."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": True}

        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        processor._send_file(
            current_file="/path/to/file.edi",
            file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            run_log=None,
        )

        assert result.sent is True

    def test_send_failure(self):
        """Test send failure records error."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": False}
        send_manager.errors = {"copy": "Connection failed"}

        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        processor._send_file(
            current_file="/path/to/file.edi",
            file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            run_log=None,
        )

        assert result.sent is False
        assert "Connection failed" in result.errors


class TestProcessFile:
    """Tests for process_file method."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary EDI file."""
        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".edi", dir="/tmp"
        ) as f:
            f.write("TEST CONTENT")
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_process_file_basic(self, temp_file):
        """Test basic file processing."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": True}

        error_handler = MagicMock()

        processor = FileProcessor(send_manager, error_handler)

        folder = {"folder_name": "/test", "alias": "test"}
        result = processor.process_file(temp_file, folder, {})

        assert result.file_name == temp_file
        assert result.checksum != ""
        assert result.sent is True

    def test_process_file_with_exception(self, temp_file):
        """Test process_file handles exceptions."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.side_effect = Exception("Test error")

        error_handler = MagicMock()

        processor = FileProcessor(send_manager, error_handler)

        folder = {"folder_name": "/test", "alias": "test"}
        result = processor.process_file(temp_file, folder, {})

        assert "Test error" in result.errors
        error_handler.record_error.assert_called_once()


class TestExtractInvoiceNumbers:
    """Tests for _extract_invoice_numbers method."""

    def test_extract_no_file(self):
        """Test extraction handles missing file."""
        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = processor._extract_invoice_numbers("/nonexistent/file.edi")

        assert result == ""

    @patch("core.edi.edi_parser.capture_records")
    def test_extract_with_records(self, mock_capture):
        """Test extraction with valid A-records."""
        mock_capture.side_effect = [
            {"record_type": "A", "invoice_number": "INV001"},
            {"record_type": "B", "invoice_number": ""},
            {"record_type": "A", "invoice_number": "INV002"},
        ]

        send_manager = MagicMock()
        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".edi") as f:
            f.write("line1\nline2\nline3")
            temp_path = f.name

        try:
            result = processor._extract_invoice_numbers(temp_path)
            assert "INV001" in result or "INV002" in result
        finally:
            os.unlink(temp_path)


class TestSendToBackends:
    """Tests for _send_to_backends method."""

    def test_send_to_backends_no_enabled(self):
        """Test send_to_backends with no enabled backends."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.return_value = set()

        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = processor._send_to_backends(
            file_path="/path/to/file.edi",
            folder={},
            run_log=None,
            settings={},
        )

        assert result is False

    def test_send_to_backends_success(self):
        """Test send_to_backends with success."""
        send_manager = MagicMock()
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": True}

        error_handler = MagicMock()
        processor = FileProcessor(send_manager, error_handler)

        result = processor._send_to_backends(
            file_path="/path/to/file.edi",
            folder={},
            run_log=None,
            settings={},
        )

        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
