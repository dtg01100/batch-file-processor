"""Folder processing service for the dispatch pipeline.

This module provides the FolderPipelineExecutor class that encapsulates
all logic for processing files within a single folder. It handles:
- File discovery and filtering
- Progress reporting
- Result aggregation
- Error handling

Responsibilities:
- File discovery (listing files in directory)
- Filtering already-processed files
- Processing each file through the pipeline
- Aggregating results and errors

Example:
    >>> executor = FolderPipelineExecutor(
    ...     file_processor=file_processor,
    ...     send_manager=send_manager,
    ...     error_handler=error_handler,
    ...     progress_reporter=progress_reporter,
    ... )
    >>> result = executor.process_folder(request)
"""

from __future__ import annotations

import datetime
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.structured_logging import (
    get_logger,
    get_or_create_correlation_id,
    log_with_context,
    set_correlation_id,
)
from core.utils.bool_utils import normalize_bool
from core.utils.format_utils import normalize_convert_to_format

if TYPE_CHECKING:
    from dispatch.orchestrator import FolderResult

logger = get_logger(__name__)


@dataclass
class FolderProcessingRequest:
    """Request for processing a single folder.

    Attributes:
        folder: Folder configuration dictionary
        run_log: Run log for recording processing activity
        processed_files: Optional database of already processed files
        upc_dict: UPC dictionary for item lookups
        settings: Global settings for backends and services
        pre_discovered_files: Optional list of files already discovered
        folder_num: Current folder index (1-based) for progress reporting
        folder_total: Total number of folders for progress reporting

    """

    folder: dict
    run_log: Any
    processed_files: Any = None
    upc_dict: dict | None = None
    settings: dict | None = None
    pre_discovered_files: list[str] | None = None
    folder_num: int | None = None
    folder_total: int | None = None


@dataclass
class FolderProcessingDependencies:
    """Dependencies for folder processing.

    Attributes:
        file_processor: Service for processing individual files
        progress_reporter: Optional progress reporter
        get_upc_dictionary: Callable that returns UPC dictionary
        file_system: Optional file system interface for file operations
        settings: Global settings for backends and services

    """

    file_processor: Any = None
    progress_reporter: Any = None
    get_upc_dictionary: Any = None
    file_system: Any = None
    settings: dict | None = None


class FolderPipelineExecutor:
    """Executes the processing pipeline for files within a single folder.

    This class encapsulates all logic for processing files within a single
    folder, including file discovery, validation, conversion, and sending.

    Responsibilities:
    - File discovery and filtering
    - Pipeline execution for each file
    - Result aggregation
    - Progress reporting

    Example:
        >>> deps = FolderProcessingDependencies(
        ...     file_processor=file_processor,
        ...     progress_reporter=progress_reporter,
        ... )
        >>> executor = FolderPipelineExecutor(deps)
        >>> request = FolderProcessingRequest(folder=folder_config, run_log=run_log)
        >>> result = executor.process_folder(request)

    """

    def __init__(
        self,
        dependencies: FolderProcessingDependencies,
    ) -> None:
        """Initialize the folder processor.

        Args:
            dependencies: Container for processing dependencies
        """
        self._deps = dependencies
        self._log_messages: list[str] = []
        self._audit_logger: Any = None
        self._correlation_id: str | None = None

    def set_audit_logger(self, audit_logger: Any) -> None:
        """Set the audit logger for the folder processor.

        Args:
            audit_logger: AuditLogger instance for event logging
        """
        self._audit_logger = audit_logger

    def process_folder(
        self,
        request: FolderProcessingRequest,
    ) -> FolderResult:
        """Process all files in a folder through the pipeline.

        Args:
            request: Processing request with folder configuration

        Returns:
            FolderResult with processing outcome
        """
        from dispatch.orchestrator import FolderResult

        folder = request.folder
        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", "")

        correlation_id = get_or_create_correlation_id()
        self._correlation_id = correlation_id
        set_correlation_id(correlation_id)

        result = FolderResult(
            folder_name=folder_path,
            alias=alias,
        )

        log_with_context(
            logger,
            logging.INFO,
            f"Starting folder processing: {alias}",
            correlation_id=correlation_id,
            operation="folder_processing",
            context={
                "folder_name": folder_path,
                "folder_alias": alias,
                "folder_num": request.folder_num,
                "folder_total": request.folder_total,
            },
        )

        self._log_message(request.run_log, f"entering folder: {alias}")

        if not self._folder_exists(folder_path):
            return self._handle_folder_not_found(folder_path, request.run_log, result)

        files = self._discover_and_filter_files(request)

        if files is None:
            return result

        logger.debug(
            "After filter: %d files to process in %s",
            len(files),
            folder_path,
        )

        self._log_message(
            request.run_log,
            f"{len(files)} found in {folder_path} (pipeline mode)",
        )

        effective_upc_dict = (
            request.upc_dict
            if request.upc_dict is not None
            else self._get_upc_dictionary()
        )

        self._init_progress_reporter(folder, len(files), request)

        self._process_folder_files(
            files=files,
            folder=folder,
            effective_upc_dict=effective_upc_dict,
            processed_files=request.processed_files,
            run_log=request.run_log,
            result=result,
        )
        self._finalize_folder_result(result)

        return result

    def _folder_exists(self, folder_path: str) -> bool:
        """Check if folder exists.

        Args:
            folder_path: Path to check

        Returns:
            True if folder exists and is a directory
        """
        if self._deps.file_system is not None:
            return self._deps.file_system.dir_exists(folder_path)
        return os.path.isdir(folder_path)

    def _handle_folder_not_found(
        self,
        folder_path: str,
        run_log: Any,
        result: FolderResult,
    ) -> FolderResult:
        """Handle case when folder doesn't exist.

        Args:
            folder_path: Path that was not found
            run_log: Run log to record error
            result: FolderResult to populate

        Returns:
            Updated FolderResult with error details
        """
        error_msg = f"Folder not found: {folder_path}"
        result.errors.append(error_msg)
        result.success = False
        result.files_failed = 1
        self._log_error(run_log, error_msg)
        return result

    def _discover_and_filter_files(
        self,
        request: FolderProcessingRequest,
    ) -> list[str] | None:
        """Discover files to process and filter already-processed files.

        Args:
            request: Processing request with folder info

        Returns:
            List of file paths to process, or None if no files found
        """
        folder_path = request.folder.get("folder_name", "")
        files = (
            list(request.pre_discovered_files)
            if request.pre_discovered_files is not None
            else None
        )

        if files is None:
            files = self._get_files_in_folder(folder_path)

            if not files:
                self._log_message(
                    request.run_log,
                    f"No files in directory: {folder_path}",
                )
                return None

            logger.debug(
                "Found %d files in %s, filtering for already-processed...",
                len(files),
                folder_path,
            )

            if request.processed_files:
                files = self._filter_processed_files(
                    files,
                    request.processed_files,
                    request.folder,
                )

        if not files:
            self._log_message(
                request.run_log,
                f"No new files in directory: {folder_path}",
            )
            return None

        return files

    def _get_files_in_folder(self, folder_path: str) -> list[str]:
        """Get all file paths in a folder.

        Args:
            folder_path: Path to directory

        Returns:
            List of file paths in the directory
        """
        if self._deps.file_system is not None:
            all_files = self._deps.file_system.list_files(folder_path)
            if hasattr(self._deps.file_system, "file_exists"):
                return [f for f in all_files if self._deps.file_system.file_exists(f)]
            return all_files
        try:
            return [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ]
        except OSError:
            return []

    def _filter_processed_files(
        self,
        files: list[str],
        processed_files: Any,
        folder: dict,
    ) -> list[str]:
        """Filter out already-processed files based on checksum.

        Files with resend_flag=1 are NOT filtered out and will be re-processed.

        Args:
            files: List of file paths to filter
            processed_files: Database table with processed file records
            folder: Folder configuration

        Returns:
            List of files that haven't been processed yet (or are marked for resend)
        """
        if not processed_files:
            return files

        folder_id = folder.get("id")
        processed = processed_files.find(folder_id=folder_id)

        # Files that should be SKIPPED (already processed AND NOT marked for resend)
        skipped_checksums = {
            f.get("file_checksum") for f in processed if not f.get("resend_flag")
        }

        filtered = []
        for file_path in files:
            checksum = self._calculate_file_checksum(file_path)
            if checksum not in skipped_checksums:
                filtered.append(file_path)

        return filtered

    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal MD5 checksum string
        """
        import hashlib

        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except OSError:
            return ""

    def _process_folder_files(
        self,
        files: list[str],
        folder: dict,
        effective_upc_dict: dict,
        processed_files: Any,
        run_log: Any,
        result: FolderResult,
    ) -> None:
        """Process all files in folder and update result counters.

        Args:
            files: List of file paths to process
            folder: Folder configuration dictionary
            effective_upc_dict: UPC lookup dictionary
            processed_files: Database table for tracking processed files
            run_log: Run log for recording activity
            result: FolderResult to update in place
        """
        if not files:
            return

        processed_count = 0
        error_count = 0

        for idx, file_path in enumerate(files):
            if self._deps.progress_reporter:
                self._deps.progress_reporter.update_file(idx + 1, len(files))

            file_result = self._process_file_with_pipeline(
                file_path, folder, effective_upc_dict, run_log
            )

            if file_result.sent:
                processed_count += 1
                if processed_files:
                    self._record_processed_file(processed_files, folder, file_result)
            else:
                error_count += 1
                result.errors.extend(file_result.errors)

        result.files_processed = processed_count
        result.files_failed = error_count

    def _process_file_with_pipeline(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict,
        run_log: Any,
    ) -> Any:
        """Process a single file through the pipeline.

        Args:
            file_path: Path to file to process
            folder: Folder configuration
            upc_dict: UPC lookup dictionary
            run_log: Run log

        Returns:
            FileResult from processing
        """
        if self._deps.file_processor:
            effective_folder = self._build_effective_folder(folder)
            # Include settings from dependencies for backend configuration
            if self._deps.settings:
                effective_folder["settings"] = self._deps.settings
            context = self._deps.file_processor._build_context(
                folder=folder,
                upc_dict=upc_dict,
                effective_folder=effective_folder,
            )
            # Pass the ProcessingContext so settings are preserved
            return self._deps.file_processor.process_file(
                file_path=file_path,
                folder=folder,
                upc_dict=upc_dict,
                run_log=run_log,
                effective_folder=context,
            )

        from dispatch.services.file_processor import FileResult

        return FileResult(
            file_name=file_path,
            checksum="",
            sent=False,
            validated=False,
            converted=False,
            errors=["No file processor configured"],
        )

    def _build_effective_folder(self, folder: dict) -> dict:
        """Build effective folder with defaults applied.

        This replicates the normalization logic from DispatchOrchestrator
        to ensure folder has all required fields with sensible defaults.

        Args:
            folder: Original folder configuration

        Returns:
            Normalized folder dict with defaults applied
        """
        from core.constants import FOLDER_DEFAULTS

        effective_folder = folder.copy()

        for key, default in FOLDER_DEFAULTS.items():
            if effective_folder.get(key) is None:
                effective_folder[key] = default

        if not effective_folder.get("upc_target_length"):
            effective_folder["upc_target_length"] = FOLDER_DEFAULTS.get(
                "upc_target_length", 11
            )

        effective_folder["convert_to_format"] = normalize_convert_to_format(
            effective_folder.get("convert_to_format", "")
        )

        if normalize_bool(effective_folder.get("tweak_edi", False)):
            effective_folder["convert_to_format"] = "tweaks"
            effective_folder["process_edi"] = True

        if "settings" not in effective_folder:
            effective_folder["settings"] = {}

        return effective_folder

    def _record_processed_file(
        self,
        processed_files: Any,
        folder: dict,
        file_result: Any,
    ) -> None:
        """Record a processed file in the database.

        Args:
            processed_files: Database table for tracking
            folder: Folder configuration
            file_result: Result from file processing
        """
        try:
            folder_id = folder.get("id")

            # Check if it was marked for resend (match by name and folder)
            existing_resend = processed_files.find_one(
                file_name=file_result.file_name, folder_id=folder_id, resend_flag=1
            )

            # Detect enabled backends for sent_to field
            enabled_backends = []
            if folder.get("process_backend_copy"):
                enabled_backends.append("Copy")
            if folder.get("process_backend_ftp"):
                enabled_backends.append("FTP")
            if folder.get("process_backend_email"):
                enabled_backends.append("Email")
            if folder.get("process_backend_http"):
                enabled_backends.append("HTTP")
            sent_to_str = ", ".join(enabled_backends) if enabled_backends else "N/A"

            if existing_resend:
                # Clear resend flag for this specific record
                processed_files.update(
                    {
                        "id": existing_resend["id"],
                        "resend_flag": 0,
                        "processed_at": datetime.datetime.now().isoformat(),
                        "sent_to": sent_to_str,
                        "status": "processed",
                    },
                    ["id"],
                )
            else:
                # Insert new record
                processed_files.insert(
                    {
                        "file_name": file_result.file_name,
                        "folder_id": folder_id,
                        "folder_alias": folder.get("alias", ""),
                        "file_checksum": file_result.checksum,
                        "processed_at": datetime.datetime.now().isoformat(),
                        "resend_flag": 0,
                        "sent_to": sent_to_str,
                        "status": "processed",
                    }
                )
        except Exception:
            logger.warning(
                "Failed to record processed file to database: %s", file_result.file_name
            )

    def _finalize_folder_result(self, result: FolderResult) -> None:
        """Finalize folder result and notify progress reporter.

        Args:
            result: FolderResult to finalize
        """
        result.success = result.files_failed == 0
        if self._deps.progress_reporter and hasattr(
            self._deps.progress_reporter, "complete_folder"
        ):
            self._deps.progress_reporter.complete_folder(success=result.success)

    def _init_progress_reporter(
        self,
        folder: dict,
        total_files: int,
        request: FolderProcessingRequest,
    ) -> None:
        """Initialize progress reporter for folder processing.

        Args:
            folder: Folder configuration
            total_files: Number of files to process
            request: Original processing request
        """
        if not self._deps.progress_reporter:
            return

        progress = self._deps.progress_reporter
        if not hasattr(progress, "start_folder"):
            return

        folder_name = folder.get("alias", folder.get("folder_name", ""))
        try:
            progress.start_folder(
                alias=folder_name,
                total_files=total_files,
            )
        except TypeError:
            try:
                progress.start_folder(
                    folder_name,
                    total_files,
                )
            except Exception:
                logger.warning(
                    "Progress reporter failed to start folder: %s",
                    folder_name,
                    exc_info=True,
                )

    def _get_upc_dictionary(self) -> dict:
        """Get UPC dictionary from configured source.

        Returns:
            UPC lookup dictionary
        """
        if self._deps.get_upc_dictionary:
            return self._deps.get_upc_dictionary()
        return {}

    def _log_message(self, run_log: Any, message: str) -> None:
        """Write message to run log.

        Args:
            run_log: Log target (file-like object or None)
            message: Message to log
        """
        self._log_messages.append(message)
        if hasattr(run_log, "write"):
            try:
                run_log.write(f"{message}\r\n".encode())
            except Exception:
                logger.warning("Failed to write to run_log: %s", message, exc_info=True)

    def _log_error(self, run_log: Any, error_msg: str) -> None:
        """Log an error message.

        Args:
            run_log: Log target
            error_msg: Error message
        """
        self._log_message(run_log, f"ERROR: {error_msg}")
        logger.error(error_msg)
