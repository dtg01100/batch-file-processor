"""EDI Tweaker Step for the dispatch pipeline.

This module provides a pipeline step for applying EDI tweaks
using the edi_tweaks module.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable, Any, Callable

from dispatch.interfaces import FileSystemInterface


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
        upc_dict: dict
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
        upc_dict: dict
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
        errors: Optional[list[str]] = None
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
                errors=errors or []
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
        upc_dict: dict
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
        file_system: Optional[FileSystemInterface] = None
    ):
        """Initialize the tweaker step.
        
        Args:
            tweak_function: Function for applying EDI tweaks (defaults to edi_tweak)
            error_handler: Optional error handler for recording errors
            file_system: Optional file system interface
        """
        import edi_tweaks
        self._tweak_function: TweakFunctionProtocol = tweak_function or edi_tweaks.edi_tweak
        self._error_handler = error_handler
        self._file_system = file_system
    
    def tweak(
        self,
        input_path: str,
        output_dir: str,
        params: dict,
        settings: dict,
        upc_dict: dict
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
        tweak_edi = params.get('tweak_edi', False)
        
        if not tweak_edi:
            return TweakerResult(
                output_path=input_path,
                success=True,
                was_tweaked=False,
                errors=[]
            )
        
        output_filename = os.path.join(output_dir, os.path.basename(input_path))
        
        errors: list[str] = []
        
        if self._file_system and not self._file_system.dir_exists(output_dir):
            try:
                self._file_system.makedirs(output_dir)
            except Exception as e:
                error_msg = f"Failed to create output directory: {e}"
                errors.append(error_msg)
                self._record_error(input_path, error_msg)
                return TweakerResult(
                    output_path=input_path,
                    success=False,
                    was_tweaked=False,
                    errors=errors
                )
        
        try:
            tweaked_path = self._tweak_function(
                input_path,
                output_filename,
                settings,
                params,
                upc_dict
            )
            
            return TweakerResult(
                output_path=tweaked_path,
                success=True,
                was_tweaked=True,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Tweaking failed: {e}"
            errors.append(error_msg)
            self._record_error(input_path, error_msg)
            return TweakerResult(
                output_path=input_path,
                success=False,
                was_tweaked=False,
                errors=errors
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
            context={'source': 'EDITweakerStep'},
            error_source="EDITweaker"
        )
