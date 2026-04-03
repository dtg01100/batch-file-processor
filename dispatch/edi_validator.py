"""EDI Validator component for dispatch processing.

This module provides a testable wrapper around the EDI validation functionality,
using dependency injection for file system operations.
"""

import os
from io import StringIO

from core.structured_logging import get_logger, log_file_operation, log_with_context
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
            error_msg = f"Validation error: {str(e)}"
            self.errors.write(error_msg + "\r\n")
            error_list.append(error_msg)
            return False, error_list

    def validate_with_warnings(
        self, file_path: str
    ) -> tuple[bool, list[str], list[str]]:
        """Validate an EDI file and return both errors and warnings.

        Args:
            file_path: Path to the EDI file to validate

        Returns:
            Tuple of (is_valid, errors, warnings)

        """
        logger.debug("Validating EDI file (with warnings): %s", file_path)
        self.errors = StringIO()
        self.has_errors = False
        self.has_minor_errors = False
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # Read file once and pass content to all validation methods
            content = self.fs.read_file_text(file_path)
            is_valid_edi, check_line = self._check_edi_format(file_path, content)

            if not is_valid_edi:
                self.has_errors = True
                error_msg = f"EDI check failed on line number: {check_line}"
                self.errors.write(error_msg + "\r\n")
                errors.append(error_msg)
                logger.error(
                    "EDI validation failed: %s (%d error(s))", file_path, len(errors)
                )
                return False, errors, warnings

            # Check for issues and categorize them
            self._check_edi_issues_with_warnings(file_path, content, errors, warnings)

            is_valid = not self.has_errors
            if is_valid and not warnings:
                logger.info("EDI validation passed (no warnings): %s", file_path)
            elif is_valid:
                logger.info(
                    "EDI validation passed with %d warning(s): %s",
                    len(warnings),
                    file_path,
                )
            else:
                logger.error(
                    "EDI validation failed: %s (%d error(s))",
                    file_path,
                    len(errors),
                )

            return is_valid, errors, warnings

        except Exception as e:
            self.has_errors = True
            error_msg = f"Validation error: {str(e)}"
            self.errors.write(error_msg + "\r\n")
            errors.append(error_msg)
            return False, errors, warnings

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
            if len(line) != 76 and len(line) != 70:
                logger.debug(
                    "EDI format check failed at line %d: %s", line_num, file_path
                )
                return False, line_num

            # Check for missing pricing in 70-char lines
            if len(line) == 70 and line[51:67] != "                ":
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
            # Strip Windows Ctrl-Z EOF marker (0x1A) before processing
            content = content.replace("\x1a", "")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                if not line or line[0] != "B":
                    continue

                proposed_upc = line[1:12]
                stripped_upc = str(proposed_upc).strip()
                description = line[12:37].strip()
                item_ctx = f"line {line_num} (UPC: {proposed_upc.strip()!r}, desc: {description!r})"

                # Check for non-numeric UPC (not blank)
                if proposed_upc != "           ":
                    try:
                        int(proposed_upc)
                    except ValueError:
                        self.has_minor_errors = True
                        issues.append(f"Non-numeric UPC in {item_ctx}")

                # Check for suppressed UPC (8 chars)
                if len(stripped_upc) == 8:
                    self.has_minor_errors = True
                    issues.append(f"Suppressed UPC in {item_ctx}")

                # Check for truncated UPC (1-10 chars)
                elif 0 < len(stripped_upc) < 11:
                    self.has_minor_errors = True
                    issues.append(f"Truncated UPC in {item_ctx}")

                # Check for blank UPC
                if line[1:12] == "           ":
                    self.has_minor_errors = True
                    issues.append(f"Blank UPC in {item_ctx}")

                # Check for missing pricing
                if len(line) == 70:
                    self.has_minor_errors = True
                    issues.append(f"Missing pricing information in {item_ctx}")

            if issues:
                logger.debug("Found %d issue(s) in: %s", len(issues), file_path)

            return issues

        except Exception as e:
            self.has_errors = True
            issues.append(f"Error checking EDI issues: {str(e)}")
            return issues

    def _check_edi_issues_with_warnings(
        self, file_path: str, content: str, errors: list[str], warnings: list[str]
    ) -> None:
        """Check for EDI issues and categorize as errors or warnings.

        Args:
            file_path: Path to the file to check
            content: File content to validate (already read)
            errors: List to append error messages to
            warnings: List to append warning messages to

        """
        try:
            # Strip Windows Ctrl-Z EOF marker (0x1A) before processing
            content = content.replace("\x1a", "")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                if not line or line[0] != "B":
                    continue

                proposed_upc = line[1:12]
                stripped_upc = str(proposed_upc).strip()
                description = line[12:37].strip()
                item_ctx = f"line {line_num} (UPC: {proposed_upc.strip()!r}, desc: {description!r})"

                # Warnings (minor errors)
                if proposed_upc != "           ":
                    try:
                        int(proposed_upc)
                    except ValueError:
                        self.has_minor_errors = True
                        warnings.append(f"Non-numeric UPC in {item_ctx}")

                if len(stripped_upc) == 8:
                    self.has_minor_errors = True
                    warnings.append(f"Suppressed UPC in {item_ctx}")
                elif 0 < len(stripped_upc) < 11:
                    self.has_minor_errors = True
                    warnings.append(f"Truncated UPC in {item_ctx}")

                if line[1:12] == "           ":
                    self.has_minor_errors = True
                    warnings.append(f"Blank UPC in {item_ctx}")

                if len(line) == 70:
                    self.has_minor_errors = True
                    warnings.append(f"Missing pricing information in {item_ctx}")

        except Exception as e:
            self.has_errors = True
            errors.append(f"Error checking EDI issues: {str(e)}")

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


class RealFileSystem:
    """Real file system implementation for production use.

    This class provides direct file system access, suitable for
    production use but difficult to test.
    """

    def read_file_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents as text.

        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)

        Returns:
            File contents as string

        """
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    def read_file(self, path: str) -> bytes:
        """Read file contents as bytes.

        Args:
            path: Path to the file

        Returns:
            File contents as bytes

        """
        with open(path, "rb") as f:
            return f.read()

    def write_file(self, path: str, data: bytes) -> None:
        """Write bytes to a file.

        Args:
            path: Path to the file
            data: Bytes to write

        """
        with open(path, "wb") as f:
            f.write(data)

    def write_file_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """Write text to a file.

        Args:
            path: Path to the file
            data: String to write
            encoding: Text encoding (default: utf-8)

        """
        with open(path, "w", encoding=encoding) as f:
            f.write(data)

    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        return os.path.isfile(path)

    def dir_exists(self, path: str) -> bool:
        """Check if a directory exists."""
        return os.path.isdir(path)

    def list_files(self, path: str) -> list[str]:
        """List all files in a directory."""
        if not os.path.isdir(path):
            return []
        return [
            os.path.abspath(os.path.join(path, f))
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
        ]

    def mkdir(self, path: str) -> None:
        """Create a directory."""
        os.mkdir(path)

    def makedirs(self, path: str) -> None:
        """Create a directory and all parent directories."""
        os.makedirs(path, exist_ok=True)

    def copy_file(self, src: str, dst: str) -> None:
        """Copy a file."""
        import shutil

        shutil.copyfile(src, dst)

    def remove_file(self, path: str) -> None:
        """Remove a file."""
        os.remove(path)

    def get_absolute_path(self, path: str) -> str:
        """Get the absolute path."""
        return os.path.abspath(path)
