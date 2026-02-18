"""Dispatch Orchestrator for coordinating file processing.

This module provides the main orchestration layer for dispatch operations,
coordinating validation, conversion, and sending of files.
"""

from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Optional, Protocol, runtime_checkable

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
        use_pipeline: Whether to use the new pipeline
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
    use_pipeline: bool = False


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
    
    def process_folder(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None
    ) -> FolderResult:
        """Process a single folder.
        
        Args:
            folder: Folder configuration dictionary
            run_log: Run log for recording processing activity
            processed_files: Optional database of already processed files
            
        Returns:
            FolderResult with processing outcome
        """
        if self.config.use_pipeline and self._is_pipeline_ready():
            upc_dict = self._get_upc_dictionary(self.config.settings)
            return self.process_folder_with_pipeline(folder, run_log, processed_files, upc_dict)
        
        return self._process_folder_legacy(folder, run_log, processed_files)
    
    def _process_folder_legacy(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None
    ) -> FolderResult:
        """Process folder using legacy method.
        
        Args:
            folder: Folder configuration dictionary
            run_log: Run log for recording processing activity
            processed_files: Optional database of already processed files
            
        Returns:
            FolderResult with processing outcome
        """
        result = FolderResult(
            folder_name=folder.get('folder_name', ''),
            alias=folder.get('alias', '')
        )
        
        folder_path = folder.get('folder_name', '')
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
        
        self._log_message(run_log, f"Processing {len(files)} files in {folder_path}")
        
        for file_path in files:
            file_result = self.process_file(file_path, folder)
            
            if file_result.sent:
                result.files_processed += 1
                self.processed_count += 1
            else:
                result.files_failed += 1
                self.error_count += 1
                result.errors.extend(file_result.errors)
        
        result.success = result.files_failed == 0
        return result
    
    def process_folder_with_pipeline(
        self,
        folder: dict,
        run_log: Any,
        processed_files: Optional[DatabaseInterface] = None,
        upc_dict: Optional[dict] = None
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
            folder_name=folder.get('folder_name', ''),
            alias=folder.get('alias', '')
        )
        
        folder_path = folder.get('folder_name', '')
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
        
        self._log_message(run_log, f"Processing {len(files)} files in {folder_path} (pipeline mode)")
        
        total_files = len(files)
        if self.config.progress_reporter:
            self.config.progress_reporter.start_folder(folder.get('alias', folder_path), total_files)
        
        effective_upc_dict = upc_dict if upc_dict is not None else self.config.upc_dict
        
        for idx, file_path in enumerate(files):
            if self.config.progress_reporter:
                self.config.progress_reporter.update_file(idx + 1, total_files)
            
            file_result = self._process_file_with_pipeline(file_path, folder, effective_upc_dict)
            
            if file_result.sent:
                result.files_processed += 1
                self.processed_count += 1
            else:
                result.files_failed += 1
                self.error_count += 1
                result.errors.extend(file_result.errors)
        
        if self.config.progress_reporter:
            self.config.progress_reporter.complete_folder(result.success)
        
        result.success = result.files_failed == 0
        return result
    
    def _is_pipeline_ready(self) -> bool:
        """Check if pipeline steps are ready for use.
        
        Returns:
            True if pipeline is configured and ready
        """
        return (
            self.config.validator_step is not None or
            self.config.splitter_step is not None or
            self.config.converter_step is not None or
            self.config.tweaker_step is not None or
            self.config.file_processor is not None
        )
    
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
    
    def _initialize_pipeline_steps(self) -> None:
        """Initialize pipeline steps if enabled."""
        if not self.config.use_pipeline:
            return
        
        if self.config.file_processor:
            if hasattr(self.config.file_processor, 'initialize'):
                self.config.file_processor.initialize()
    
    def _process_file_with_pipeline(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict
    ) -> FileResult:
        """Process single file with pipeline.
        
        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary
            upc_dict: UPC dictionary for lookup
            
        Returns:
            FileResult with processing outcome
        """
        result = FileResult(
            file_name=file_path,
            checksum=self._calculate_checksum(file_path)
        )
        
        try:
            current_file = file_path
            
            if self.config.validator_step and self._should_validate(folder):
                validated, errors_or_file = self.config.validator_step.execute(current_file, folder)
                result.validated = validated
                
                if not validated:
                    if isinstance(errors_or_file, list):
                        result.errors.extend(errors_or_file)
                    else:
                        result.errors.append(str(errors_or_file))
                    
                    if not folder.get('force_edi_validation', False):
                        return result
                
                if isinstance(errors_or_file, str):
                    current_file = errors_or_file
            
            if self.config.splitter_step and folder.get('split_edi', False):
                split_files = self.config.splitter_step.execute(current_file, folder)
                
                if split_files and isinstance(split_files, list):
                    for split_file in split_files:
                        send_result = self._send_pipeline_file(split_file, folder)
                        if not send_result:
                            result.errors.append(f"Failed to send split file: {split_file}")
                    
                    result.sent = len(result.errors) == 0
                    return result
            
            if self.config.converter_step and folder.get('convert_edi', False):
                converted_file = self.config.converter_step.execute(current_file, folder)
                if converted_file:
                    current_file = converted_file
                    result.converted = True
            
            if self.config.tweaker_step and folder.get('tweak_edi', False):
                tweaked_file = self.config.tweaker_step.execute(current_file, folder, upc_dict)
                if tweaked_file:
                    current_file = tweaked_file
            
            if self.config.file_processor:
                processed_file = self.config.file_processor.process(current_file, folder)
                if processed_file:
                    current_file = processed_file
            
            result.sent = self._send_pipeline_file(current_file, folder)
            
            if not result.sent:
                result.errors.append(f"Failed to send file: {current_file}")
        
        except Exception as e:
            result.errors.append(str(e))
            self.error_handler.record_error(
                folder=folder.get('folder_name', ''),
                filename=file_path,
                error=e,
                context={'folder_config': folder, 'pipeline_mode': True}
            )
        
        return result
    
    def _send_pipeline_file(self, file_path: str, folder: dict) -> bool:
        """Send file through pipeline to backends.
        
        Args:
            file_path: Path to the file to send
            folder: Folder configuration dictionary
            
        Returns:
            True if file was sent successfully
        """
        enabled_backends = self.send_manager.get_enabled_backends(folder)
        
        if not enabled_backends:
            return False
        
        settings = self.config.settings
        send_results = self.send_manager.send_all(
            enabled_backends, file_path, folder, settings
        )
        
        return all(send_results.values())
    
    def process_file(self, file_path: str, folder: dict) -> FileResult:
        """Process a single file.
        
        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary
            
        Returns:
            FileResult with processing outcome
        """
        if self.config.use_pipeline and self._is_pipeline_ready():
            upc_dict = self._get_upc_dictionary(self.config.settings)
            return self._process_file_with_pipeline(file_path, folder, upc_dict)
        
        return self._process_file_legacy(file_path, folder)
    
    def _process_file_legacy(self, file_path: str, folder: dict) -> FileResult:
        """Process a single file using legacy method.
        
        Args:
            file_path: Path to the file to process
            folder: Folder configuration dictionary
            
        Returns:
            FileResult with processing outcome
        """
        result = FileResult(
            file_name=file_path,
            checksum=self._calculate_checksum(file_path)
        )
        
        try:
            if self._should_validate(folder):
                is_valid, errors = self.validator.validate(file_path)
                result.validated = is_valid
                
                if not is_valid:
                    result.errors.extend(errors)
                    if not folder.get('force_edi_validation', False):
                        return result
            
            enabled_backends = self.send_manager.get_enabled_backends(folder)
            
            if not enabled_backends:
                result.errors.append("No backends enabled")
                return result
            
            settings = self.config.settings
            send_results = self.send_manager.send_all(
                enabled_backends, file_path, folder, settings
            )
            
            result.sent = all(send_results.values())
            
            if not result.sent:
                failed_backends = [
                    name for name, success in send_results.items()
                    if not success
                ]
                result.errors.append(f"Failed backends: {', '.join(failed_backends)}")
        
        except Exception as e:
            result.errors.append(str(e))
            self.error_handler.record_error(
                folder=folder.get('folder_name', ''),
                filename=file_path,
                error=e,
                context={'folder_config': folder}
            )
        
        return result
    
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
        self,
        files: list[str],
        processed_files: DatabaseInterface,
        folder: dict
    ) -> list[str]:
        """Filter out already processed files.
        
        Args:
            files: List of file paths
            processed_files: Database of processed files
            folder: Folder configuration
            
        Returns:
            List of unprocessed file paths
        """
        folder_id = folder.get('id') or folder.get('old_id')
        processed = processed_files.find(folder_id=folder_id)
        
        processed_checksums = {
            f.get('file_checksum') for f in processed
        }
        
        return [
            f for f in files
            if self._calculate_checksum(f) not in processed_checksums
        ]
    
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
            with open(file_path, 'rb') as f:
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
            folder.get('process_edi') == "True" or
            folder.get('tweak_edi', False) or
            folder.get('split_edi', False) or
            folder.get('force_edi_validation', False)
        )
    
    def _log_message(self, run_log: Any, message: str) -> None:
        """Log a message to the run log.
        
        Args:
            run_log: Run log to write to
            message: Message to log
        """
        if hasattr(run_log, 'write'):
            run_log.write((message + "\r\n").encode())
        elif hasattr(run_log, 'append'):
            run_log.append(message)
    
    def _log_error(self, run_log: Any, message: str) -> None:
        """Log an error message to the run log.
        
        Args:
            run_log: Run log to write to
            message: Error message to log
        """
        self._log_message(run_log, f"ERROR: {message}")
    
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
