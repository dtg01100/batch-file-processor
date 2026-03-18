"""EDI Tweaker Step for the dispatch pipeline.

This module provides a pipeline step for applying EDI tweaks
using the edi_tweaks module.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from batch_file_processor.structured_logging import (
    StructuredLogger,
    get_logger,
    get_or_create_correlation_id,
)
from dispatch.interfaces import FileSystemInterface

logger = get_logger(__name__)


@dataclass
class TweakerResult:
    """Result of EDI tweak operation.

    Attributes:
        output_path: Path to tweaked output file
        success: True if tweaking succeeded
        was_tweaked: True if tweaking was actually applied
        errors: List of error messages
    """

    output_path: str = ""
    success: bool = False
    was_tweaked: bool = False
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class TweakerInterface(Protocol):
    """Protocol for tweaker step implementations."""

    def tweak(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> TweakerResult:
        """Apply EDI tweaks to a file.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups

        Returns:
            TweakerResult with tweak outcome
        """
        ...


@runtime_checkable
class TweakFunctionProtocol(Protocol):
    """Protocol for the edi_tweak function."""

    def __call__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_dict: dict,
    ) -> str:
        """Apply EDI tweaks to a file.

        Args:
            edi_process: Path to input EDI file
            output_filename: Path to output file
            settings_dict: Dictionary containing database and app settings
            parameters_dict: Dictionary containing processing parameters
            upc_dict: Dictionary containing UPC mappings

        Returns:
            Path to the output file
        """
        ...


class MockTweaker:
    """Mock tweaker for testing purposes.

    This tweaker can be configured to return specific results
    and allows inspection of tweak calls.

    Attributes:
        result: The result to return from tweak()
        call_count: Number of times tweak was called
        last_input_path: Last input path passed to tweak
        last_output_dir: Last output directory passed to tweak
        last_params: Last params dict passed to tweak
        last_settings: Last settings dict passed to tweak
        last_upc_dict: Last upc_dict passed to tweak
    """

    def __init__(
        self,
        result: Optional[TweakerResult] = None,
        output_path: str = "",
        success: bool = True,
        was_tweaked: bool = True,
        errors: Optional[list[str]] = None,
    ):
        """Initialize the mock tweaker.

        Args:
            result: Complete result to return (overrides other params)
            output_path: Output path to return
            success: Whether to report success
            was_tweaked: Whether to report was_tweaked
            errors: List of error messages
        """
        if result is not None:
            self._result = result
        else:
            self._result = TweakerResult(
                output_path=output_path,
                success=success,
                was_tweaked=was_tweaked,
                errors=errors or [],
            )
        self.call_count: int = 0
        self.last_input_path: Optional[str] = None
        self.last_output_dir: Optional[str] = None
        self.last_params: Optional[dict] = None
        self.last_settings: Optional[dict] = None
        self.last_upc_dict: Optional[dict] = None

    def tweak(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> TweakerResult:
        """Mock tweak method.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary

        Returns:
            The configured TweakerResult
        """
        self.call_count += 1
        self.last_input_path = input_path
        self.last_output_dir = output_dir
        self.last_params = params
        self.last_settings = settings
        self.last_upc_dict = upc_dict
        return self._result

    def reset(self) -> None:
        """Reset the mock state."""
        self.call_count = 0
        self.last_input_path = None
        self.last_output_dir = None
        self.last_params = None
        self.last_settings = None
        self.last_upc_dict = None

    def set_result(self, result: TweakerResult) -> None:
        """Set the result to return.

        Args:
            result: The TweakerResult to return
        """
        self._result = result


class EDITweakerStep:
    """EDI tweaker step for the dispatch pipeline.

    This class handles applying EDI tweaks using the edi_tweaks module
    and integrates with the error handler for pipeline-based processing.

    Attributes:
        tweak_function: Function for applying EDI tweaks
        error_handler: Optional error handler for recording errors
        file_system: Optional file system interface
    """

    def __init__(
        self,
        tweak_function: Optional[TweakFunctionProtocol] = None,
        error_handler: Optional[Any] = None,
        file_system: Optional[FileSystemInterface] = None,
    ):
        """Initialize the tweaker step.

        Args:
            tweak_function: Function for applying EDI tweaks (defaults to edi_tweak)
            error_handler: Optional error handler for recording errors
            file_system: Optional file system interface
        """
        # Import from archive folder (legacy location)
        import os
        import sys

        archive_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "archive"
        )
        if archive_path not in sys.path:
            sys.path.insert(0, archive_path)
        import edi_tweaks

        self._tweak_function: TweakFunctionProtocol = (
            tweak_function or edi_tweaks.edi_tweak
        )
        self._error_handler = error_handler
        self._file_system = file_system

    def tweak(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> TweakerResult:
        """Apply EDI tweaks to a file.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary with tweak_edi setting
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups

        Returns:
            TweakerResult with tweak outcome
        """
        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()

        tweak_edi = params.get("tweak_edi", False)
        basename = os.path.basename(input_path)

        StructuredLogger.log_debug(
            logger,
            "tweak",
            __name__,
            f"Starting tweak for {basename}",
            input_path=basename,
            tweak_edi=tweak_edi,
            correlation_id=correlation_id,
        )

        if not tweak_edi:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "tweak",
                __name__,
                f"tweak_edi is False, skipping tweak for {basename}",
                decision="tweak_edi_false",
                input_path=basename,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            return TweakerResult(
                output_path=input_path, success=True, was_tweaked=False, errors=[]
            )

        output_filename = os.path.join(output_dir, basename)

        StructuredLogger.log_debug(
            logger,
            "tweak",
            __name__,
            f"Output will be written to: {output_filename}",
            input_path=basename,
            output_path=output_filename,
            correlation_id=correlation_id,
        )

        errors: list[str] = []

        if self._file_system and not self._file_system.dir_exists(output_dir):
            StructuredLogger.log_debug(
                logger,
                "tweak",
                __name__,
                f"Creating output directory: {output_dir}",
                output_dir=output_dir,
                correlation_id=correlation_id,
            )
            try:
                self._file_system.makedirs(output_dir)
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Failed to create output directory: {e}"
                StructuredLogger.log_error(
                    logger,
                    "tweak",
                    __name__,
                    e,
                    {
                        "input_path": basename,
                        "output_dir": output_dir,
                    },
                    duration_ms,
                )
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
                return TweakerResult(
                    output_path=input_path,
                    success=False,
                    was_tweaked=False,
                    errors=errors,
                )

        try:
            StructuredLogger.log_debug(
                logger,
                "tweak",
                __name__,
                f"Calling tweak function for {basename}",
                input_path=basename,
                output_path=output_filename,
                correlation_id=correlation_id,
            )

            tweaked_path = self._tweak_function(
                input_path, output_filename, settings, params, upc_dict
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "tweak",
                __name__,
                f"Tweaked {basename} -> {tweaked_path}",
                input_path=basename,
                output_path=tweaked_path,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            return TweakerResult(
                output_path=tweaked_path, success=True, was_tweaked=True, errors=errors
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_error(
                logger,
                "tweak",
                __name__,
                e,
                {
                    "input_path": basename,
                    "output_path": output_filename,
                },
                duration_ms,
            )
            logger.error("Tweaking failed for %s: %s", basename, e, exc_info=True)
            error_msg = f"Tweaking failed: {e}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return TweakerResult(
                output_path=input_path, success=False, was_tweaked=False, errors=errors
            )

    def _record_error(self, filename: str, error_msg: str) -> None:
        """Record an error to the error handler.

        Args:
            filename: Filename being processed
            error_msg: Error message
        """
        if self._error_handler is None:
            return

        self._error_handler.record_error(
            folder="",
            filename=filename,
            error=Exception(error_msg),
            context={"source": "EDITweakerStep"},
            error_source="EDITweaker",
        )

    def execute(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict,
        settings: Optional[dict] = None,
        context: Optional[Any] = None,
    ) -> str | None:
        """Execute tweak step (wrapper for pipeline compatibility).

        Args:
            file_path: Path to the file to tweak
            folder: Folder configuration dictionary
            upc_dict: UPC dictionary for lookups
            settings: Global settings dictionary

        Returns:
            Path to tweaked file, or None if tweaking failed/not needed
        """
        import os
        import shutil
        import tempfile

        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()

        basename = os.path.basename(file_path)

        StructuredLogger.log_debug(
            logger,
            "execute",
            __name__,
            f"Execute tweaker step for {basename}",
            file_path=basename,
            correlation_id=correlation_id,
        )

        effective_settings = (
            settings if settings is not None else folder.get("settings", {})
        )

        # Create a TEMPORARY directory for intermediate processing
        temp_dir = tempfile.mkdtemp(prefix="edi_tweaker_")
        StructuredLogger.log_debug(
            logger,
            "execute",
            __name__,
            f"Created temp dir for tweaking: {temp_dir}",
            temp_dir=temp_dir,
            file_path=basename,
            correlation_id=correlation_id,
        )

        temp_dirs: Optional[list[str]] = None
        if context is not None and hasattr(context, "temp_dirs"):
            temp_dirs = context.temp_dirs
        elif "_pipeline_temp_dirs" in folder and isinstance(
            folder.get("_pipeline_temp_dirs"), list
        ):
            temp_dirs = folder["_pipeline_temp_dirs"]

        if temp_dirs is not None:
            temp_dirs.append(temp_dir)

        try:
            result = self.tweak(
                file_path, temp_dir, folder, effective_settings, upc_dict
            )

            if (
                result.success
                and result.output_path != file_path
                and os.path.exists(result.output_path)
            ):
                duration_ms = (time.perf_counter() - start_time) * 1000
                StructuredLogger.log_debug(
                    logger,
                    "execute",
                    __name__,
                    f"Tweaker step produced: {result.output_path}",
                    file_path=basename,
                    output_path=result.output_path,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms,
                )
                # Return the output path directly while temp_dir still exists
                # The path is inside temp_dir which we'll keep until orchestrator sends it
                return result.output_path

            # Cleanup if tweaking didn't produce output
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "execute",
                __name__,
                f"Tweaker step produced no output for {basename}, cleaning up",
                file_path=basename,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dirs is not None and temp_dir in temp_dirs:
                temp_dirs.remove(temp_dir)
            return None
        except Exception as e:
            # Cleanup on exception
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_error(
                logger,
                "execute",
                __name__,
                e,
                {
                    "file_path": basename,
                    "temp_dir": temp_dir,
                },
                duration_ms,
            )
            shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dirs is not None and temp_dir in temp_dirs:
                temp_dirs.remove(temp_dir)
            raise
