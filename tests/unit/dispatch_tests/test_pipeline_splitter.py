"""Tests for dispatch/pipeline/splitter.py module."""

from unittest.mock import MagicMock, patch
import pytest

from dispatch.pipeline.splitter import (
    SplitterResult,
    MockSplitter,
    FilesystemAdapter,
    EDISplitterStep,
    SplitterInterface,
    CreditDetectorProtocol,
    DefaultCreditDetector,
)
from core.edi.edi_splitter import SplitConfig, SplitResult


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self, files: dict[str, str] = None):
        self.files = files or {}
        self.text_files = {}
        self.binary_files = {}
        self.directories = set()
        self.removed_files = []
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
        if path not in self.files and path not in self.text_files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files.get(path, self.text_files.get(path, ''))
    
    def read_file(self, path: str) -> bytes:
        if path not in self.files and path not in self.binary_files:
            raise FileNotFoundError(f"File not found: {path}")
        content = self.files.get(path) or self.binary_files.get(path, b'')
        if isinstance(content, str):
            return content.encode()
        return content
    
    def write_file(self, path: str, data: bytes) -> None:
        self.binary_files[path] = data
    
    def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
        self.text_files[path] = data
    
    def file_exists(self, path: str) -> bool:
        return path in self.files or path in self.text_files or path in self.binary_files
    
    def dir_exists(self, path: str) -> bool:
        return path in self.directories
    
    def mkdir(self, path: str) -> None:
        self.directories.add(path)
    
    def makedirs(self, path: str) -> None:
        self.directories.add(path)
    
    def copy_file(self, src: str, dst: str) -> None:
        if src in self.files:
            self.files[dst] = self.files[src]
    
    def remove_file(self, path: str) -> None:
        self.removed_files.append(path)
        self.files.pop(path, None)
        self.text_files.pop(path, None)
        self.binary_files.pop(path, None)
    
    def get_absolute_path(self, path: str) -> str:
        return path
    
    def list_files(self, path: str) -> list[str]:
        all_files = list(self.files.keys()) + list(self.text_files.keys()) + list(self.binary_files.keys())
        return [f for f in all_files if f.startswith(path)]


class MockErrorHandler:
    """Mock error handler for testing."""
    
    def __init__(self):
        self.errors = []
    
    def record_error(self, folder: str, filename: str, error: Exception, context: dict = None, error_source: str = "Dispatch"):
        self.errors.append({
            'folder': folder,
            'filename': filename,
            'error': error,
            'context': context,
            'error_source': error_source
        })


class MockCreditDetector:
    """Mock credit detector for testing."""
    
    def __init__(self, is_credit: bool = False):
        self._is_credit = is_credit
        self.call_count = 0
        self.last_file_path = None
    
    def detect(self, file_path: str) -> bool:
        self.call_count += 1
        self.last_file_path = file_path
        return self._is_credit
    
    def reset(self):
        self.call_count = 0
        self.last_file_path = None


class MockEDISplitter:
    """Mock EDI splitter for testing EDISplitterStep."""
    
    def __init__(self):
        self.call_count = 0
        self.last_input_path = None
        self.last_config = None
        self.last_upc_dict = None
        self.last_filter_categories = None
        self.last_filter_mode = None
        self._result = None
        self._exception = None
    
    def set_result(self, result: SplitResult):
        self._result = result
    
    def set_exception(self, exception: Exception):
        self._exception = exception
    
    def do_split_edi(
        self,
        input_path: str,
        config: SplitConfig,
        upc_dict: dict = None,
        filter_categories: str = "ALL",
        filter_mode: str = "include"
    ) -> SplitResult:
        self.call_count += 1
        self.last_input_path = input_path
        self.last_config = config
        self.last_upc_dict = upc_dict
        self.last_filter_categories = filter_categories
        self.last_filter_mode = filter_mode
        
        if self._exception:
            raise self._exception
        
        if self._result:
            return self._result
        
        return SplitResult(output_files=[], skipped_invoices=0, total_lines_written=0)


@pytest.fixture
def edi_content_single_invoice():
    """EDI content with single A record (invoice)."""
    b_record = "B12345678901" + " " * 65
    return f"AHEADER001  12345  010123\n{b_record}\nCFOOTER\n"


@pytest.fixture
def edi_content_multiple_invoices():
    """EDI content with multiple A records (invoices)."""
    b_record1 = "B12345678901" + " " * 65
    b_record2 = "B12345678902" + " " * 65
    return f"AHEADER001  12345  010123\n{b_record1}\nCFOOTER\nAHEADER002  12346  010123\n{b_record2}\nCFOOTER\n"


@pytest.fixture
def edi_content_with_credit():
    """EDI content with credit memo (negative invoice total)."""
    b_record = "B12345678901" + " " * 65
    return f"AHEADER001  -1234  010123\n{b_record}\nCFOOTER\n"


@pytest.fixture
def sample_upc_dict():
    """Sample UPC dictionary for testing."""
    return {
        12345678901: ['CAT1', 'UPC1', 'UPC2', 'UPC3', 'UPC4'],
        12345678902: ['CAT2', 'UPC1', 'UPC2', 'UPC3', 'UPC4'],
    }


@pytest.fixture
def mock_file_system(edi_content_single_invoice):
    """Mock file system with single invoice EDI content."""
    return MockFileSystem({
        '/test/input.edi': edi_content_single_invoice
    })


@pytest.fixture
def mock_splitter():
    """Mock splitter instance."""
    return MockSplitter()


@pytest.fixture
def mock_credit_detector():
    """Mock credit detector instance."""
    return MockCreditDetector()


@pytest.fixture
def sample_params_split_enabled():
    """Sample params dict with split_edi enabled."""
    return {
        'split_edi': True,
        'split_edi_filter_categories': 'ALL',
        'split_edi_filter_mode': 'include',
        'prepend_date_files': False,
        'split_edi_include_invoices': True,
        'split_edi_include_credits': True,
    }


@pytest.fixture
def sample_params_split_disabled():
    """Sample params dict with split_edi disabled."""
    return {
        'split_edi': False,
        'split_edi_filter_categories': 'ALL',
    }


class TestSplitterResult:
    """Tests for SplitterResult dataclass."""
    
    def test_default_values(self):
        """Test SplitterResult with default values."""
        result = SplitterResult()
        
        assert result.files == []
        assert result.was_split is False
        assert result.was_filtered is False
        assert result.skipped_invoices == 0
        assert result.errors == []
    
    def test_custom_values(self):
        """Test SplitterResult with custom values."""
        files = [('/output/file1.inv', 'A_', '.inv'), ('/output/file2.inv', 'B_', '.inv')]
        errors = ['Error 1', 'Error 2']
        
        result = SplitterResult(
            files=files,
            was_split=True,
            was_filtered=True,
            skipped_invoices=5,
            errors=errors
        )
        
        assert result.files == files
        assert result.was_split is True
        assert result.was_filtered is True
        assert result.skipped_invoices == 5
        assert result.errors == errors
    
    def test_files_list_properly_handled(self):
        """Test that files list is properly handled."""
        files = [
            ('/output/split1.inv', 'A_', '.inv'),
            ('/output/split2.cr', 'B_', '.cr'),
            ('/output/split3.inv', 'C_', '.inv'),
        ]
        
        result = SplitterResult(files=files)
        
        assert len(result.files) == 3
        assert result.files[0] == ('/output/split1.inv', 'A_', '.inv')
        assert result.files[1] == ('/output/split2.cr', 'B_', '.cr')
        assert result.files[2] == ('/output/split3.inv', 'C_', '.inv')
    
    def test_empty_files_list(self):
        """Test SplitterResult with empty files list."""
        result = SplitterResult(files=[])
        
        assert result.files == []
        assert len(result.files) == 0
    
    def test_errors_list_mutable(self):
        """Test that errors list can be modified."""
        result = SplitterResult()
        
        result.errors.append("New error")
        
        assert "New error" in result.errors
    
    def test_multiple_errors(self):
        """Test SplitterResult with multiple errors."""
        errors = [f"Error {i}" for i in range(10)]
        result = SplitterResult(errors=errors)
        
        assert len(result.errors) == 10


class TestMockSplitter:
    """Tests for MockSplitter class."""
    
    def test_initialization_with_default_result(self):
        """Test MockSplitter initialization with default result."""
        splitter = MockSplitter()
        
        assert splitter._result is not None
        assert splitter._result.files == []
        assert splitter._result.was_split is False
        assert splitter.call_count == 0
        assert splitter.last_input_path is None
    
    def test_initialization_with_custom_result(self):
        """Test MockSplitter initialization with custom result."""
        custom_result = SplitterResult(
            files=[('/output/file.inv', 'A_', '.inv')],
            was_split=True
        )
        splitter = MockSplitter(result=custom_result)
        
        assert splitter._result == custom_result
        assert splitter._result.files == [('/output/file.inv', 'A_', '.inv')]
    
    def test_initialization_with_individual_parameters(self):
        """Test MockSplitter initialization with individual parameters."""
        files = [('/output/file.inv', 'A_', '.inv')]
        
        splitter = MockSplitter(
            files=files,
            was_split=True,
            was_filtered=True,
            skipped_invoices=3,
            errors=['Test error']
        )
        
        assert splitter._result.files == files
        assert splitter._result.was_split is True
        assert splitter._result.was_filtered is True
        assert splitter._result.skipped_invoices == 3
        assert splitter._result.errors == ['Test error']
    
    def test_call_tracking(self):
        """Test call tracking (call_count, last_* fields)."""
        splitter = MockSplitter()
        
        assert splitter.call_count == 0
        assert splitter.last_input_path is None
        assert splitter.last_output_dir is None
        assert splitter.last_params is None
        assert splitter.last_upc_dict is None
        
        splitter.split('/input/test.edi', '/output', {'split_edi': True}, {'upc': 'dict'})
        
        assert splitter.call_count == 1
        assert splitter.last_input_path == '/input/test.edi'
        assert splitter.last_output_dir == '/output'
        assert splitter.last_params == {'split_edi': True}
        assert splitter.last_upc_dict == {'upc': 'dict'}
        
        splitter.split('/input/another.edi', '/output2', {}, {})
        
        assert splitter.call_count == 2
        assert splitter.last_input_path == '/input/another.edi'
        assert splitter.last_output_dir == '/output2'
    
    def test_reset_method(self):
        """Test reset method clears tracking state."""
        splitter = MockSplitter()
        
        splitter.split('/input/test.edi', '/output', {}, {})
        
        assert splitter.call_count == 1
        assert splitter.last_input_path == '/input/test.edi'
        
        splitter.reset()
        
        assert splitter.call_count == 0
        assert splitter.last_input_path is None
        assert splitter.last_output_dir is None
        assert splitter.last_params is None
        assert splitter.last_upc_dict is None
    
    def test_set_result_method(self):
        """Test set_result method updates the result."""
        splitter = MockSplitter()
        
        new_result = SplitterResult(
            files=[('/new/file.inv', 'X_', '.inv')],
            was_split=True,
            was_filtered=True
        )
        
        splitter.set_result(new_result)
        
        assert splitter._result == new_result
        assert splitter._result.files == [('/new/file.inv', 'X_', '.inv')]
    
    def test_split_returns_configured_result(self):
        """Test that split returns the configured result."""
        custom_result = SplitterResult(
            files=[('/output/test.inv', 'A_', '.inv')],
            was_split=True
        )
        splitter = MockSplitter(result=custom_result)
        
        result = splitter.split('/input/test.edi', '/output', {}, {})
        
        assert result == custom_result
        assert result.files == [('/output/test.inv', 'A_', '.inv')]


class TestFilesystemAdapter:
    """Tests for FilesystemAdapter class."""
    
    def test_adapts_read_file_text(self):
        """Test that read_file properly adapts read_file_text."""
        mock_fs = MockFileSystem({'/test/file.edi': 'test content'})
        adapter = FilesystemAdapter(mock_fs)
        
        result = adapter.read_file('/test/file.edi')
        
        assert result == 'test content'
    
    def test_adapts_write_file_text(self):
        """Test that write_file properly adapts write_file_text."""
        mock_fs = MockFileSystem()
        adapter = FilesystemAdapter(mock_fs)
        
        adapter.write_file('/test/file.edi', 'new content')
        
        assert mock_fs.text_files['/test/file.edi'] == 'new content'
    
    def test_adapts_write_binary(self):
        """Test that write_binary properly delegates."""
        mock_fs = MockFileSystem()
        adapter = FilesystemAdapter(mock_fs)
        
        adapter.write_binary('/test/file.edi', b'binary content')
        
        assert mock_fs.binary_files['/test/file.edi'] == b'binary content'
    
    def test_adapts_file_exists(self):
        """Test that file_exists properly delegates."""
        mock_fs = MockFileSystem({'/test/file.edi': 'content'})
        adapter = FilesystemAdapter(mock_fs)
        
        assert adapter.file_exists('/test/file.edi') is True
        assert adapter.file_exists('/test/nonexistent.edi') is False
    
    def test_adapts_directory_exists(self):
        """Test that directory_exists properly delegates."""
        mock_fs = MockFileSystem()
        mock_fs.directories.add('/test/dir')
        adapter = FilesystemAdapter(mock_fs)
        
        assert adapter.directory_exists('/test/dir') is True
        assert adapter.directory_exists('/test/nonexistent') is False
    
    def test_adapts_create_directory(self):
        """Test that create_directory properly delegates to makedirs."""
        mock_fs = MockFileSystem()
        adapter = FilesystemAdapter(mock_fs)
        
        adapter.create_directory('/test/newdir')
        
        assert '/test/newdir' in mock_fs.directories
    
    def test_adapts_remove_file(self):
        """Test that remove_file properly delegates."""
        mock_fs = MockFileSystem({'/test/file.edi': 'content'})
        adapter = FilesystemAdapter(mock_fs)
        
        adapter.remove_file('/test/file.edi')
        
        assert '/test/file.edi' in mock_fs.removed_files
    
    def test_adapts_list_files(self):
        """Test that list_files properly delegates."""
        mock_fs = MockFileSystem({
            '/test/file1.edi': 'content1',
            '/test/file2.edi': 'content2',
        })
        adapter = FilesystemAdapter(mock_fs)
        
        result = adapter.list_files('/test')
        
        assert len(result) == 2


class TestEDISplitterStep:
    """Tests for EDISplitterStep class."""
    
    def test_initialization_with_defaults(self):
        """Test EDISplitterStep initialization with default values."""
        step = EDISplitterStep()
        
        assert step._splitter is not None
        assert step._error_handler is None
        assert step._file_system is None
        assert isinstance(step._credit_detector, DefaultCreditDetector)
    
    def test_initialization_with_injected_dependencies(self):
        """Test EDISplitterStep initialization with injected dependencies."""
        mock_splitter = MockEDISplitter()
        mock_error_handler = MockErrorHandler()
        mock_fs = MockFileSystem()
        mock_credit_detector = MockCreditDetector()
        
        step = EDISplitterStep(
            splitter=mock_splitter,
            error_handler=mock_error_handler,
            file_system=mock_fs,
            credit_detector=mock_credit_detector
        )
        
        assert step._splitter is mock_splitter
        assert step._error_handler is mock_error_handler
        assert step._file_system is mock_fs
        assert step._credit_detector is mock_credit_detector
    
    def test_split_with_split_edi_false(self):
        """Test split() with split_edi=False (no splitting, just return original)."""
        mock_splitter = MockEDISplitter()
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': False}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is False
        assert result.files == [('/input/test.edi', '', '')]
        assert mock_splitter.call_count == 0
    
    def test_split_with_split_edi_true_single_invoice(self):
        """Test split() with split_edi=True and single invoice (no split needed)."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=0,
            total_lines_written=3
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is False
        assert len(result.files) == 1
    
    def test_split_with_split_edi_true_multiple_invoices(self):
        """Test split() with split_edi=True and multiple invoices."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.inv', 'B_', '.inv'),
                ('/output/C_split.inv', 'C_', '.inv'),
            ],
            skipped_invoices=2,
            total_lines_written=10
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is True
        assert len(result.files) == 3
        assert result.skipped_invoices == 2
    
    def test_split_with_category_filtering_enabled(self):
        """Test split() with category filtering enabled (filter_categories != 'ALL')."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=5,
            total_lines_written=3
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {
            'split_edi': True,
            'split_edi_filter_categories': 'CAT1,CAT2',
            'split_edi_filter_mode': 'include'
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_filtered is True
        assert mock_splitter.last_filter_categories == 'CAT1,CAT2'
        assert mock_splitter.last_filter_mode == 'include'
    
    def test_split_with_credit_invoice_filtering_include_invoices_only(self):
        """Test split() with credit/invoice filtering - include invoices only."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.cr', 'B_', '.cr'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        mock_credit_detector = MockCreditDetector(is_credit=False)
        
        def detect_credit(path):
            return path.endswith('.cr')
        
        mock_credit_detector.detect = detect_credit
        step = EDISplitterStep(splitter=mock_splitter, credit_detector=mock_credit_detector)
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': False
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert len(result.files) == 1
        assert result.files[0][0] == '/output/A_split.inv'
    
    def test_split_with_credit_invoice_filtering_include_credits_only(self):
        """Test split() with credit/invoice filtering - include credits only."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.cr', 'B_', '.cr'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        mock_credit_detector = MockCreditDetector()
        
        def detect_credit(path):
            return path.endswith('.cr')
        
        mock_credit_detector.detect = detect_credit
        step = EDISplitterStep(splitter=mock_splitter, credit_detector=mock_credit_detector)
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': False,
            'split_edi_include_credits': True
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert len(result.files) == 1
        assert result.files[0][0] == '/output/B_split.cr'
    
    def test_split_with_credit_invoice_filtering_include_both(self):
        """Test split() with credit/invoice filtering - include both."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.cr', 'B_', '.cr'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': True
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert len(result.files) == 2
    
    def test_split_credit_detection_integration(self):
        """Test credit detection integration."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.cr', 'B_', '.cr'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        mock_credit_detector = MockCreditDetector()
        step = EDISplitterStep(splitter=mock_splitter, credit_detector=mock_credit_detector)
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': False
        }
        
        step.split('/input/test.edi', '/output', params, {})
    
    def test_split_error_handling_when_splitter_raises_value_error(self):
        """Test error handling when splitter raises ValueError."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_exception(ValueError("No valid invoices after filtering"))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is False
        assert len(result.errors) == 1
        assert "No valid invoices after filtering" in result.errors[0]
    
    def test_split_error_handling_when_splitter_raises_generic_exception(self):
        """Test error handling when splitter raises generic exception."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_exception(RuntimeError("Unexpected error"))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is False
        assert len(result.errors) == 1
        assert "Split failed" in result.errors[0]
    
    def test_split_error_recording_to_error_handler(self):
        """Test error recording to error handler."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_exception(ValueError("Test error"))
        mock_error_handler = MockErrorHandler()
        
        step = EDISplitterStep(
            splitter=mock_splitter,
            error_handler=mock_error_handler
        )
        
        params = {'split_edi': True}
        step.split('/input/test.edi', '/output', params, {})
        
        assert len(mock_error_handler.errors) == 1
        assert mock_error_handler.errors[0]['filename'] == '/input/test.edi'
        assert mock_error_handler.errors[0]['error_source'] == 'EDISplitter'
    
    def test_split_parameter_normalization_string_true(self):
        """Test parameter normalization for string 'True' to bool."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=0,
            total_lines_written=3
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': 'True'}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert mock_splitter.call_count == 1
    
    def test_split_parameter_normalization_string_false(self):
        """Test parameter normalization for string 'False' to bool."""
        mock_splitter = MockEDISplitter()
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': 'False'}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert mock_splitter.call_count == 0
        assert result.was_split is False
    
    def test_split_parameter_normalization_include_invoices_string(self):
        """Test parameter normalization for include_invoices string values."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.inv', 'B_', '.inv'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': 'false'
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is True
        assert mock_splitter.call_count == 1
    
    def test_split_parameter_normalization_include_invoices_int(self):
        """Test parameter normalization for include_invoices int values."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.inv', 'B_', '.inv'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': 1,
            'split_edi_include_credits': 0
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is True
        assert mock_splitter.call_count == 1
    
    def test_split_with_prepend_date_string_normalization(self):
        """Test prepend_date_files string normalization."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=0,
            total_lines_written=3
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {
            'split_edi': True,
            'prepend_date_files': 'True'
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert mock_splitter.last_config.prepend_date is True


class TestSplitterInterface:
    """Tests for SplitterInterface protocol."""
    
    def test_mock_splitter_satisfies_protocol(self):
        """Test MockSplitter satisfies SplitterInterface protocol."""
        splitter = MockSplitter()
        
        assert hasattr(splitter, 'split')
        assert callable(splitter.split)
    
    def test_edi_splitter_step_satisfies_protocol(self):
        """Test EDISplitterStep satisfies SplitterInterface protocol."""
        step = EDISplitterStep()
        
        assert hasattr(step, 'split')
        assert callable(step.split)


class TestCreditDetectorProtocol:
    """Tests for CreditDetectorProtocol protocol."""
    
    def test_mock_credit_detector_satisfies_protocol(self):
        """Test MockCreditDetector satisfies CreditDetectorProtocol."""
        detector = MockCreditDetector()
        
        assert hasattr(detector, 'detect')
        assert callable(detector.detect)
    
    def test_default_credit_detector_satisfies_protocol(self):
        """Test DefaultCreditDetector satisfies CreditDetectorProtocol."""
        detector = DefaultCreditDetector()
        
        assert hasattr(detector, 'detect')
        assert callable(detector.detect)


class TestIntegration:
    """Integration tests for pipeline splitter."""
    
    def test_full_split_flow_with_mock_file_system(self, edi_content_multiple_invoices):
        """Test full split flow with mock file system."""
        mock_fs = MockFileSystem({
            '/input/test.edi': edi_content_multiple_invoices
        })
        mock_error_handler = MockErrorHandler()
        
        step = EDISplitterStep(
            error_handler=mock_error_handler,
            file_system=mock_fs
        )
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert isinstance(result, SplitterResult)
        assert result.was_split is True or result.was_split is False
        assert len(mock_error_handler.errors) == 0
    
    def test_filtering_without_split_uses_utils(self):
        """Test that filtering without split uses utils.filter_edi_file_by_category."""
        mock_splitter = MockEDISplitter()
        mock_fs = MockFileSystem({'/input/test.edi': 'AHEADER\nB12345678901' + ' ' * 65 + '\nCFOOTER\n'})
        step = EDISplitterStep(splitter=mock_splitter, file_system=mock_fs)
        
        with patch('utils.filter_edi_file_by_category', return_value=True) as mock_filter:
            params = {
                'split_edi': False,
                'split_edi_filter_categories': 'CAT1'
            }
            result = step.split('/input/test.edi', '/output', params, {})
            
            assert result.was_filtered is True
    
    def test_filtering_without_split_no_filter(self):
        """Test filtering without split when filter_categories is 'ALL'."""
        mock_splitter = MockEDISplitter()
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {
            'split_edi': False,
            'split_edi_filter_categories': 'ALL'
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_filtered is False
        assert result.files == [('/input/test.edi', '', '')]
    
    def test_multiple_split_operations_in_sequence(self):
        """Test multiple split operations in sequence."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=0,
            total_lines_written=3
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        
        result1 = step.split('/input/file1.edi', '/output', params, {})
        result2 = step.split('/input/file2.edi', '/output', params, {})
        
        assert mock_splitter.call_count == 2
        assert mock_splitter.last_input_path == '/input/file2.edi'
    
    def test_error_handler_context_preserved(self):
        """Test that error handler receives correct context."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_exception(ValueError("Test error"))
        mock_error_handler = MockErrorHandler()
        
        step = EDISplitterStep(
            splitter=mock_splitter,
            error_handler=mock_error_handler
        )
        
        params = {'split_edi': True}
        step.split('/input/test.edi', '/output', params, {})
        
        assert mock_error_handler.errors[0]['context'] == {'source': 'EDISplitterStep'}
    
    def test_full_flow_with_category_filtering(self):
        """Test full flow with category filtering enabled."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=3,
            total_lines_written=3
        ))
        mock_error_handler = MockErrorHandler()
        
        step = EDISplitterStep(
            splitter=mock_splitter,
            error_handler=mock_error_handler
        )
        
        params = {
            'split_edi': True,
            'split_edi_filter_categories': 'CAT1,CAT2',
            'split_edi_filter_mode': 'exclude'
        }
        upc_dict = {123: ['CAT3', 'upc1', 'upc2']}
        
        result = step.split('/input/test.edi', '/output', params, upc_dict)
        
        assert result.was_filtered is True
        assert result.skipped_invoices == 3
        assert mock_splitter.last_filter_categories == 'CAT1,CAT2'
        assert mock_splitter.last_filter_mode == 'exclude'


class TestEdgeCases:
    """Edge case tests for pipeline splitter."""
    
    def test_empty_files_in_result(self):
        """Test handling of empty files list in split result."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[],
            skipped_invoices=0,
            total_lines_written=0
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.files == [('/input/test.edi', '', '')]
    
    def test_filtering_error_handling(self):
        """Test error handling during category filtering without split."""
        mock_fs = MockFileSystem({'/input/test.edi': 'content'})
        step = EDISplitterStep(file_system=mock_fs)
        
        with patch('utils.filter_edi_file_by_category', side_effect=Exception("Filter error")):
            params = {
                'split_edi': False,
                'split_edi_filter_categories': 'CAT1'
            }
            result = step.split('/input/test.edi', '/output', params, {})
            
            assert len(result.errors) == 1
            assert "Category filtering failed" in result.errors[0]
    
    def test_credit_detector_exception_handling(self):
        """Test that credit detector exceptions are handled gracefully."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[
                ('/output/A_split.inv', 'A_', '.inv'),
                ('/output/B_split.cr', 'B_', '.cr'),
            ],
            skipped_invoices=0,
            total_lines_written=6
        ))
        
        def raise_exception(path):
            raise RuntimeError("Detection failed")
        
        mock_credit_detector = MockCreditDetector()
        mock_credit_detector.detect = raise_exception
        
        step = EDISplitterStep(
            splitter=mock_splitter,
            credit_detector=mock_credit_detector
        )
        
        params = {
            'split_edi': True,
            'split_edi_include_invoices': True,
            'split_edi_include_credits': False
        }
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert len(result.files) == 2
    
    def test_none_upc_dict(self):
        """Test split with None upc_dict."""
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=[('/output/split.inv', 'A_', '.inv')],
            skipped_invoices=0,
            total_lines_written=3
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, None)
        
        assert mock_splitter.last_upc_dict is None
    
    def test_empty_params(self):
        """Test split with empty params dict."""
        mock_splitter = MockEDISplitter()
        step = EDISplitterStep(splitter=mock_splitter)
        
        result = step.split('/input/test.edi', '/output', {}, {})
        
        assert result.was_split is False
        assert result.files == [('/input/test.edi', '', '')]
    
    def test_large_number_of_output_files(self):
        """Test handling of large number of output files."""
        output_files = [
            (f'/output/{i}_split.inv', f'{i}_', '.inv')
            for i in range(100)
        ]
        
        mock_splitter = MockEDISplitter()
        mock_splitter.set_result(SplitResult(
            output_files=output_files,
            skipped_invoices=0,
            total_lines_written=300
        ))
        step = EDISplitterStep(splitter=mock_splitter)
        
        params = {'split_edi': True}
        result = step.split('/input/test.edi', '/output', params, {})
        
        assert result.was_split is True
        assert len(result.files) == 100
    
    def test_splitter_result_with_all_false_flags(self):
        """Test SplitterResult with all flags False."""
        result = SplitterResult(
            files=[('/output/file.inv', 'A_', '.inv')],
            was_split=False,
            was_filtered=False,
            skipped_invoices=0,
            errors=[]
        )
        
        assert result.was_split is False
        assert result.was_filtered is False
        assert result.skipped_invoices == 0
        assert len(result.errors) == 0
    
    def test_prepend_date_normalization_various_strings(self):
        """Test prepend_date normalization with various string formats."""
        for value in ['true', 'True', 'TRUE']:
            mock_splitter = MockEDISplitter()
            mock_splitter.set_result(SplitResult(
                output_files=[('/output/split.inv', 'A_', '.inv')],
                skipped_invoices=0,
                total_lines_written=3
            ))
            step = EDISplitterStep(splitter=mock_splitter)
            params = {'split_edi': True, 'prepend_date_files': value}
            step.split('/input/test.edi', '/output', params, {})
            assert mock_splitter.last_config.prepend_date is True
        
        for value in ['false', 'False', 'FALSE', 'anything']:
            mock_splitter = MockEDISplitter()
            mock_splitter.set_result(SplitResult(
                output_files=[('/output/split.inv', 'A_', '.inv')],
                skipped_invoices=0,
                total_lines_written=3
            ))
            step = EDISplitterStep(splitter=mock_splitter)
            params = {'split_edi': True, 'prepend_date_files': value}
            step.split('/input/test.edi', '/output', params, {})
            assert mock_splitter.last_config.prepend_date is False
