"""File Processor for the dispatch service layer.

This module provides file-level processing that coordinates the pipeline steps:
validation, splitting, conversion, tweaking, and sending to backends.
"""

import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable, Any

from dispatch.pipeline.validator import ValidationResult, ValidatorStepInterface
from dispatch.pipeline.splitter import SplitterResult, SplitterInterface
from dispatch.pipeline.converter import ConverterResult, ConverterInterface
from dispatch.pipeline.tweaker import TweakerResult, TweakerInterface
from dispatch.send_manager import SendManager
from dispatch.hash_utils import generate_file_hash


@dataclass
class FileProcessorResult:
    """Result of file processing through the pipeline.
    
    Attributes:
        input_path: Original input file path
        output_path: Final output file path (after all processing)
        was_validated: Whether validation was performed
        validation_passed: Whether validation passed
        was_split: Whether file was split
        was_converted: Whether file was converted
        was_tweaked: Whether file was tweaked
        files_sent: Whether file was sent to backends
        checksum: MD5 checksum of output file
        errors: List of error messages
    """
    input_path: str = ""
    output_path: str = ""
    was_validated: bool = False
    validation_passed: bool = True
    was_split: bool = False
    was_converted: bool = False
    was_tweaked: bool = False
    files_sent: bool = False
    checksum: str = ""
    errors: list[str] = field(default_factory=list)


@runtime_checkable
class FileProcessorInterface(Protocol):
    """Protocol for file processor implementations."""
    
    def process_file(
        self,
        file_path: str,
        folder: dict,
        settings: dict,
        upc_dict: dict
    ) -> FileProcessorResult:
        """Process a file through the complete pipeline.
        
        Args:
            file_path: Path to the input file
            folder: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups
            
        Returns:
            FileProcessorResult with processing outcome and metadata
        """
        ...


class MockFileProcessor:
    """Mock file processor for testing purposes.
    
    This processor can be configured to return specific results
    and allows inspection of processing calls.
    
    Attributes:
        result: The result to return from process_file()
        call_count: Number of times process_file was called
        last_file_path: Last file path passed to process_file
        last_folder: Last folder dict passed to process_file
        last_settings: Last settings dict passed to process_file
        last_upc_dict: Last upc_dict passed to process_file
    """
    
    def __init__(
        self,
        result: Optional[FileProcessorResult] = None,
        input_path: str = "",
        output_path: str = "",
        was_validated: bool = False,
        validation_passed: bool = True,
        was_split: bool = False,
        was_converted: bool = False,
        was_tweaked: bool = False,
        files_sent: bool = False,
        checksum: str = "",
        errors: Optional[list[str]] = None
    ):
        """Initialize the mock file processor.
        
        Args:
            result: Complete result to return (overrides other params)
            input_path: Input path to report
            output_path: Output path to report
            was_validated: Whether to report validation was performed
            validation_passed: Whether validation passed
            was_split: Whether to report splitting occurred
            was_converted: Whether to report conversion occurred
            was_tweaked: Whether to report tweaking occurred
            files_sent: Whether to report files were sent
            checksum: Checksum to report
            errors: List of error messages
        """
        if result is not None:
            self._result = result
        else:
            self._result = FileProcessorResult(
                input_path=input_path,
                output_path=output_path,
                was_validated=was_validated,
                validation_passed=validation_passed,
                was_split=was_split,
                was_converted=was_converted,
                was_tweaked=was_tweaked,
                files_sent=files_sent,
                checksum=checksum,
                errors=errors or []
            )
        self.call_count: int = 0
        self.last_file_path: Optional[str] = None
        self.last_folder: Optional[dict] = None
        self.last_settings: Optional[dict] = None
        self.last_upc_dict: Optional[dict] = None
    
    def process_file(
        self,
        file_path: str,
        folder: dict,
        settings: dict,
        upc_dict: dict
    ) -> FileProcessorResult:
        """Mock process_file method.
        
        Args:
            file_path: Path to the input file
            folder: Folder parameters dictionary
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups
            
        Returns:
            The configured FileProcessorResult
        """
        self.call_count += 1
        self.last_file_path = file_path
        self.last_folder = folder
        self.last_settings = settings
        self.last_upc_dict = upc_dict
        return self._result
    
    def reset(self) -> None:
        """Reset the mock state."""
        self.call_count = 0
        self.last_file_path = None
        self.last_folder = None
        self.last_settings = None
        self.last_upc_dict = None
    
    def set_result(self, result: FileProcessorResult) -> None:
        """Set the result to return.
        
        Args:
            result: The FileProcessorResult to return
        """
        self._result = result


class FileProcessor:
    """File processor that coordinates the complete processing pipeline.
    
    This class orchestrates the pipeline steps in the correct order:
    1. Validation (if enabled)
    2. Splitting (if enabled)
    3. Tweaking (if enabled)
    4. Conversion (if enabled)
    5. Sending to backends
    
    Attributes:
        validator: Optional validator step implementation
        splitter: Optional splitter step implementation
        converter: Optional converter step implementation
        tweaker: Optional tweaker step implementation
        send_manager: Send manager for sending to backends
        error_handler: Optional error handler for recording errors
    """
    
    def __init__(
        self,
        validator: Optional[ValidatorStepInterface] = None,
        splitter: Optional[SplitterInterface] = None,
        converter: Optional[ConverterInterface] = None,
        tweaker: Optional[TweakerInterface] = None,
        send_manager: Optional[SendManager] = None,
        error_handler: Optional[Any] = None
    ):
        """Initialize the file processor.
        
        Args:
            validator: Validator step implementation
            splitter: Splitter step implementation
            converter: Converter step implementation
            tweaker: Tweaker step implementation
            send_manager: Send manager for sending to backends
            error_handler: Optional error handler for recording errors
        """
        self._validator = validator
        self._splitter = splitter
        self._converter = converter
        self._tweaker = tweaker
        self._send_manager = send_manager
        self._error_handler = error_handler
    
    def process_file(
        self,
        file_path: str,
        folder: dict,
        settings: dict,
        upc_dict: dict
    ) -> FileProcessorResult:
        """Process a file through the complete pipeline.
        
        Args:
            file_path: Path to the input file
            folder: Folder parameters dictionary containing:
                - process_edi: Whether to process EDI
                - tweak_edi: Whether to apply EDI tweaks
                - split_edi: Whether to split EDI files
                - force_edi_validation: Force validation
                - split_edi_filter_categories: Categories to filter
                - split_edi_filter_mode: Filter mode
                - convert_to_format: Target format for conversion
                - split_edi_include_invoices: Include invoices
                - split_edi_include_credits: Include credits
                - prepend_date_files: Prepend date to filenames
                - rename_file: Rename pattern
            settings: Global settings dictionary
            upc_dict: UPC dictionary for lookups
            
        Returns:
            FileProcessorResult with processing outcome and metadata
        """
        errors: list[str] = []
        
        was_validated = False
        validation_passed = True
        was_split = False
        was_tweaked = False
        was_converted = False
        files_sent = False
        output_path = file_path
        final_checksum = ""
        
        original_filename = os.path.basename(file_path)
        
        needs_validation = self._should_validate(folder)
        
        if needs_validation and self._validator is not None:
            was_validated = True
            validation_result = self._validator.validate(file_path, original_filename)
            validation_passed = validation_result.is_valid
            errors.extend(validation_result.errors)
            
            if not validation_passed and self._validator.should_block_processing(folder):
                return FileProcessorResult(
                    input_path=file_path,
                    output_path=file_path,
                    was_validated=was_validated,
                    validation_passed=validation_passed,
                    was_split=False,
                    was_converted=False,
                    was_tweaked=False,
                    files_sent=False,
                    checksum="",
                    errors=errors
                )
        
        if validation_passed or not needs_validation:
            with tempfile.TemporaryDirectory() as scratch_folder:
                split_result = self._process_splitting(
                    file_path, scratch_folder, folder, upc_dict
                )
                was_split = split_result.was_split
                errors.extend(split_result.errors)
                
                for output_file, prefix, suffix in split_result.files:
                    if errors and any(e for e in errors if 'split' in e.lower()):
                        continue
                    
                    output_file = self._apply_rename(output_file, prefix, suffix, folder)
                    
                    tweak_result = self._process_tweaking(
                        output_file, scratch_folder, folder, settings, upc_dict
                    )
                    was_tweaked = was_tweaked or tweak_result.was_tweaked
                    if tweak_result.output_path:
                        output_file = tweak_result.output_path
                    errors.extend(tweak_result.errors)
                    
                    convert_result = self._process_conversion(
                        output_file, scratch_folder, folder, settings, upc_dict
                    )
                    was_converted = was_converted or convert_result.success
                    if convert_result.output_path:
                        output_file = convert_result.output_path
                    errors.extend(convert_result.errors)
                    
                    if output_file and os.path.exists(output_file):
                        send_result = self._process_sending(
                            output_file, folder, settings
                        )
                        files_sent = files_sent or send_result
                        if not send_result:
                            errors.append("Failed to send file to backends")
                        
                        try:
                            final_checksum = generate_file_hash(output_file)
                        except Exception as e:
                            errors.append(f"Failed to generate checksum: {e}")
                        
                        output_path = output_file
        
        return FileProcessorResult(
            input_path=file_path,
            output_path=output_path,
            was_validated=was_validated,
            validation_passed=validation_passed,
            was_split=was_split,
            was_converted=was_converted,
            was_tweaked=was_tweaked,
            files_sent=files_sent,
            checksum=final_checksum,
            errors=errors
        )
    
    def _should_validate(self, folder: dict) -> bool:
        """Determine if validation should be performed.
        
        Args:
            folder: Folder parameters dictionary
            
        Returns:
            True if validation should be performed
        """
        process_edi = folder.get('process_edi', '')
        tweak_edi = folder.get('tweak_edi', False)
        split_edi = folder.get('split_edi', False)
        force_validation = folder.get('force_edi_validation', False)
        
        if isinstance(process_edi, str):
            process_edi = process_edi.lower() == 'true'
        
        return process_edi or tweak_edi or split_edi or force_validation
    
    def _process_splitting(
        self,
        file_path: str,
        output_dir: str,
        folder: dict,
        upc_dict: dict
    ) -> SplitterResult:
        """Process file splitting.
        
        Args:
            file_path: Path to input file
            output_dir: Output directory
            folder: Folder parameters
            upc_dict: UPC dictionary
            
        Returns:
            SplitterResult
        """
        if self._splitter is None:
            return SplitterResult(files=[(file_path, "", "")])
        
        return self._splitter.split(file_path, output_dir, folder, upc_dict)
    
    def _process_tweaking(
        self,
        file_path: str,
        output_dir: str,
        folder: dict,
        settings: dict,
        upc_dict: dict
    ) -> TweakerResult:
        """Process file tweaking.
        
        Args:
            file_path: Path to input file
            output_dir: Output directory
            folder: Folder parameters
            settings: Global settings
            upc_dict: UPC dictionary
            
        Returns:
            TweakerResult
        """
        if self._tweaker is None:
            return TweakerResult(output_path=file_path, success=True, was_tweaked=False)
        
        return self._tweaker.tweak(file_path, output_dir, folder, settings, upc_dict)
    
    def _process_conversion(
        self,
        file_path: str,
        output_dir: str,
        folder: dict,
        settings: dict,
        upc_dict: dict
    ) -> ConverterResult:
        """Process file conversion.
        
        Args:
            file_path: Path to input file
            output_dir: Output directory
            folder: Folder parameters
            settings: Global settings
            upc_dict: UPC dictionary
            
        Returns:
            ConverterResult
        """
        if self._converter is None:
            return ConverterResult(output_path=file_path, success=True)
        
        return self._converter.convert(file_path, output_dir, folder, settings, upc_dict)
    
    def _process_sending(
        self,
        file_path: str,
        folder: dict,
        settings: dict
    ) -> bool:
        """Process sending to backends.
        
        Args:
            file_path: Path to file to send
            folder: Folder parameters
            settings: Global settings
            
        Returns:
            True if send was successful
        """
        if self._send_manager is None:
            return False
        
        enabled_backends = self._send_manager.get_enabled_backends(folder)
        
        if not enabled_backends:
            return False
        
        try:
            results = self._send_manager.send_all(
                enabled_backends, file_path, folder, settings
            )
            return all(results.values())
        except Exception:
            return False
    
    def _apply_rename(
        self,
        file_path: str,
        prefix: str,
        suffix: str,
        folder: dict
    ) -> str:
        """Apply rename pattern to filename.
        
        Args:
            file_path: Current file path
            prefix: Prefix from splitting
            suffix: Suffix from splitting
            folder: Folder parameters
            
        Returns:
            Potentially renamed file path
        """
        import datetime
        import re
        
        rename_pattern = folder.get('rename_file', '').strip()
        
        if not rename_pattern:
            return file_path
        
        date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d")
        
        original_ext = os.path.basename(file_path).split('.')[-1]
        
        new_name = "".join([
            prefix,
            rename_pattern.replace("%datetime%", date_time),
            ".",
            original_ext,
            suffix
        ])
        
        new_name = re.sub(r'[^A-Za-z0-9. _]+', '', new_name)
        
        return os.path.join(os.path.dirname(file_path), new_name)
