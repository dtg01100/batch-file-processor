"""Dispatch Orchestrator for coordinating file processing.

This module provides the main orchestration layer for dispatch operations,
coordinating validation, conversion, and sending of files.
"""

import datetime
import logging
import os
from io import StringIO

from core.structured_logging import (
    CorrelationContext,
    get_logger,
    get_or_create_correlation_id,
    log_with_context,
)
from core.utils import normalize_bool
from core.utils.folder_utils import build_effective_folder
from dispatch.error_handler import ErrorHandler
from dispatch.file_utils import (
    extract_invoice_numbers,
    write_to_run_log,
)
from dispatch.interfaces import DatabaseInterface, RunLog
from dispatch.results import DispatchConfig, FolderResult
from dispatch.send_manager import SendManager
from dispatch.services.file_processor import (
    FileProcessor,
    FileResult,
    ProcessingContext,
)
from dispatch.services.folder_discovery import FolderDiscoveryService
from dispatch.services.progress_reporter import ProgressReporter
from dispatch.services.progress_reporting import ProgressReportingService
from dispatch.services.upc_service import UPCLookupService

logger = get_logger(__name__)


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
            progress_reporter=self._progress_service,
            get_upc_dictionary=self._get_upc_dictionary,
            file_system=config.file_system,
            settings=config.settings,
        )
        self._folder_executor = FolderPipelineExecutor(folder_deps)

    def process_folder(
        self,
        folder: dict,
        run_log: RunLog,
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

    def discover_pending_files(
        self,
        folders: list[dict],
        processed_files: DatabaseInterface | None = None,
        progress_reporter: ProgressReporter | None = None,
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
        run_log: RunLog,
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
        run_log: RunLog,
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
        run_log: RunLog,
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

    def _folder_not_found_result(
        self, folder_path: str, run_log: RunLog, result: FolderResult
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
        log_with_context(
            logger,
            logging.ERROR,
            f"ERROR: {error_msg}",
            correlation_id=get_or_create_correlation_id(),
            operation="run_log",
        )
        write_to_run_log(run_log, error_msg, prefix="ERROR: ")
        return result

    def _get_upc_dictionary(self, settings: dict) -> dict:
        """Get or fetch UPC dictionary using the UPC lookup service.

        Args:
            settings: Application settings

        Returns:
            UPC dictionary (may be empty if initialization fails)

        """
        if self.config.upc_dict:
            return self.config.upc_dict

        strict_db_mode = str(
            settings.get("database_lookup_mode", "optional")
        ).strip().lower() in {"strict", "required", "test"}
        self.upc_service.settings = settings
        result = self.upc_service.get_dictionary(
            upc_service=self.config.upc_service,
            strict_db_mode=strict_db_mode,
        )
        if result:
            self.config.upc_dict = result
        return result

    def _process_file_with_pipeline(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict,
        run_log: RunLog | None = None,
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

    def _build_processing_context(
        self, folder: dict, upc_dict: dict
    ) -> ProcessingContext:
        """Build non-mutating per-file processing context."""
        effective_folder = build_effective_folder(folder)

        return ProcessingContext(
            folder=folder,
            effective_folder=effective_folder,
            settings=self.config.settings,
            upc_dict=upc_dict,
        )

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
    ) -> list[str]:
        """Filter out already processed files, unless marked for resend.

        Args:
            files: List of file paths
            processed_files: Database of processed files
            folder: Folder configuration
            folder_index: Current folder index (1-based, optional)
            folder_total: Total number of folders (optional)
            progress_reporter: Optional progress reporter for per-file updates

        Returns:
            List of unprocessed or resend-marked file paths


        """
        from dispatch.services.file_filter import filter_pending_files

        folder_id = (
            folder.get("id") if folder.get("id") is not None else folder.get("old_id")
        )

        if folder_id is None:
            logger.warning("No folder_id available, returning all files")
            return files

        logger.debug(
            "Filtering %d files for folder_id=%d via SQL",
            len(files),
            folder_id,
        )

        return filter_pending_files(
            processed_files,
            folder_id,
            files,
        )

    def _record_processed_file(
        self, processed_files: DatabaseInterface, folder: dict, file_result: FileResult
    ) -> None:
        """Record a successfully processed file in the database.

        Uses the dataset API (find_one / insert / update) so this method
        works against any processed_files implementation, including
        in-memory mocks without a raw_connection.
        """
        folder_id = (
            folder.get("id") if folder.get("id") is not None else folder.get("old_id")
        )

        sent_to_str = ", ".join(self._detect_enabled_backends(folder)) or "N/A"
        invoice_numbers = self._extract_invoice_numbers(file_result.file_name)
        file_mtime = self._get_file_mtime(file_result.file_name)
        now = datetime.datetime.now().isoformat()

        # Check if it was marked for resend (match by name and folder)
        existing = processed_files.find_one(
            file_name=file_result.file_name,
            folder_id=folder_id,
            resend_flag=1,
        )

        if existing:
            # Clear resend flag for this specific record
            processed_files.update(
                {
                    "id": existing["id"],
                    "resend_flag": 0,
                    "processed_at": now,
                    "sent_to": sent_to_str,
                    "status": "processed",
                    "invoice_numbers": invoice_numbers,
                    "file_mtime": file_mtime,
                },
                keys=["id"],
            )
        else:
            # Insert new record
            processed_files.insert(
                {
                    "file_name": file_result.file_name,
                    "folder_id": folder_id,
                    "folder_alias": folder.get("alias", ""),
                    "file_checksum": file_result.checksum,
                    "processed_at": now,
                    "resend_flag": 0,
                    "sent_to": sent_to_str,
                    "status": "processed",
                    "invoice_numbers": invoice_numbers,
                    "file_mtime": file_mtime,
                }
            )

    @staticmethod
    def _get_file_mtime(file_path: str) -> float | None:
        """Get the modification time of a file, or None if unavailable."""
        try:
            return os.path.getmtime(file_path)
        except OSError:
            return None

    def _extract_invoice_numbers(self, file_path: str) -> str:
        """Extract invoice numbers from EDI A-records in a file."""

        return extract_invoice_numbers(file_path, self.config.file_system)

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
