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
    """
    database: Optional[DatabaseInterface] = None
    file_system: Optional[FileSystemInterface] = None
    backends: dict[str, BackendInterface] = field(default_factory=dict)
    validator: Optional[ValidatorInterface] = None
    error_handler: Optional[ErrorHandlerInterface] = None
    settings: dict = field(default_factory=dict)
    version: str = "1.0.0"


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
        result = FolderResult(
            folder_name=folder.get('folder_name', ''),
            alias=folder.get('alias', '')
        )
        
        # Check if folder exists
        folder_path = folder.get('folder_name', '')
        if not self._folder_exists(folder_path):
            error_msg = f"Folder not found: {folder_path}"
            result.errors.append(error_msg)
            result.success = False
            result.files_failed = 1
            self._log_error(run_log, error_msg)
            return result
        
        # Get files to process
        files = self._get_files_in_folder(folder_path)
        
        if not files:
            self._log_message(run_log, f"No files in directory: {folder_path}")
            return result
        
        # Filter already processed files
        if processed_files:
            files = self._filter_processed_files(files, processed_files, folder)
        
        if not files:
            self._log_message(run_log, f"No new files in directory: {folder_path}")
            return result
        
        self._log_message(run_log, f"Processing {len(files)} files in {folder_path}")
        
        # Process each file
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
    
    def process_file(self, file_path: str, folder: dict) -> FileResult:
        """Process a single file.
        
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
            # Validate if required
            if self._should_validate(folder):
                is_valid, errors = self.validator.validate(file_path)
                result.validated = is_valid
                
                if not is_valid:
                    result.errors.extend(errors)
                    if not folder.get('force_edi_validation', False):
                        return result
            
            # Get enabled backends
            enabled_backends = self.send_manager.get_enabled_backends(folder)
            
            if not enabled_backends:
                result.errors.append("No backends enabled")
                return result
            
            # Send to backends
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
        # Get processed files for this folder
        folder_id = folder.get('id') or folder.get('old_id')
        processed = processed_files.find(folder_id=folder_id)
        
        # Build set of processed checksums
        processed_checksums = {
            f.get('file_checksum') for f in processed
        }
        
        # Filter files
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
