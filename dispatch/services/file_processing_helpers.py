"""File Processing Helpers for the dispatch orchestrator.

This module extracts file processing utility methods from the orchestrator
to reduce its size and improve cohesion. These helpers deal with:
- File system operations (existence, listing, checksums)
- Invoice number extraction
- Backend detection
- File renaming
- Temporary artifact cleanup
"""

import hashlib
import os
import shutil
from typing import Any

from core.edi.edi_parser import capture_records
from core.structured_logging import (
    get_logger,
    log_file_operation,
)
from core.utils.bool_utils import normalize_bool

logger = get_logger(__name__)


class FileProcessingHelpers:
    """Helper methods for file processing operations.

    This class provides utility methods used during file processing,
    extracted from the orchestrator to improve cohesion and reduce
    orchestrator complexity.
    """

    def __init__(
        self,
        file_system: Any | None = None,
        settings: dict | None = None,
    ) -> None:
        """Initialize file processing helpers.

        Args:
            file_system: Optional file system interface for operations
            settings: Application settings dictionary

        """
        self._file_system = file_system
        self._settings = settings or {}

    def folder_exists(self, path: str) -> bool:
        """Check if a folder exists.

        Args:
            path: Path to check

        Returns:
            True if folder exists and is a directory

        """
        if self._file_system:
            return self._file_system.dir_exists(path)
        return os.path.isdir(path)

    def get_files_in_folder(self, path: str) -> list[str]:
        """Get list of files in a folder.

        Args:
            path: Path to the folder

        Returns:
            List of file paths (full paths) in the folder

        """
        try:
            if self._file_system:
                return self._file_system.list_files(path)
            return [
                os.path.join(path, f)
                for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f))
            ]
        except OSError as e:
            logger.error("Failed to list files in %s: %s", path, e)
            return []

    def calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hex digest string

        """
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def extract_invoice_numbers(self, file_path: str) -> str:
        """Extract invoice numbers from an EDI file.

        Reads the file and extracts invoice numbers from A records.

        Args:
            file_path: Path to the EDI file

        Returns:
            Comma-separated string of invoice numbers, or empty string

        """
        invoice_numbers = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("A"):
                        try:
                            record = capture_records(line)
                            invoice_num = record.get("invoice_number", "")
                            if invoice_num:
                                invoice_numbers.append(invoice_num)
                        except Exception:
                            logger.warning(
                                "Skipping malformed A-record in %s while extracting invoice numbers",
                                file_path,
                            )
        except OSError as e:
            logger.error("Failed to read file %s: %s", file_path, e)
        return ", ".join(invoice_numbers)

    def cleanup_temp_artifacts(self, context: Any) -> None:
        """Clean up temporary files and directories from processing.

        Args:
            context: ProcessingContext with temp_dirs and temp_files lists

        """
        for temp_dir in context.temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                log_file_operation(
                    logger,
                    "delete",
                    temp_dir,
                    file_type="directory",
                    success=True,
                    context={"reason": "temp_cleanup"},
                )
            except Exception as e:
                logger.warning("Failed to clean temp dir %s: %s", temp_dir, e)

        for temp_file in context.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    log_file_operation(
                        logger,
                        "delete",
                        temp_file,
                        file_type="file",
                        success=True,
                        context={"reason": "temp_cleanup"},
                    )
            except Exception as e:
                logger.warning("Failed to clean temp file %s: %s", temp_file, e)

        context.temp_dirs.clear()
        context.temp_files.clear()

    def extract_split_files(self, split_result: Any) -> list[str]:
        """Extract file paths from split result.

        Handles different split result formats and returns list of file paths.

        Args:
            split_result: Result from splitter (list, tuple, or object with files attr)

        Returns:
            List of file paths from split result

        """
        if split_result is None:
            return []

        if isinstance(split_result, list):
            return split_result

        if hasattr(split_result, "files"):
            return split_result.files

        if hasattr(split_result, "output_files"):
            return split_result.output_files

        logger.warning("Unknown split result type: %s", type(split_result))
        return []

    def detect_enabled_backends(self, folder: dict) -> list[str]:
        """Detect which backends are enabled for a folder.

        Args:
            folder: Folder configuration dictionary

        Returns:
            List of enabled backend names

        """
        enabled_backends = []

        if normalize_bool(folder.get("enable_copy_backend", False)):
            enabled_backends.append("copy")

        if normalize_bool(folder.get("enable_ftp_backend", False)):
            enabled_backends.append("ftp")

        if normalize_bool(folder.get("enable_email_backend", False)):
            enabled_backends.append("email")

        if normalize_bool(folder.get("enable_http_backend", False)):
            enabled_backends.append("http")

        return enabled_backends

    def validate_rename_template(self, template: str) -> None:
        """Validate a file rename template string.

        Args:
            template: Template string with placeholders

        Raises:
            ValueError: If template is invalid

        """
        if not template:
            raise ValueError("Rename template cannot be empty")

        # Check for balanced braces
        if template.count("{") != template.count("}"):
            raise ValueError(f"Unbalanced braces in template: {template}")

    def apply_file_rename(self, file_path: str, context: Any) -> str:
        """Apply file renaming based on folder configuration.

        Args:
            file_path: Current file path
            context: Processing context with folder configuration

        Returns:
            New file path after renaming (or original if no rename)

        """
        folder = context.effective_folder
        rename_template = folder.get("rename_file_template")

        if not rename_template:
            return file_path

        try:
            self.validate_rename_template(rename_template)

            # Extract context for template
            template_context = {
                "filename": os.path.basename(file_path),
                "dirname": os.path.basename(os.path.dirname(file_path)),
                "folder_name": folder.get("folder_name", ""),
                "alias": folder.get("alias", ""),
            }

            # Add invoice numbers if available
            if hasattr(context, "invoice_numbers"):
                template_context["invoice_numbers"] = context.invoice_numbers

            # Apply template
            new_filename = rename_template.format(**template_context)
            new_path = os.path.join(os.path.dirname(file_path), new_filename)

            # Perform rename
            if file_path != new_path:
                os.rename(file_path, new_path)
                logger.debug("Renamed file: %s -> %s", file_path, new_path)
                return new_path

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to apply rename template '%s' to %s: %s",
                rename_template,
                file_path,
                e,
            )

        return file_path

    def should_validate(self, folder: dict) -> bool:
        """Check if EDI validation is enabled for folder.

        Args:
            folder: Folder configuration dictionary

        Returns:
            True if validation should be performed

        """
        return normalize_bool(folder.get("validate_edi", False))
