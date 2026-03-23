"""EDI Converter Step for the dispatch pipeline.

This module provides a pipeline step for EDI format conversion,
using dynamic module loading for different output formats.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from core.structured_logging import (
    StructuredLogger,
    get_logger,
    get_or_create_correlation_id,
    redact_sensitive_data,
)
from core.utils.bool_utils import normalize_bool
from dispatch.interfaces import FileSystemInterface

logger = get_logger(__name__)


def _normalize_process_edi_flag(value: Any) -> bool:
    """Normalize process_edi to boolean.

    Handles all stored forms: string "True"/"False" (legacy), integer 1/0
    (modern), and string "1"/"0" (produced by the v41→v42 migration due to
    SQLite TEXT affinity converting integer writes back to strings).
    """
    return normalize_bool(value)


SUPPORTED_FORMATS = [
    "csv",
    "estore_einvoice",
    "estore_einvoice_generic",
    "fintech",
    "jolley_custom",
    "scannerware",
    "scansheet_type_a",
    "simplified_csv",
    "stewarts_custom",
    "tweaks",
    "yellowdog_csv",
]


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
        result: Optional[ConverterResult] = None,
        output_path: str = "",
        format_used: str = "",
        success: bool = True,
        errors: Optional[list[str]] = None,
    ):
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
        self.last_input_path: Optional[str] = None
        self.last_output_dir: Optional[str] = None
        self.last_params: Optional[dict] = None
        self.last_settings: Optional[dict] = None
        self.last_upc_dict: Optional[dict] = None

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
        """Reset the mock state."""
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
        module_loader: Optional[ModuleLoaderProtocol] = None,
        error_handler: Optional[Any] = None,
        file_system: Optional[FileSystemInterface] = None,
    ):
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
        """Convert an EDI file to another format.

        Args:
            input_path: Path to the input EDI file
            output_dir: Directory for output file
            params: Folder parameters dictionary with settings:
                - convert_to_format: Target format name
                - process_edi: Whether to process (must be "True")
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups

        Returns:
            ConverterResult with conversion outcome
        """
        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()

        errors: list[str] = []

        convert_to_format = params.get("convert_to_format", "")
        tweak_edi = params.get("tweak_edi", False)
        input_basename = os.path.basename(input_path)

        # Normalize tweak_edi to convert_to_format="tweaks" for unified handling
        if tweak_edi:
            convert_to_format = "tweaks"

        StructuredLogger.log_debug(
            logger,
            "convert",
            __name__,
            f"Starting conversion for {input_basename}",
            input_path=input_basename,
            output_dir=output_dir,
            format=convert_to_format,
            tweak_edi=tweak_edi,
            process_edi=params.get("process_edi"),
            correlation_id=correlation_id,
        )

        if not convert_to_format and not tweak_edi:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"No convert_to_format or tweak_edi set, "
                f"skipping conversion for {input_basename}",
                decision="no_format_no_tweak",
                input_path=input_basename,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            return ConverterResult(
                output_path=input_path, format_used="", success=True, errors=errors
            )

        process_edi = _normalize_process_edi_flag(params.get("process_edi", False))

        StructuredLogger.log_debug(
            logger,
            "convert",
            __name__,
            f"process_edi flag is {process_edi}",
            process_edi=process_edi,
            input_path=input_basename,
            correlation_id=correlation_id,
        )

        if not process_edi and not tweak_edi:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"process_edi is False and tweak_edi is False, "
                f"skipping for {input_basename}",
                decision="process_edi_and_tweak_edi_false",
                input_path=input_basename,
                format=convert_to_format,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
            )
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=True,
                errors=errors,
            )

        format_normalized = (
            convert_to_format.lower().replace(" ", "_").replace("-", "_")
        )

        if format_normalized not in SUPPORTED_FORMATS:
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
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors,
            )

        module_name = f"dispatch.converters.convert_to_{format_normalized}"

        output_filename = os.path.join(output_dir, os.path.basename(input_path))

        if self._file_system and not self._file_system.dir_exists(output_dir):
            try:
                self._file_system.makedirs(output_dir)
            except Exception as e:
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
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
                return ConverterResult(
                    output_path=input_path,
                    format_used=convert_to_format,
                    success=False,
                    errors=errors,
                )

        try:
            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"Loading converter module: {module_name}",
                module_name=module_name,
                input_path=input_basename,
                correlation_id=correlation_id,
            )
            module = self._module_loader.load_module(module_name)

            if not hasattr(module, "edi_convert"):
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_msg = f"Module {module_name} does not have edi_convert function"
                StructuredLogger.log_error(
                    logger,
                    "convert",
                    __name__,
                    Exception(error_msg),
                    {"input_path": input_basename, "module_name": module_name},
                    duration_ms,
                )
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
                return ConverterResult(
                    output_path=input_path,
                    format_used=convert_to_format,
                    success=False,
                    errors=errors,
                )

            if not upc_dict:
                StructuredLogger.log_debug(
                    logger,
                    "convert",
                    __name__,
                    f"Converting {input_basename} with empty UPC dictionary",
                    decision="empty_upc_dict",
                    input_path=input_basename,
                    format=convert_to_format,
                    correlation_id=correlation_id,
                )

            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"Calling edi_convert for {input_basename}",
                input_path=input_basename,
                output_path=output_filename,
                format=convert_to_format,
                correlation_id=correlation_id,
            )

            converted_path = module.edi_convert(
                input_path, output_filename, settings, params, upc_dict
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Converted %s -> %s (format: %s)",
                os.path.basename(input_path),
                converted_path,
                convert_to_format,
            )

            StructuredLogger.log_debug(
                logger,
                "convert",
                __name__,
                f"Conversion successful for {input_basename}",
                input_path=input_basename,
                output_path=converted_path,
                format=convert_to_format,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                success=True,
            )

            return ConverterResult(
                output_path=converted_path,
                format_used=convert_to_format,
                success=True,
                errors=errors,
            )

        except ImportError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = f"Conversion module not found: {module_name} - {e}"
            logger.error("Converter module not found: %s", module_name, exc_info=True)
            StructuredLogger.log_error(
                logger,
                "convert",
                __name__,
                e,
                {
                    "input_path": input_basename,
                    "module_name": module_name,
                    "format": convert_to_format,
                    "settings_redacted": redact_sensitive_data(settings),
                },
                duration_ms,
            )
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = f"Conversion failed: {e}"
            StructuredLogger.log_error(
                logger,
                "convert",
                __name__,
                e,
                {
                    "input_path": input_basename,
                    "output_dir": output_dir,
                    "format": convert_to_format,
                    "settings_redacted": redact_sensitive_data(settings),
                    "params_redacted": redact_sensitive_data(params),
                },
                duration_ms,
            )
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors,
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

    def execute(
        self,
        file_path: str,
        folder: dict,
        settings: Optional[dict] = None,
        upc_dict: Optional[dict] = None,
        context: Optional[Any] = None,
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
        import shutil
        import tempfile

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

        temp_dir = tempfile.mkdtemp(prefix="edi_converter_")
        StructuredLogger.log_debug(
            logger,
            "execute",
            __name__,
            f"Created temp dir for conversion: {temp_dir}",
            temp_dir=temp_dir,
            file_path=file_basename,
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
            shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dirs is not None and temp_dir in temp_dirs:
                temp_dirs.remove(temp_dir)
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
            shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dirs is not None and temp_dir in temp_dirs:
                temp_dirs.remove(temp_dir)
            raise
