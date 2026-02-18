"""Tests for dispatch/pipeline/validator.py module."""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from dispatch.pipeline.validator import (
    ValidationResult,
    MockValidator,
    EDIValidationStep,
    ValidationError,
    ValidatorStepInterface,
)
from dispatch.edi_validator import EDIValidator


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self, files: dict[str, str] = None):
        self.files = files or {}
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files[path]


class MockValidatorForStep:
    """Mock validator for EDIValidationStep that has validate_with_warnings."""
    
    def __init__(
        self,
        should_pass: bool = True,
        should_have_minor_errors: bool = False,
        errors: list[str] = None,
        warnings: list[str] = None,
        log_output: str = ""
    ):
        self.should_pass = should_pass
        self.should_have_minor_errors = should_have_minor_errors
        self._errors = errors or []
        self._warnings = warnings or []
        self._log_output = log_output
    
    def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
        return (
            self.should_pass,
            self._errors.copy() if not self.should_pass else [],
            self._warnings.copy() if self.should_have_minor_errors else []
        )
    
    @property
    def has_minor_errors(self):
        return self.should_have_minor_errors
    
    def get_error_log(self):
        return self._log_output


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


@pytest.fixture
def valid_edi_content():
    """Valid EDI content with A, B, and C records."""
    b_record = "B12345678901" + " " * 65
    return f"AHEADER\n{b_record}\nCFOOTER\n"


@pytest.fixture
def invalid_edi_content():
    """Invalid EDI content (first char not A)."""
    return "XINVALID\nB12345678901" + " " * 65 + "\nCFOOTER\n"


@pytest.fixture
def edi_content_with_minor_errors():
    """EDI content with minor errors (suppressed UPC - 8 chars)."""
    b_record = "B12345678" + " " * 62
    return f"AHEADER\n{b_record}\nCFOOTER\n"


@pytest.fixture
def edi_content_truncated_upc():
    """EDI content with truncated UPC (less than 11 chars)."""
    b_record = "B12345" + " " * 65
    return f"AHEADER\n{b_record}\nCFOOTER\n"


@pytest.fixture
def edi_content_blank_upc():
    """EDI content with blank UPC (11 spaces for item number)."""
    b_record = "B" + " " * 11 + " " * 65
    return f"AHEADER\n{b_record}\nCFOOTER\n"


@pytest.fixture
def edi_content_missing_pricing():
    """EDI content with missing pricing (71-char B record)."""
    b_record = "B1234567890" + " " * 60
    return f"AHEADER\n{b_record}\nCFOOTER\n"


@pytest.fixture
def mock_file_system(valid_edi_content):
    """Mock file system with valid EDI content."""
    return MockFileSystem({
        '/test/valid.edi': valid_edi_content
    })


@pytest.fixture
def mock_file_system_with_errors(invalid_edi_content):
    """Mock file system with invalid EDI content."""
    return MockFileSystem({
        '/test/invalid.edi': invalid_edi_content
    })


class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_default_values(self):
        """Test ValidationResult with only required field."""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.has_minor_errors is False
        assert result.errors == []
        assert result.warnings == []
        assert result.log_output == ""
    
    def test_custom_values(self):
        """Test ValidationResult with all custom values."""
        result = ValidationResult(
            is_valid=False,
            has_minor_errors=True,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            log_output="Test log output"
        )
        
        assert result.is_valid is False
        assert result.has_minor_errors is True
        assert result.errors == ["Error 1", "Error 2"]
        assert result.warnings == ["Warning 1"]
        assert result.log_output == "Test log output"
    
    def test_all_fields_properly_set(self):
        """Test that all fields are properly set."""
        result = ValidationResult(
            is_valid=True,
            has_minor_errors=True,
            errors=["Test error"],
            warnings=["Test warning"],
            log_output="Log content"
        )
        
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'has_minor_errors')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'log_output')
    
    def test_is_valid_false_with_no_errors(self):
        """Test ValidationResult can be invalid with empty errors list."""
        result = ValidationResult(is_valid=False, errors=[])
        
        assert result.is_valid is False
        assert result.errors == []
    
    def test_is_valid_true_with_warnings(self):
        """Test ValidationResult can be valid with warnings."""
        result = ValidationResult(
            is_valid=True,
            has_minor_errors=True,
            warnings=["Minor issue"]
        )
        
        assert result.is_valid is True
        assert result.has_minor_errors is True
        assert len(result.warnings) == 1
    
    def test_empty_strings(self):
        """Test ValidationResult with empty string values."""
        result = ValidationResult(
            is_valid=True,
            log_output=""
        )
        
        assert result.log_output == ""
    
    def test_multiple_errors_and_warnings(self):
        """Test ValidationResult with multiple errors and warnings."""
        errors = [f"Error {i}" for i in range(10)]
        warnings = [f"Warning {i}" for i in range(5)]
        
        result = ValidationResult(
            is_valid=False,
            has_minor_errors=True,
            errors=errors,
            warnings=warnings
        )
        
        assert len(result.errors) == 10
        assert len(result.warnings) == 5
    
    def test_dataclass_immutability_of_lists(self):
        """Test that modifying returned lists doesn't affect original."""
        result = ValidationResult(
            is_valid=True,
            errors=["Error 1"],
            warnings=["Warning 1"]
        )
        
        result.errors.append("Error 2")
        
        assert "Error 2" in result.errors


class TestMockValidator:
    """Tests for MockValidator class."""
    
    def test_passing_validation(self):
        """Test mock validator configured to pass."""
        validator = MockValidator(should_pass=True)
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.is_valid is True
        assert result.has_minor_errors is False
        assert result.errors == []
    
    def test_failing_validation(self):
        """Test mock validator configured to fail."""
        validator = MockValidator(should_pass=False, errors=["Validation failed"])
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.is_valid is False
        assert result.errors == ["Validation failed"]
    
    def test_minor_errors(self):
        """Test mock validator with minor errors."""
        validator = MockValidator(
            should_pass=True,
            should_have_minor_errors=True,
            warnings=["Minor warning"]
        )
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.is_valid is True
        assert result.has_minor_errors is True
        assert result.warnings == ["Minor warning"]
    
    def test_custom_error_messages(self):
        """Test mock validator with custom error messages."""
        custom_errors = ["Custom error 1", "Custom error 2"]
        validator = MockValidator(should_pass=False, errors=custom_errors)
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.errors == custom_errors
    
    def test_custom_warning_messages(self):
        """Test mock validator with custom warning messages."""
        custom_warnings = ["Custom warning 1", "Custom warning 2"]
        validator = MockValidator(
            should_pass=True,
            should_have_minor_errors=True,
            warnings=custom_warnings
        )
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.warnings == custom_warnings
    
    def test_custom_log_output(self):
        """Test mock validator with custom log output."""
        validator = MockValidator(log_output="Custom log output")
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.log_output == "Custom log output"
    
    def test_call_tracking(self):
        """Test that call count and last file info are tracked."""
        validator = MockValidator()
        
        assert validator.call_count == 0
        assert validator.last_file_path is None
        assert validator.last_filename_for_log is None
        
        validator.validate('/test/file1.edi', 'file1.edi')
        
        assert validator.call_count == 1
        assert validator.last_file_path == '/test/file1.edi'
        assert validator.last_filename_for_log == 'file1.edi'
        
        validator.validate('/test/file2.edi', 'file2.edi')
        
        assert validator.call_count == 2
        assert validator.last_file_path == '/test/file2.edi'
        assert validator.last_filename_for_log == 'file2.edi'
    
    def test_reset_method(self):
        """Test reset method clears tracking state."""
        validator = MockValidator()
        
        validator.validate('/test/file.edi', 'file.edi')
        
        assert validator.call_count == 1
        assert validator.last_file_path == '/test/file.edi'
        
        validator.reset()
        
        assert validator.call_count == 0
        assert validator.last_file_path is None
        assert validator.last_filename_for_log is None
    
    def test_should_block_processing_when_passing(self):
        """Test should_block_processing returns False when passing."""
        validator = MockValidator(should_pass=True)
        
        assert validator.should_block_processing({'report_edi_errors': True}) is False
        assert validator.should_block_processing({'report_edi_errors': False}) is False
    
    def test_should_block_processing_when_failing_with_report_enabled(self):
        """Test should_block_processing returns True when failing and report enabled."""
        validator = MockValidator(should_pass=False)
        
        assert validator.should_block_processing({'report_edi_errors': True}) is True
    
    def test_should_block_processing_when_failing_with_report_disabled(self):
        """Test should_block_processing returns False when failing but report disabled."""
        validator = MockValidator(should_pass=False)
        
        assert validator.should_block_processing({'report_edi_errors': False}) is False
    
    def test_should_block_processing_default_param(self):
        """Test should_block_processing with missing report_edi_errors key."""
        validator = MockValidator(should_pass=False)
        
        assert validator.should_block_processing({}) is False
    
    def test_multiple_validations_independent_results(self):
        """Test that each validation returns independent result."""
        validator = MockValidator(should_pass=True)
        
        result1 = validator.validate('/test/file1.edi', 'file1.edi')
        result2 = validator.validate('/test/file2.edi', 'file2.edi')
        
        assert result1 is not result2
    
    def test_default_constructor_values(self):
        """Test MockValidator default constructor values."""
        validator = MockValidator()
        
        assert validator.should_pass is True
        assert validator.should_have_minor_errors is False
        assert validator._errors == []
        assert validator._warnings == []
        assert validator._log_output == ""


class TestEDIValidationStep:
    """Tests for EDIValidationStep class."""
    
    def test_initialization_with_defaults(self):
        """Test EDIValidationStep initialization with default values."""
        step = EDIValidationStep()
        
        assert step._validator is not None
        assert step._error_handler is None
        assert step._file_system is None
    
    def test_initialization_with_injected_dependencies(self):
        """Test EDIValidationStep initialization with injected dependencies."""
        mock_validator = MockValidator()
        mock_error_handler = MockErrorHandler()
        mock_fs = MockFileSystem()
        
        step = EDIValidationStep(
            validator=mock_validator,
            error_handler=mock_error_handler,
            file_system=mock_fs
        )
        
        assert step._validator is mock_validator
        assert step._error_handler is mock_error_handler
        assert step._file_system is mock_fs
    
    def test_validate_valid_edi_file(self, valid_edi_content):
        """Test validate() with valid EDI file."""
        mock_fs = MockFileSystem({
            '/test/valid.edi': valid_edi_content
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/valid.edi', 'valid.edi')
        
        assert result.is_valid is True
        assert result.errors == []
    
    def test_validate_invalid_edi_file(self, invalid_edi_content):
        """Test validate() with invalid EDI file."""
        mock_fs = MockFileSystem({
            '/test/invalid.edi': invalid_edi_content
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/invalid.edi', 'invalid.edi')
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_with_minor_errors_suppressed_upc(self, edi_content_with_minor_errors):
        """Test validate() with minor errors (suppressed UPC)."""
        mock_fs = MockFileSystem({
            '/test/minor.edi': edi_content_with_minor_errors
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/minor.edi', 'minor.edi')
        
        assert result.is_valid is True
        assert result.has_minor_errors is True
        assert any("Suppressed UPC" in w for w in result.warnings)
    
    def test_validate_with_truncated_upc(self, edi_content_truncated_upc):
        """Test validate() with truncated UPC."""
        mock_fs = MockFileSystem({
            '/test/truncated.edi': edi_content_truncated_upc
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/truncated.edi', 'truncated.edi')
        
        assert result.is_valid is True
        assert result.has_minor_errors is True
        assert any("Truncated UPC" in w for w in result.warnings)
    
    def test_validate_with_blank_upc(self, edi_content_blank_upc):
        """Test validate() with blank UPC."""
        mock_fs = MockFileSystem({
            '/test/blank.edi': edi_content_blank_upc
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/blank.edi', 'blank.edi')
        
        assert result.is_valid is True
        assert result.has_minor_errors is True
        assert any("Blank UPC" in w for w in result.warnings)
    
    def test_validate_with_missing_pricing(self, edi_content_missing_pricing):
        """Test validate() with missing pricing."""
        mock_fs = MockFileSystem({
            '/test/pricing.edi': edi_content_missing_pricing
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/pricing.edi', 'pricing.edi')
        
        assert result.is_valid is True
        assert result.has_minor_errors is True
        assert any("Missing pricing" in w for w in result.warnings)
    
    def test_should_block_processing_with_report_enabled(self):
        """Test should_block_processing with report_edi_errors True."""
        step = EDIValidationStep()
        
        result = step.should_block_processing({'report_edi_errors': True})
        
        assert result is True
    
    def test_should_block_processing_with_report_disabled(self):
        """Test should_block_processing with report_edi_errors False."""
        step = EDIValidationStep()
        
        result = step.should_block_processing({'report_edi_errors': False})
        
        assert result is False
    
    def test_should_block_processing_default(self):
        """Test should_block_processing with missing key defaults to False."""
        step = EDIValidationStep()
        
        result = step.should_block_processing({})
        
        assert result is False
    
    def test_get_error_log_empty(self):
        """Test get_error_log() returns empty string initially."""
        step = EDIValidationStep()
        
        assert step.get_error_log() == ""
    
    def test_get_error_log_with_content(self, edi_content_with_minor_errors):
        """Test get_error_log() returns accumulated content."""
        mock_fs = MockFileSystem({
            '/test/minor.edi': edi_content_with_minor_errors
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        step.validate('/test/minor.edi', 'minor.edi')
        
        log = step.get_error_log()
        
        assert len(log) > 0
        assert 'minor.edi' in log
    
    def test_clear_error_log(self, edi_content_with_minor_errors):
        """Test clear_error_log() clears the log buffer."""
        mock_fs = MockFileSystem({
            '/test/minor.edi': edi_content_with_minor_errors
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        step.validate('/test/minor.edi', 'minor.edi')
        
        assert step.get_error_log() != ""
        
        step.clear_error_log()
        
        assert step.get_error_log() == ""
    
    def test_error_recording_to_error_handler(self):
        """Test that errors are recorded to error handler."""
        mock_validator = MockValidatorForStep(should_pass=False, errors=["Test error"])
        mock_error_handler = MockErrorHandler()
        
        step = EDIValidationStep(
            validator=mock_validator,
            error_handler=mock_error_handler
        )
        
        step.validate('/test/file.edi', 'file.edi')
        
        assert len(mock_error_handler.errors) == 1
        assert mock_error_handler.errors[0]['filename'] == 'file.edi'
        assert isinstance(mock_error_handler.errors[0]['error'], ValidationError)
    
    def test_no_error_recording_when_valid(self):
        """Test that no errors are recorded when validation passes."""
        mock_validator = MockValidatorForStep(should_pass=True)
        mock_error_handler = MockErrorHandler()
        
        step = EDIValidationStep(
            validator=mock_validator,
            error_handler=mock_error_handler
        )
        
        step.validate('/test/file.edi', 'file.edi')
        
        assert len(mock_error_handler.errors) == 0
    
    def test_no_error_recording_when_no_handler(self):
        """Test validation works without error handler."""
        mock_validator = MockValidatorForStep(should_pass=False, errors=["Test error"])
        
        step = EDIValidationStep(validator=mock_validator)
        
        result = step.validate('/test/file.edi', 'file.edi')
        
        assert result.is_valid is False
    
    def test_log_output_built_correctly(self):
        """Test that log_output is built correctly."""
        mock_validator = MockValidatorForStep(
            should_pass=False,
            errors=["Error 1"],
            log_output="Validator log content"
        )
        
        step = EDIValidationStep(validator=mock_validator)
        result = step.validate('/test/file.edi', 'test_file.edi')
        
        assert 'test_file.edi' in result.log_output
    
    def test_validate_file_not_found(self):
        """Test validation with non-existent file."""
        mock_fs = MockFileSystem({})
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/nonexistent/file.edi', 'file.edi')
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_multiple_validations_accumulate_log(self, edi_content_with_minor_errors):
        """Test multiple validations accumulate error log."""
        mock_fs = MockFileSystem({
            '/test/file1.edi': edi_content_with_minor_errors,
            '/test/file2.edi': edi_content_with_minor_errors
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        step.validate('/test/file1.edi', 'file1.edi')
        step.validate('/test/file2.edi', 'file2.edi')
        
        log = step.get_error_log()
        
        assert 'file1.edi' in log
        assert 'file2.edi' in log


class TestValidationError:
    """Tests for ValidationError exception class."""
    
    def test_validation_error_message(self):
        """Test ValidationError stores message correctly."""
        error = ValidationError("Test validation error")
        
        assert str(error) == "Test validation error"
    
    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from Exception."""
        error = ValidationError("Test")
        
        assert isinstance(error, Exception)
    
    def test_validation_error_raise_catch(self):
        """Test ValidationError can be raised and caught."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Validation failed")
        
        assert str(exc_info.value) == "Validation failed"


class TestValidatorStepInterface:
    """Tests for ValidatorStepInterface protocol."""
    
    def test_mock_validator_satisfies_protocol(self):
        """Test MockValidator satisfies ValidatorStepInterface protocol."""
        validator = MockValidator()
        
        assert hasattr(validator, 'validate')
        assert hasattr(validator, 'should_block_processing')
        assert callable(validator.validate)
        assert callable(validator.should_block_processing)
    
    def test_edi_validation_step_satisfies_protocol(self):
        """Test EDIValidationStep satisfies ValidatorStepInterface protocol."""
        step = EDIValidationStep()
        
        assert hasattr(step, 'validate')
        assert hasattr(step, 'should_block_processing')
        assert callable(step.validate)
        assert callable(step.should_block_processing)


class TestIntegration:
    """Integration tests for pipeline validator."""
    
    def test_full_validation_flow_valid_file(self, valid_edi_content):
        """Test full validation flow with valid EDI file."""
        mock_fs = MockFileSystem({
            '/data/input/order.edi': valid_edi_content
        })
        mock_error_handler = MockErrorHandler()
        
        step = EDIValidationStep(
            error_handler=mock_error_handler,
            file_system=mock_fs
        )
        
        result = step.validate('/data/input/order.edi', 'order.edi')
        
        assert result.is_valid is True
        assert result.errors == []
        assert len(mock_error_handler.errors) == 0
    
    def test_full_validation_flow_invalid_file(self, invalid_edi_content):
        """Test full validation flow with invalid EDI file."""
        mock_fs = MockFileSystem({
            '/data/input/bad.edi': invalid_edi_content
        })
        mock_error_handler = MockErrorHandler()
        
        step = EDIValidationStep(
            error_handler=mock_error_handler,
            file_system=mock_fs
        )
        
        result = step.validate('/data/input/bad.edi', 'bad.edi')
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert len(mock_error_handler.errors) == 1
    
    def test_validation_integrates_with_error_handler(self):
        """Test validation properly integrates with error handler."""
        mock_validator = MockValidatorForStep(
            should_pass=False,
            errors=["Critical error", "Secondary error"]
        )
        mock_error_handler = MockErrorHandler()
        
        step = EDIValidationStep(
            validator=mock_validator,
            error_handler=mock_error_handler
        )
        
        step.validate('/test/file.edi', 'file.edi')
        
        assert len(mock_error_handler.errors) == 2
    
    def test_should_block_processing_integration(self):
        """Test should_block_processing in processing context."""
        mock_validator = MockValidator(should_pass=False)
        params = {'report_edi_errors': True, 'other_setting': 'value'}
        
        result = mock_validator.should_block_processing(params)
        
        assert result is True
    
    def test_multiple_files_validation(self, valid_edi_content, edi_content_with_minor_errors):
        """Test validating multiple files in sequence."""
        mock_fs = MockFileSystem({
            '/data/valid.edi': valid_edi_content,
            '/data/minor.edi': edi_content_with_minor_errors
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        
        result1 = step.validate('/data/valid.edi', 'valid.edi')
        result2 = step.validate('/data/minor.edi', 'minor.edi')
        
        assert result1.is_valid is True
        assert result1.has_minor_errors is False
        
        assert result2.is_valid is True
        assert result2.has_minor_errors is True
    
    def test_mock_file_system_returns_correct_content(self, valid_edi_content):
        """Test mock file system returns expected content."""
        mock_fs = MockFileSystem({
            '/test/file.edi': valid_edi_content
        })
        
        content = mock_fs.read_file_text('/test/file.edi')
        
        assert content == valid_edi_content
        assert content.startswith('A')
    
    def test_validation_result_used_in_decision_making(self):
        """Test ValidationResult can be used for processing decisions."""
        mock_validator = MockValidatorForStep(should_pass=False, errors=["Error"])
        
        step = EDIValidationStep(validator=mock_validator)
        result = step.validate('/test/file.edi', 'file.edi')
        
        should_block = step.should_block_processing({'report_edi_errors': True})
        
        if not result.is_valid and should_block:
            processing_blocked = True
        else:
            processing_blocked = False
        
        assert processing_blocked is True
    
    def test_error_handler_context_preserved(self):
        """Test that error handler receives correct context."""
        mock_validator = MockValidatorForStep(should_pass=False, errors=["Error"])
        mock_error_handler = MockErrorHandler()
        
        step = EDIValidationStep(
            validator=mock_validator,
            error_handler=mock_error_handler
        )
        
        step.validate('/test/myfile.edi', 'myfile.edi')
        
        error = mock_error_handler.errors[0]
        assert error['context'] == {'source': 'EDIValidationStep'}
        assert error['error_source'] == 'EDIValidator'


class TestEdgeCases:
    """Edge case tests for pipeline validator."""
    
    def test_empty_file(self):
        """Test validation of empty file."""
        mock_fs = MockFileSystem({
            '/test/empty.edi': ''
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/empty.edi', 'empty.edi')
        
        assert result.is_valid is False
    
    def test_single_line_valid(self):
        """Test validation of single line file starting with A."""
        mock_fs = MockFileSystem({
            '/test/single.edi': 'AHEADER'
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/single.edi', 'single.edi')
        
        assert result.is_valid is True
    
    def test_unicode_content(self, valid_edi_content):
        """Test validation handles unicode content."""
        content = valid_edi_content + "Unicode: 你好世界\n"
        mock_fs = MockFileSystem({
            '/test/unicode.edi': content
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/unicode.edi', 'unicode.edi')
        
        assert isinstance(result.is_valid, bool)
    
    def test_very_long_file(self):
        """Test validation of very long EDI file."""
        b_record = "B12345678901" + " " * 65
        lines = ["AHEADER"]
        for i in range(1000):
            lines.append(b_record)
        lines.append("CFOOTER")
        
        content = "\n".join(lines) + "\n"
        mock_fs = MockFileSystem({
            '/test/large.edi': content
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test/large.edi', 'large.edi')
        
        assert result.is_valid is True
    
    def test_mock_validator_with_none_values(self):
        """Test MockValidator handles None values for errors/warnings."""
        validator = MockValidator(
            should_pass=False,
            errors=None,
            warnings=None
        )
        
        result = validator.validate('/test/file.edi', 'file.edi')
        
        assert result.errors == []
    
    def test_file_path_with_spaces(self, valid_edi_content):
        """Test validation of file with spaces in path."""
        mock_fs = MockFileSystem({
            '/test folder/my file.edi': valid_edi_content
        })
        
        step = EDIValidationStep(file_system=mock_fs)
        result = step.validate('/test folder/my file.edi', 'my file.edi')
        
        assert result.is_valid is True
