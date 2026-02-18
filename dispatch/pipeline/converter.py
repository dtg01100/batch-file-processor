"""EDI Converter Step for the dispatch pipeline.

This module provides a pipeline step for EDI format conversion,
using dynamic module loading for different output formats.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable, Any

from dispatch.interfaces import FileSystemInterface


SUPPORTED_FORMATS = [
    'csv',
    'estore_einvoice',
    'estore_einvoice_generic',
    'fintech',
    'jolley_custom',
    'scannerware',
    'scansheet_type_a',
    'simplified_csv',
    'stewarts_custom',
    'yellowdog_csv',
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
        upc_dict: dict
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
        errors: Optional[list[str]] = None
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
                errors=errors or []
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
        upc_dict: dict
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
        file_system: Optional[FileSystemInterface] = None
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
        upc_dict: dict
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
        errors: list[str] = []
        
        convert_to_format = params.get('convert_to_format', '')
        if not convert_to_format:
            return ConverterResult(
                output_path=input_path,
                format_used="",
                success=True,
                errors=errors
            )
        
        process_edi = params.get('process_edi', '')
        if process_edi != "True":
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=True,
                errors=errors
            )
        
        format_normalized = convert_to_format.lower().replace(' ', '_').replace('-', '_')
        
        if format_normalized not in SUPPORTED_FORMATS:
            error_msg = f"Unsupported conversion format: {convert_to_format}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors
            )
        
        module_name = f'convert_to_{format_normalized}'
        
        output_filename = os.path.join(output_dir, os.path.basename(input_path))
        
        if self._file_system and not self._file_system.dir_exists(os.path.dirname(output_filename)):
            try:
                self._file_system.makedirs(os.path.dirname(output_filename))
            except Exception as e:
                error_msg = f"Failed to create output directory: {e}"
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
                return ConverterResult(
                    output_path=input_path,
                    format_used=convert_to_format,
                    success=False,
                    errors=errors
                )
        
        try:
            module = self._module_loader.load_module(module_name)
            
            if not hasattr(module, 'edi_convert'):
                error_msg = f"Module {module_name} does not have edi_convert function"
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
                return ConverterResult(
                    output_path=input_path,
                    format_used=convert_to_format,
                    success=False,
                    errors=errors
                )
            
            converted_path = module.edi_convert(
                input_path,
                output_filename,
                settings,
                params,
                upc_dict
            )
            
            return ConverterResult(
                output_path=converted_path,
                format_used=convert_to_format,
                success=True,
                errors=errors
            )
            
        except ImportError as e:
            error_msg = f"Conversion module not found: {module_name} - {e}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors
            )
        except Exception as e:
            error_msg = f"Conversion failed: {e}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return ConverterResult(
                output_path=input_path,
                format_used=convert_to_format,
                success=False,
                errors=errors
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
            context={'source': 'EDIConverterStep'},
            error_source="EDIConverter"
        )