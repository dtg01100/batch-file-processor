"""Dispatch Orchestrator for coordinating file processing.

This module provides the main orchestration layer for dispatch operations,
coordinating validation, conversion, and sending of files.
"""

import datetime
import os
import shutil
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Optional

from core.database import LegacyQueryRunnerAdapter, create_query_runner
from core.structured_logging import (
    CorrelationContext,
    get_logger,
    get_or_create_correlation_id,
    log_backend_call,
    log_file_operation,
    log_with_context,
)
from core.utils.bool_utils import normalize_bool
from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler
from dispatch.feature_flags import get_strict_testing_mode
from dispatch.interfaces import (
    BackendInterface,
    DatabaseInterface,
    ErrorHandlerInterface,
    FileSystemInterface,
    ValidatorInterface,
)
from dispatch.send_manager import SendManager

logger = get_logger(__name__)


@dataclass
class DispatchConfig:
    """Configuration for the dispatch orchestrator.

    Attributes:
        database: Database interface for persistence
        file_system: File system interface for file operations
        backends: Dictionary of backend name to backend instance
        validator: EDI validator instance
        error_handler: Error handler instance
        settings: Global application settings
        version: Application version string
        upc_service: UPC service for dictionary fetching
        progress_reporter: Progress reporter
        validator_step: Pipeline validator step
        splitter_step: Pipeline splitter step
        converter_step: Pipeline converter step
        tweaker_step: Pipeline tweaker step
        file_processor: File processor service
        upc_dict: Cached UPC dictionary
    """

    database: Optional[DatabaseInterface] = None
    file_system: Optional[FileSystemInterface] = None
    backends: dict[str, BackendInterface] = field(default_factory=dict)
    validator: Optional[ValidatorInterface] = None
    error_handler: Optional[ErrorHandlerInterface] = None
    settings: dict = field(default_factory=dict)
    version: str = "1.0.0"
    upc_service: Optional[Any] = None
    progress_reporter: Optional[Any] = None
    validator_step: Optional[Any] = None
    splitter_step: Optional[Any] = None
    converter_step: Optional[Any] = None
    tweaker_step: Optional[Any] = None
    file_processor: Optional[Any] = None
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


@dataclass
class FileResult:
    """Result of processing a single file.

    Attributes:
        file_name: Name of the processed file
        checksum: MD5 checksum of the file
        sent: Whether the file was sent successfully
        validated: Whether validation passed
        converted: Whether conversion was applied
        errors: List of error messages
    """

    file_name: str
    checksum: str
    sent: bool = False
    validated: bool = True
    converted: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class ProcessingContext:
    """Per-file mutable processing state for pipeline execution."""

    folder: dict
    effective_folder: dict
    settings: dict
    upc_dict: dict
    temp_dirs: list[str] = field(default_factory=list)
    temp_files: list[str] = field(default_factory=list)


class DispatchOrchestrator:
    """Orchestrates the dispatch process for file processing.

    This class coordinates the processing of files across folders,
    managing validation, conversion, and sending operations.

    Attributes:
        config: Dispatch configuration
        send_manager: Manager for sending files to backends
        run_log: In-memory log of processing run
    """

    def __init__(self, config: DispatchConfig):
        """Initialize the dispatch orchestrator.

        Args:
            config: Dispatch configuration
        """
        self.config = config
        self.validator = config.validator or EDIValidator()
        self.send_manager = SendManager(backends=config.backends)
        self.error_handler = config.error_handler or ErrorHandler()
        self.run_log: StringIO = StringIO()
        self.processed_count: int = 0
        self.error_count: int = 0
        logger.debug(
            "DispatchOrchestrator initialized (pipeline_steps: "
            "validator=%s, splitter=%s, converter=%s, tweaker=%s)",
            bool(config.validator_step),
            bool(config.splitter_step),
            bool(config.converter_step),
            bool(config.tweaker_step),
        )

    def process_folder(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None,
        pre_discovered_files: Optional[list[str]] = None,
        folder_num: Optional[int] = None,
        folder_total: Optional[int] = None,
    ) -> FolderResult:
        """Process a single folder via the pipeline path.

        Args:
            folder: Folder configuration dictionary
            run_log: Run log for recording processing activity
            processed_files: Optional database of already processed files

        Returns:
            FolderResult with processing outcome
        """
        correlation_id = get_or_create_correlation_id()
        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        import logging

        log_with_context(
            logger,
            logging.INFO,
            f"Starting folder processing: {alias}",
            correlation_id=correlation_id,
            operation="process_folder",
            context={
                "folder_name": folder_path,
                "folder_alias": alias,
                "folder_num": folder_num,
                "folder_total": folder_total,
            },
        )

        with CorrelationContext(correlation_id):
            upc_dict = self._get_upc_dictionary(self.config.settings)
            return self.process_folder_with_pipeline(
                folder,
                run_log,
                processed_files,
                upc_dict,
                pre_discovered_files=pre_discovered_files,
                folder_num=folder_num,
                folder_total=folder_total,
            )

    def process_folder_with_pipeline(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None,
        upc_dict: Optional[dict] = None,
        pre_discovered_files: Optional[list[str]] = None,
        folder_num: Optional[int] = None,
        folder_total: Optional[int] = None,
    ) -> FolderResult:
        """Process folder using new pipeline steps.

        Args:
            folder: Folder configuration dictionary
            run_log: Run log for recording processing activity
            processed_files: Optional database of already processed files
            upc_dict: UPC dictionary for lookup

        Returns:
            FolderResult with processing outcome
        """
        result = FolderResult(
            folder_name=folder.get("folder_name", ""), alias=folder.get("alias", "")
        )

        folder_path = folder.get("folder_name", "")
        alias = folder.get("alias", folder_path)

        logger.debug("Processing folder: %s (path=%s)", alias, folder_path)

        self._log_message(run_log, f"entering folder: {alias}")

        if not self._folder_exists(folder_path):
            error_msg = f"Folder not found: {folder_path}"
            result.errors.append(error_msg)
            result.success = False
            result.files_failed = 1
            self._log_error(run_log, error_msg)
            return result

        files = list(pre_discovered_files) if pre_discovered_files is not None else None

        if files is None:
            files = self._get_files_in_folder(folder_path)

            if not files:
                self._log_message(run_log, f"No files in directory: {folder_path}")
                return result

            logger.debug(
                "Found %d files in %s, filtering for already-processed...",
                len(files),
                folder_path,
            )

            if processed_files:
                files = self._filter_processed_files(files, processed_files, folder)

        logger.debug("After filter: %d files to process in %s", len(files), folder_path)

        if not files:
            self._log_message(run_log, f"No new files in directory: {folder_path}")
            return result

        self._log_message(
            run_log, f"{len(files)} found in {folder_path} (pipeline mode)"
        )

        total_files = len(files)
        if self.config.progress_reporter:
            progress = self.config.progress_reporter
            if hasattr(progress, "start_folder"):
                try:
                    progress.start_folder(
                        folder.get("alias", folder_path),
                        total_files,
                        folder_num=folder_num,
                        folder_total=folder_total,
                    )
                except TypeError:
                    # Backward compatibility for callbacks that only accept
                    # (folder_name, total_files).
                    progress.start_folder(folder.get("alias", folder_path), total_files)

        effective_upc_dict = upc_dict if upc_dict is not None else self.config.upc_dict

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

    def discover_pending_files(
        self,
        folders: list[dict],
        processed_files: Optional[DatabaseInterface] = None,
        progress_reporter: Optional[Any] = None,
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
        folder_total = len(folders)
        pending_lists: list[list[str]] = []
        total_pending = 0

        if progress_reporter and hasattr(progress_reporter, "start_discovery"):
            progress_reporter.start_discovery(folder_total=folder_total)

        for folder_index, folder in enumerate(folders, start=1):
            folder_path = folder.get("folder_name", "")
            alias = folder.get("alias", folder_path)

            if not self._folder_exists(folder_path):
                pending: list[str] = []
            else:
                pending = self._get_files_in_folder(folder_path)
                if processed_files and pending:
                    pending = self._filter_processed_files(
                        pending,
                        processed_files,
                        folder,
                    )

            pending_lists.append(pending)
            total_pending += len(pending)

            if progress_reporter and hasattr(
                progress_reporter, "update_discovery_progress"
            ):
                progress_reporter.update_discovery_progress(
                    folder_num=folder_index,
                    folder_total=folder_total,
                    folder_name=alias,
                    pending_for_folder=len(pending),
                    pending_total=total_pending,
                )

        if progress_reporter and hasattr(progress_reporter, "finish_discovery"):
            progress_reporter.finish_discovery(total_pending=total_pending)

        return pending_lists, total_pending

    def _process_folder_files(
        self,
        files: list[str],
        folder: dict,
        effective_upc_dict: dict,
        processed_files: Optional[DatabaseInterface],
        run_log: Any,
        result: FolderResult,
        total_files: int,
    ) -> None:
        """Process all files in folder and update result counters in place."""
        for idx, file_path in enumerate(files):
            if self.config.progress_reporter:
                self.config.progress_reporter.update_file(idx + 1, total_files)

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
        """Finalize folder result and notify progress reporter."""
        result.success = result.files_failed == 0
        if self.config.progress_reporter:
            self.config.progress_reporter.complete_folder(result.success)

    @staticmethod
    def _is_strict_database_lookup(settings: dict) -> bool:
        """Return True when database lookup mode requires fail-fast behavior."""
        mode = str(settings.get("database_lookup_mode", "optional")).strip().lower()
        return mode in {"strict", "required", "test"}

    def _get_upc_dictionary(self, settings: dict) -> dict:
        """Get or fetch UPC dictionary.

        Args:
            settings: Application settings

        Returns:
            UPC dictionary (may be empty if initialization fails)
        """
        logger.debug("Fetching UPC dictionary (cached=%s)", bool(self.config.upc_dict))
        strict_db_mode = self._is_strict_database_lookup(settings)
        strict_testing_mode = get_strict_testing_mode()

        if self.config.upc_dict:
            return self.config.upc_dict

        if self.config.upc_service:
            try:
                upc_dict = self.config.upc_service.get_dictionary()
                if upc_dict:
                    self.config.upc_dict = upc_dict
                    logger.debug("UPC dictionary loaded: %d entries", len(upc_dict))
                    return upc_dict
            except Exception as exc:
                if strict_db_mode:
                    raise
                if strict_testing_mode:
                    raise RuntimeError(
                        "Failed to fetch UPC dictionary from upc_service"
                    ) from exc
                logger.exception("Failed to fetch UPC dictionary from upc_service")

        # Backward-compatible fallback for app/runtime usage where no explicit
        # upc_service is injected into DispatchConfig.
        fallback_dict = self._fetch_upc_dictionary_from_settings(settings)
        if fallback_dict:
            self.config.upc_dict = fallback_dict
            logger.debug(
                "UPC dictionary loaded via fallback query: %d entries",
                len(fallback_dict),
            )
            return fallback_dict

        # UPC dict could not be loaded - converters needing UPC data will fail
        # silently or produce degraded output
        logger.warning(
            "UPC dictionary is empty: no service configured and fallback query "
            "failed (check AS400 credentials in settings)"
        )
        if strict_db_mode:
            raise RuntimeError(
                "database_lookup_mode is strict but UPC dictionary could not be loaded"
            )
        return {}

    def _parse_upc_query_rows(
        self, rows: list[Any], strict_testing_mode: bool
    ) -> dict[int, list[Any]]:
        """Build UPC lookup data from raw query rows."""
        upc_dict = {}
        for row in rows:
            try:
                item_number = int(row[0])
                upc_dict[item_number] = [row[1], row[2], row[3], row[4], row[5]]
            except (TypeError, ValueError, IndexError) as exc:
                if strict_testing_mode:
                    raise RuntimeError(
                        f"Malformed UPC row returned from fallback query: {row!r}"
                    ) from exc
                continue
        return upc_dict

    def _close_legacy_upc_runner(
        self, legacy_runner: Any, strict_testing_mode: bool
    ) -> None:
        """Close legacy UPC query runner, surfacing failures in strict mode."""
        try:
            # legacy wrapper keeps the new-style runner in _runner
            legacy_runner._runner.close()
        except Exception as exc:
            if strict_testing_mode:
                raise RuntimeError("Failed to close legacy UPC query runner") from exc

    def _fetch_upc_dictionary_from_settings(self, settings: dict) -> dict:
        """Fetch UPC dictionary directly from AS400 using app settings.

        This mirrors legacy dispatch behavior and serves as a fallback path when
        no ``upc_service`` is configured in ``DispatchConfig``.
        """
        required_keys = (
            "as400_username",
            "as400_password",
            "as400_address",
            "odbc_driver",
        )
        strict_db_mode = self._is_strict_database_lookup(settings)
        strict_testing_mode = get_strict_testing_mode()
        missing_keys = [key for key in required_keys if not settings.get(key)]
        if missing_keys:
            if strict_db_mode:
                raise ValueError(
                    "database_lookup_mode is strict but AS400 settings are missing: "
                    + ", ".join(missing_keys)
                )
            logger.warning(
                "Cannot fetch UPC dictionary: missing AS400 credentials (%s)",
                ", ".join(missing_keys),
            )
            return {}

        runner = create_query_runner(
            username=settings["as400_username"],
            password=settings["as400_password"],
            dsn=settings["as400_address"],
            database="QGPL",
            odbc_driver=settings["odbc_driver"],
        )
        legacy_runner = LegacyQueryRunnerAdapter(runner)

        try:
            rows = legacy_runner.run_arbitrary_query(
                """
                select
                    dsanrep.anbacd,
                    dsanrep.anbbcd,
                    strip(dsanrep.anbgcd),
                    strip(dsanrep.anbhcd),
                    strip(dsanrep.anbicd),
                    strip(dsanrep.anbjcd)
                from dacdata.dsanrep dsanrep
                """
            )

            if strict_db_mode and not rows:
                raise LookupError(
                    "database_lookup_mode is strict but UPC query returned no rows"
                )

            return self._parse_upc_query_rows(rows, strict_testing_mode)
        except Exception as exc:
            if strict_db_mode:
                raise
            # Preserve RuntimeError messages that already have specific context
            if strict_testing_mode:
                if isinstance(exc, RuntimeError) and "Malformed UPC row" in str(exc):
                    raise
                raise RuntimeError(
                    "Failed to fetch UPC dictionary via fallback query"
                ) from exc
            logger.exception("Failed to fetch UPC dictionary via fallback query")
            return {}
        finally:
            self._close_legacy_upc_runner(legacy_runner, strict_testing_mode)

    def _process_file_with_pipeline(
        self, file_path: str, folder: dict, upc_dict: dict, run_log: Any = None
    ) -> FileResult:
        """Process single file with pipeline.

        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary
            upc_dict: UPC dictionary for lookup
            run_log: Optional run log for recording processing activity

        Returns:
            FileResult with processing outcome
        """
        import os

        correlation_id = get_or_create_correlation_id()
        result = FileResult(file_name=file_path, checksum="")
        context = self._build_processing_context(folder=folder, upc_dict=upc_dict)
        file_basename = os.path.basename(file_path)

        log_file_operation(
            logger,
            "process",
            file_path,
            correlation_id=correlation_id,
            file_type="edi",
        )
        logger.debug("Processing file: %s", file_basename)

        try:
            self._execute_file_pipeline(
                file_path=file_path,
                file_basename=file_basename,
                context=context,
                result=result,
                run_log=run_log,
            )

        except Exception as e:
            result.errors.append(str(e))
            self.error_handler.record_error(
                folder=folder.get("folder_name", ""),
                filename=file_path,
                error=e,
                context={"folder_config": folder, "pipeline_mode": True},
            )

        finally:
            self._cleanup_temp_artifacts(context)

        return result

    def _execute_file_pipeline(
        self,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> None:
        """Execute core file pipeline and update result in place."""
        result.checksum = self._calculate_checksum(file_path)
        logger.debug("Calculated checksum for %s: %s", file_basename, result.checksum)
        current_file = file_path

        continue_processing, current_file = self._run_validation_pipeline(
            current_file=current_file,
            context=context,
            result=result,
            run_log=run_log,
            file_basename=file_basename,
        )
        if not continue_processing:
            return

        if self._process_split_pipeline(
            current_file=current_file,
            file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            run_log=run_log,
        ):
            return

        current_file, did_convert = self._apply_conversion_and_tweaks(
            current_file=current_file,
            file_basename=file_basename,
            original_file_path=file_path,
            context=context,
            run_log=run_log,
            validation_passed=result.validated,
        )
        if did_convert:
            result.converted = True

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
            except Exception as exc:
                if strict_testing_mode:
                    cleanup_errors.append(
                        f"directory '{temp_dir}' could not be removed: {exc}"
                    )

        for temp_file in context.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as exc:
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
        split_edi = context.effective_folder.get("split_edi", False)
        logger.debug(
            "Splitter step: enabled=%s, split_edi=%s",
            bool(self.config.splitter_step),
            split_edi,
        )
        if not (self.config.splitter_step and split_edi):
            return False

        import tempfile

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
                current_pipeline_file, did_convert = self._apply_conversion_and_tweaks(
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
                    f"Failed to send split file via {backend_name}: {error_message}"
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
                    f"Failed to send file via {backend_name}: {error_message}"
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
            bool(self.config.validator_step or self.config.validator),
            should_validate,
        )

        if not should_validate:
            return True, current_file

        if self.config.validator_step:
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

        if self.config.validator:
            is_valid, errors_or_file = self.config.validator.validate(current_file)
            return self._apply_validation_outcome(
                is_valid=is_valid,
                errors_or_file=errors_or_file,
                current_file=current_file,
                result=result,
                run_log=run_log,
                file_basename=file_basename,
                context=context,
            )

        return True, current_file

    def _apply_conversion_and_tweaks(
        self,
        current_file: str,
        file_basename: str,
        original_file_path: str,
        context: ProcessingContext,
        run_log: Any,
        validation_passed: bool = True,
    ) -> tuple[str, bool]:
        """Apply converter and tweaker steps for a single file path.

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
        tweak_edi = context.effective_folder.get("tweak_edi", False)
        run_conversion = converter_step is not None and (
            convert_edi or (tweak_edi and validation_passed)
        )

        logger.debug(
            "Converter step: enabled=%s, convert_edi=%s, tweak_edi=%s",
            bool(converter_step),
            convert_edi,
            tweak_edi,
        )

        if run_conversion:
            convert_format = context.effective_folder.get(
                "convert_to_format", "unknown"
            )
            self._log_message(
                run_log,
                f"Converting {file_basename} to {convert_format}"
                if convert_edi
                else f"Applying tweaks to {file_basename}",
            )
            converted_file = converter_step.execute(
                current_file,
                context.effective_folder,
                context.settings,
                context.upc_dict,
                context=context,
            )
            if converted_file:
                if converted_file != original_file_path:
                    context.temp_files.append(converted_file)
                current_file = converted_file
                did_convert = True

        return current_file, did_convert

    def _normalize_validation_output(
        self,
        validation_output: Any,
        current_file: str,
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

        return bool(validation_output), current_file

    def _apply_validation_outcome(
        self,
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

        if not context.effective_folder.get("force_edi_validation", False):
            return False, current_file

        return True, current_file

    # Defaults for folder configuration fields that may be NULL in the database.
    # These mirror the defaults applied by app.py when opening the edit dialog.
    _FOLDER_DEFAULTS: dict = {
        "ftp_port": 21,
        "a_record_padding": "",
        "a_record_padding_length": 6,
        "a_record_append_text": "",
        "invoice_date_offset": 0,
        "invoice_date_custom_format": False,
        "invoice_date_custom_format_string": "%Y%m%d",
        "override_upc_level": 1,
        "override_upc_category_filter": "",
        "upc_target_length": 11,
        "upc_padding_pattern": "           ",
        "simple_csv_sort_order": "",
        "split_edi_filter_categories": "ALL",
        "split_edi_filter_mode": "include",
        "rename_file": "",
        "convert_to_format": "",
        "estore_store_number": "",
        "estore_Vendor_OId": "",
        "estore_vendor_NameVendorOID": "",
        "estore_c_record_OID": "",
        "fintech_division_id": "",
        # Boolean tweak fields -- accessed via direct dict key in archive/edi_tweaks.py;
        # must default to False so missing/NULL DB values don't raise KeyError.
        "pad_a_records": False,
        "append_a_records": False,
        "force_txt_file_ext": False,
        "calculate_upc_check_digit": False,
        "retail_uom": False,
        "override_upc_bool": False,
        "split_prepaid_sales_tax_crec": False,
    }

    def _build_processing_context(
        self, folder: dict, upc_dict: dict
    ) -> ProcessingContext:
        """Build non-mutating per-file processing context."""
        effective_folder = folder.copy()

        # Apply defaults for fields that may be NULL in the database.
        for key, default in self._FOLDER_DEFAULTS.items():
            if effective_folder.get(key) is None:
                effective_folder[key] = default

        # upc_target_length of 0 is not meaningful -- treat as default (11).
        if not effective_folder.get("upc_target_length"):
            effective_folder["upc_target_length"] = self._FOLDER_DEFAULTS[
                "upc_target_length"
            ]

        # Map DB field process_edi → convert_edi (orchestrator's internal gate).
        # The database stores process_edi=True to mean "convert EDI to another format".
        # The orchestrator uses convert_edi to gate the converter step.
        if "convert_edi" not in effective_folder:
            effective_folder["convert_edi"] = normalize_bool(
                effective_folder.get("process_edi", False)
            )

        if "process_edi" not in effective_folder and (
            effective_folder.get("split_edi", False)
            or effective_folder.get("convert_edi", False)
            or effective_folder.get("tweak_edi", False)
        ):
            effective_folder["process_edi"] = True

        return ProcessingContext(
            folder=folder,
            effective_folder=effective_folder,
            settings=self.config.settings,
            upc_dict=upc_dict,
        )

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
        import datetime
        import os
        import re
        import shutil
        import tempfile

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

        dest_path = os.path.join(temp_dir, new_name)
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
        import os

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

        import logging

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

        import os

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

        import os

        if not os.path.isdir(path):
            return []

        return [
            os.path.abspath(os.path.join(path, f))
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
        ]

    def _filter_processed_files(
        self, files: list[str], processed_files: DatabaseInterface, folder: dict
    ) -> list[str]:
        """Filter out already processed files, unless marked for resend.

        Args:
            files: List of file paths
            processed_files: Database of processed files
            folder: Folder configuration

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

        return [
            f for f in files if self._calculate_checksum(f) not in skipped_checksums
        ]

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
        sent_to = []
        if folder.get("process_backend_copy"):
            sent_to.append(f"Copy: {folder.get('copy_to_directory', 'N/A')}")
        if folder.get("process_backend_ftp"):
            sent_to.append(f"FTP: {folder.get('ftp_server', 'N/A')}")
        if folder.get("process_backend_email"):
            sent_to.append(f"Email: {folder.get('email_to', 'N/A')}")
        sent_to_str = ", ".join(sent_to) if sent_to else "N/A"

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
        import hashlib

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
            from core.edi.edi_parser import capture_records

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

            seen = []
            seen_set = set()
            for line in content.splitlines():
                try:
                    rec = capture_records(line)
                    if rec and rec.get("record_type") == "A":
                        inv_num = rec["invoice_number"].strip()
                        if inv_num and inv_num not in seen_set:
                            seen.append(inv_num)
                            seen_set.add(inv_num)
                except Exception:
                    continue

            return ", ".join(seen)
        except Exception:
            logger.exception("Failed to extract invoice numbers from %s", file_path)
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
            or folder.get("tweak_edi", False)
            or folder.get("split_edi", False)
            or folder.get("force_edi_validation", False)
        )

    def _log_message(self, run_log: Any, message: str) -> None:
        """Log a message to the run log and Python logger.

        Args:
            run_log: Run log to write to
            message: Message to log
        """
        import logging

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
            message: Error message to log
        """
        import logging

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
            database_connection: Database connection (not used directly, kept for compatibility)
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
        from dispatch.pipeline.converter import EDIConverterStep
        from dispatch.pipeline.splitter import EDISplitterStep
        from dispatch.pipeline.tweaker import EDITweakerStep
        from dispatch.pipeline.validator import EDIValidationStep

        # Create orchestrator config
        config = DispatchConfig(
            database=folders_database,
            settings=settings,
            version=version,
            progress_reporter=progress_callback,
            validator_step=EDIValidationStep(),
            splitter_step=EDISplitterStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )

        orchestrator = DispatchOrchestrator(config)

        # Get all active folders
        folders = list(folders_database.find(folder_is_active=True, order_by="alias"))

        logger.debug("Starting dispatch process for %d active folders", len(folders))

        has_errors = False

        for folder in folders:
            try:
                result = orchestrator.process_folder(folder, run_log, processed_files)
                if not result.success:
                    has_errors = True
            except Exception as folder_error:
                has_errors = True
                if hasattr(run_log, "write"):
                    run_log.write(
                        f"ERROR processing folder {folder.get('alias', 'unknown')}: {folder_error}\r\n".encode()
                    )

        summary = orchestrator.get_summary()
        logger.info("Dispatch complete: %s", summary)
        return has_errors, summary
