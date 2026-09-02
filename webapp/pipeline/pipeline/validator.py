"""EDI Validation Step for the dispatch pipeline.

This module provides a pipeline step for EDI file validation,
wrapping the existing EDIValidator with pipeline integration.
"""

import os
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Protocol, runtime_checkable

from core.structured_logging import get_logger, log_file_operation, log_with_context
from webapp.pipeline.edi_validator import EDIValidator
from webapp.pipeline.error_handler import ErrorHandler
from webapp.pipeline.interfaces import FileSystemInterface

logger = get_logger(__name__)


def normalize_validation_output(
    output: object,
    current_file: str,
) -> tuple[bool, Any]:
    """Normalize a validator step's return value to ``(is_valid, errors_or_file)``.

    Accepts a 2-tuple, ``ValidationResult``, ``dict`` with a ``"valid"`` key,
    or a plain ``bool``. Any other type is logged as a warning and returned
    as invalid with a diagnostic error message.

    Spec: specs/refactor-dispatch-simplification.md §3.4 (Phase 1 contract
    unification between ``orchestrator._normalize_validation_output`` and
    the isinstance-cascade head of
    ``file_processor._handle_validation_result``).
    """
    if isinstance(output, tuple) and len(output) == 2:
        return bool(output[0]), output[1]
    if isinstance(output, ValidationResult):
        return output.is_valid, (output.errors if not output.is_valid else current_file)
    if isinstance(output, dict):
        is_valid = bool(output.get("valid", True))
        if is_valid:
            return is_valid, output.get("file_path", current_file)
        return is_valid, output.get("errors", [])
    if isinstance(output, bool):
        return output, current_file
    logger.warning(
        "Unexpected validation output type: %s, treating as invalid",
        type(output).__name__,
    )
    return False, [f"Validator returned unexpected type: {type(output).__name__}"]


@dataclass
class ValidationResult:
    """Result of EDI file validation.

    Attributes:
        is_valid: True if file passes validation (no blocking errors)
        has_minor_errors: True if there are warnings (suppressed UPC,
        missing pricing, etc.)
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
        *,
        should_pass: bool = True,
        should_have_minor_errors: bool = False,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        log_output: str = "",
    ) -> None:
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
        self.last_file_path: str | None = None
        self.last_filename_for_log: str | None = None

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
            log_output=self._log_output,
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
        return params.get("report_edi_errors", False)  # type: ignore[no-any-return]

    def reset(self) -> None:
        """Reset the mock state to initial values.

        Clears call counts, recorded file paths, errors, warnings, and
        log output. Useful for reusing the same mock instance across
        multiple test cases.

        """
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
        validator: EDIValidator | None = None,
        error_handler: ErrorHandler | None = None,
        file_system: FileSystemInterface | None = None,
    ) -> None:
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
        import logging

        log_file_operation(
            logger,
            "validate",
            file_path,
            file_type="edi",
        )
        logger.debug("Validating file: %s", filename_for_log)

        is_valid, errors, warnings = self._validator.validate_with_warnings(file_path)
        has_minor_errors = self._validator.has_minor_errors

        logger.debug(
            "Validation result for %s: valid=%s, has_minor_errors=%s",
            filename_for_log,
            is_valid,
            has_minor_errors,
        )

        if is_valid and not has_minor_errors:
            log_file_operation(
                logger,
                "validate",
                file_path,
                file_type="edi",
                success=True,
            )
            logger.info("Validation passed for: %s", filename_for_log)
        if has_minor_errors:
            log_with_context(
                logger,
                logging.WARNING,
                f"Validation warnings for {filename_for_log}: {warnings}",
                context={"file_path": file_path, "warnings": warnings},
            )
        if not is_valid:
            log_file_operation(
                logger,
                "validate",
                file_path,
                file_type="edi",
                success=False,
            )
            log_with_context(
                logger,
                logging.ERROR,
                f"Validation failed for {filename_for_log}: {errors}",
                context={"file_path": file_path, "errors": errors},
            )

        log_output = self._build_log_output(
            filename_for_log, errors, warnings, self._validator.get_error_log()
        )

        # Phase 5.5: record EDI validation problems in the errors ledger
        # with the original program's major/minor distinction — format
        # failures are major (they block the file), UPC/pricing issues are
        # minor (they don't). The folder is derived from the file path so
        # the rows match the runner's folder filter + raw-artifact linking
        # (which key on the resolved folder path).
        if self._error_handler is not None:
            folder = os.path.dirname(file_path)
            if errors:
                self._record_errors(filename_for_log, errors, folder=folder)
            if warnings:
                self._record_warnings(filename_for_log, warnings, folder=folder)

        if log_output:
            self._error_log.write(log_output)

        return ValidationResult(
            is_valid=is_valid,
            has_minor_errors=has_minor_errors,
            errors=errors,
            warnings=warnings,
            log_output=log_output,
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
        return params.get("report_edi_errors", False)  # type: ignore[no-any-return]

    def execute(self, file_path: str, folder: dict) -> tuple[bool, list[str] | str]:
        """Execute validation step (wrapper for pipeline compatibility).

        Args:
            file_path: Path to the file to validate
            folder: Folder configuration dictionary

        Returns:
            Tuple of (is_valid, errors_or_file_path)

        """
        logger.debug("Execute validation step for: %s", file_path)
        filename = folder.get("filename_for_log", file_path)
        result = self.validate(file_path, filename)
        if result.is_valid:
            logger.debug("Execute validation result for %s: valid=True", file_path)
            return True, file_path
        logger.debug("Execute validation result for %s: valid=False", file_path)
        return False, result.errors

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
        self, filename: str, errors: list[str], warnings: list[str], validator_log: str
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
        logger.debug(
            "Building log output for %s (errors=%d, warnings=%d)",
            filename,
            len(errors),
            len(warnings),
        )
        output = StringIO()

        if errors or warnings:
            output.write(f"\r\nErrors for {filename}:\r\n")
            output.write(validator_log)

        return output.getvalue()

    def _record_errors(
        self, filename: str, errors: list[str], *, folder: str = ""
    ) -> None:
        """Record major EDI validation problems to the error handler.

        Major problems are format failures that block the file (bad
        record type, wrong B-record length, etc.). They are recorded with
        ``severity="major"`` so the errors ledger can distinguish them
        from minor issues.

        Args:
            filename: Filename being processed
            errors: List of error messages
            folder: Folder the file lives in (resolved path)

        """
        if self._error_handler is None:
            return

        logger.debug("Recording %d major problem(s) for %s", len(errors), filename)
        for error_msg in errors:
            self._error_handler.record_error(
                folder=folder,
                filename=filename,
                error=ValidationError(error_msg),
                context={"source": "EDIValidationStep", "severity": "major"},
                error_source="EDIValidator",
                severity="major",
            )

    def _record_warnings(
        self, filename: str, warnings: list[str], *, folder: str = ""
    ) -> None:
        """Record minor EDI validation problems to the error handler.

        Minor problems (non-numeric/suppressed/truncated UPC, missing
        pricing, etc.) are warnings — the file still processes. They are
        recorded with ``severity="minor"`` and ``alert_on_failure=False``
        so a future alert integration doesn't page operators for a file
        that went through fine.

        Args:
            filename: Filename being processed
            warnings: List of warning messages
            folder: Folder the file lives in (resolved path)

        """
        if self._error_handler is None:
            return

        logger.debug("Recording %d minor problem(s) for %s", len(warnings), filename)
        for warning_msg in warnings:
            self._error_handler.record_error(
                folder=folder,
                filename=filename,
                error=ValidationError(warning_msg),
                context={
                    "source": "EDIValidationStep",
                    "severity": "minor",
                    "alert_on_failure": False,
                },
                error_source="EDIValidator",
                severity="minor",
            )


class ValidationError(Exception):
    """Exception raised when EDI validation detects irrecoverable errors.

    This exception signals that the EDI file has structural or content
    errors that make it unsuitable for further processing. The exception
    message typically contains details about the validation failures.

    """
