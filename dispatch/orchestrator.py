"""Dispatch Orchestrator for coordinating file processing.

This module provides the main orchestration layer for dispatch operations,
coordinating validation, conversion, and sending of files.
"""

import datetime
import hashlib
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

from core.constants import FOLDER_DEFAULTS
from core.structured_logging import (
    CorrelationContext,
    get_logger,
    get_or_create_correlation_id,
    log_backend_call,
    log_file_operation,
    log_with_context,
)
from core.utils import capture_records, normalize_bool, normalize_convert_to_format
from dispatch.error_handler import ErrorHandler
from dispatch.feature_flags import get_strict_testing_mode
from dispatch.interfaces import (
    BackendInterface,
    DatabaseInterface,
    ErrorHandlerInterface,
    FileSystemInterface,
)
from dispatch.send_manager import SendManager
from dispatch.services.file_processor import (
    FileProcessor,
    FileResult,
    ProcessingContext,
)
from dispatch.services.folder_discovery import FolderDiscoveryService
from dispatch.services.progress_reporting import ProgressReportingService
from dispatch.services.upc_service import UPCLookupService

logger = get_logger(__name__)


@dataclass
class DispatchConfig:
    """Configuration for the dispatch orchestrator.

    Attributes:
        database: Database interface for persistence
        file_system: File system interface for file operations
        backends: Dictionary of backend name to backend instance
        error_handler: Error handler instance
        settings: Global application settings
        version: Application version string
        upc_service: UPC service for dictionary fetching
        progress_reporter: Progress reporter
        validator_step: Pipeline validator step
        splitter_step: Pipeline splitter step
        converter_step: Pipeline converter step
        file_processor: File processor service
        upc_dict: Cached UPC dictionary

    """

    database: DatabaseInterface | None = None
    file_system: FileSystemInterface | None = None
    backends: dict[str, BackendInterface] = field(default_factory=dict)
    error_handler: ErrorHandlerInterface | None = None
    settings: dict = field(default_factory=dict)
    version: str = "1.0.0"
    upc_service: Any | None = None
    progress_reporter: Any | None = None
    validator_step: Any | None = None
    splitter_step: Any | None = None
    converter_step: Any | None = None
    file_processor: Any | None = None
    upc_dict: dict = field(default_factory=dict)


@dataclass
class FolderResult:
    """Result of processing a single folder.

    Attributes:
        folder_name: Name of the processed folder
        alias: Folder alias
        files_processed: Number of files successfully processed
        files_failed: Number of files that failed
        errors: List of error messages
        success: Whether the folder was processed successfully

    """

    folder_name: str
    alias: str
    files_processed: int = 0
    files_failed: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = True


class DispatchOrchestrator:
    """Orchestrates the dispatch process for file processing.

    This class coordinates the processing of files across folders,
    managing validation, conversion, and sending operations.

    The orchestrator delegates per-folder processing to FolderPipelineExecutor
    while maintaining high-level coordination responsibilities.

    Attributes:
        config: Dispatch configuration
        send_manager: Manager for sending files to backends
        run_log: In-memory log of processing run

    """

    def __init__(self, config: DispatchConfig) -> None:
        """Initialize the dispatch orchestrator.

        Args:
            config: Dispatch configuration

        """
        from dispatch.services.folder_processor import (
            FolderPipelineExecutor,
            FolderProcessingDependencies,
        )

        self.config = config
        self.send_manager = SendManager(backends=config.backends)
        self.error_handler = config.error_handler or ErrorHandler()
        self.run_log: StringIO = StringIO()
        self.processed_count: int = 0
        self.error_count: int = 0
        self.upc_service = UPCLookupService(config.settings)

        self.file_processor = FileProcessor(
            send_manager=self.send_manager,
            error_handler=self.error_handler,
            validator_step=config.validator_step,
            splitter_step=config.splitter_step,
            converter_step=config.converter_step,
            file_system=config.file_system,
        )

        self._discovery_service = FolderDiscoveryService(
            file_system=config.file_system,
            progress_reporter=config.progress_reporter,
        )

        self._progress_service = ProgressReportingService(
            progress_reporter=config.progress_reporter,
        )

        folder_deps = FolderProcessingDependencies(
            file_processor=self.file_processor,
            progress_reporter=config.progress_reporter,
            get_upc_dictionary=lambda: self._get_upc_dictionary(),
            file_system=config.file_system,
            settings=config.settings,
        )
        self._folder_executor = FolderPipelineExecutor(folder_deps)

        logger.debug(
            "DispatchOrchestrator initialized (pipeline_steps: "
            "validator=%s, splitter=%s, converter=%s)",
            bool(config.validator_step),
            bool(config.splitter_step),
            bool(config.converter_step),
        )

    def process_folder(
        self,
        folder: dict,
        run_log: Any,
        processed_files: DatabaseInterface | None = None,
        pre_discovered_files: list[str] | None = None,
        folder_num: int | None = None,
        folder_total: int | None = None,
    ) -> FolderResult:
        """Process a single folder via the pipeline path.

        Args:
            folder: Folder configuration dictionary.
            run_log: Run log for recording processing activity.
            processed_files: Optional database of already processed files.
            pre_discovered_files: Optional list of files already discovered
                (skips file discovery if provided).
            folder_num: Current folder index (1-based) for progress reporting.
            folder_total: Total number of folders for progress reporting.

        Returns:
            FolderResult with processing outcome.

        """
        correlation_id = get_or_create_correlation_id()
        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        logger.debug("Processing folder: %s (path=%s)", alias, folder_path)

        with CorrelationContext(correlation_id):
            from dispatch.services.folder_processor import FolderProcessingRequest

            request = FolderProcessingRequest(
                folder=folder,
                run_log=run_log,
                processed_files=processed_files,
                upc_dict=self._get_upc_dictionary(self.config.settings),
                settings=self.config.settings,
                pre_discovered_files=pre_discovered_files,
                folder_num=folder_num,
                folder_total=folder_total,
            )
            result = self._folder_executor.process_folder(request)
            self.processed_count += result.files_processed
            self.error_count += result.files_failed
            return result

    def process_folder_with_pipeline(
        self,
        folder: dict,
        run_log: Any,
        processed_files: DatabaseInterface | None = None,
        upc_dict: dict | None = None,
        pre_discovered_files: list[str] | None = None,
        folder_num: int | None = None,
        folder_total: int | None = None,
    ) -> FolderResult:
        """Process folder using new pipeline steps.

        DEPRECATED: This method is kept for backward compatibility.
        Use process_folder() instead which delegates to FolderPipelineExecutor.

        Args:
            folder: Folder configuration dictionary.
            run_log: Run log for recording processing activity.
            processed_files: Optional database of already processed files.
            upc_dict: UPC dictionary for lookup.
            pre_discovered_files: Optional list of files already discovered
                (skips file discovery if provided).
            folder_num: Current folder index (1-based) for progress reporting.
            folder_total: Total number of folders for progress reporting.

        Returns:
            FolderResult with processing outcome.

        """
        result = FolderResult(
            folder_name=folder.get("folder_name", ""), alias=folder.get("alias", "")
        )

        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        logger.debug("Processing folder: %s (path=%s)", alias, folder_path)

        self._log_message(run_log, f"entering folder: {alias}")

        if not self._folder_exists(folder_path):
            return self._folder_not_found_result(folder_path, run_log, result)

        files = self._discover_folder_files(
            folder_path=folder_path,
            pre_discovered_files=pre_discovered_files,
            processed_files=processed_files,
            folder=folder,
            run_log=run_log,
        )

        if files is None:
            return result

        logger.debug("After filter: %d files to process in %s", len(files), folder_path)

        self._log_message(
            run_log, f"{len(files)} found in {folder_path} (pipeline mode)"
        )

        total_files = len(files)
        # Setup progress reporting
        self._setup_folder_progress(
            folder=folder,
            total_files=total_files,
            folder_num=folder_num,
            folder_total=folder_total,
        )

        effective_upc_dict = upc_dict if upc_dict is not None else self.config.upc_dict

        # Delegate actual per-file processing to a small wrapper to keep this
        # method focused on orchestration.
        self._process_folder_file_list(
            files=files,
            folder=folder,
            effective_upc_dict=effective_upc_dict,
            processed_files=processed_files,
            run_log=run_log,
            result=result,
            total_files=total_files,
        )

        self._finalize_folder_result(result)

        return result

    def discover_pending_files(
        self,
        folders: list[dict],
        processed_files: DatabaseInterface | None = None,
        progress_reporter: Any | None = None,
    ) -> tuple[list[list[str]], int]:
        """Discover files pending send for each folder.

        Performs a lightweight pre-pass that identifies files to be sent for each
        active folder, including already-processed filtering. This enables a
        dedicated "finding files" progress phase and avoids duplicate discovery
        work during processing by reusing the returned file lists.

        Args:
            folders: Active folder configuration rows in processing order.
            processed_files: Optional processed-files table for resend filtering.
            progress_reporter: Optional progress reporter that may expose
                discovery-specific methods.

        Returns:
            Tuple of:
                - List of pending-file lists aligned with ``folders`` order.
                - Total number of pending files across all folders.

        """
        # Use provided progress_reporter or fall back to config's
        original_reporter = self._discovery_service._progress_reporter
        if progress_reporter is not None:
            self._discovery_service._progress_reporter = progress_reporter

        try:
            return self._discovery_service.discover_pending_files(
                folders, processed_files=processed_files
            )
        finally:
            # Restore original reporter
            self._discovery_service._progress_reporter = original_reporter

    def discover_and_process_folder(
        self,
        folder: dict,
        run_log: Any,
        processed_files: DatabaseInterface | None = None,
        effective_upc_dict: dict | None = None,
        folder_num: int | None = None,
        folder_total: int | None = None,
    ) -> FolderResult:
        """Discover files for a folder and process them in a single pass.

        This method combines file discovery and processing into one operation,
        eliminating the need for a separate pre-discovery phase. Files are
        discovered, filtered, and processed immediately.

        Args:
            folder: Folder configuration dictionary.
            run_log: Run log for recording processing activity.
            processed_files: Optional database of already processed files.
            effective_upc_dict: UPC lookup dictionary (computed if not provided).
            folder_num: Current folder index (1-based) for progress reporting.
            folder_total: Total number of folders for progress reporting.

        Returns:
            FolderResult with processing outcome.

        """
        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        logger.debug("Discovering and processing folder: %s", alias)

        # Step 1: Discover files for this folder
        files = self._discover_folder_files(
            folder_path=folder_path,
            pre_discovered_files=None,  # Force fresh discovery
            processed_files=processed_files,
            folder=folder,
            run_log=run_log,
        )

        if not files:
            # No files to process - return empty success result
            result = FolderResult(
                folder_name=alias,
                alias=alias,
                files_processed=0,
                files_failed=0,
                errors=[],
                success=True,
            )
            self._finalize_folder_result(result)
            return result

        # Step 2: Initialize progress for this folder
        total_files = len(files)
        self._setup_folder_progress(folder, total_files, folder_num, folder_total)

        # Step 3: Process discovered files immediately
        result = FolderResult(
            folder_name=alias,
            alias=alias,
            files_processed=0,
            files_failed=0,
            errors=[],
            success=True,
        )

        if effective_upc_dict is None:
            effective_upc_dict = self._get_upc_dictionary(self.config.settings)

        self._process_folder_files(
            files=files,
            folder=folder,
            effective_upc_dict=effective_upc_dict,
            processed_files=processed_files,
            run_log=run_log,
            result=result,
            total_files=total_files,
        )

        self._finalize_folder_result(result)
        return result

    def _process_folder_files(
        self,
        files: list[str],
        folder: dict,
        effective_upc_dict: dict,
        processed_files: DatabaseInterface | None,
        run_log: Any,
        result: FolderResult,
        total_files: int,
    ) -> None:
        """Process all files in folder and update result counters in place.

        Iterates through the file list, processing each via the pipeline
        and accumulating success/failure counts in the result object.

        Args:
            files: List of file paths to process.
            folder: Folder configuration dictionary.
            effective_upc_dict: UPC lookup dictionary.
            processed_files: Database table for tracking processed files.
            run_log: Run log for recording processing activity.
            result: FolderResult object to update (mutated in place).
            total_files: Total file count for progress reporting.

        """
        if not files:
            return

        for idx, file_path in enumerate(files):
            self._progress_service.update_file(idx + 1, total_files)

            file_result = self._process_file_with_pipeline(
                file_path, folder, effective_upc_dict, run_log
            )

            if file_result.sent:
                result.files_processed += 1
                self.processed_count += 1
                if processed_files:
                    self._record_processed_file(processed_files, folder, file_result)
            else:
                result.files_failed += 1
                self.error_count += 1
                result.errors.extend(file_result.errors)

    def _finalize_folder_result(self, result: FolderResult) -> None:
        """Finalize folder result and notify progress reporter.

        Sets the success flag based on whether any files failed, and
        notifies the progress reporter that the folder is complete.

        Args:
            result: FolderResult object to finalize (mutated in place).

        """
        result.success = result.files_failed == 0
        self._progress_service.complete_folder(success=result.success)

    # --- Small helper wrappers extracted to aid readability ---
    def _discover_folder_files(
        self,
        folder_path: str,
        pre_discovered_files: list[str] | None,
        processed_files: DatabaseInterface | None,
        folder: dict,
        run_log: Any,
    ) -> list[str] | None:
        """Wrapper for file discovery/filtering for a folder."""
        return self._discovery_service.discover_and_filter_files(
            folder_path=folder_path,
            pre_discovered_files=pre_discovered_files,
            processed_files=processed_files,
            folder=folder,
            run_log=run_log,
        )

    def _setup_folder_progress(
        self,
        folder: dict,
        total_files: int,
        folder_num: int | None,
        folder_total: int | None,
    ) -> None:
        """Wrapper to initialize progress reporter for a folder."""
        self._progress_service.start_folder(
            folder=folder,
            total_files=total_files,
            folder_num=folder_num,
            folder_total=folder_total,
        )

    def _process_folder_file_list(
        self,
        files: list[str],
        folder: dict,
        effective_upc_dict: dict,
        processed_files: DatabaseInterface | None,
        run_log: Any,
        result: FolderResult,
        total_files: int,
    ) -> None:
        """Wrapper delegating to the per-file loop processor."""
        self._process_folder_files(
            files=files,
            folder=folder,
            effective_upc_dict=effective_upc_dict,
            processed_files=processed_files,
            run_log=run_log,
            result=result,
            total_files=total_files,
        )

    def _folder_not_found_result(
        self, folder_path: str, run_log: Any, result: FolderResult
    ) -> FolderResult:
        """Create error result for missing folder.

        Args:
            folder_path: Path to the folder that was not found.
            run_log: Run log to record the error message.
            result: FolderResult to populate with error details.

        Returns:
            The updated FolderResult with success=False and files_failed=1.

        """
        error_msg = f"Folder not found: {folder_path}"
        result.errors.append(error_msg)
        result.success = False
        result.files_failed = 1
        self._log_error(run_log, error_msg)
        return result

    def _init_progress_reporter(
        self,
        folder: dict,
        total_files: int,
        folder_num: int | None,
        folder_total: int | None,
    ) -> None:
        """Initialize progress reporter for folder processing.

        Calls the progress reporter's start_folder method with folder alias
        and file counts. Handles both old and new progress reporter interfaces
        (with/without folder_num and folder_total parameters).

        Args:
            folder: Folder configuration dictionary containing 'alias' or 'folder_name'.
            total_files: Number of files to process in this folder.
            folder_num: Current folder index (1-based), if available.
            folder_total: Total number of folders to process, if available.

        """
        if not self.config.progress_reporter:
            return

        progress = self.config.progress_reporter
        if not hasattr(progress, "start_folder"):
            return

        try:
            progress.start_folder(
                folder.get("alias", folder.get("folder_name", "")),
                total_files,
                folder_num=folder_num,
                folder_total=folder_total,
            )
        except TypeError:
            logger.warning(
                "Progress reporter start_folder() missing optional parameters "
                "(folder_num, folder_total). Update reporter signature."
            )
            progress.start_folder(
                folder.get("alias", folder.get("folder_name", "")), total_files
            )

    @staticmethod
    def _is_strict_database_lookup(settings: dict) -> bool:
        """Return True when database lookup mode requires fail-fast behavior."""
        mode = str(settings.get("database_lookup_mode", "optional")).strip().lower()
        return mode in {"strict", "required", "test"}

    def _get_upc_dictionary(self, settings: dict) -> dict:
        """Get or fetch UPC dictionary using the UPC lookup service.

        Args:
            settings: Application settings

        Returns:
            UPC dictionary (may be empty if initialization fails)

        """
        if self.config.upc_dict:
            return self.config.upc_dict

        strict_db_mode = self._is_strict_database_lookup(settings)
        self.upc_service.settings = settings
        result = self.upc_service.get_dictionary(
            upc_service=self.config.upc_service,
            strict_db_mode=strict_db_mode,
        )
        if result:
            self.config.upc_dict = result
        return result

    @property
    def _last_upc_lookup_error(self) -> str | None:
        """Return the last error from the UPC lookup service."""
        return self.upc_service.last_error

    def _process_file_with_pipeline(
        self, file_path: str, folder: dict, upc_dict: dict, run_log: Any = None
    ) -> FileResult:
        """Process single file with pipeline using the FileProcessor service.

        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary
            upc_dict: UPC dictionary for lookup
            run_log: Optional run log for recording processing activity

        Returns:
            FileResult with processing outcome

        """
        context = self._build_processing_context(folder, upc_dict)
        # Pass the full ProcessingContext object so downstream services receive
        # settings and temp artifact tracking.
        return self.file_processor.process_file(
            file_path=file_path,
            folder=folder,
            upc_dict=upc_dict,
            run_log=run_log,
            effective_folder=context,
        )

    def _execute_file_pipeline(
        self,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> None:
        """Execute core file pipeline and update result in place.

        Runs the file through checksum calculation, validation, splitting
        (if enabled), conversion, and sending stages. The result
        object is mutated in place to reflect processing outcomes.

        Args:
            file_path: Absolute path to the file being processed.
            file_basename: Base name of the file (for logging).
            context: ProcessingContext containing settings and temp tracking.
            result: FileResult to update (mutated in place).
            run_log: Optional run log for recording processing activity.

        """
        # calculate checksum and log
        self._set_checksum_for_result(result, file_path, file_basename)

        current_file = file_path

        # validation
        continue_processing, current_file = self._run_validation_pipeline(
            current_file=current_file,
            context=context,
            result=result,
            run_log=run_log,
            file_basename=file_basename,
        )
        if not continue_processing:
            return

        # splitting path (may send split files)
        if self._process_split_pipeline(
            current_file=current_file,
            file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            run_log=run_log,
        ):
            return

        # conversion
        current_file, did_convert = self._apply_conversion(
            current_file=current_file,
            file_basename=file_basename,
            original_file_path=file_path,
            context=context,
            run_log=run_log,
            validation_passed=result.validated,
        )
        if did_convert:
            result.converted = True

        # send final output
        self._send_single_pipeline_file(
            current_file=current_file,
            file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            run_log=run_log,
        )

    def _send_single_pipeline_file(
        self,
        current_file: str,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> None:
        """Send a single (non-split) pipeline output file."""
        enabled_backends = self.send_manager.get_enabled_backends(
            context.effective_folder
        )
        if not enabled_backends:
            result.sent = False
            result.errors.append("No backends enabled")
            return

        result.sent = self._send_pipeline_file(
            self._apply_file_rename(current_file, context),
            context.effective_folder,
            run_log,
        )

        if not result.sent:
            self._record_send_failure(
                result=result,
                file_basename=file_basename,
                current_file=current_file,
                run_log=run_log,
            )
            return

        self._log_success_with_invoices(
            run_log=run_log,
            file_basename=file_basename,
            file_path=file_path,
        )

    def _cleanup_temp_artifacts(self, context: ProcessingContext) -> None:
        """Best-effort cleanup for pipeline temporary directories and files."""
        strict_testing_mode = get_strict_testing_mode()
        cleanup_errors = []
        logger.debug(
            "Temp cleanup: %d dirs, %d files",
            len(context.temp_dirs),
            len(context.temp_files),
        )

        for temp_dir in context.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=not strict_testing_mode)
            except OSError as exc:
                if strict_testing_mode:
                    cleanup_errors.append(
                        f"directory '{temp_dir}' could not be removed: {exc}"
                    )

        for temp_file in context.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except OSError as exc:
                if strict_testing_mode:
                    cleanup_errors.append(
                        f"file '{temp_file}' could not be removed: {exc}"
                    )

        if cleanup_errors:
            raise RuntimeError(
                "Failed to clean up temporary artifacts: " + "; ".join(cleanup_errors)
            )

    def _process_split_pipeline(
        self,
        current_file: str,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> bool:
        """Process split pipeline path. Returns True if split flow was executed."""
        split_edi = normalize_bool(context.effective_folder.get("split_edi", False))
        logger.debug(
            "Splitter step: enabled=%s, split_edi=%s",
            bool(self.config.splitter_step),
            split_edi,
        )
        if not (self.config.splitter_step and split_edi):
            return False

        with tempfile.TemporaryDirectory() as temp_dir:
            split_result = self.config.splitter_step.split(
                current_file,
                temp_dir,
                context.effective_folder,
                context.upc_dict,
            )
            split_files = self._extract_split_files(split_result)
            files_to_send = split_files if split_files else [current_file]

            for pipeline_file in files_to_send:
                current_pipeline_file, did_convert = self._apply_conversion(
                    current_file=pipeline_file,
                    file_basename=file_basename,
                    original_file_path=file_path,
                    context=context,
                    run_log=run_log,
                    validation_passed=result.validated,
                )
                if did_convert:
                    result.converted = True

                send_result = self._send_pipeline_file(
                    self._apply_file_rename(current_pipeline_file, context),
                    context.effective_folder,
                    run_log,
                )
                if not send_result:
                    self._record_split_send_failure(result, current_pipeline_file)

            result.sent = len(result.errors) == 0
            if result.sent:
                self._log_success_with_invoices(
                    run_log=run_log,
                    file_basename=file_basename,
                    file_path=file_path,
                )
            return True

    def _extract_split_files(self, split_result: Any) -> list[str]:
        """Extract output split file paths from splitter result."""
        if hasattr(split_result, "files"):
            return [f[0] for f in split_result.files]
        if isinstance(split_result, list):
            return split_result
        return []

    def _record_split_send_failure(
        self,
        result: FileResult,
        current_pipeline_file: str,
    ) -> None:
        """Record split-file send failures from send manager errors."""
        send_errors = self.send_manager.get_errors()
        if send_errors:
            for backend_name, error_message in send_errors.items():
                result.errors.append(
                    self._format_send_error(
                        backend_name, error_message, is_split_file=True
                    )
                )
            return

        result.errors.append(f"Failed to send split file: {current_pipeline_file}")

    def _record_send_failure(
        self,
        result: FileResult,
        file_basename: str,
        current_file: str,
        run_log: Any,
    ) -> None:
        """Record non-split send failures and corresponding log messages."""
        send_errors = self.send_manager.get_errors()
        if send_errors:
            for backend_name, error_message in send_errors.items():
                result.errors.append(
                    self._format_send_error(backend_name, error_message)
                )
                self._log_message(
                    run_log,
                    f"FAILED sending {file_basename} via {backend_name}: "
                    f"{error_message}",
                )
            return

        result.errors.append(f"Failed to send file: {current_file}")
        self._log_message(
            run_log,
            f"FAILED sending {file_basename}",
        )

    def _format_send_error(
        self, backend_name: str, error_message: str, is_split_file: bool = False
    ) -> str:
        """Format a send error message for a specific backend."""
        file_type = "split file" if is_split_file else "file"
        return f"Failed to send {file_type} via {backend_name}: {error_message}"

    def _log_success_with_invoices(
        self,
        run_log: Any,
        file_basename: str,
        file_path: str,
    ) -> None:
        """Log success and any extracted invoice numbers."""
        self._log_message(run_log, f"Success: {file_basename}")
        invoice_numbers = self._extract_invoice_numbers(file_path)
        if invoice_numbers:
            self._log_message(run_log, f"Invoice numbers: {invoice_numbers}")

    def _run_validation_pipeline(
        self,
        current_file: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
        file_basename: str,
    ) -> tuple[bool, str]:
        """Run validation and update processing state.

        Returns:
            Tuple of (continue_processing, current_file_path)

        """
        should_validate = self._should_validate(context.effective_folder)
        logger.debug(
            "Validation step: enabled=%s, should_validate=%s",
            bool(self.config.validator_step),
            should_validate,
        )

        if not should_validate:
            return True, current_file

        if not self.config.validator_step:
            return True, current_file

        validation_output = self.config.validator_step.execute(
            current_file, context.effective_folder
        )
        is_valid, errors_or_file = self._normalize_validation_output(
            validation_output=validation_output,
            current_file=current_file,
        )
        return self._apply_validation_outcome(
            is_valid=is_valid,
            errors_or_file=errors_or_file,
            current_file=current_file,
            result=result,
            run_log=run_log,
            file_basename=file_basename,
            context=context,
        )

    def _apply_conversion(
        self,
        current_file: str,
        file_basename: str,
        original_file_path: str,
        context: ProcessingContext,
        run_log: Any,
        *,
        validation_passed: bool = True,
    ) -> tuple[str, bool]:
        """Apply the converter step for a single file path.

        Args:
            current_file: Current file path in the pipeline
            file_basename: Base name of the file
            original_file_path: Original file path before any processing
            context: Processing context
            run_log: Run log for recording activity
            validation_passed: Whether validation passed for this file

        Returns:
            Tuple of (final_file_path, did_convert)

        """
        did_convert = False
        converter_step = self.config.converter_step
        convert_edi = context.effective_folder.get("convert_edi", False)
        convert_format = context.effective_folder.get("convert_to_format", "")
        run_conversion = converter_step is not None and convert_edi

        logger.debug(
            "Converter step: enabled=%s, convert_edi=%s, convert_to_format=%s",
            bool(converter_step),
            convert_edi,
            convert_format,
        )

        if run_conversion:
            self._log_message(
                run_log,
                f"Converting {file_basename} to {convert_format}",
            )
            converted_file = self._execute_conversion_step(
                converter_step=converter_step,
                current_file=current_file,
                original_file_path=original_file_path,
                context=context,
            )
            if converted_file:
                if converted_file != original_file_path:
                    context.temp_files.append(converted_file)
                current_file = converted_file
                did_convert = True
            elif str(convert_format).strip():
                raise RuntimeError(
                    "Conversion was requested for "
                    f"format '{convert_format}' but no converted output "
                    "was produced"
                )

        return current_file, did_convert

    def _execute_conversion_step(
        self,
        converter_step: Any,
        current_file: str,
        original_file_path: str,
        context: ProcessingContext,
    ) -> str | None:
        """Execute the configured converter step and return converted path or None.

        Kept as a separate method to keep _apply_conversion concise.
        """
        # The converter API expects: (input_path, folder, settings,
        # upc_dict, context=...)
        return converter_step.execute(
            current_file,
            context.effective_folder,
            context.settings,
            context.upc_dict,
            context=context,
        )

    def _set_checksum_for_result(
        self, result: FileResult, file_path: str, file_basename: str
    ) -> None:
        """Calculate and set checksum on a FileResult and log debug info."""
        result.checksum = self._calculate_checksum(file_path)
        logger.debug("Calculated checksum for %s: %s", file_basename, result.checksum)

    def _normalize_validation_output(
        self, validation_output: Any, current_file: str
    ) -> tuple[bool, Any]:
        """Normalize validator step output to `(is_valid, errors_or_file)` tuple."""
        if isinstance(validation_output, tuple):
            return validation_output

        from dispatch.pipeline.validator import ValidationResult

        if isinstance(validation_output, ValidationResult):
            return (
                validation_output.is_valid,
                (
                    validation_output.errors
                    if not validation_output.is_valid
                    else current_file
                ),
            )

        if isinstance(validation_output, bool):
            return validation_output, current_file

        logger.warning(
            "Unexpected validation output type: %s, treating as invalid",
            type(validation_output).__name__,
        )
        return False, [str(validation_output)]

    def _apply_validation_outcome(
        self,
        *,
        is_valid: bool,
        errors_or_file: Any,
        current_file: str,
        result: FileResult,
        run_log: Any,
        file_basename: str,
        context: ProcessingContext,
    ) -> tuple[bool, str]:
        """Apply validation result to file result and control flow.

        Returns:
            Tuple of (continue_processing, current_file_path)

        """
        result.validated = is_valid

        if is_valid:
            if isinstance(errors_or_file, str):
                return True, errors_or_file
            return True, current_file

        if isinstance(errors_or_file, list):
            result.errors.extend(errors_or_file)
        else:
            result.errors.append(str(errors_or_file))

        self._log_message(
            run_log,
            f"Validation failed for {file_basename}: {result.errors}",
        )

        if not normalize_bool(
            context.effective_folder.get("force_edi_validation", False)
        ):
            return False, current_file

        return True, current_file

    def _detect_enabled_backends(self, folder: dict) -> list[str]:
        """Detect which backends are enabled for a folder.

        Args:
            folder: Folder configuration dictionary

        Returns:
            List of enabled backend descriptions like "Copy: /path" or "FTP: server"

        """
        enabled = []
        if normalize_bool(folder.get("process_backend_copy", False)):
            enabled.append(f"Copy: {folder.get('copy_to_directory', 'N/A')}")
        if normalize_bool(folder.get("process_backend_ftp", False)):
            enabled.append(f"FTP: {folder.get('ftp_server', 'N/A')}")
        if normalize_bool(folder.get("process_backend_email", False)):
            enabled.append(f"Email: {folder.get('email_to', 'N/A')}")
        return enabled

    def _normalize_edi_flags(
        self, effective_folder: dict, *, has_convert_target: bool
    ) -> None:
        """Normalize EDI-related flags in the folder dict.

        Modifies effective_folder in place.

        Args:
            effective_folder: Folder configuration dictionary
            has_convert_target: Whether a conversion target is configured

        """
        process_edi_raw = effective_folder.get("process_edi")
        process_edi_bool = (
            normalize_bool(process_edi_raw) if process_edi_raw is not None else False
        )

        if "convert_edi" not in effective_folder:
            if process_edi_raw is None:
                effective_folder["convert_edi"] = has_convert_target
            else:
                effective_folder["convert_edi"] = process_edi_bool

        if effective_folder.get("convert_edi", False):
            effective_folder["process_edi"] = True

        if "process_edi" not in effective_folder and (
            effective_folder.get("split_edi", False)
            or effective_folder.get("convert_edi", False)
        ):
            effective_folder["process_edi"] = True

    def _build_processing_context(
        self, folder: dict, upc_dict: dict
    ) -> ProcessingContext:
        """Build non-mutating per-file processing context."""
        effective_folder = folder.copy()

        # Apply defaults for fields that may be NULL in the database.
        for key, default in FOLDER_DEFAULTS.items():
            if effective_folder.get(key) is None:
                effective_folder[key] = default

        # upc_target_length of 0 is not meaningful -- treat as default (11).
        if not effective_folder.get("upc_target_length"):
            effective_folder["upc_target_length"] = FOLDER_DEFAULTS["upc_target_length"]

        effective_folder["convert_to_format"] = normalize_convert_to_format(
            effective_folder.get("convert_to_format", "")
        )

        if normalize_bool(effective_folder.get("tweak_edi", False)):
            # Always override convert_to_format when tweak_edi is enabled,
            # even if a stale non-tweaks value exists from a prior profile.
            effective_folder["convert_to_format"] = "tweaks"
            effective_folder["process_edi"] = True

        has_convert_target = bool(effective_folder.get("convert_to_format"))

        self._normalize_edi_flags(
            effective_folder, has_convert_target=has_convert_target
        )

        return ProcessingContext(
            folder=folder,
            effective_folder=effective_folder,
            settings=self.config.settings,
            upc_dict=upc_dict,
        )

    def _validate_rename_template(self, template: str) -> None:
        """Validate the rename template for security issues.

        Args:
            template: The filename template to validate

        Raises:
            ValueError: If the template is absolute or contains path traversal

        """
        if os.path.isabs(template) or ".." in template:
            raise ValueError(f"Invalid filename pattern in rename template: {template}")

    def _apply_file_rename(self, file_path: str, context: Any) -> str:
        """Return a renamed copy of file_path if rename_file is configured.

        Creates a temp copy with the new name (tracked in context.temp_dirs
        for automatic cleanup) and returns its path.  If rename_file is empty,
        returns the original path unchanged.

        Args:
            file_path: Current file path
            context: ProcessingContext with effective_folder and temp_dirs

        Returns:
            Path to send (renamed copy, or original if no rename configured)

        """
        rename_template = context.effective_folder.get("rename_file", "").strip()
        if not rename_template:
            return file_path

        original_basename = os.path.basename(file_path)
        date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d")
        ext = original_basename.split(".")[-1] if "." in original_basename else ""
        new_name = rename_template.replace("%datetime%", date_time)
        if ext:
            new_name = f"{new_name}.{ext}"
        new_name = re.sub("[^A-Za-z0-9. _]+", "", new_name)

        temp_dir = tempfile.mkdtemp(prefix="edi_rename_")
        if hasattr(context, "temp_dirs"):
            context.temp_dirs.append(temp_dir)

        self._validate_rename_template(new_name)

        if not new_name or new_name == ".." or os.path.isabs(new_name):
            raise ValueError(f"Invalid filename from template: {new_name}")

        full_dest = os.path.join(temp_dir, new_name)
        real_full_dest = os.path.realpath(full_dest)
        if not real_full_dest.startswith(os.path.realpath(temp_dir) + os.sep):
            raise ValueError(f"Path traversal attempt detected: {new_name}")

        dest_path = full_dest
        shutil.copy2(file_path, dest_path)
        logger.debug("Renamed %s → %s for send", original_basename, new_name)
        return dest_path

    def _send_pipeline_file(
        self, file_path: str, folder: dict, run_log: Any = None
    ) -> bool:
        """Send file through pipeline to backends.

        Args:
            file_path: Path to the file to send
            folder: Folder configuration dictionary
            run_log: Optional run log for recording processing activity

        Returns:
            True if file was sent successfully

        """
        enabled_backends = self.send_manager.get_enabled_backends(folder)

        if not enabled_backends:
            return False

        file_basename = os.path.basename(file_path)

        for backend_name in enabled_backends:
            display_name = self.send_manager.DEFAULT_BACKENDS.get(backend_name, {}).get(
                "display_name", backend_name
            )
            self._log_message(
                run_log,
                f"sending {file_basename} to {display_name}",
            )
            log_backend_call(
                logger,
                backend_name,
                "send",
                endpoint=folder.get(
                    f"{backend_name}_server",
                    folder.get(f"{backend_name}_to_directory", ""),
                ),
                correlation_id=get_or_create_correlation_id(),
            )

        settings = self.config.settings
        send_results = self.send_manager.send_all(
            enabled_backends, file_path, folder, settings
        )

        success = all(send_results.values())
        for backend_name, backend_success in send_results.items():
            log_backend_call(
                logger,
                backend_name,
                "send",
                success=backend_success,
                correlation_id=get_or_create_correlation_id(),
            )

        return success

    def process_file(self, file_path: str, folder: dict) -> FileResult:
        """Process a single file via the pipeline path.

        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary

        Returns:
            FileResult with processing outcome

        """
        correlation_id = get_or_create_correlation_id()
        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        log_with_context(
            logger,
            logging.INFO,
            f"Starting file processing: {file_path}",
            correlation_id=correlation_id,
            operation="process_file",
            context={
                "file_path": file_path,
                "folder_name": folder_path,
                "folder_alias": alias,
            },
        )

        with CorrelationContext(correlation_id):
            upc_dict = self._get_upc_dictionary(self.config.settings)
            return self._process_file_with_pipeline(file_path, folder, upc_dict)

    def _folder_exists(self, path: str) -> bool:
        """Check if a folder exists.

        Args:
            path: Folder path to check

        Returns:
            True if folder exists, False otherwise

        """
        if self.config.file_system:
            return self.config.file_system.dir_exists(path)

        return os.path.isdir(path)

    def _get_files_in_folder(self, path: str) -> list[str]:
        """Get list of files in a folder.

        Args:
            path: Folder path

        Returns:
            List of file paths

        """
        if self.config.file_system:
            return self.config.file_system.list_files(path)

        if not os.path.isdir(path):
            return []

        return [
            os.path.abspath(os.path.join(path, f))
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
        ]

    def _filter_processed_files(
        self,
        files: list[str],
        processed_files: DatabaseInterface,
        folder: dict,
        folder_index: int | None = None,
        folder_total: int | None = None,
        folder_name: str | None = None,
        progress_reporter: Any | None = None,
    ) -> list[str]:
        """Filter out already processed files, unless marked for resend.

        Args:
            files: List of file paths
            processed_files: Database of processed files
            folder: Folder configuration
            folder_index: Current folder index (1-based, optional)
            folder_total: Total number of folders (optional)
            folder_name: Display name of the folder (optional)
            progress_reporter: Optional progress reporter for per-file updates

        Returns:
            List of unprocessed or resend-marked file paths

        """
        folder_id = folder.get("id") or folder.get("old_id")
        processed = processed_files.find(folder_id=folder_id)

        # Files that should be SKIPPED (already processed AND NOT marked for resend)
        skipped_checksums = {
            f.get("file_checksum") for f in processed if not f.get("resend_flag")
        }

        logger.debug(
            "Filtering %d files, %d already processed (skip %d checksums)",
            len(files),
            len(processed),
            len(skipped_checksums),
        )

        # Calculate checksums one at a time to enable per-file progress reporting
        file_checksums: dict[str, str] = {}
        for file_index, file_path in enumerate(files, start=1):
            file_checksums[file_path] = self._calculate_checksum(file_path)

            # Report per-file progress if reporter supports it
            if progress_reporter and hasattr(
                progress_reporter, "update_discovery_file"
            ):
                progress_reporter.update_discovery_file(
                    folder_num=folder_index,
                    folder_total=folder_total,
                    file_num=file_index,
                    file_total=len(files),
                    filename=os.path.basename(file_path),
                )

        return [f for f in files if file_checksums[f] not in skipped_checksums]

    def _record_processed_file(
        self, processed_files: DatabaseInterface, folder: dict, file_result: FileResult
    ) -> None:
        """Record a successfully processed file in the database.

        Args:
            processed_files: Database interface for processed files
            folder: Folder configuration
            file_result: Result of file processing

        """
        folder_id = folder.get("id") or folder.get("old_id")

        # Check if it was marked for resend (match by name and folder)
        existing_resend = processed_files.find_one(
            file_name=file_result.file_name, folder_id=folder_id, resend_flag=1
        )

        # Construct sent_to string for the database
        enabled_backends = self._detect_enabled_backends(folder)
        sent_to_str = ", ".join(enabled_backends) if enabled_backends else "N/A"

        invoice_numbers = self._extract_invoice_numbers(file_result.file_name)

        if existing_resend:
            # Clear resend flag for this specific record
            processed_files.update(
                {
                    "id": existing_resend["id"],
                    "resend_flag": 0,
                    "processed_at": datetime.datetime.now().isoformat(),
                    "sent_to": sent_to_str,
                    "status": "processed",
                    "invoice_numbers": invoice_numbers,
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
                    "invoice_numbers": invoice_numbers,
                }
            )

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            MD5 checksum as hex string

        """
        log_file_operation(
            logger,
            "read",
            file_path,
            correlation_id=get_or_create_correlation_id(),
            file_type="edi",
        )
        logger.debug("Calculating checksum for: %s", file_path)

        if self.config.file_system:
            content = self.config.file_system.read_file(file_path)
        else:
            with open(file_path, "rb") as f:
                content = f.read()

        checksum = hashlib.md5(content).hexdigest()
        log_file_operation(
            logger,
            "read",
            file_path,
            success=True,
            correlation_id=get_or_create_correlation_id(),
            file_type="edi",
        )
        return checksum

    def _extract_invoice_numbers(self, file_path: str) -> str:
        """Extract invoice numbers from EDI A-records in a file.

        Args:
            file_path: Path to the EDI file

        Returns:
            Comma-separated string of invoice numbers, or empty string

        """
        try:
            if self.config.file_system:
                content_bytes = self.config.file_system.read_file(file_path)
                content = (
                    content_bytes.decode("utf-8", errors="replace")
                    if isinstance(content_bytes, bytes)
                    else content_bytes
                )
            else:
                with open(file_path, "r", errors="replace") as f:
                    content = f.read()

            seen: dict[str, None] = {}
            for line in content.splitlines():
                try:
                    rec = capture_records(line)
                    if rec and rec.get("record_type") == "A":
                        inv_num = rec.get("invoice_number", "").strip()
                        if inv_num:
                            seen[inv_num] = None
                except (ValueError, KeyError):
                    continue

            return ", ".join(seen)
        except (OSError, ValueError, KeyError) as e:
            logger.exception(
                "Failed to extract invoice numbers from %s: %s", file_path, e
            )
            return ""

    def _should_validate(self, folder: dict) -> bool:
        """Check if a folder's files should be validated.

        Args:
            folder: Folder configuration

        Returns:
            True if validation should be performed

        """
        return (
            normalize_bool(folder.get("process_edi"))
            or normalize_bool(folder.get("split_edi", False))
            or normalize_bool(folder.get("force_edi_validation", False))
        )

    def _log_message(self, run_log: Any, message: str) -> None:
        """Log a message to the run log and Python logger.

        Args:
            run_log: Run log to write to
            message:             Message to log

        """
        log_with_context(
            logger,
            logging.INFO,
            message,
            correlation_id=get_or_create_correlation_id(),
            operation="run_log",
        )
        if hasattr(run_log, "write"):
            run_log.write((message + "\r\n").encode())
        elif hasattr(run_log, "append"):
            run_log.append(message)

    def _log_error(self, run_log: Any, message: str) -> None:
        """Log an error message to the run log and Python logger.

        Args:
            run_log: Run log to write to
            message:             Error message to log

        """
        log_with_context(
            logger,
            logging.ERROR,
            f"ERROR: {message}",
            correlation_id=get_or_create_correlation_id(),
            operation="run_log",
        )
        if hasattr(run_log, "write"):
            run_log.write(("ERROR: %s" % message + "\r\n").encode())
        elif hasattr(run_log, "append"):
            run_log.append("ERROR: %s" % message)

    def get_summary(self) -> str:
        """Get a summary of the processing run.

        Returns:
            Summary string

        """
        return f"{self.processed_count} processed, {self.error_count} errors"

    def reset(self) -> None:
        """Reset the orchestrator state."""
        self.run_log = StringIO()
        self.processed_count = 0
        self.error_count = 0
        self.error_handler.clear_errors()

    @staticmethod
    def process(
        database_connection,
        folders_database,
        run_log,
        emails_table,
        run_log_directory,
        reporting,
        processed_files,
        version,
        errors_folder,
        settings,
        progress_callback=None,
    ):
        """Static method for backward-compatible dispatch processing.

        This provides a drop-in replacement for the legacy dispatch.process() function.
        It creates a DispatchOrchestrator and processes all active folders.

        Args:
            database_connection: Database connection (not used directly,
            kept for compatibility)
            folders_database: Folders database interface
            run_log: Run log for recording processing activity
            emails_table: Emails table for storing log references
            run_log_directory: Directory for storing run logs
            reporting: Reporting configuration
            processed_files: Processed files database
            version: Application version string
            errors_folder: Directory for storing error logs
            settings: Global application settings
            progress_callback: Optional progress callback for UI updates

        Returns:
            Tuple of (has_errors: bool, summary: str)

        """

        # Prepare orchestrator and folder list
        orchestrator, folders = DispatchOrchestrator._prepare_processing(
            folders_database, settings, version, progress_callback
        )

        logger.debug("Starting dispatch process for %d active folders", len(folders))

        # Iterate folders and collect errors
        has_errors = DispatchOrchestrator._iterate_folders(
            orchestrator, folders, run_log, processed_files
        )

        # Finalize and return summary
        summary = DispatchOrchestrator._finalize_processing(orchestrator)
        logger.info("Dispatch complete: %s", summary)
        return has_errors, summary

    @staticmethod
    def _prepare_processing(folders_database, settings, version, progress_callback):
        """Prepare the DispatchOrchestrator and return (orchestrator, folders).

        This extracts the initial configuration and folder retrieval from the
        main process() method to improve readability.
        """
        # Local imports kept here to avoid importing heavy pipeline modules at
        # module import time (preserves original lazy-import behavior).
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.splitter import EDISplitterStep
        from dispatch.pipeline.validator import EDIValidationStep

        config = DispatchConfig(
            database=folders_database,
            settings=settings,
            version=version,
            progress_reporter=progress_callback,
            validator_step=EDIValidationStep(),
            splitter_step=EDISplitterStep(),
            converter_step=EDIConverterStep(),
        )

        orchestrator = DispatchOrchestrator(config)
        folders = list(folders_database.find(folder_is_active=True, order_by="alias"))
        return orchestrator, folders

    @staticmethod
    def _iterate_folders(
        orchestrator: "DispatchOrchestrator", folders: list, run_log, processed_files
    ) -> bool:
        """Iterate over folders and run processing, returning whether
    any errors occurred.

        Uses single-pass discovery and processing: files are discovered and
        processed immediately for each folder, eliminating the pre-discovery phase.
        """
        has_errors = False
        for folder_index, folder in enumerate(folders, start=1):
            try:
                # Discover and process in single pass
                result = orchestrator.discover_and_process_folder(
                    folder,
                    run_log,
                    processed_files,
                    folder_num=folder_index,
                    folder_total=len(folders),
                )
                if not result.success:
                    has_errors = True
            except Exception as folder_error:
                has_errors = True
                if hasattr(run_log, "write"):
                    try:
                        run_log.write(
                            (
                                f"ERROR processing folder"
                                f" {folder.get('alias', 'unknown')}:"
                                f" {folder_error}\r\n"
                            ).encode()
                        )
                    except Exception:
                        # best-effort logging; avoid masking original error
                        logger.exception("Failed to write folder error to run_log")
        return has_errors

    @staticmethod
    def _finalize_processing(orchestrator: "DispatchOrchestrator") -> str:
        """Finalize processing and return summary string."""
        return orchestrator.get_summary()
