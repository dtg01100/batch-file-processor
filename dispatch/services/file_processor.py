"""File Processor Service for EDI file processing.

This module provides a dedicated service for processing individual EDI files
through the validation, splitting, conversion, and sending pipeline. It handles:
- File checksum calculation
- Pipeline execution (validation, splitting, conversion)
- Temporary file management
- Send operations coordination
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Type-checking only: importing dispatch.pipeline at module level creates
    # a circular import (dispatch.results -> dispatch.services ->
    # file_processor -> dispatch.pipeline -> dispatch.results). The runtime
    # imports live inside _run_splitting. See docs/IMPORT_ARCHITECTURE.md.
    from dispatch.pipeline.splitter import SplitterResult

from core.structured_logging import (
    get_logger,
    get_or_create_correlation_id,
    log_file_operation,
)
from core.utils import normalize_bool
from core.utils.file_utils import calculate_file_checksum
from dispatch.file_utils import extract_invoice_numbers
from dispatch.interfaces import ErrorHandlerInterface, FileSystemInterface, RunLog
from dispatch.send_manager import SendManager

logger = get_logger(__name__)


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

    def record_validation_outcome(
        self,
        validated: bool,  # noqa: FBT001 - boolean flag is intentional (validation outcome)
        errors_or_file: Any,
    ) -> None:
        """Record validation outcome: set validated flag and append errors.

        Mutates self.validated and self.errors. Does NOT log or write to
        run_log — logging is the caller's responsibility.
        """
        self.validated = validated
        if not validated:
            if isinstance(errors_or_file, list):
                self.errors.extend(errors_or_file)
            else:
                self.errors.append(str(errors_or_file))


@dataclass
class ProcessingContext:
    """Per-file mutable processing state for pipeline execution.

    Attributes:
        folder: Folder configuration dictionary
        effective_folder: Effective folder configuration (after inheritance)
        settings: Application settings dictionary
        upc_dict: UPC dictionary for item lookups
        temp_dirs: List of temporary directories to clean up
        temp_files: List of temporary files to clean up

    """

    folder: dict
    effective_folder: dict
    settings: dict | None = None
    upc_dict: dict | None = None
    temp_dirs: list[str] = field(default_factory=list)
    temp_files: list[str] = field(default_factory=list)


class FileProcessor:
    """Service for processing individual EDI files.

    This service encapsulates all logic related to processing a single EDI file
    through the complete pipeline: validation, splitting, conversion, and sending
    to backends.

    Attributes:
        send_manager: Manager for backend send operations
        error_handler: Handler for error recording
        validator_step: Pipeline validator step
        splitter_step: Pipeline splitter step
        converter_step: Pipeline converter step
        file_system: File system interface (optional)

    Example:
        >>> processor = FileProcessor(send_manager, error_handler, config)
        >>> result = processor.process_file(file_path, folder, upc_dict)
        >>> if result.sent:
        ...     print(f"File {result.file_name} sent successfully")

    """

    def __init__(
        self,
        send_manager: SendManager,
        error_handler: ErrorHandlerInterface,
        validator_step: Any | None = None,
        splitter_step: Any | None = None,
        converter_step: Any | None = None,
        file_system: FileSystemInterface | None = None,
        audit_logger: Any = None,
    ) -> None:
        """Initialize the file processor.

        Args:
            send_manager: Manager for backend send operations
            error_handler: Handler for error recording
            validator_step: Pipeline validator step
            splitter_step: Pipeline splitter step
            converter_step: Pipeline converter step
            file_system: Optional file system interface
            audit_logger: Optional audit logger for event recording

        """
        self.send_manager = send_manager
        self.error_handler = error_handler
        self.validator_step = validator_step
        self.splitter_step = splitter_step
        self.converter_step = converter_step
        self.file_system = file_system
        self._audit_logger = audit_logger

    def set_audit_logger(self, audit_logger: Any) -> None:
        """Set the audit logger for the file processor.

        Args:
            audit_logger: AuditLogger instance for event recording
        """
        self._audit_logger = audit_logger

    def process_file(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict,
        run_log: RunLog | None = None,
        effective_folder: dict | ProcessingContext | None = None,
    ) -> FileResult:
        """Process a single EDI file through the pipeline.

        Args:
            file_path: Path to the EDI file
            folder: Folder configuration dictionary
            upc_dict: UPC dictionary for lookups
            run_log: Optional run log for recording activity
            effective_folder:
                Pre-normalized folder dict; if omitted, folder is used as-is

        Returns:
            FileResult with processing outcome

        """
        correlation_id = get_or_create_correlation_id()
        result = FileResult(file_name=file_path, checksum="")
        context = self._build_context(
            folder=folder, upc_dict=upc_dict, effective_folder=effective_folder
        )
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
            self._execute_pipeline(
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
                context={
                    "folder_config": folder,
                    "correlation_id": correlation_id,
                    "file_path": file_path,
                },
            )

        finally:
            self._cleanup_temp_artifacts(context)

        return result

    def _build_context(
        self,
        folder: dict,
        upc_dict: dict,
        effective_folder: dict | ProcessingContext | None = None,
    ) -> ProcessingContext:
        """Build processing context for a file."""
        if isinstance(effective_folder, ProcessingContext):
            return effective_folder
        settings = (
            effective_folder.get("settings")
            if isinstance(effective_folder, dict)
            else {}
        )
        return ProcessingContext(
            folder=folder,
            effective_folder=effective_folder or folder,
            settings=settings,
            upc_dict=upc_dict,
        )

    def _execute_pipeline(
        self,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: RunLog | None,
    ) -> None:
        """Execute the core file processing pipeline.

        Args:
            file_path: Path to the file
            file_basename: File basename
            context: Processing context
            result: File result to update
            run_log: Run log for activity recording

        """
        import time

        result.checksum = calculate_file_checksum(file_path)
        logger.debug("Calculated checksum for %s: %s", file_basename, result.checksum)
        current_file = file_path

        correlation_id = get_or_create_correlation_id()
        folder_id = context.folder.get("id", 0)
        file_name = os.path.basename(file_path)

        # Run validation
        val_start = time.time()
        continue_processing, current_file = self._run_validation(
            current_file=current_file,
            context=context,
            result=result,
            _run_log=run_log,
            file_basename=file_basename,
        )
        val_duration = int((time.time() - val_start) * 1000)
        if self._audit_logger:
            validation_status = "success" if result.validated else "failure"
            validation_error = None
            if result.errors and not result.validated:
                validation_error = ValueError(result.errors[-1])
            self._audit_logger.log_step(
                correlation_id=correlation_id,
                folder_id=folder_id,
                file_name=file_name,
                step="validation",
                status=validation_status,
                duration_ms=val_duration,
                error=validation_error,
                input_path=file_path,
                output_path=current_file if current_file != file_path else None,
            )
        if not continue_processing:
            return

        # Run splitting
        split_start = time.time()
        split_outcome = self._run_splitting(
            current_file=current_file,
            _file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            _run_log=run_log,
        )
        split_duration = int((time.time() - split_start) * 1000)
        if self._audit_logger:
            split_output = (
                split_outcome.files[0][0]
                if split_outcome.files and split_outcome.files[0][0] != current_file
                else None
            )
            self._audit_logger.log_step(
                correlation_id=correlation_id,
                folder_id=folder_id,
                file_name=file_name,
                step="split",
                status="success" if split_outcome.was_split else "skipped",
                duration_ms=split_duration,
                input_path=current_file,
                output_path=split_output,
            )

        # When the file was split, convert and send each split output instead
        # of the original (which may be a multi-invoice file the receiver
        # cannot process as-is). Split outputs live in a temp dir tracked on
        # the context and are cleaned up by _cleanup_temp_artifacts.
        if self._handle_split_outputs(
            split_outcome=split_outcome,
            current_file=current_file,
            file_path=file_path,
            context=context,
            result=result,
            run_log=run_log,
            correlation_id=correlation_id,
            folder_id=folder_id,
            file_name=file_name,
        ):
            return

        # Without a split, the splitter may still have produced a single
        # category-filtered copy — send that instead of the original input.
        if split_outcome.files and split_outcome.files[0][0] != current_file:
            current_file = split_outcome.files[0][0]

        # Run conversion
        convert_start = time.time()
        current_file, conversion_failed = self._run_conversion(
            current_file=current_file,
            context=context,
            result=result,
            file_basename=file_basename,
        )
        convert_duration = int((time.time() - convert_start) * 1000)
        if self._audit_logger:
            convert_status = "failure" if conversion_failed else "success"
            self._audit_logger.log_step(
                correlation_id=correlation_id,
                folder_id=folder_id,
                file_name=file_name,
                step="convert",
                status=convert_status,
                duration_ms=convert_duration,
                input_path=file_path,
                output_path=current_file if current_file != file_path else None,
            )

        # If conversion failed (i.e., conversion was attempted but produced no output),
        # treat as error. However, when process_edi is False and convert_to_format
        # is not set, we expect the original file to be sent unchanged.
        process_edi_flag = normalize_bool(
            context.effective_folder.get("process_edi", False)
        )
        convert_format = context.effective_folder.get("convert_to_format", "")
        conversion_was_requested = process_edi_flag or bool(convert_format)
        if conversion_failed and conversion_was_requested:
            result.errors.append("No converted output was produced")
            result.sent = False
            return

        # Send to backends
        send_start = time.time()
        self._send_file(
            current_file=current_file,
            file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            run_log=run_log,
        )
        send_duration = int((time.time() - send_start) * 1000)
        if self._audit_logger:
            send_status = "success" if result.sent else "failure"
            self._audit_logger.log_step(
                correlation_id=correlation_id,
                folder_id=folder_id,
                file_name=file_name,
                step="send",
                status=send_status,
                duration_ms=send_duration,
                input_path=current_file,
            )

    def _run_conversion(
        self,
        current_file: str,
        context: ProcessingContext,
        result: FileResult,
        file_basename: str,
    ) -> tuple[str, bool]:
        """Run conversion step of the pipeline.

        Args:
            current_file: Current file path
            context: Processing context
            result: File result to update
            file_basename: File basename for logging

        Returns:
            Tuple of (current_file, conversion_failed)

        """
        if not self.converter_step or not result.validated:
            return current_file, False

        try:
            converted_file = self.converter_step.execute(
                current_file,
                context.effective_folder,
                context.settings,
                context.upc_dict,
                context=context,
            )
        except Exception as e:
            logger.exception("Conversion error for %s: %s", file_basename, e)
            return current_file, True

        if converted_file:
            logger.debug(
                "Conversion completed for %s: %s", file_basename, converted_file
            )
            result.converted = True
            return converted_file, False

        return current_file, True

    def _run_validation(
        self,
        current_file: str,
        context: ProcessingContext,
        result: FileResult,
        _run_log: RunLog | None,
        file_basename: str,
    ) -> tuple[bool, str]:
        """Run validation step of the pipeline.

        Args:
            current_file: Current file path
            context: Processing context
            result: File result
            run_log: Run log
            file_basename: File basename

        Returns:
            Tuple of (continue_processing, current_file)

        """
        if not self.validator_step:
            return True, current_file

        # Respect folder-level validation settings
        should_validate = any(
            normalize_bool(context.effective_folder.get(key, False))
            for key in ("process_edi", "split_edi", "force_edi_validation")
        )
        if not should_validate:
            return True, current_file

        try:
            validation_output = self.validator_step.execute(
                current_file,
                context.effective_folder,
            )
            return self._handle_validation_result(
                validation_output, current_file, file_basename, result, context
            )
        except Exception as e:
            return self._handle_validation_error(e, file_basename, result, current_file)

    def _handle_validation_result(
        self,
        validation_output: Any,
        current_file: str,
        file_basename: str,
        result: FileResult,
        context: ProcessingContext | None = None,
    ) -> tuple[bool, str]:
        """Handle validation step result.

        Args:
            validation_output: Output from validator
            current_file: Current file path
            file_basename: File basename
            result: File result to update
            context: Processing context (needed for force_edi_validation check)

        Returns:
            Tuple of (continue_processing, current_file)

        """
        from dispatch.pipeline.validator import normalize_validation_output

        is_valid, errors_or_file = normalize_validation_output(
            validation_output, current_file
        )

        result.validated = is_valid
        if not is_valid:
            logger.warning(
                "Validation failed for %s: %s", file_basename, errors_or_file
            )
            if isinstance(errors_or_file, list):
                result.errors.extend(str(e) for e in errors_or_file)
            elif isinstance(errors_or_file, str):
                result.errors.append(errors_or_file)
            # Check if we should force continue despite validation failure
            force_continue = False
            if context and context.effective_folder:
                force_continue = normalize_bool(
                    context.effective_folder.get("force_edi_validation", False)
                )
            if force_continue:
                return True, current_file
            return False, current_file

        new_file = errors_or_file if isinstance(errors_or_file, str) else current_file
        return True, new_file

    def _handle_validation_error(
        self,
        error: Exception,
        file_basename: str,
        result: FileResult,
        current_file: str,
    ) -> tuple[bool, str]:
        """Handle validation error.

        Args:
            error: Exception from validation
            file_basename: File basename
            result: File result to update
            current_file: Current file path

        Returns:
            Tuple of (continue_processing, current_file)

        """
        logger.exception("Validation error for %s: %s", file_basename, error)
        result.validated = False
        result.errors.append(str(error))
        return False, current_file

    def _run_splitting(
        self,
        current_file: str,
        _file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        _run_log: RunLog | None,
    ) -> "SplitterResult":
        """Run splitting step of the pipeline.

        Split outputs are written to a temp directory tracked on the
        processing context so the files remain on disk until they are sent;
        cleanup happens in ``_cleanup_temp_artifacts``.

        Args:
            current_file: Current file path
            file_path: Original file path
            file_basename: File basename
            context: Processing context
            result: File result
            run_log: Run log

        Returns:
            SplitterResult describing the split outcome. ``was_split`` is
            True when the input was split into multiple outputs; ``files``
            holds ``(path, prefix, suffix)`` tuples for the outputs.

        """
        # Function-local imports: importing dispatch.pipeline at module level
        # creates a circular import (dispatch.results -> dispatch.services ->
        # file_processor -> dispatch.pipeline -> dispatch.results).
        from dispatch.pipeline.splitter import SplitterResult
        from dispatch.pipeline.temp_dir_utils import create_pipeline_temp_dir

        if not self.splitter_step:
            return SplitterResult(files=[], was_split=False)

        temp_dir, _ = create_pipeline_temp_dir(
            "edi_split", context.effective_folder, context
        )

        try:
            split_result: SplitterResult = self.splitter_step.split(
                current_file,
                temp_dir,
                context.effective_folder,
                context.upc_dict or {},
            )
        except Exception as e:
            logger.exception("Splitting error for %s: %s", file_basename, e)
            result.errors.append(f"Splitting error: {e}")
            return SplitterResult(files=[], was_split=False, errors=[str(e)])

        if split_result.was_split:
            logger.info(
                "File %s was split into %d files",
                file_basename,
                len(split_result.files),
            )
        else:
            logger.debug(
                "File %s was not split (was_filtered=%s)",
                file_basename,
                split_result.was_filtered,
            )
        return split_result

    def _handle_split_outputs(
        self,
        split_outcome: "SplitterResult",
        current_file: str,
        file_path: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: RunLog | None,
        *,
        correlation_id: str,
        folder_id: int,
        file_name: str,
    ) -> bool:
        """Send split outputs when a split occurred, logging the send step.

        Returns:
            True when the file was split and its outputs were sent (the
            pipeline should stop); False when no split occurred.

        """
        import time

        if not split_outcome.was_split:
            return False

        send_start = time.time()
        self._send_split_files(
            split_files=split_outcome.files or [(current_file, "", "")],
            context=context,
            result=result,
            run_log=run_log,
        )
        send_duration = int((time.time() - send_start) * 1000)
        if self._audit_logger:
            send_status = "success" if result.sent else "failure"
            self._audit_logger.log_step(
                correlation_id=correlation_id,
                folder_id=folder_id,
                file_name=file_name,
                step="send",
                status=send_status,
                duration_ms=send_duration,
                input_path=file_path,
            )
        return True

    def _send_split_files(
        self,
        split_files: list[tuple[str, str, str]],
        context: ProcessingContext,
        result: FileResult,
        run_log: RunLog | None,
    ) -> None:
        """Convert (if enabled) and send each split output file.

        Aggregates the send outcome across all split files into
        ``result.sent``. Conversion is applied per split file when a
        converter step is configured and validation passed.

        Args:
            split_files: List of (path, prefix, suffix) split outputs
            context: Processing context
            result: File result
            run_log: Run log

        """
        all_sends_succeeded = True
        for split_path, _prefix, _suffix in split_files:
            pipeline_file = split_path
            if self.converter_step and result.validated:
                try:
                    converted_file = self.converter_step.execute(
                        pipeline_file,
                        context.effective_folder,
                        context.settings,
                        context.upc_dict,
                        context=context,
                    )
                except Exception as e:
                    logger.exception(
                        "Conversion error for split file %s: %s", pipeline_file, e
                    )
                    converted_file = None
                if converted_file:
                    result.converted = True
                    pipeline_file = converted_file

            send_ok = self._send_file(
                current_file=pipeline_file,
                file_path=pipeline_file,
                file_basename=os.path.basename(pipeline_file),
                context=context,
                result=result,
                run_log=run_log,
            )
            if not send_ok:
                all_sends_succeeded = False

        result.sent = all_sends_succeeded

    def _send_file(
        self,
        current_file: str,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: RunLog | None,
    ) -> bool:
        """Send file to enabled backends.

        Args:
            current_file: Current file path
            file_path: Original file path
            file_basename: File basename
            context: Processing context
            result: File result
            run_log: Run log

        Returns:
            True if the send succeeded

        """
        enabled_backends = self.send_manager.get_enabled_backends(
            context.effective_folder
        )
        if not enabled_backends:
            result.sent = False
            result.errors.append("No backends enabled")
            return False

        # Apply file rename if configured
        from dispatch.file_utils import apply_file_rename as _ar

        _td = context.temp_dirs
        _tmpl = context.effective_folder.get("rename_file", "").strip()
        final_file = _ar(current_file, _tmpl, _td)

        # Send to backends
        result.sent = self._send_to_backends(
            file_path=final_file,
            folder=context.effective_folder,
            _run_log=run_log,
            settings=context.settings,
        )

        if not result.sent:
            # Preserve backend error details for diagnostics and audit coverage.
            if self.send_manager.errors:
                result.errors.extend(self.send_manager.errors.values())

            self._record_send_failure(
                result=result,
                file_basename=file_basename,
                current_file=current_file,
                _run_log=run_log,
            )
            return result.sent

        self._log_success(file_basename, file_path, run_log)
        return result.sent

    def _send_to_backends(
        self,
        file_path: str,
        folder: dict,
        _run_log: RunLog | None,
        settings: dict | None,
    ) -> bool:
        """Send file to all enabled backends via send_manager.

        Args:
            file_path: File to send
            folder: Folder configuration
            run_log: Run log
            settings: Global settings for backends

        Returns:
            True if all sends were successful

        """
        enabled_backends = self.send_manager.get_enabled_backends(folder)
        if not enabled_backends:
            return False
        effective_settings = settings if settings is not None else {}
        send_results = self.send_manager.send_all(
            enabled_backends, file_path, folder, effective_settings
        )
        return bool(send_results) and all(send_results.values())

    def _record_send_failure(
        self,
        result: FileResult,
        file_basename: str,
        current_file: str,
        _run_log: RunLog | None,
    ) -> None:
        """Record send failure.

        Args:
            result: File result
            file_basename: File basename
            current_file: Current file path
            run_log: Run log

        """
        result.errors.append(f"Failed to send {file_basename}")
        logger.warning("Failed to send file: %s", current_file)

    def _log_success(
        self, file_basename: str, file_path: str, _run_log: RunLog | None
    ) -> None:
        """Log successful processing.

        Args:
            file_basename: File basename
            file_path: Original file path
            run_log: Run log

        """
        invoice_numbers = self._extract_invoice_numbers(file_path)
        logger.info(
            "Successfully processed %s (invoices: %s)",
            file_basename,
            invoice_numbers or "unknown",
        )

    def _cleanup_temp_artifacts(self, context: ProcessingContext) -> None:
        """Clean up temporary directories and files.

        Args:
            context: Processing context with temp artifacts

        """
        for temp_dir in context.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.debug("Cleaned up temp directory: %s", temp_dir)
            except OSError as e:
                logger.warning("Failed to clean up temp dir %s: %s", temp_dir, e)

        for temp_file in context.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug("Cleaned up temp file: %s", temp_file)
            except OSError as e:
                logger.warning("Failed to clean up temp file %s: %s", temp_file, e)

        context.temp_dirs.clear()
        context.temp_files.clear()

    def _extract_invoice_numbers(self, file_path: str) -> str:
        """Extract invoice numbers from EDI A-records."""

        return extract_invoice_numbers(file_path, self.file_system)
