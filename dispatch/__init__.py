"""Dispatch module for batch file processing.

This module contains refactored components for the dispatch system,
designed for testability and loose coupling.
"""

# Import process function from dispatch_process module
from dispatch_process import process

from dispatch.hash_utils import generate_match_lists, generate_file_hash
from dispatch.file_utils import build_output_filename, filter_files_by_checksum, do_clear_old_files
from dispatch.interfaces import (
    DatabaseInterface,
    FileSystemInterface,
    BackendInterface,
)
from dispatch.edi_validator import EDIValidator
from dispatch.send_manager import SendManager
from dispatch.error_handler import ErrorHandler
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.log_sender import (
    EmailConfig,
    LogSender,
    LogEntry,
    SMTPEmailService,
    MockEmailService,
    MockUIService,
    NullUIService,
)
from dispatch.print_service import (
    PrintServiceProtocol,
    WindowsPrintService,
    UnixPrintService,
    MockPrintService,
    NullPrintService,
    RunLogPrinter,
)
from dispatch.processed_files_tracker import (
    ProcessedFileRecord,
    InMemoryDatabase,
    ProcessedFilesTracker,
)

__all__ = [
    # Coordinator
    'process',
    # Hash utilities
    'generate_match_lists',
    'generate_file_hash',
    # File utilities
    'build_output_filename',
    'filter_files_by_checksum',
    'do_clear_old_files',
    # Interfaces
    'DatabaseInterface',
    'FileSystemInterface',
    'BackendInterface',
    # Components
    'EDIValidator',
    'SendManager',
    'ErrorHandler',
    'DispatchConfig',
    'DispatchOrchestrator',
    # Log Sender
    'EmailConfig',
    'LogSender',
    'LogEntry',
    'SMTPEmailService',
    'MockEmailService',
    'MockUIService',
    'NullUIService',
    # Print Service
    'PrintServiceProtocol',
    'WindowsPrintService',
    'UnixPrintService',
    'MockPrintService',
    'NullPrintService',
    'RunLogPrinter',
    # Processed Files Tracker
    'ProcessedFileRecord',
    'InMemoryDatabase',
    'ProcessedFilesTracker',
]
