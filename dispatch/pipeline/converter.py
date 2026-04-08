"""EDI Converter Step for the dispatch pipeline.

This module provides a pipeline step for EDI format conversion,
using dynamic module loading for different output formats.
"""

import os
import pkgutil
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from core.structured_logging import (
    StructuredLogger,
    get_logger,
    get_or_create_correlation_id,
    redact_sensitive_data,
)
from core.utils import normalize_bool, normalize_convert_to_format
from dispatch.interfaces import FileSystemInterface
from dispatch.pipeline.temp_dir_utils import (
    cleanup_pipeline_temp_dir,
    create_pipeline_temp_dir,
)

logger = get_logger(__name__)


def _discover_supported_formats() -> list[str]:
    """Auto-discover supported conversion formats by scanning converters package."""
    formats = []
    converter_path = os.path.join(os.path.dirname(__file__), "..", "converters")
    if not os.path.isdir(converter_path):
        return formats
    for _, module_name, is_pkg in pkgutil.iter_modules([converter_path]):
        if module_name.startswith("convert_to_") and not is_pkg:
            format_name = module_name.replace("convert_to_", "")
            formats.append(format_name)
    return sorted(formats)


SUPPORTED_FORMATS = _discover_supported_formats()


@dataclass
class ConverterResult:
    """Result of EDI conversion operation.

    Attributes:
        output_path: Path to converted output file
        format_used: Format that was used for conversion
        success: True if conversion succeeded
        errors: List of error messages

    """

    output_path: str = ""
    format_used: str = ""
    success: bool = False
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class ConverterInterface(Protocol):
    """Protocol for converter step implementations."""

    def convert(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> ConverterResult:
        """Convert an EDI file to another format.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups

        Returns:
            ConverterResult with conversion outcome

        """
        ...


@runtime_checkable
class ModuleLoaderProtocol(Protocol):
    """Protocol for module loading mechanism."""

    def load_module(self, module_name: str) -> Any:
        """Load a module by name.

        Args:
            module_name: Name of the module to load

        Returns:
            The loaded module

        Raises:
            ImportError: If module cannot be loaded

        """
        ...

    def module_exists(self, module_name: str) -> bool:
        """Check if a module can be loaded.

        Args:
            module_name: Name of the module to check

        Returns:
            True if module can be loaded

        """
        ...


class DefaultModuleLoader:
    """Default module loader using importlib."""

    def load_module(self, module_name: str) -> Any:
        """Load a module by name using importlib.

        Args:
            module_name: Name of the module to load

        Returns:
            The loaded module

        Raises:
            ImportError: If module cannot be loaded

        """
        import importlib

        return importlib.import_module(module_name)

    def module_exists(self, module_name: str) -> bool:
        """Check if a module can be loaded.

        Args:
            module_name: Name of the module to check

        Returns:
            True if module can be loaded

        """
        try:
            self.load_module(module_name)
            return True
        except ImportError:
            return False


class MockConverter:
    """Mock converter for testing purposes.

    This converter can be configured to return specific results
    and allows inspection of convert calls.

    Attributes:
        result: The result to return from convert()
        call_count: Number of times convert was called
        last_input_path: Last input path passed to convert
        last_output_dir: Last output directory passed to convert
        last_params: Last params dict passed to convert
        last_settings: Last settings dict passed to convert
        last_upc_dict: Last upc_dict passed to convert

    """

    def __init__(
        self,
        result: ConverterResult | None = None,
        output_path: str = "",
        format_used: str = "",
        *,
        success: bool = True,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize the mock converter.

        Args:
            result: Complete result to return (overrides other params)
            output_path: Output path to return
            format_used: Format to report
            success: Whether to report success
            errors: List of error messages

        """
        if result is not None:
            self._result = result
        else:
            self._result = ConverterResult(
                output_path=output_path,
                format_used=format_used,
                success=success,
                errors=errors or [],
            )
        self.call_count: int = 0
        self.last_input_path: str | None = None
        self.last_output_dir: str | None = None
        self.last_params: dict | None = None
        self.last_settings: dict | None = None
        self.last_upc_dict: dict | None = None

    def convert(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> ConverterResult:
        """Mock convert method.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary

        Returns:
            The configured ConverterResult

        """
        self.call_count += 1
        self.last_input_path = input_path
        self.last_output_dir = output_dir
        self.last_params = params
        self.last_settings = settings
        self.last_upc_dict = upc_dict
        return self._result

    def reset(self) -> None:
        """Reset the mock state to initial values.

        Clears call counts, recorded arguments, output files, and result
        settings. Useful for reusing the same mock instance across
        multiple test cases.

        """
        self.call_count = 0
        self.last_input_path = None
        self.last_output_dir = None
        self.last_params = None
        self.last_settings = None
        self.last_upc_dict = None

    def set_result(self, result: ConverterResult) -> None:
        """Set the result to return.

        Args:
            result: The ConverterResult to return

        """
        self._result = result


class EDIConverterStep:
    """EDI converter step for the dispatch pipeline.

    This class handles format conversion using dynamically loaded
    modules and integrates with the error handler for pipeline-based
    processing.

    Attributes:
        module_loader: Module loader for loading conversion modules
        error_handler: Optional error handler for recording errors
        file_system: Optional file system interface

    """

    def __init__(
        self,
        module_loader: ModuleLoaderProtocol | None = None,
        error_handler: Any | None = None,
        file_system: FileSystemInterface | None = None,
    ) -> None:
        """Initialize the converter step.

        Args:
            module_loader: Module loader for loading conversion modules
            error_handler: Optional error handler for recording errors
            file_system: Optional file system interface

        """
        self._module_loader = module_loader or DefaultModuleLoader()
        self._error_handler = error_handler
        self._file_system = file_system

    def convert(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict,
    ) -> ConverterResult:
        """Convert an EDI file to another format."""
        # Prepare conversion context and parameters
        (
            correlation_id,
            start_time,
            convert_to_format,
            input_basename,
            module_name,
            output_filename,
            process_edi,
        ) = self._prepare_conversion(input_path, output_dir, params)

        # Run pre-execution checks which may return early
        precheck_result = self._pre_execution_checks(
            convert_to_format,
            input_path,
            input_basename,
            output_dir,
            module_name,
            process_edi,
            correlation_id,
            start_time,
        )
        if isinstance(precheck_result, ConverterResult):
            return precheck_result

        module = precheck_result

        # Execute the conversion and handle results/errors
        try:
            return self._run_conversion(
                module,
                input_path,
                output_filename,
                settings,
                params,
                upc_dict,
                convert_to_format,
                input_basename,
                correlation_id,
                start_time,
            )
        except Exception as e:
            return self._handle_conversion_error(
                e,
                input_path,
                output_dir,
                convert_to_format,
                input_basename,
                correlation_id,
                start_time,
            )

    def get_supported_formats(self) -> list[str]:
        """Get list of supported conversion formats.

        Returns:
            List of supported format names

        """
        return SUPPORTED_FORMATS.copy()

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
            context={"source": "EDIConverterStep"},
            error_source="EDIConverter",
        )

    def _is_noop_conversion(
        self,
        convert_to_format: str,
        input_path: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> tuple[bool, ConverterResult | None]:
        """Check if conversion should be skipped (no format specified).

        Returns:
            Tuple of (is_noop, early_return_result). If is_noop is True,
            early_return_result contains the result to return.

        """
        if not convert_to_format:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"No convert_to_format set, skipping conversion for {input_basename}",
                decision="no_format",
                input_path=input_basename,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            return True, ConverterResult(
                output_path=input_path, format_used="", success=True, errors=[]
            )
        return False, None

    def _is_process_edi_disabled(
        self,
        *,
        process_edi: bool,
        convert_to_format: str,
        input_path: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> tuple[bool, ConverterResult | None]:
        """Check if EDI processing is disabled.

        Returns:
            Tuple of (is_disabled, early_return_result). If is_disabled is True,
            early_return_result contains the result to return.

        """
        if not process_edi:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"process_edi is False, skipping for {input_basename}",
                decision="process_edi_false",
                input_path=input_basename,
                format=convert_to_format,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            return True, ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=True,
                errors=[],
            )
        return False, None

    def _validate_conversion_format(
        self,
        convert_to_format: str,
        input_path: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> tuple[bool, ConverterResult | None]:
        """Validate the conversion format is supported.

        Returns:
            Tuple of (is_invalid, early_return_result). If is_invalid is True,
            early_return_result contains the result to return.

        """
        if convert_to_format not in SUPPORTED_FORMATS:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = f"Unsupported conversion format: {convert_to_format}"
            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"Unsupported format: {convert_to_format}",
                decision="unsupported_format",
                input_path=input_basename,
                format=convert_to_format,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            StructuredLogger.log_error(
                logger,
                "convert",
                __name__,
                Exception(error_msg),
                {
                    "input_path": input_basename,
                    "format": convert_to_format,
                    "supported_formats": SUPPORTED_FORMATS,
                },
                duration_ms,
            )
            errors = [error_msg]
            self._record_error(input_path, error_msg)
            return True, ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors,
            )
        return False, None

    def _ensure_output_directory(
        self,
        output_dir: str,
        convert_to_format: str,
        input_path: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> tuple[bool, ConverterResult | None]:
        """Ensure output directory exists, creating if necessary.

        Returns:
            Tuple of (failed, early_return_result). If failed is True,
            early_return_result contains the result to return.

        """
        if self._file_system and not self._file_system.dir_exists(output_dir):
            try:
                self._file_system.makedirs(output_dir)
            except OSError as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Failed to create output directory: {e}"
                StructuredLogger.log_error(
                    logger,
                    "convert",
                    __name__,
                    e,
                    {
                        "input_path": input_basename,
                        "output_dir": output_dir,
                        "format": convert_to_format,
                    },
                    duration_ms,
                )
                errors = [error_msg]
                self._record_error(input_path, error_msg)
                return True, ConverterResult(
                    output_path=input_path,
                    format_used=convert_to_format,
                    success=False,
                    errors=errors,
                )
        return False, None

    def _load_converter_module(
        self,
        module_name: str,
        convert_to_format: str,
        input_path: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> tuple[Any | None, ConverterResult | None]:
        """Load the converter module.

        Returns:
            Tuple of (module, error_result). If module is None,
            error_result contains the result to return.

        """
        StructuredLogger.log_debug(
            logger,
            "convert",
            __name__,
            f"Loading converter module: {module_name}",
            module_name=module_name,
            input_path=input_basename,
            correlation_id=correlation_id,
        )
        try:
            module = self._module_loader.load_module(module_name)
        except ImportError:
            # Log a clear, operator-facing message and return a friendly
            # conversion error to the pipeline. Tests expect the returned
            # ConverterResult.errors to contain the token "Conversion module
            # not found" while logs should include "Converter module not
            # found" for quick operator scanning.
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Log a message with the wording expected by log assertions
            StructuredLogger.log_error(
                logger,
                "convert",
                __name__,
                Exception("Converter module not found"),
                {
                    "input_path": input_basename,
                    "module_name": module_name,
                    "format": convert_to_format,
                },
                duration_ms,
            )

            # Return a ConverterResult via the centralized error handler
            # using the user-visible phrasing expected by tests.
            return None, self._handle_conversion_error(
                Exception("Conversion module not found"),
                input_path,
                "",
                convert_to_format,
                input_basename,
                correlation_id,
                start_time,
            )

        if not hasattr(module, "edi_convert"):
            return None, self._handle_conversion_error(
                Exception(f"Module {module_name} does not have edi_convert function"),
                input_path,
                "",
                convert_to_format,
                input_basename,
                correlation_id,
                start_time,
            )

        return module, None

    # --- Helper methods extracted from large functions ---
    def _prepare_conversion(self, input_path: str, output_dir: str, params: dict):
        """Prepare common conversion variables and context."""
        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()
        raw_convert_to_format = params.get("convert_to_format", "")
        convert_to_format = normalize_convert_to_format(raw_convert_to_format)
        input_basename = os.path.basename(input_path)
        process_edi = normalize_bool(params.get("process_edi", False))
        module_name = f"dispatch.converters.convert_to_{convert_to_format}"
        output_filename = os.path.join(output_dir, input_basename)
        return (
            correlation_id,
            start_time,
            convert_to_format,
            input_basename,
            module_name,
            output_filename,
            process_edi,
        )

    def _pre_execution_checks(
        self,
        convert_to_format: str,
        input_path: str,
        input_basename: str,
        output_dir: str,
        module_name: str,
        process_edi: bool,
        correlation_id: str,
        start_time: float,
    ):
        """Run the sequence of pre-execution checks. Returns module or ConverterResult on early return."""
        is_noop, result = self._is_noop_conversion(
            convert_to_format, input_path, input_basename, correlation_id, start_time
        )
        if is_noop:
            return result

        is_disabled, result = self._is_process_edi_disabled(
            process_edi=process_edi,
            convert_to_format=convert_to_format,
            input_path=input_path,
            input_basename=input_basename,
            correlation_id=correlation_id,
            start_time=start_time,
        )
        if is_disabled:
            return result

        is_invalid, result = self._validate_conversion_format(
            convert_to_format, input_path, input_basename, correlation_id, start_time
        )
        if is_invalid:
            return result

        failed, result = self._ensure_output_directory(
            output_dir,
            convert_to_format,
            input_path,
            input_basename,
            correlation_id,
            start_time,
        )
        if failed:
            return result

        module, result = self._load_converter_module(
            module_name,
            convert_to_format,
            input_path,
            input_basename,
            correlation_id,
            start_time,
        )
        if module is None:
            return result

        return module

    def _run_conversion(
        self,
        module: Any,
        input_path: str,
        output_filename: str,
        settings: dict,
        params: dict,
        upc_dict: dict,
        convert_to_format: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> ConverterResult:
        """Execute the module conversion and return a ConverterResult."""
        converted_path = module.edi_convert(
            input_path, output_filename, settings, params, upc_dict
        )
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Converted %s -> %s (format: %s) in %.0fms",
            input_basename,
            converted_path,
            convert_to_format,
            duration_ms,
        )
        return ConverterResult(
            output_path=converted_path,
            format_used=convert_to_format,
            success=True,
            errors=[],
        )

    def _handle_conversion_result(self, result: ConverterResult) -> ConverterResult:
        """Hook for post-processing of successful conversion results (placeholder)."""
        # Currently no-op, but keep single-responsibility for future actions
        return result

    def _handle_conversion_error(
        self,
        exc: Exception,
        input_path: str,
        output_dir: str,
        convert_to_format: str,
        input_basename: str,
        correlation_id: str,
        start_time: float,
    ) -> ConverterResult:
        """Centralized conversion error handling that logs and records the error and returns a failure result."""
        duration_ms = (time.perf_counter() - start_time) * 1000
        error_msg = f"Conversion failed: {exc}"
        # If this is an ImportError wrapped, log appropriately
        StructuredLogger.log_error(
            logger,
            "convert",
            __name__,
            exc,
            {
                "input_path": input_basename,
                "output_dir": output_dir,
                "format": convert_to_format,
            },
            duration_ms,
        )
        errors = [error_msg]
        # Record via error handler
        try:
            self._record_error(input_path, error_msg)
        except Exception:
            logger.debug("Failed to record error for %s", input_path, exc_info=True)
        return ConverterResult(
            output_path=input_path,
            format_used=convert_to_format,
            success=False,
            errors=errors,
        )

    def execute(
        self,
        file_path: str,
        folder: dict,
        settings: dict | None = None,
        upc_dict: dict | None = None,
        context: Any | None = None,
    ) -> str | None:
        """Execute convert step (wrapper for pipeline compatibility).

        Args:
            file_path: Path to the file to convert
            folder: Folder configuration dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups

        Returns:
            Path to converted file, or None if conversion failed/not needed

        """
        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()
        file_basename = os.path.basename(file_path)

        StructuredLogger.log_debug(
            logger,
            "execute",
            __name__,
            f"Execute converter step for {file_basename}",
            file_path=file_basename,
            correlation_id=correlation_id,
        )

        effective_settings = (
            settings if settings is not None else folder.get("settings", {})
        )
        effective_upc_dict = (
            upc_dict if upc_dict is not None else folder.get("upc_dict", {})
        )

        if upc_dict is None and not effective_upc_dict:
            StructuredLogger.log_debug(
                logger,
                "execute",
                __name__,
                f"Converter step for {file_basename} using empty UPC dictionary",
                decision="empty_upc_dict_fallback",
                file_path=file_basename,
                correlation_id=correlation_id,
            )

        temp_dir, temp_dirs = create_pipeline_temp_dir(
            "edi_converter", folder, context
        )
        StructuredLogger.log_debug(
            logger,
            "execute",
            __name__,
            f"Created temp dir for conversion: {temp_dir}",
            temp_dir=temp_dir,
            file_path=file_basename,
            correlation_id=correlation_id,
        )

        try:
            result = self.convert(
                file_path, temp_dir, folder, effective_settings, effective_upc_dict
            )
            if result.success and result.output_path != file_path:
                duration_ms = (time.perf_counter() - start_time) * 1000
                StructuredLogger.log_debug(
                    logger,
                    "execute",
                    __name__,
                    f"Converter step produced output for {file_basename}",
                    file_path=file_basename,
                    output_path=result.output_path,
                    format=result.format_used,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms,
                )
                return result.output_path

            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "execute",
                __name__,
                f"Converter step produced no output for {file_basename}",
                decision="no_output",
                file_path=file_basename,
                format=result.format_used,
                success=result.success,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            cleanup_pipeline_temp_dir(temp_dir, temp_dirs)
            return None
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_error(
                logger,
                "execute",
                __name__,
                e,
                {
                    "file_path": file_basename,
                    "temp_dir": temp_dir,
                    "settings_redacted": redact_sensitive_data(effective_settings),
                },
                duration_ms,
            )
            cleanup_pipeline_temp_dir(temp_dir, temp_dirs)
            raise
