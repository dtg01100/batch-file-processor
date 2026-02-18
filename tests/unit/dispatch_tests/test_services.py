"""Tests for dispatch/services/ module."""

import logging
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from dispatch.services.upc_service import (
    UPCServiceResult,
    MockQueryRunner,
    UPCService,
)
from dispatch.services.progress_reporter import (
    ProgressReporter,
    CLIProgressReporter,
    NullProgressReporter,
    LoggingProgressReporter,
)
from dispatch.services.file_processor import (
    FileProcessorResult,
    MockFileProcessor,
    FileProcessor,
)


class TestUPCServiceResult:
    """Tests for UPCServiceResult dataclass."""

    def test_creation_with_all_fields(self):
        """Test creating UPCServiceResult with all fields."""
        upc_dict = {1: ["cat", "upc1", "a", "b", "c"]}
        result = UPCServiceResult(upc_dict=upc_dict, success=True, errors=[])
        
        assert result.upc_dict == upc_dict
        assert result.success is True
        assert result.errors == []

    def test_creation_with_errors(self):
        """Test creating UPCServiceResult with errors."""
        result = UPCServiceResult(upc_dict={}, success=False, errors=["Error 1", "Error 2"])
        
        assert result.upc_dict == {}
        assert result.success is False
        assert len(result.errors) == 2

    def test_empty_dict_creation(self):
        """Test creating UPCServiceResult with empty dict."""
        result = UPCServiceResult(upc_dict={}, success=True, errors=[])
        
        assert result.upc_dict == {}
        assert result.success is True
        assert result.errors == []


class TestMockQueryRunner:
    """Tests for MockQueryRunner class."""

    def test_creation_with_no_data(self):
        """Test creating MockQueryRunner with no data."""
        runner = MockQueryRunner()
        
        result = runner.execute("SELECT * FROM table", {})
        
        assert result == []

    def test_creation_with_data(self):
        """Test creating MockQueryRunner with data."""
        mock_data = [
            (1, "cat1", "upc1", "a", "b", "c"),
            (2, "cat2", "upc2", "d", "e", "f"),
        ]
        runner = MockQueryRunner(mock_data)
        
        result = runner.execute("SELECT * FROM table", {})
        
        assert result == mock_data
        assert len(result) == 2

    def test_execute_returns_mock_data_regardless_of_query(self):
        """Test that execute returns mock data regardless of query."""
        mock_data = [(1, "cat", "upc", "a", "b", "c")]
        runner = MockQueryRunner(mock_data)
        
        result1 = runner.execute("SELECT * FROM table1", {})
        result2 = runner.execute("DELETE FROM table2", {"param": "value"})
        result3 = runner.execute("INSERT INTO table3 VALUES (1)", {"x": 1})
        
        assert result1 == mock_data
        assert result2 == mock_data
        assert result3 == mock_data


class TestUPCService:
    """Tests for UPCService class."""

    def test_fetch_upc_dictionary_success(self):
        """Test successful UPC dictionary fetch."""
        mock_data = [
            (1, "cat1", "upc1", "a", "b", "c"),
            (2, "cat2", "upc2", "d", "e", "f"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        
        result = service.fetch_upc_dictionary({})
        
        assert result.success is True
        assert len(result.errors) == 0
        assert 1 in result.upc_dict
        assert 2 in result.upc_dict

    def test_fetch_upc_dictionary_builds_correct_structure(self):
        """Test that UPC dictionary is built correctly."""
        mock_data = [
            (100, "ELEC", "123456789012", "desc1", "brand1", "item1"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        
        result = service.fetch_upc_dictionary({})
        
        upc_list = result.upc_dict[100]
        assert upc_list[0] == "ELEC"
        assert upc_list[1] == "123456789012"

    def test_fetch_upc_dictionary_error_handling(self):
        """Test error handling when query fails."""
        def failing_execute(query, params=None):
            raise Exception("Database connection failed")
        
        query_runner = MagicMock()
        query_runner.execute = failing_execute
        service = UPCService(query_runner)
        
        result = service.fetch_upc_dictionary({})
        
        assert result.success is False
        assert len(result.errors) == 1
        assert "Database connection failed" in result.errors[0]
        assert result.upc_dict == {}

    def test_get_upc_for_item_when_cached(self):
        """Test getting UPC for item when cache is populated."""
        mock_data = [
            (1, "cat", "123456789", "a", "b", "c"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        service.fetch_upc_dictionary({})
        
        upc = service.get_upc_for_item(1)
        
        assert upc == "123456789"

    def test_get_upc_for_item_not_in_cache(self):
        """Test getting UPC for item not in cache."""
        mock_data = [
            (1, "cat", "upc", "a", "b", "c"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        service.fetch_upc_dictionary({})
        
        upc = service.get_upc_for_item(999)
        
        assert upc is None

    def test_get_upc_for_item_before_fetch(self):
        """Test getting UPC before cache is populated."""
        query_runner = MockQueryRunner([])
        service = UPCService(query_runner)
        
        upc = service.get_upc_for_item(1)
        
        assert upc is None

    def test_get_category_for_item_when_cached(self):
        """Test getting category for item when cache is populated."""
        mock_data = [
            (1, "ELECTRONICS", "upc", "a", "b", "c"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        service.fetch_upc_dictionary({})
        
        category = service.get_category_for_item(1)
        
        assert category == "ELECTRONICS"

    def test_get_category_for_item_not_in_cache(self):
        """Test getting category for item not in cache."""
        mock_data = [
            (1, "cat", "upc", "a", "b", "c"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        service.fetch_upc_dictionary({})
        
        category = service.get_category_for_item(999)
        
        assert category is None

    def test_get_category_for_item_before_fetch(self):
        """Test getting category before cache is populated."""
        query_runner = MockQueryRunner([])
        service = UPCService(query_runner)
        
        category = service.get_category_for_item(1)
        
        assert category is None

    def test_caching_behavior(self):
        """Test that UPC dictionary is cached properly."""
        mock_data = [
            (1, "cat", "upc", "a", "b", "c"),
        ]
        query_runner = MockQueryRunner(mock_data)
        service = UPCService(query_runner)
        
        assert service._upc_cache is None
        
        service.fetch_upc_dictionary({})
        
        assert service._upc_cache is not None
        assert 1 in service._upc_cache


class TestProgressReporterProtocol:
    """Tests for ProgressReporter protocol."""

    def test_protocol_exists(self):
        """Test that ProgressReporter protocol exists."""
        assert ProgressReporter is not None


class TestNullProgressReporter:
    """Tests for NullProgressReporter class."""

    def test_update_does_nothing(self):
        """Test that update does nothing."""
        reporter = NullProgressReporter()
        
        reporter.update(
            message="Test",
            folder_num=1,
            folder_total=5,
            file_num=1,
            file_total=10,
            footer="Footer"
        )

    def test_update_with_empty_values(self):
        """Test update with empty values."""
        reporter = NullProgressReporter()
        
        reporter.update(
            message="",
            folder_num=0,
            folder_total=0,
            file_num=0,
            file_total=0,
            footer=""
        )


class TestCLIProgressReporter:
    """Tests for CLIProgressReporter class."""

    def test_output_format(self):
        """Test CLI output format."""
        output = StringIO()
        reporter = CLIProgressReporter(output)
        
        reporter.update(
            message="Processing file",
            folder_num=2,
            folder_total=5,
            file_num=3,
            file_total=10,
            footer="Status: OK"
        )
        
        output.seek(0)
        content = output.read()
        
        assert "Processing file" in content
        assert "Folder 2 of 5" in content
        assert "File 3 of 10" in content
        assert "Status: OK" in content

    def test_output_without_footer(self):
        """Test CLI output without footer."""
        output = StringIO()
        reporter = CLIProgressReporter(output)
        
        reporter.update(
            message="Processing",
            folder_num=1,
            folder_total=3,
            file_num=5,
            file_total=20,
            footer=""
        )
        
        output.seek(0)
        content = output.read()
        
        assert "Processing" in content
        assert "Folder 1 of 3" in content

    def test_finish_writes_newline(self):
        """Test that finish writes a newline."""
        output = StringIO()
        reporter = CLIProgressReporter(output)
        
        reporter.finish()
        
        output.seek(0)
        content = output.read()
        
        assert content == "\n"

    def test_default_output_is_stdout(self):
        """Test that default output is sys.stdout."""
        reporter = CLIProgressReporter()
        
        assert reporter._output is sys.stdout


class TestLoggingProgressReporter:
    """Tests for LoggingProgressReporter class."""

    def test_logs_info_message(self):
        """Test that update logs info message."""
        logger = MagicMock(spec=logging.Logger)
        reporter = LoggingProgressReporter(logger)
        
        reporter.update(
            message="Processing file",
            folder_num=1,
            folder_total=5,
            file_num=3,
            file_total=10,
            footer="Status: OK"
        )
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]
        
        assert "Processing file" in call_args
        assert "Folder 1/5" in call_args
        assert "File 3/10" in call_args
        assert "Status: OK" in call_args

    def test_logs_without_footer(self):
        """Test logging without footer - pipe still present but no footer text."""
        logger = MagicMock(spec=logging.Logger)
        reporter = LoggingProgressReporter(logger)
        
        reporter.update(
            message="Processing",
            folder_num=1,
            folder_total=3,
            file_num=5,
            file_total=20,
            footer=""
        )
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]
        
        assert "Processing" in call_args
        assert "Folder 1/3" in call_args


class TestFileProcessorResult:
    """Tests for FileProcessorResult dataclass."""

    def test_creation_with_defaults(self):
        """Test creating FileProcessorResult with defaults."""
        result = FileProcessorResult()
        
        assert result.input_path == ""
        assert result.output_path == ""
        assert result.was_validated is False
        assert result.validation_passed is True
        assert result.was_split is False
        assert result.was_converted is False
        assert result.was_tweaked is False
        assert result.files_sent is False
        assert result.checksum == ""
        assert result.errors == []

    def test_creation_with_all_fields(self):
        """Test creating FileProcessorResult with all fields."""
        result = FileProcessorResult(
            input_path="/input/file.txt",
            output_path="/output/file.txt",
            was_validated=True,
            validation_passed=True,
            was_split=True,
            was_converted=True,
            was_tweaked=True,
            files_sent=True,
            checksum="abc123",
            errors=["Error 1"]
        )
        
        assert result.input_path == "/input/file.txt"
        assert result.output_path == "/output/file.txt"
        assert result.was_validated is True
        assert result.validation_passed is True
        assert result.was_split is True
        assert result.was_converted is True
        assert result.was_tweaked is True
        assert result.files_sent is True
        assert result.checksum == "abc123"
        assert result.errors == ["Error 1"]


class TestMockFileProcessor:
    """Tests for MockFileProcessor class."""

    def test_creation_with_result(self):
        """Test creating MockFileProcessor with result."""
        result = FileProcessorResult(input_path="/in", output_path="/out")
        processor = MockFileProcessor(result=result)
        
        output = processor.process_file("/in", {}, {}, {})
        
        assert output == result
        assert processor.call_count == 1

    def test_creation_with_fields(self):
        """Test creating MockFileProcessor with individual fields."""
        processor = MockFileProcessor(
            input_path="/in",
            output_path="/out",
            was_validated=True,
            validation_passed=True
        )
        
        result = processor.process_file("/in", {}, {}, {})
        
        assert result.input_path == "/in"
        assert result.output_path == "/out"
        assert result.was_validated is True
        assert result.validation_passed is True

    def test_call_tracking(self):
        """Test that mock tracks calls correctly."""
        processor = MockFileProcessor(
            input_path="/in",
            output_path="/out"
        )
        
        processor.process_file("file1.txt", {"key": "val"}, {"setting": 1}, {})
        processor.process_file("file2.txt", {"key": "val2"}, {"setting": 2}, {1: "a"})
        
        assert processor.call_count == 2
        assert processor.last_file_path == "file2.txt"
        assert processor.last_folder == {"key": "val2"}
        assert processor.last_settings == {"setting": 2}
        assert processor.last_upc_dict == {1: "a"}

    def test_reset(self):
        """Test resetting the mock."""
        processor = MockFileProcessor(input_path="/in", output_path="/out")
        
        processor.process_file("file1.txt", {}, {}, {})
        processor.reset()
        
        assert processor.call_count == 0
        assert processor.last_file_path is None
        assert processor.last_folder is None
        assert processor.last_settings is None
        assert processor.last_upc_dict is None

    def test_set_result(self):
        """Test setting a new result."""
        processor = MockFileProcessor()
        
        result1 = FileProcessorResult(input_path="/in1")
        result2 = FileProcessorResult(input_path="/in2")
        
        processor.set_result(result1)
        assert processor.process_file("", {}, {}, {}).input_path == "/in1"
        
        processor.set_result(result2)
        assert processor.process_file("", {}, {}, {}).input_path == "/in2"


class TestFileProcessor:
    """Tests for FileProcessor class."""

    def test_process_file_without_validators(self):
        """Test processing without any pipeline steps."""
        processor = FileProcessor()
        
        result = processor.process_file("/input/file.txt", {}, {}, {})
        
        assert result.input_path == "/input/file.txt"
        assert result.was_validated is False

    def test_process_file_with_validator_pass(self):
        """Test processing with passing validator."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = MagicMock(
            is_valid=True,
            errors=[]
        )
        mock_validator.should_block_processing.return_value = False
        
        processor = FileProcessor(validator=mock_validator)
        
        result = processor.process_file(
            "/input/file.txt",
            {"process_edi": True},
            {},
            {}
        )
        
        assert result.was_validated is True
        assert result.validation_passed is True

    def test_process_file_with_validator_fail(self):
        """Test processing with failing validator."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = MagicMock(
            is_valid=False,
            errors=["Invalid file"]
        )
        mock_validator.should_block_processing.return_value = True
        
        processor = FileProcessor(validator=mock_validator)
        
        result = processor.process_file(
            "/input/file.txt",
            {"process_edi": True},
            {},
            {}
        )
        
        assert result.was_validated is True
        assert result.validation_passed is False

    def test_process_file_validation_blocked(self):
        """Test that processing is blocked when validation fails."""
        mock_validator = MagicMock()
        mock_validator.validate.return_value = MagicMock(
            is_valid=False,
            errors=["Error 1"]
        )
        mock_validator.should_block_processing.return_value = True
        
        processor = FileProcessor(validator=mock_validator)
        
        result = processor.process_file(
            "/input/file.txt",
            {"process_edi": True},
            {},
            {}
        )
        
        assert result.validation_passed is False
        assert result.was_split is False
        assert result.was_tweaked is False
        assert result.was_converted is False

    def test_process_file_with_splitter(self):
        """Test processing with splitter."""
        mock_splitter = MagicMock()
        mock_splitter.split.return_value = MagicMock(
            files=[("/output/file.txt", "", "")],
            was_split=True,
            errors=[]
        )
        
        processor = FileProcessor(splitter=mock_splitter)
        
        result = processor.process_file(
            "/input/file.txt",
            {"split_edi": True},
            {},
            {}
        )
        
        assert result.was_split is True

    def test_process_file_with_tweaker(self):
        """Test processing with tweaker."""
        mock_tweaker = MagicMock()
        mock_tweaker.tweak.return_value = MagicMock(
            output_path="/output/tweaked.txt",
            success=True,
            was_tweaked=True,
            errors=[]
        )
        
        processor = FileProcessor(tweaker=mock_tweaker)
        
        result = processor.process_file(
            "/input/file.txt",
            {"tweak_edi": True},
            {},
            {}
        )
        
        assert result.was_tweaked is True

    def test_process_file_with_converter(self):
        """Test processing with converter."""
        mock_converter = MagicMock()
        mock_converter.convert.return_value = MagicMock(
            output_path="/output/converted.csv",
            success=True,
            errors=[]
        )
        
        processor = FileProcessor(converter=mock_converter)
        
        result = processor.process_file(
            "/input/file.txt",
            {},
            {},
            {}
        )
        
        assert result.was_converted is True

    @patch('dispatch.services.file_processor.os.path.exists')
    @patch('dispatch.services.file_processor.generate_file_hash')
    def test_process_file_sending_success(self, mock_hash, mock_exists):
        """Test successful file sending."""
        mock_hash.return_value = "abc123"
        mock_exists.return_value = True
        
        mock_send_manager = MagicMock()
        mock_send_manager.get_enabled_backends.return_value = ["backend1"]
        mock_send_manager.send_all.return_value = {"backend1": True}
        
        processor = FileProcessor(send_manager=mock_send_manager)
        
        result = processor.process_file(
            "/input/file.txt",
            {},
            {},
            {}
        )
        
        assert result.files_sent is True

    def test_process_file_sending_failure(self):
        """Test failed file sending."""
        mock_send_manager = MagicMock()
        mock_send_manager.get_enabled_backends.return_value = []
        
        processor = FileProcessor(send_manager=mock_send_manager)
        
        result = processor.process_file(
            "/input/file.txt",
            {},
            {},
            {}
        )
        
        assert result.files_sent is False

    def test_should_validate_true_for_process_edi(self):
        """Test that validation is triggered for process_edi."""
        processor = FileProcessor()
        
        assert processor._should_validate({"process_edi": True}) is True

    def test_should_validate_true_for_tweak_edi(self):
        """Test that validation is triggered for tweak_edi."""
        processor = FileProcessor()
        
        assert processor._should_validate({"tweak_edi": True}) is True

    def test_should_validate_true_for_split_edi(self):
        """Test that validation is triggered for split_edi."""
        processor = FileProcessor()
        
        assert processor._should_validate({"split_edi": True}) is True

    def test_should_validate_true_for_force_validation(self):
        """Test that validation is triggered for force_edi_validation."""
        processor = FileProcessor()
        
        assert processor._should_validate({"force_edi_validation": True}) is True

    def test_should_validate_false_by_default(self):
        """Test that validation is not triggered by default."""
        processor = FileProcessor()
        
        assert processor._should_validate({}) is False

    def test_should_validate_string_process_edi(self):
        """Test validation with string process_edi."""
        processor = FileProcessor()
        
        assert processor._should_validate({"process_edi": "true"}) is True

    @patch('dispatch.services.file_processor.os.path.exists')
    @patch('dispatch.services.file_processor.generate_file_hash')
    def test_process_file_error_accumulation(self, mock_hash, mock_exists):
        """Test that errors are accumulated through pipeline when no split error."""
        mock_hash.return_value = "abc123"
        mock_exists.return_value = True
        
        mock_splitter = MagicMock()
        mock_splitter.split.return_value = MagicMock(
            files=[("/output/file.txt", "", "")],
            was_split=False,
            errors=[]
        )
        
        mock_tweaker = MagicMock()
        mock_tweaker.tweak.return_value = MagicMock(
            output_path="/output/file.txt",
            success=False,
            was_tweaked=False,
            errors=["Tweak error"]
        )
        
        mock_converter = MagicMock()
        mock_converter.convert.return_value = MagicMock(
            output_path="/output/file.txt",
            success=False,
            errors=["Convert error"]
        )
        
        processor = FileProcessor(
            splitter=mock_splitter,
            tweaker=mock_tweaker,
            converter=mock_converter
        )
        
        result = processor.process_file(
            "/input/file.txt",
            {},
            {},
            {}
        )
        
        assert "Tweak error" in result.errors
        assert "Convert error" in result.errors
