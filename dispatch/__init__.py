"""Dispatch module for batch file processing.

This module contains refactored components for the dispatch system,
designed for testability and loose coupling.

Feature Flags:
    DISPATCH_DEBUG_MODE: Set to 'true' for verbose debug logging
"""

from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler
from dispatch.feature_flags import get_debug_mode, get_feature_flags, set_feature_flag
from dispatch.file_utils import build_output_filename, do_clear_old_files
from dispatch.hash_utils import generate_file_hash, generate_match_lists
from dispatch.interfaces import BackendInterface, DatabaseInterface, FileSystemInterface
from dispatch.legacy_process import process
from dispatch.log_sender import (
    EmailConfig,
    LogEntry,
    LogSender,
    MockEmailService,
    MockUIService,
    NullUIService,
    SMTPEmailService,
)
from dispatch.orchestrator import DispatchOrchestrator
from dispatch.preflight_validator import (
    PreflightIssue,
    PreflightResult,
    PreflightValidator,
)
from dispatch.print_service import (
    MockPrintService,
    NullPrintService,
    PrintServiceProtocol,
    RunLogPrinter,
    UnixPrintService,
    WindowsPrintService,
)
from dispatch.processed_files_tracker import (
    InMemoryDatabase,
    ProcessedFileRecord,
    ProcessedFilesTracker,
)
from dispatch.results import DispatchConfig, FolderResult
from dispatch.send_manager import SendManager

__all__ = [
    "BackendInterface",
    # Interfaces
    "DatabaseInterface",
    "DispatchConfig",
    "DispatchOrchestrator",
    # Components
    "EDIValidator",
    # Log Sender
    "EmailConfig",
    "ErrorHandler",
    "FileSystemInterface",
    "FolderResult",
    "InMemoryDatabase",
    "LogEntry",
    "LogSender",
    "MockEmailService",
    "MockPrintService",
    "MockUIService",
    "NullPrintService",
    "NullUIService",
    "PreflightIssue",
    "PreflightResult",
    # Preflight Validation
    "PreflightValidator",
    # Print Service
    "PrintServiceProtocol",
    # Processed Files Tracker
    "ProcessedFileRecord",
    "ProcessedFilesTracker",
    "RunLogPrinter",
    "SMTPEmailService",
    "SendManager",
    "UnixPrintService",
    "WindowsPrintService",
    # File utilities
    "build_output_filename",
    "do_clear_old_files",
    "generate_file_hash",
    # Hash utilities
    "generate_match_lists",
    # Feature Flags
    "get_debug_mode",
    "get_feature_flags",
    # Legacy process function
    "process",
    "set_feature_flag",
]
