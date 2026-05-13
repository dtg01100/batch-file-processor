"""EDI Validator component for dispatch processing.

This module provides a testable wrapper around the EDI validation functionality,
using dependency injection for file system operations.
"""

from io import StringIO

from core.constants import (
    EDI_B_RECORD_NO_PRICING_LENGTH,
    EDI_B_RECORD_STANDARD_LENGTH,
    UPC_A_NO_CHECK_LENGTH,
    UPCE_LENGTH,
)
from core.structured_logging import get_logger, log_file_operation, log_with_context
from dispatch.file_system import RealFileSystem
from dispatch.interfaces import FileSystemInterface

logger = get_logger(__name__)


class EDIValidator:
    """EDI file validator with dependency injection support.

    This class wraps the EDI validation functionality, allowing for
    testable validation through injected file system interfaces.

    Attributes:
        fs: File system interface for file operations
        errors: StringIO buffer for error messages
        has_errors: Flag indicating if validation errors occurred
        has_minor_errors: Flag indicating if minor errors occurred

    """

    def __init__(self, file_system: FileSystemInterface | None = None) -> None:
        """Initialize the EDI validator.

        Args:
            file_system: Optional file system interface (uses RealFileSystem if None)

        """
        self.fs = file_system or RealFileSystem()
        self.errors: StringIO = StringIO()
        self.has_errors: bool = False
        self.has_minor_errors: bool = False

    def validate(self, file_path: str) -> tuple[bool, list[str]]:
        """Validate an EDI file.

        Args:
            file_path: Path to the EDI file to validate

        Returns:
            Tuple of (is_valid, errors) where errors is a list of
            error messages (empty if valid)

        """
        import logging

        log_file_operation(
            logger,
            "validate",
            file_path,
            file_type="edi",
        )
        logger.debug("Validating EDI file: %s", file_path)
        self.errors = StringIO()
        self.has_errors = False
        self.has_minor_errors = False
        error_list: list[str] = []

        try:
            # Read file once and pass content to all validation methods
            content = self.fs.read_file_text(file_path)

            # First check if file is valid EDI format
            logger.debug("Checking EDI format for: %s", file_path)
            is_valid_edi, check_line = self._check_edi_format(file_path, content)

            if not is_valid_edi:
                logger.error(
                    "EDI format check failed at line %d for: %s", check_line, file_path
                )
                self.has_errors = True
                error_msg = f"EDI check failed on line number: {check_line}"
                self.errors.write(error_msg + "\r\n")
                error_list.append(error_msg)
                return False, error_list

            # Check for specific EDI issues
            logger.debug("Checking EDI-specific issues for: %s", file_path)
            issues = self._check_edi_issues(file_path, content)
            error_list.extend(issues)

            is_valid = not self.has_errors
            if is_valid and self.has_minor_errors:
                log_with_context(
                    logger,
                    logging.WARNING,
                    f"EDI validation passed with minor errors for: {file_path} "
                    f"({len(error_list)} issues)",
                    context={
                        "file_path": file_path,
                        "issues": len(error_list),
                        "warnings": error_list,
                    },
                )
            elif is_valid:
                log_file_operation(
                    logger,
                    "validate",
                    file_path,
                    file_type="edi",
                    success=True,
                )
                logger.info("EDI validation passed: %s", file_path)
            else:
                log_file_operation(
                    logger,
                    "validate",
                    file_path,
                    file_type="edi",
                    success=False,
                    context={"errors": error_list},
                )
                log_with_context(
                    logger,
                    logging.ERROR,
                    f"EDI validation failed for: {file_path} "
                    f"({len(error_list)} errors)",
                    context={"file_path": file_path, "errors": error_list},
                )

            return is_valid, error_list

        except Exception as e:
            logger.error("Exception during validation of %s: %s", file_path, e)
            self.has_errors = True
            error_msg = f"Validation error: {e!s}"
            self.errors.write(error_msg + "\r\n")
            error_list.append(error_msg)
            return False, error_list

    def validate_with_warnings(
        self, file_path: str
    ) -> tuple[bool, list[str], list[str]]:
        """Validate an EDI file and return both errors and warnings.

        Delegates to validate() and categorizes its results into
        errors (format failures) and warnings (minor issues).

        Args:
            file_path: Path to the EDI file to validate

        Returns:
            Tuple of (is_valid, errors, warnings)

        """
        is_valid, issues = self.validate(file_path)
        if is_valid:
            return True, [], issues
        return False, issues, []

    def _check_edi_format(self, file_path: str, content: str) -> tuple[bool, int]:
        """Check if file is a valid EDI format.

        Args:
            file_path: Path to the file to check
            content: File content to validate (already read)

        Returns:
            Tuple of (is_valid, line_number) where line_number is the
            line where validation failed (0 if valid)

        """
        logger.debug("Checking EDI format: %s", file_path)
        try:
            # Strip Windows Ctrl-Z EOF marker (0x1A) before processing
            content = content.replace("\x1a", "")
            lines = content.splitlines()

            # Check first character is 'A'
            if not lines or len(lines[0]) == 0 or lines[0][0] != "A":
                logger.debug("EDI format check failed at line %d: %s", 1, file_path)
                return False, 1

            # Check each line starts with valid record type
            for line_num, line in enumerate(lines, start=1):
                is_valid, failed_line = self._validate_edi_line(
                    line, line_num, file_path
                )
                if not is_valid:
                    return False, failed_line

            logger.debug("EDI format OK: %s (%d lines)", file_path, len(lines))
            return True, len(lines)

        except (OSError, UnicodeDecodeError):
            return False, 0

    def _validate_edi_line(
        self, line: str, line_num: int, file_path: str
    ) -> tuple[bool, int]:
        """Validate a single EDI line.

        Args:
            line: Line content to validate
            line_num: Line number for logging
            file_path: File path for logging

        Returns:
            Tuple of (is_valid, line_number) where line_number is the
            line where validation failed (0 if valid)

        """
        if not line:
            return True, 0
        first_char = line[0]
        if first_char not in ("A", "B", "C", ""):
            logger.debug("EDI format check failed at line %d: %s", line_num, file_path)
            return False, line_num

        # Validate B records
        if first_char == "B":
            if (
            len(line) != EDI_B_RECORD_STANDARD_LENGTH
            and len(line) != EDI_B_RECORD_NO_PRICING_LENGTH
        ):
                logger.debug(
                    "EDI format check failed at line %d: %s", line_num, file_path
                )
                return False, line_num

            # Check for missing pricing in 70-char lines
            if len(line) == EDI_B_RECORD_NO_PRICING_LENGTH and line[51:67] != "                ":  # noqa: E501
                logger.debug(
                    "EDI format check failed at line %d: %s", line_num, file_path
                )
                return False, line_num

        return True, 0

    def _check_edi_issues(self, file_path: str, content: str) -> list[str]:
        """Check for specific EDI issues.

        Args:
            file_path: Path to the file to check
            content: File content to validate (already read)

        Returns:
            List of issue messages

        """
        logger.debug("Checking EDI issues in: %s", file_path)
        issues: list[str] = []

        try:
            content = content.replace("\x1a", "")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                issues.extend(self._edi_check_line_for_issues(line_num, line))

            if issues:
                logger.debug("Found %d issue(s) in: %s", len(issues), file_path)

            return issues

        except Exception as e:
            self.has_errors = True
            issues.append(f"Error checking EDI issues: {e!s}")
            return issues

    def _edi_item_context(
        self, line_num: int, proposed_upc: str, description: str
    ) -> str:
        return (
            f"line {line_num}"
            f" (UPC: {proposed_upc.strip()!r},"
            f" desc: {description!r})"
        )

    def _edi_check_line_for_issues(self, line_num: int, line: str) -> list[str]:
        """Check a single line for EDI issues and return messages."""
        msgs: list[str] = []
        if not line or line[0] != "B":
            return msgs

        proposed_upc = line[1:12]
        stripped_upc = str(proposed_upc).strip()
        description = line[12:37].strip()
        item_ctx = self._edi_item_context(line_num, proposed_upc, description)

        def _append_minor(msg: str) -> None:
            self.has_minor_errors = True
            msgs.append(msg)

        if proposed_upc != "           ":
            try:
                int(proposed_upc)
            except ValueError:
                _append_minor(f"Non-numeric UPC in {item_ctx}")

        if len(stripped_upc) == UPCE_LENGTH:
            _append_minor(f"Suppressed UPC in {item_ctx}")
        elif 0 < len(stripped_upc) < UPC_A_NO_CHECK_LENGTH:
            _append_minor(f"Truncated UPC in {item_ctx}")

        if line[1:12] == "           ":
            _append_minor(f"Blank UPC in {item_ctx}")

        if len(line) == EDI_B_RECORD_NO_PRICING_LENGTH:
            _append_minor(f"Missing pricing information in {item_ctx}")

        return msgs

    def get_error_log(self) -> str:
        """Get the current error log contents.

        Returns:
            Error log as string

        """
        return self.errors.getvalue()

    def clear(self) -> None:
        """Clear the validator state."""
        self.errors = StringIO()
        self.has_errors = False
        self.has_minor_errors = False



