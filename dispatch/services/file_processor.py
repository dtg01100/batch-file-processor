"""File Processor Service for EDI file processing.

This module provides a dedicated service for processing individual EDI files
through the validation, splitting, conversion, and sending pipeline. It handles:
- File checksum calculation
- Pipeline execution (validation, splitting, conversion, tweaks)
- Temporary file management
- Send operations coordination
"""

import datetime
import hashlib
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Any

from core.structured_logging import (
    get_logger,
    get_or_create_correlation_id,
    log_file_operation,
)
from core.utils import normalize_bool
from dispatch.error_handler import ErrorHandler
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
    settings: dict
    upc_dict: dict
    temp_dirs: list[str] = field(default_factory=list)
    temp_files: list[str] = field(default_factory=list)


class FileProcessor:
    """Service for processing individual EDI files.

    This service encapsulates all logic related to processing a single EDI file
    through the complete pipeline: validation, splitting, conversion, tweaks,
    and sending to backends.

    Attributes:
        send_manager: Manager for backend send operations
        error_handler: Handler for error recording
        validator_step: Pipeline validator step
        splitter_step: Pipeline splitter step
        converter_step: Pipeline converter step
        tweaker_step: Pipeline tweaker step
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
        error_handler: ErrorHandler,
        validator_step: Any | None = None,
        splitter_step: Any | None = None,
        converter_step: Any | None = None,
        tweaker_step: Any | None = None,
        file_system: Any | None = None,
    ) -> None:
        """Initialize the file processor.

        Args:
            send_manager: Manager for backend send operations
            error_handler: Handler for error recording
            validator_step: Pipeline validator step
            splitter_step: Pipeline splitter step
            converter_step: Pipeline converter step
            tweaker_step: Pipeline tweaker step
            file_system: Optional file system interface

        """
        self.send_manager = send_manager
        self.error_handler = error_handler
        self.validator_step = validator_step
        self.splitter_step = splitter_step
        self.converter_step = converter_step
        self.tweaker_step = tweaker_step
        self.file_system = file_system

    def process_file(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict,
        run_log: Any = None,
        effective_folder: dict | None = None,
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
                context={"folder_config": folder, "pipeline_mode": True},
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
        """Build processing context for a file.

        Args:
            folder: Folder configuration
            upc_dict: UPC dictionary
            effective_folder: Either a pre-built ProcessingContext or a normalized
                folder dict. If a ProcessingContext is provided it is returned
                unchanged; if a dict is provided it will be used as the
                effective_folder field on a new ProcessingContext.

        Returns:
            ProcessingContext with initialized state

        """
        # If a full ProcessingContext was passed (from DispatchOrchestrator),
        # reuse it directly so settings and temp tracking are preserved.
        if isinstance(effective_folder, ProcessingContext):
            return effective_folder

        # Otherwise treat effective_folder as the normalized folder dict (or None)
        return ProcessingContext(
            folder=folder,
            effective_folder=(
                effective_folder if effective_folder is not None else folder
            ),
            # If the caller supplied a dict with 'settings', use it, otherwise
            # default to an empty dict. DispatchOrchestrator passes a full
            # ProcessingContext which was handled above.
            settings=(
                effective_folder.get("settings")
                if isinstance(effective_folder, dict)
                else {}
            ),
            upc_dict=upc_dict,
        )

    def _execute_pipeline(
        self,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> None:
        """Execute the core file processing pipeline.

        Args:
            file_path: Path to the file
            file_basename: File basename
            context: Processing context
            result: File result to update
            run_log: Run log for activity recording

        """
        result.checksum = self._calculate_checksum(file_path)
        logger.debug("Calculated checksum for %s: %s", file_basename, result.checksum)
        current_file = file_path

        # Run validation
        continue_processing, current_file = self._run_validation(
            current_file=current_file,
            context=context,
            result=result,
            run_log=run_log,
            file_basename=file_basename,
        )
        if not continue_processing:
            return

        # Run splitting
        if self._run_splitting(
            current_file=current_file,
            file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            run_log=run_log,
        ):
            return

        # Run conversion and tweaks
        current_file, did_convert, conversion_failed = self._run_conversion_and_tweaks(
            current_file=current_file,
            file_basename=file_basename,
            original_file_path=file_path,
            context=context,
            run_log=run_log,
            validation_passed=result.validated,
        )
        if did_convert:
            result.converted = True

        # If conversion failed (i.e., conversion was attempted but produced no output),
        # treat as error. However, when process_edi is False we expect the original
        # file to be sent unchanged — do not mark this as conversion failure.
        process_edi_flag = normalize_bool(
            context.effective_folder.get("process_edi", False)
        )
        if conversion_failed and process_edi_flag:
            result.errors.append("No converted output was produced")
            result.sent = False
            return

        # Send to backends
        self._send_file(
            current_file=current_file,
            file_path=file_path,
            file_basename=file_basename,
            context=context,
            result=result,
            run_log=run_log,
        )

    def _run_validation(
        self,
        current_file: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
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

        try:
            validation_output = self.validator_step.execute(
                current_file,
                context.effective_folder,
            )
            # Handle tuple return: (is_valid, file_path_or_errors)
            if isinstance(validation_output, tuple):
                is_valid, errors_or_file = validation_output
            else:
                # Fallback for dict-style return
                is_valid = validation_output.get("valid", True)
                errors_or_file = (
                    validation_output.get("file_path", current_file)
                    if is_valid
                    else validation_output.get("errors", [])
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
                return False, current_file
            # errors_or_file is the (possibly modified) file path on success
            new_file = (
                errors_or_file if isinstance(errors_or_file, str) else current_file
            )
            return True, new_file
        except Exception as e:
            logger.exception("Validation error for %s: %s", file_basename, e)
            result.validated = False
            result.errors.append(str(e))
            return False, current_file

    def _run_splitting(
        self,
        current_file: str,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> bool:
        """Run splitting step of the pipeline.

        Args:
            current_file: Current file path
            file_path: Original file path
            file_basename: File basename
            context: Processing context
            result: File result
            run_log: Run log

        Returns:
            True if processing should stop (split occurred)

        """
        if not self.splitter_step:
            return False

        try:
            split_output = self.splitter_step.execute(
                current_file,
                context.effective_folder,
            )
            # Returns list[str] of output paths
            was_split = bool(split_output)
            if was_split:
                logger.info(
                    "File %s was split into %d files", file_basename, len(split_output)
                )
                return True
            return False
        except Exception as e:
            logger.exception("Splitting error for %s: %s", file_basename, e)
            result.errors.append(f"Splitting error: {e}")
            return False

    def _run_conversion_and_tweaks(
        self,
        current_file: str,
        file_basename: str,
        original_file_path: str,
        context: ProcessingContext,
        run_log: Any,
        validation_passed: bool,
    ) -> tuple[str, bool, bool]:
        """Run conversion and tweaks steps of the pipeline.

        Args:
            current_file: Current file path
            file_basename: File basename
            original_file_path: Original file path
            context: Processing context
            run_log: Run log
            validation_passed: Whether validation passed

        Returns:
            Tuple of (new_file_path, did_convert, conversion_failed)

        """
        did_convert = False
        conversion_failed = False
        file_path = current_file

        # Run conversion
        if self.converter_step and validation_passed:
            try:
                converted_file = self.converter_step.execute(
                    file_path,
                    context.effective_folder,
                    context.settings,
                    context.upc_dict,
                    context=context,
                )
                if converted_file:
                    file_path = converted_file
                    did_convert = True
                    logger.debug(
                        "Conversion completed for %s: %s", file_basename, file_path
                    )
                else:
                    # Conversion was attempted but produced no output — treat as failure
                    conversion_failed = True
            except Exception as e:
                logger.exception("Conversion error for %s: %s", file_basename, e)
                conversion_failed = True

        # Run tweaks
        if self.tweaker_step and file_path:
            try:
                tweaked_file = self.tweaker_step.execute(
                    file_path,
                    context.effective_folder,
                    context.upc_dict,
                    settings=context.settings,
                    context=context,
                )
                if tweaked_file:
                    file_path = tweaked_file
                    logger.debug("Tweaks applied to %s: %s", file_basename, file_path)
            except Exception as e:
                logger.exception("Tweak error for %s: %s", file_basename, e)

        return file_path, did_convert, conversion_failed

    def _send_file(
        self,
        current_file: str,
        file_path: str,
        file_basename: str,
        context: ProcessingContext,
        result: FileResult,
        run_log: Any,
    ) -> None:
        """Send file to enabled backends.

        Args:
            current_file: Current file path
            file_path: Original file path
            file_basename: File basename
            context: Processing context
            result: File result
            run_log: Run log

        """
        enabled_backends = self.send_manager.get_enabled_backends(
            context.effective_folder
        )
        if not enabled_backends:
            result.sent = False
            result.errors.append("No backends enabled")
            return

        # Apply file rename if configured
        final_file = self._apply_rename(current_file, context)

        # Send to backends
        result.sent = self._send_to_backends(
            file_path=final_file,
            folder=context.effective_folder,
            run_log=run_log,
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
                run_log=run_log,
            )
            return

        self._log_success(file_basename, file_path, run_log)

    def _apply_rename(self, file_path: str, context: ProcessingContext) -> str:
        """Apply file rename if configured.

        Args:
            file_path: Current file path
            context: Processing context

        Returns:
            Possibly renamed file path

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
        context.temp_dirs.append(temp_dir)

        if os.path.isabs(new_name) or ".." in new_name:
            raise ValueError(f"Invalid filename pattern in rename template: {new_name}")

        full_dest = os.path.join(temp_dir, new_name)
        if not full_dest.startswith(temp_dir + os.sep) and full_dest != temp_dir:
            raise ValueError(f"Path traversal attempt detected: {new_name}")

        shutil.copy2(file_path, full_dest)
        logger.debug("Renamed %s → %s for send", original_basename, new_name)
        return full_dest

    def _send_to_backends(
        self,
        file_path: str,
        folder: dict,
        run_log: Any,
        settings: dict,
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
        send_results = self.send_manager.send_all(
            enabled_backends, file_path, folder, settings
        )
        return bool(send_results) and all(send_results.values())

    def _record_send_failure(
        self,
        result: FileResult,
        file_basename: str,
        current_file: str,
        run_log: Any,
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

    def _log_success(self, file_basename: str, file_path: str, run_log: Any) -> None:
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
                    import shutil

                    shutil.rmtree(temp_dir)
                    logger.debug("Cleaned up temp directory: %s", temp_dir)
            except Exception as e:
                logger.warning("Failed to clean up temp dir %s: %s", temp_dir, e)

        for temp_file in context.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.debug("Cleaned up temp file: %s", temp_file)
            except Exception as e:
                logger.warning("Failed to clean up temp file %s: %s", temp_file, e)

        context.temp_dirs.clear()
        context.temp_files.clear()

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

        if self.file_system:
            content = self.file_system.read_file(file_path)
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
        """Extract invoice numbers from EDI A-records.

        Args:
            file_path: Path to the EDI file

        Returns:
            Comma-separated string of invoice numbers

        """
        try:
            if self.file_system:
                content_bytes = self.file_system.read_file(file_path)
                content = (
                    content_bytes.decode("utf-8", errors="replace")
                    if isinstance(content_bytes, bytes)
                    else content_bytes
                )
            else:
                with open(file_path, "r", errors="replace") as f:
                    content = f.read()

            from core.edi.edi_parser import capture_records

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
