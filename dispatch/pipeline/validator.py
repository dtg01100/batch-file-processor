"""EDI Validation Step for the dispatch pipeline.

This module provides a pipeline step for EDI file validation,
wrapping the existing EDIValidator with pipeline integration.
"""

from dataclasses import dataclass, field
from io import StringIO
from typing import Optional, Protocol, runtime_checkable

from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler
from dispatch.interfaces import FileSystemInterface


@dataclass
class ValidationResult:
    """Result of EDI file validation.
    
    Attributes:
        is_valid: True if file passes validation (no blocking errors)
        has_minor_errors: True if there are warnings (suppressed UPC, missing pricing, etc.)
        errors: List of error messages
        warnings: List of warning messages
        log_output: Full log output for reporting
    """
    is_valid: bool
    has_minor_errors: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    log_output: str = ""


@runtime_checkable
class ValidatorStepInterface(Protocol):
    """Protocol for validation step implementations."""
    
    def validate(self, file_path: str, filename_for_log: str) -> ValidationResult:
        """Validate a file.
        
        Args:
            file_path: Path to the file to validate
            filename_for_log: Filename to use in log messages
            
        Returns:
            ValidationResult with validation outcome
        """
        ...
    
    def should_block_processing(self, params: dict) -> bool:
        """Check if validation failure should block processing.
        
        Args:
            params: Folder parameters dictionary
            
        Returns:
            True if processing should be blocked on validation failure
        """
        ...


class MockValidator:
    """Mock validator for testing purposes.
    
    This validator can be configured to pass or fail validation
    and allows inspection of validation calls.
    
    Attributes:
        should_pass: If True, validation passes; if False, fails
        should_have_minor_errors: If True, report minor errors
        call_count: Number of times validate was called
        last_file_path: Last file path passed to validate
        last_filename_for_log: Last filename_for_log passed to validate
    """
    
    def __init__(
        self,
        should_pass: bool = True,
        should_have_minor_errors: bool = False,
        errors: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        log_output: str = ""
    ):
        """Initialize the mock validator.
        
        Args:
            should_pass: If True, validation passes; if False, fails
            should_have_minor_errors: If True, report minor errors
            errors: List of error messages to return
            warnings: List of warning messages to return
            log_output: Log output string to return
        """
        self.should_pass = should_pass
        self.should_have_minor_errors = should_have_minor_errors
        self._errors = errors or []
        self._warnings = warnings or []
        self._log_output = log_output
        self.call_count: int = 0
        self.last_file_path: Optional[str] = None
        self.last_filename_for_log: Optional[str] = None
    
    def validate(self, file_path: str, filename_for_log: str) -> ValidationResult:
        """Mock validate method.
        
        Args:
            file_path: Path to the file to validate
            filename_for_log: Filename to use in log messages
            
        Returns:
            ValidationResult based on mock configuration
        """
        self.call_count += 1
        self.last_file_path = file_path
        self.last_filename_for_log = filename_for_log
        
        return ValidationResult(
            is_valid=self.should_pass,
            has_minor_errors=self.should_have_minor_errors,
            errors=self._errors.copy() if not self.should_pass else [],
            warnings=self._warnings.copy() if self.should_have_minor_errors else [],
            log_output=self._log_output
        )
    
    def should_block_processing(self, params: dict) -> bool:
        """Mock should_block_processing method.
        
        Args:
            params: Folder parameters dictionary
            
        Returns:
            True if should_pass is False and report_edi_errors is True
        """
        if self.should_pass:
            return False
        return params.get('report_edi_errors', False)
    
    def reset(self) -> None:
        """Reset the mock state."""
        self.call_count = 0
        self.last_file_path = None
        self.last_filename_for_log = None


class EDIValidationStep:
    """EDI validation step for the dispatch pipeline.
    
    This class wraps the EDIValidator and integrates with the error handler
    for pipeline-based processing.
    
    Attributes:
        validator: EDI validator instance
        error_handler: Optional error handler for recording errors
        file_system: Optional file system interface
    """
    
    def __init__(
        self,
        validator: Optional[EDIValidator] = None,
        error_handler: Optional[ErrorHandler] = None,
        file_system: Optional[FileSystemInterface] = None
    ):
        """Initialize the validation step.
        
        Args:
            validator: EDI validator instance (creates new one if None)
            error_handler: Optional error handler for recording errors
            file_system: Optional file system interface for the validator
        """
        self._file_system = file_system
        self._validator = validator or EDIValidator(file_system=file_system)
        self._error_handler = error_handler
        self._error_log: StringIO = StringIO()
    
    def validate(self, file_path: str, filename_for_log: str) -> ValidationResult:
        """Validate an EDI file.
        
        This method wraps the EDIValidator.validate_with_warnings method
        and integrates with the error handler.
        
        Args:
            file_path: Path to the EDI file to validate
            filename_for_log: Filename to use in log messages
            
        Returns:
            ValidationResult with validation outcome
        """
        is_valid, errors, warnings = self._validator.validate_with_warnings(file_path)
        has_minor_errors = self._validator.has_minor_errors
        
        log_output = self._build_log_output(
            filename_for_log,
            errors,
            warnings,
            self._validator.get_error_log()
        )
        
        if errors and self._error_handler is not None:
            self._record_errors(filename_for_log, errors)
        
        if warnings:
            self._error_log.write(log_output)
        
        return ValidationResult(
            is_valid=is_valid,
            has_minor_errors=has_minor_errors,
            errors=errors,
            warnings=warnings,
            log_output=log_output
        )
    
    def should_block_processing(self, params: dict) -> bool:
        """Check if validation failure should block processing.
        
        This checks the folder settings to determine if EDI validation
        errors should stop file processing.
        
        Args:
            params: Folder parameters dictionary with settings
            
        Returns:
            True if processing should be blocked on validation failure
        """
        report_edi_errors = params.get('report_edi_errors', False)
        return report_edi_errors
    
    def get_error_log(self) -> str:
        """Get the accumulated error log contents.
        
        Returns:
            Error log as string
        """
        return self._error_log.getvalue()
    
    def clear_error_log(self) -> None:
        """Clear the error log buffer."""
        self._error_log = StringIO()
    
    def _build_log_output(
        self,
        filename: str,
        errors: list[str],
        warnings: list[str],
        validator_log: str
    ) -> str:
        """Build the complete log output for a validation result.
        
        Args:
            filename: Filename for log header
            errors: List of error messages
            warnings: List of warning messages
            validator_log: Raw log from the validator
            
        Returns:
            Formatted log output string
        """
        output = StringIO()
        
        if errors or warnings:
            output.write(f"\r\nErrors for {filename}:\r\n")
            output.write(validator_log)
        
        return output.getvalue()
    
    def _record_errors(self, filename: str, errors: list[str]) -> None:
        """Record errors to the error handler.
        
        Args:
            filename: Filename being processed
            errors: List of error messages
        """
        if self._error_handler is None:
            return
        
        for error_msg in errors:
            self._error_handler.record_error(
                folder="",
                filename=filename,
                error=ValidationError(error_msg),
                context={'source': 'EDIValidationStep'},
                error_source="EDIValidator"
            )


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass