"""Dispatch Orchestrator for coordinating file processing.

This module provides the main orchestration layer for dispatch operations,
coordinating validation, conversion, and sending of files.
"""

from dataclasses import dataclass, field
import datetime
import logging
from io import StringIO
from typing import Any, Optional

from dispatch.interfaces import (
    DatabaseInterface,
    FileSystemInterface,
    BackendInterface,
    ValidatorInterface,
    ErrorHandlerInterface,
)
from dispatch.edi_validator import EDIValidator
from dispatch.send_manager import SendManager
from dispatch.error_handler import ErrorHandler
from core.utils.bool_utils import normalize_bool

logger = logging.getLogger("dispatch.orchestrator")


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
    # Deprecated: pipeline mode is always enabled in Phase 3.
    # Retained only for config compatibility with existing callers.
    use_pipeline: bool = True


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

    def _initialize_pipeline_steps(self) -> None:
        """Initialize optional integration hooks.

        Kept for compatibility with older tests/callers.
        """
        if self.config.file_processor and hasattr(
            self.config.file_processor, "initialize"
        ):
            self.config.file_processor.initialize()

    def _is_pipeline_ready(self) -> bool:
        """Phase 3 compatibility shim.

        Pipeline path is now the only runtime path.
        """
        return True

    def _process_folder_legacy(self, folder, run_log, processed_files=None):
        """Deprecated shim that delegates to the pipeline path."""
        upc_dict = self._get_upc_dictionary(self.config.settings)
        return self.process_folder_with_pipeline(
            folder, run_log, processed_files, upc_dict
        )

    def _process_file_legacy(self, file_path, folder):
        """Deprecated shim that delegates to the pipeline path."""
        upc_dict = self._get_upc_dictionary(self.config.settings)
        return self._process_file_with_pipeline(file_path, folder, upc_dict)

    def process_folder(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None,
    ) -> FolderResult:
        """Process a single folder via the pipeline path.

        Args:
            folder: Folder configuration dictionary
            run_log: Run log for recording processing activity
            processed_files: Optional database of already processed files

        Returns:
            FolderResult with processing outcome
        """
        upc_dict = self._get_upc_dictionary(self.config.settings)
        return self.process_folder_with_pipeline(
            folder, run_log, processed_files, upc_dict
        )

    def process_folder_with_pipeline(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None,
        upc_dict: Optional[dict] = None,
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

        self._log_message(run_log, f"entering folder: {alias}")

        if not self._folder_exists(folder_path):
            error_msg = f"Folder not found: {folder_path}"
            result.errors.append(error_msg)
            result.success = False
            result.files_failed = 1
            self._log_error(run_log, error_msg)
            return result

        files = self._get_files_in_folder(folder_path)

        if not files:
            self._log_message(run_log, f"No files in directory: {folder_path}")
            return result

        if processed_files:
            files = self._filter_processed_files(files, processed_files, folder)

        if not files:
            self._log_message(run_log, f"No new files in directory: {folder_path}")
            return result

        self._log_message(
            run_log, f"{len(files)} found in {folder_path} (pipeline mode)"
        )

        total_files = len(files)
        if self.config.progress_reporter:
            self.config.progress_reporter.start_folder(
                folder.get("alias", folder_path), total_files
            )

        effective_upc_dict = upc_dict if upc_dict is not None else self.config.upc_dict

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

        result.success = result.files_failed == 0

        if self.config.progress_reporter:
            self.config.progress_reporter.complete_folder(result.success)

        return result

    def _get_upc_dictionary(self, settings: dict) -> dict:
        """Get or fetch UPC dictionary.

        Args:
            settings: Application settings

        Returns:
            UPC dictionary
        """
        if self.config.upc_dict:
            return self.config.upc_dict

        if self.config.upc_service:
            try:
                upc_dict = self.config.upc_service.get_dictionary()
                if upc_dict:
                    self.config.upc_dict = upc_dict
                    return upc_dict
            except Exception:
                pass

        return {}

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
        import shutil

        result = FileResult(file_name=file_path, checksum="")
        context = self._build_processing_context(folder=folder, upc_dict=upc_dict)
        file_basename = os.path.basename(file_path)

        try:
            result.checksum = self._calculate_checksum(file_path)
            current_file = file_path

            # Support both legacy validator and new validator_step
            # Determine which interface to use based on which config field is set
            if self.config.validator_step and self._should_validate(
                context.effective_folder
            ):
                # New pipeline interface
                validation_result = self.config.validator_step.execute(
                    current_file, context.effective_folder
                )
                # Handle both tuple return (old) and ValidationResult object (new)
                if isinstance(validation_result, tuple):
                    is_valid, errors_or_file = validation_result
                else:
                    from dispatch.pipeline.validator import ValidationResult

                    if isinstance(validation_result, ValidationResult):
                        is_valid = validation_result.is_valid
                        errors_or_file = (
                            validation_result.errors
                            if not validation_result.is_valid
                            else current_file
                        )
                    else:
                        is_valid = bool(validation_result)
                        errors_or_file = current_file

                result.validated = is_valid

                if not is_valid:
                    if isinstance(errors_or_file, list):
                        result.errors.extend(errors_or_file)
                    else:
                        result.errors.append(str(errors_or_file))

                    self._log_message(
                        run_log,
                        f"Validation failed for {file_basename}: {result.errors}",
                    )

                    if not context.effective_folder.get("force_edi_validation", False):
                        return result
                elif isinstance(errors_or_file, str):
                    current_file = errors_or_file
            elif self.config.validator and self._should_validate(
                context.effective_folder
            ):
                # Legacy interface
                is_valid, errors_or_file = self.config.validator.validate(current_file)
                result.validated = is_valid

                if not is_valid:
                    if isinstance(errors_or_file, list):
                        result.errors.extend(errors_or_file)
                    else:
                        result.errors.append(str(errors_or_file))

                    self._log_message(
                        run_log,
                        f"Validation failed for {file_basename}: {result.errors}",
                    )

                    if not context.effective_folder.get("force_edi_validation", False):
                        return result
                elif isinstance(errors_or_file, str):
                    current_file = errors_or_file

            files_to_send = [current_file]

            if self.config.splitter_step and context.effective_folder.get(
                "split_edi", False
            ):
                import tempfile

                with tempfile.TemporaryDirectory() as temp_dir:
                    split_result = self.config.splitter_step.split(
                        current_file,
                        temp_dir,
                        context.effective_folder,
                        context.upc_dict,
                    )
                    if hasattr(split_result, "files"):
                        split_files = [f[0] for f in split_result.files]
                    else:
                        split_files = split_result

                    if split_files and isinstance(split_files, list):
                        files_to_send = split_files

                    for pipeline_file in files_to_send:
                        current_pipeline_file = pipeline_file

                        converter_step = self.config.converter_step
                        if converter_step is not None and context.effective_folder.get(
                            "convert_edi", False
                        ):
                            convert_format = context.effective_folder.get(
                                "convert_to_format", "unknown"
                            )
                            self._log_message(
                                run_log,
                                f"Converting {file_basename} to {convert_format}",
                            )
                            converted_file = converter_step.execute(
                                current_pipeline_file,
                                context.effective_folder,
                                context.settings,
                                context.upc_dict,
                                context=context,
                            )
                            if converted_file:
                                # Track temp files created by converter (mkstemp persistent files)
                                if converted_file != file_path:
                                    context.temp_files.append(converted_file)
                                current_pipeline_file = converted_file
                                result.converted = True

                        tweaker_step = self.config.tweaker_step
                        if tweaker_step is not None and context.effective_folder.get(
                            "tweak_edi", False
                        ):
                            self._log_message(
                                run_log,
                                f"Applying tweaks to {file_basename}",
                            )
                            tweaked_file = tweaker_step.execute(
                                current_pipeline_file,
                                context.effective_folder,
                                context.upc_dict,
                                context.settings,
                                context=context,
                            )
                            if tweaked_file:
                                # Track temp files created by tweaker (mkstemp)
                                if tweaked_file != file_path:
                                    context.temp_files.append(tweaked_file)
                                current_pipeline_file = tweaked_file

                        send_result = self._send_pipeline_file(
                            current_pipeline_file, context.effective_folder, run_log
                        )
                        if not send_result:
                            send_errors = self.send_manager.get_errors()
                            if send_errors:
                                for backend_name, error_message in send_errors.items():
                                    result.errors.append(
                                        f"Failed to send split file via {backend_name}: {error_message}"
                                    )
                            else:
                                result.errors.append(
                                    f"Failed to send split file: {current_pipeline_file}"
                                )

                    result.sent = len(result.errors) == 0
                    if result.sent:
                        self._log_message(run_log, f"Success: {file_basename}")
                    return result

            converter_step = self.config.converter_step
            if converter_step is not None and context.effective_folder.get(
                "convert_edi", False
            ):
                convert_format = context.effective_folder.get(
                    "convert_to_format", "unknown"
                )
                self._log_message(
                    run_log,
                    f"Converting {file_basename} to {convert_format}",
                )
                converted_file = converter_step.execute(
                    current_file,
                    context.effective_folder,
                    context.settings,
                    context.upc_dict,
                    context=context,
                )
                if converted_file:
                    # Track temp files created by converter (mkstemp persistent files)
                    if converted_file != file_path:
                        context.temp_files.append(converted_file)
                    current_file = converted_file
                    result.converted = True

            tweaker_step = self.config.tweaker_step
            if tweaker_step is not None and context.effective_folder.get(
                "tweak_edi", False
            ):
                self._log_message(
                    run_log,
                    f"Applying tweaks to {file_basename}",
                )
                tweaked_file = tweaker_step.execute(
                    current_file,
                    context.effective_folder,
                    context.upc_dict,
                    context.settings,
                    context=context,
                )
                if tweaked_file:
                    # Track temp files created by tweaker (mkstemp)
                    if tweaked_file != file_path:
                        context.temp_files.append(tweaked_file)
                    current_file = tweaked_file

            # Check if any backends are enabled before attempting to send
            enabled_backends = self.send_manager.get_enabled_backends(
                context.effective_folder
            )
            if not enabled_backends:
                result.sent = False
                result.errors.append("No backends enabled")
            else:
                result.sent = self._send_pipeline_file(
                    current_file, context.effective_folder, run_log
                )

                if not result.sent:
                    send_errors = self.send_manager.get_errors()
                    if send_errors:
                        for backend_name, error_message in send_errors.items():
                            result.errors.append(
                                f"Failed to send file via {backend_name}: {error_message}"
                            )
                            self._log_message(
                                run_log,
                                f"FAILED sending {file_basename} via {backend_name}: {error_message}",
                            )
                    else:
                        result.errors.append(f"Failed to send file: {current_file}")
                        self._log_message(
                            run_log,
                            f"FAILED sending {file_basename}",
                        )
                else:
                    self._log_message(run_log, f"Success: {file_basename}")

        except Exception as e:
            result.errors.append(str(e))
            self.error_handler.record_error(
                folder=folder.get("folder_name", ""),
                filename=file_path,
                error=e,
                context={"folder_config": folder, "pipeline_mode": True},
            )

        finally:
            # Clean up temporary directories from pipeline steps (mkdtemp)
            for temp_dir in context.temp_dirs:
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass  # Best effort cleanup

            # Clean up temporary files created by pipeline steps (mkstemp)
            for temp_file in context.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass  # Best effort cleanup

        return result

    def _build_processing_context(
        self, folder: dict, upc_dict: dict
    ) -> ProcessingContext:
        """Build non-mutating per-file processing context."""
        effective_folder = folder.copy()
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

    def _send_pipeline_file(self, file_path: str, folder: dict, run_log: Any = None) -> bool:
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
            display_name = self.send_manager.DEFAULT_BACKENDS.get(
                backend_name, {}
            ).get("display_name", backend_name)
            self._log_message(
                run_log,
                f"sending {file_basename} to {display_name}",
            )

        settings = self.config.settings
        send_results = self.send_manager.send_all(
            enabled_backends, file_path, folder, settings
        )

        return all(send_results.values())

    def process_file(self, file_path: str, folder: dict) -> FileResult:
        """Process a single file via the pipeline path.

        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary

        Returns:
            FileResult with processing outcome
        """
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
                    "md5": file_result.checksum,
                    "processed_at": datetime.datetime.now().isoformat(),
                    "resend_flag": 0,
                    "sent_to": sent_to_str,
                    "status": "processed",
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

        if self.config.file_system:
            content = self.config.file_system.read_file(file_path)
        else:
            with open(file_path, "rb") as f:
                content = f.read()

        return hashlib.md5(content).hexdigest()

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
        logger.info(message)
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
        logger.error(f"ERROR: {message}")
        if hasattr(run_log, "write"):
            run_log.write((f"ERROR: {message}" + "\r\n").encode())
        elif hasattr(run_log, "append"):
            run_log.append(f"ERROR: {message}")

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
            use_pipeline=True,
            progress_reporter=progress_callback,
            validator_step=EDIValidationStep(),
            splitter_step=EDISplitterStep(),
            converter_step=EDIConverterStep(),
            tweaker_step=EDITweakerStep(),
        )

        orchestrator = DispatchOrchestrator(config)

        # Get UPC dictionary for category filtering
        upc_dict = orchestrator._get_upc_dictionary(settings)

        # Get all active folders
        folders = list(folders_database.find(folder_is_active=True, order_by="alias"))

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

        return has_errors, orchestrator.get_summary()
