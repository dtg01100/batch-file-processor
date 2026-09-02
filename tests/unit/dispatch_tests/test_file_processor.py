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

from webapp.pipeline.interfaces import ErrorHandlerInterface, FileSystemInterface
from webapp.pipeline.pipeline.interfaces import PipelineStep
from webapp.pipeline.pipeline.splitter import (
    EDISplitterStep,
    SplitterInterface,
    SplitterResult,
)
from webapp.pipeline.send_manager import MockBackend, SendManager
from webapp.pipeline.services.file_processor import (
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
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        validator = MagicMock(spec=PipelineStep)
        splitter = MagicMock(spec=PipelineStep)
        converter = MagicMock(spec=PipelineStep)
        file_system = MagicMock(spec=FileSystemInterface)

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
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)

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
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        from core.utils.file_utils import calculate_file_checksum

        checksum = calculate_file_checksum(temp_file)

        expected = hashlib.md5(b"test content for checksum").hexdigest()
        assert checksum == expected

    def test_calculate_checksum_with_file_system(self, temp_file):
        """Test checksum calculation works with direct file I/O."""
        from core.utils.file_utils import calculate_file_checksum

        checksum = calculate_file_checksum(temp_file)

        expected = hashlib.md5(b"test content for checksum").hexdigest()
        assert checksum == expected


class TestCleanupTempArtifacts:
    """Tests for _cleanup_temp_artifacts method."""

    def test_cleanup_empty_context(self):
        """Test cleanup with no temp artifacts."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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

    @patch("webapp.pipeline.services.file_processor.os.path.exists")
    @patch("webapp.pipeline.services.file_processor.shutil.rmtree")
    def test_cleanup_removes_dirs(self, mock_rmtree, mock_exists):
        """Test cleanup removes temp directories."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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

    @patch("webapp.pipeline.services.file_processor.os.path.exists")
    @patch("webapp.pipeline.services.file_processor.os.remove")
    def test_cleanup_removes_files(self, mock_remove, mock_exists):
        """Test cleanup removes temp files."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

        continue_processing, _current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            _run_log=None,
            file_basename="file.edi",
        )

        assert continue_processing
        assert result.validated is True

    def test_validation_success(self):
        """Test validation with successful result."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        validator = MagicMock(spec=PipelineStep)
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
            _run_log=None,
            file_basename="file.edi",
        )

        assert continue_processing
        assert result.validated is True
        assert current_file == "/path/to/validated.edi"

    def test_validation_failure(self):
        """Test validation with failed result."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        validator = MagicMock(spec=PipelineStep)
        validator.execute.return_value = (False, "Validation error message")

        processor = FileProcessor(send_manager, error_handler, validator_step=validator)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={"process_edi": True},
            settings={},
            upc_dict={},
        )

        continue_processing, _current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            _run_log=None,
            file_basename="file.edi",
        )

        assert not continue_processing
        assert result.validated is False
        assert "Validation error message" in result.errors[0]

    def test_validation_exception(self):
        """Test validation with exception."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        validator = MagicMock(spec=PipelineStep)
        validator.execute.side_effect = Exception("Validation exception")

        processor = FileProcessor(send_manager, error_handler, validator_step=validator)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={"force_edi_validation": True},
            settings={},
            upc_dict={},
        )

        continue_processing, _current_file = processor._run_validation(
            current_file="/path/to/file.edi",
            context=context,
            result=result,
            _run_log=None,
            file_basename="file.edi",
        )

        assert not continue_processing
        assert result.validated is False


class TestRunSplitting:
    """Tests for _run_splitting method."""

    def _make_context(self):
        return ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={},
        )

    def test_splitting_no_step(self):
        """Test splitting with no splitter step returns a no-split outcome."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        processor = FileProcessor(send_manager, error_handler)

        result = FileResult(file_name="test.edi", checksum="")
        context = self._make_context()

        split_outcome = processor._run_splitting(
            current_file="/path/to/file.edi",
            _file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            _run_log=None,
        )

        assert not split_outcome.was_split
        assert split_outcome.files == []

    def test_splitting_no_output(self):
        """Test splitting with no output returns a no-split outcome."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        splitter = MagicMock(spec=SplitterInterface)
        splitter.split.return_value = SplitterResult(files=[], was_split=False)

        processor = FileProcessor(send_manager, error_handler, splitter_step=splitter)

        result = FileResult(file_name="test.edi", checksum="")
        context = self._make_context()

        split_outcome = processor._run_splitting(
            current_file="/path/to/file.edi",
            _file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            _run_log=None,
        )

        assert not split_outcome.was_split
        assert split_outcome.files == []
        processor._cleanup_temp_artifacts(context)

    def test_splitting_with_output(self):
        """Test splitting with output reports was_split with the split files."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        splitter = MagicMock(spec=SplitterInterface)
        splitter.split.return_value = SplitterResult(
            files=[
                ("/path/to/output1.edi", "A_", ".edi"),
                ("/path/to/output2.edi", "B_", ".edi"),
            ],
            was_split=True,
        )

        processor = FileProcessor(send_manager, error_handler, splitter_step=splitter)

        result = FileResult(file_name="test.edi", checksum="")
        context = self._make_context()

        split_outcome = processor._run_splitting(
            current_file="/path/to/file.edi",
            _file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            _run_log=None,
        )

        assert split_outcome.was_split
        assert [f[0] for f in split_outcome.files] == [
            "/path/to/output1.edi",
            "/path/to/output2.edi",
        ]
        # The splitter receives the caller's UPC dictionary, not an empty one.
        splitter.split.assert_called_once()
        assert splitter.split.call_args.args[3] == {}
        processor._cleanup_temp_artifacts(context)

    def test_splitting_passes_upc_dict_to_splitter(self):
        """The UPC dictionary is threaded into the splitter call."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        splitter = MagicMock(spec=SplitterInterface)
        splitter.split.return_value = SplitterResult(files=[], was_split=False)

        processor = FileProcessor(send_manager, error_handler, splitter_step=splitter)

        result = FileResult(file_name="test.edi", checksum="")
        context = ProcessingContext(
            folder={},
            effective_folder={},
            settings={},
            upc_dict={"123456": ("cat1", "upc_pack", "upc_case")},
        )

        processor._run_splitting(
            current_file="/path/to/file.edi",
            _file_path="/path/to/file.edi",
            file_basename="file.edi",
            context=context,
            result=result,
            _run_log=None,
        )

        splitter.split.assert_called_once()
        assert splitter.split.call_args.args[3] == {
            "123456": ("cat1", "upc_pack", "upc_case")
        }
        processor._cleanup_temp_artifacts(context)


class TestSplitPipelineEndToEnd:
    """End-to-end: split outputs — not the original — are what get sent."""

    # Two A records (distinct invoices) each followed by a B record so the
    # real EDISplitter produces one output file per invoice.
    _TWO_INVOICE_EDI = (
        "AVENDOR00000000010101250000100000\r\n"
        "B01234567890Test Item Description    1234560001000100000100010991001000000\r\n"
        "AVENDOR00000000020201250000100000\r\n"
        "B01234567890Test Item Description    1234560001000100000100010991001000000\r\n"
    )

    def _build_processor(self, converter_step=None, backend=None):
        backend = backend or MockBackend()
        send_manager = SendManager(backends={"mock": backend})
        error_handler = MagicMock(spec=ErrorHandlerInterface)
        processor = FileProcessor(
            send_manager=send_manager,
            error_handler=error_handler,
            splitter_step=EDISplitterStep(),
            converter_step=converter_step,
        )
        return processor, backend

    def _write_input(self, tmp_path, name="multi_invoice.edi"):
        input_file = tmp_path / name
        input_file.write_text(self._TWO_INVOICE_EDI, encoding="utf-8")
        return str(input_file)

    def test_split_outputs_are_sent_instead_of_original(self, tmp_path):
        """Each per-invoice split file reaches the backend, never the original."""
        input_file = self._write_input(tmp_path)
        processor, backend = self._build_processor(backend=_SnapshotBackend())

        folder = {
            "id": 1,
            "alias": "split-test",
            "folder_name": str(tmp_path),
            "split_edi": True,
        }
        result = processor.process_file(
            file_path=input_file,
            folder=folder,
            upc_dict={},
            run_log=None,
        )

        assert (
            result.sent is True
        ), f"expected split files sent, errors: {result.errors}"
        sent_files = [call[2] for call in backend.send_calls]
        assert len(sent_files) == 2, f"expected 2 split files, got {sent_files}"
        assert input_file not in sent_files, "original file must not be sent"
        for sent_path in sent_files:
            # Split outputs live in the pipeline temp dir, not the source dir.
            assert os.path.dirname(sent_path) != str(tmp_path)
            assert os.path.basename(sent_path).endswith(".inv"), sent_path
        assert len(set(sent_files)) == 2, "split files must be distinct outputs"
        # Files exist (and are readable) at send time.
        assert len(backend.snapshots) == 2, backend.snapshots
        assert all(content for _, content in backend.snapshots), backend.snapshots

    def test_conversion_applies_to_each_split_file(self, tmp_path):
        """Each split file is converted before it is sent."""
        input_file = self._write_input(tmp_path)
        converter = _RecordingConverter()
        processor, backend = self._build_processor(
            converter_step=converter, backend=_SnapshotBackend()
        )

        folder = {
            "id": 2,
            "alias": "split-convert",
            "folder_name": str(tmp_path),
            "split_edi": True,
        }
        result = processor.process_file(
            file_path=input_file,
            folder=folder,
            upc_dict={},
            run_log=None,
        )

        assert (
            result.sent is True
        ), f"expected converted split files sent: {result.errors}"
        assert result.converted is True
        assert (
            len(converter.inputs) == 2
        ), f"expected 2 conversions, got {converter.inputs}"
        assert input_file not in converter.inputs
        sent_files = [call[2] for call in backend.send_calls]
        assert len(sent_files) == 2
        assert all(path.endswith(".csv") for path in sent_files)
        # The converted files exist (and are readable) at send time.
        assert len(backend.snapshots) == 2, backend.snapshots
        assert all(content == b"converted" for _, content in backend.snapshots)

    def test_split_disabled_sends_original(self, tmp_path):
        """Without split_edi, the original file is sent unchanged."""
        input_file = self._write_input(tmp_path)
        processor, backend = self._build_processor()

        folder = {
            "id": 3,
            "alias": "no-split",
            "folder_name": str(tmp_path),
            "split_edi": False,
        }
        result = processor.process_file(
            file_path=input_file,
            folder=folder,
            upc_dict={},
            run_log=None,
        )

        assert result.sent is True, f"expected original sent, errors: {result.errors}"
        sent_files = [call[2] for call in backend.send_calls]
        assert sent_files == [input_file]

    # --- Category filtering without splitting (split_edi=False) ------------

    def _write_category_input(self, tmp_path, name="filter_me.edi"):
        """Two invoices: inv 1 has a cat1 and a cat2 line item, inv 2 only cat2."""
        from core.edi.edi_parser import build_a_record, build_b_record

        a1 = build_a_record("VENDOR", "0000000101", "012500", "0000100000")
        b1_cat1 = build_b_record(
            "01234567890",
            "Cat One Item".ljust(25),
            "123456",
            "000100",
            "01",
            "000100",
            "00010",
            "00109",
        )
        b1_cat2 = build_b_record(
            "09876543210",
            "Cat Two Item".ljust(25),
            "654321",
            "000100",
            "01",
            "000100",
            "00010",
            "00109",
        )
        a2 = build_a_record("VENDOR", "0000000202", "012500", "0000100000")
        b2_cat2 = build_b_record(
            "09876543210",
            "Cat Two Item".ljust(25),
            "654321",
            "000100",
            "01",
            "000100",
            "00010",
            "00109",
        )
        input_file = tmp_path / name
        input_file.write_text(a1 + b1_cat1 + b1_cat2 + a2 + b2_cat2, encoding="utf-8")
        return str(input_file)

    @staticmethod
    def _upc_dict():
        """vendor_item -> (category, upc_each, upc_case, upc_pack, ...)."""
        return {
            123456: ("cat1", "01234567890", "", "", ""),
            654321: ("cat2", "09876543210", "", "", ""),
        }

    def _build_filter_processor(self):
        backend = _SnapshotBackend()
        send_manager = SendManager(backends={"mock": backend})
        processor = FileProcessor(
            send_manager=send_manager,
            error_handler=MagicMock(spec=ErrorHandlerInterface),
            splitter_step=EDISplitterStep(),
        )
        return processor, backend

    def test_category_filter_without_split_uses_upc_lookup(self, tmp_path):
        """split_edi=False + include filter sends the UPC-filtered copy."""
        input_file = self._write_category_input(tmp_path)
        processor, backend = self._build_filter_processor()

        folder = {
            "id": 4,
            "alias": "filter-include",
            "folder_name": str(tmp_path),
            "split_edi": False,
            "split_edi_filter_categories": "cat1",
            "split_edi_filter_mode": "include",
        }
        result = processor.process_file(
            file_path=input_file,
            folder=folder,
            upc_dict=self._upc_dict(),
            run_log=None,
        )

        assert (
            result.sent is True
        ), f"expected filtered file sent, errors: {result.errors}"
        assert len(backend.snapshots) == 1, backend.snapshots
        sent_path, content = backend.snapshots[0]
        assert sent_path != input_file, "filtered copy must be sent, not the original"
        text = content.decode("utf-8")
        # Invoice 1 keeps its cat1 line item and drops the cat2 one.
        assert "0000000101" in text
        assert "123456" in text
        assert "654321" not in text
        # Invoice 2 has no remaining line items and is dropped entirely.
        assert "0000000202" not in text

    def test_category_filter_exclude_mode_without_split(self, tmp_path):
        """split_edi=False + exclude filter removes the matching category."""
        input_file = self._write_category_input(tmp_path)
        processor, backend = self._build_filter_processor()

        folder = {
            "id": 5,
            "alias": "filter-exclude",
            "folder_name": str(tmp_path),
            "split_edi": False,
            "split_edi_filter_categories": "cat1",
            "split_edi_filter_mode": "exclude",
        }
        result = processor.process_file(
            file_path=input_file,
            folder=folder,
            upc_dict=self._upc_dict(),
            run_log=None,
        )

        assert (
            result.sent is True
        ), f"expected filtered file sent, errors: {result.errors}"
        assert len(backend.snapshots) == 1, backend.snapshots
        sent_path, content = backend.snapshots[0]
        assert sent_path != input_file, "filtered copy must be sent, not the original"
        text = content.decode("utf-8")
        # Invoice 1 drops its cat1 line item but keeps the cat2 one.
        assert "0000000101" in text
        assert "654321" in text
        assert "123456" not in text
        # Invoice 2 (cat2 only) is fully retained.
        assert "0000000202" in text

    # --- Splitting combined with category filtering ------------------------

    @staticmethod
    def _make_b_record(vendor_item: str) -> str:
        """Build a B record line for the given 6-digit vendor item."""
        from core.edi.edi_parser import build_b_record

        return build_b_record(
            "01234567890",
            "Cat Item".ljust(25),
            vendor_item,
            "000100",
            "01",
            "000100",
            "00010",
            "00109",
        )

    def _write_split_category_input(self, tmp_path, name="split_filter.edi"):
        """Three invoices: inv1 has cat1+cat2 items, inv2 only cat2, inv3 only cat1."""
        from core.edi.edi_parser import build_a_record

        a1 = build_a_record("VENDOR", "0000000101", "012500", "0000100000")
        a2 = build_a_record("VENDOR", "0000000202", "012500", "0000100000")
        a3 = build_a_record("VENDOR", "0000000303", "012500", "0000100000")
        input_file = tmp_path / name
        input_file.write_text(
            a1
            + self._make_b_record("123456")
            + self._make_b_record("654321")
            + a2
            + self._make_b_record("654321")
            + a3
            + self._make_b_record("123456"),
            encoding="utf-8",
        )
        return str(input_file)

    def test_split_with_category_filter_filters_each_split_file(self, tmp_path):
        """split_edi=True + include filter: each split output keeps only matching items."""
        input_file = self._write_split_category_input(tmp_path)
        processor, backend = self._build_processor(backend=_SnapshotBackend())

        folder = {
            "id": 6,
            "alias": "split-filter",
            "folder_name": str(tmp_path),
            "split_edi": True,
            "split_edi_filter_categories": "cat1",
            "split_edi_filter_mode": "include",
        }
        result = processor.process_file(
            file_path=input_file,
            folder=folder,
            upc_dict=self._upc_dict(),
            run_log=None,
        )

        assert (
            result.sent is True
        ), f"expected split files sent, errors: {result.errors}"
        sent_paths = [path for path, _ in backend.snapshots]
        assert len(sent_paths) == 2, backend.snapshots
        assert input_file not in sent_paths, "original must not be sent"
        texts = [content.decode("utf-8") for _, content in backend.snapshots]
        # Invoice 2 has no surviving cat1 line item, so it is dropped entirely.
        assert all("0000000202" not in text for text in texts), texts
        for text in texts:
            a_records = [ln for ln in text.splitlines() if ln.startswith("A")]
            assert len(a_records) == 1, f"expected one invoice per split file: {text}"
            # Each split output retains only the cat1 line item.
            assert "123456" in text
            assert "654321" not in text
        # The two surviving invoices arrive as distinct filtered outputs.
        assert any("0000000101" in t for t in texts), texts
        assert any("0000000303" in t for t in texts), texts


class _SnapshotBackend(MockBackend):
    """MockBackend that also snapshots file contents at send time."""

    def __init__(self):
        super().__init__()
        self.snapshots: list[tuple[str, bytes]] = []

    def send(self, params, settings, filename):
        super().send(params, settings, filename)
        with open(filename, "rb") as f:
            self.snapshots.append((filename, f.read()))


class _RecordingConverter:
    """Converter stub that records its inputs and emits a .csv copy."""

    def __init__(self):
        self.inputs: list[str] = []

    def execute(self, file_path, folder, settings, upc_dict, context=None):
        self.inputs.append(file_path)
        converted = file_path + ".csv"
        with open(converted, "w", encoding="utf-8") as f:
            f.write("converted")
        return converted


class TestSendFile:
    """Tests for _send_file method."""

    def test_send_no_backends_enabled(self):
        """Test send with no enabled backends."""
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = set()

        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": True}

        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": False}
        send_manager.errors = {"copy": "Connection failed"}

        error_handler = MagicMock(spec=ErrorHandlerInterface)
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

    def test_send_partial_failure(self):
        """A single failed backend marks the whole send as failed."""
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = {"copy1", "copy2"}
        send_manager.send_all.return_value = {"copy1": True, "copy2": False}
        send_manager.errors = {"copy2": "Connection failed"}

        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": True}

        error_handler = MagicMock(spec=ErrorHandlerInterface)

        processor = FileProcessor(send_manager, error_handler)

        folder = {"folder_name": "/test", "alias": "test"}
        result = processor.process_file(temp_file, folder, {})

        assert result.file_name == temp_file
        assert result.checksum != ""
        assert result.sent is True

    def test_process_file_with_exception(self, temp_file):
        """Test process_file handles exceptions."""
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.side_effect = Exception("Test error")

        error_handler = MagicMock(spec=ErrorHandlerInterface)

        processor = FileProcessor(send_manager, error_handler)

        folder = {"folder_name": "/test", "alias": "test"}
        result = processor.process_file(temp_file, folder, {})

        assert "Test error" in result.errors
        error_handler.record_error.assert_called_once()


class TestExtractInvoiceNumbers:
    """Tests for _extract_invoice_numbers method."""

    def test_extract_no_file(self):
        """Test extraction handles missing file."""
        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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

        send_manager = MagicMock(spec=SendManager)
        error_handler = MagicMock(spec=ErrorHandlerInterface)
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
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = set()

        error_handler = MagicMock(spec=ErrorHandlerInterface)
        processor = FileProcessor(send_manager, error_handler)

        result = processor._send_to_backends(
            file_path="/path/to/file.edi",
            folder={},
            _run_log=None,
            settings={},
        )

        assert not result

    def test_send_to_backends_success(self):
        """Test send_to_backends with success."""
        send_manager = MagicMock(spec=SendManager)
        send_manager.get_enabled_backends.return_value = {"copy"}
        send_manager.send_all.return_value = {"copy": True}

        error_handler = MagicMock(spec=ErrorHandlerInterface)
        processor = FileProcessor(send_manager, error_handler)

        result = processor._send_to_backends(
            file_path="/path/to/file.edi",
            folder={},
            _run_log=None,
            settings={},
        )

        assert result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
