"""Dispatch module for batch file processing.

This module contains refactored components for the dispatch system,
designed for testability and loose coupling.

Feature Flags:
    USE_LEGACY_DISPATCH: Set to 'true' for legacy behavior during migration
    DISPATCH_PIPELINE_ENABLED: Set to 'false' to disable new pipeline
    DISPATCH_DEBUG_MODE: Set to 'true' for verbose debug logging
"""

from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler
from dispatch.feature_flags import (
    get_debug_mode,
    get_feature_flags,
    is_legacy_mode,
    is_pipeline_enabled,
    set_feature_flag,
)
from dispatch.file_utils import (
    build_output_filename,
    do_clear_old_files,
)
from dispatch.hash_utils import generate_file_hash, generate_match_lists
from dispatch.interfaces import (
    BackendInterface,
    DatabaseInterface,
    FileSystemInterface,
)
from dispatch.log_sender import (
    EmailConfig,
    LogEntry,
    LogSender,
    MockEmailService,
    MockUIService,
    NullUIService,
    SMTPEmailService,
)
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
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
from dispatch.send_manager import SendManager

# Import process function after modules are fully loaded to avoid circular imports

process = DispatchOrchestrator.process

__all__ = [
    # Hash utilities
    "generate_match_lists",
    "generate_file_hash",
    # File utilities
    "build_output_filename",
    "do_clear_old_files",
    # Interfaces
    "DatabaseInterface",
    "FileSystemInterface",
    "BackendInterface",
    # Components
    "EDIValidator",
    "SendManager",
    "ErrorHandler",
    "DispatchConfig",
    "DispatchOrchestrator",
    "process",
    # Feature Flags
    "is_legacy_mode",
    "is_pipeline_enabled",
    "get_debug_mode",
    "get_feature_flags",
    "set_feature_flag",
    # Log Sender
    "EmailConfig",
    "LogSender",
    "LogEntry",
    "SMTPEmailService",
    "MockEmailService",
    "MockUIService",
    "NullUIService",
    # Print Service
    "PrintServiceProtocol",
    "WindowsPrintService",
    "UnixPrintService",
    "MockPrintService",
    "NullPrintService",
    "RunLogPrinter",
    # Processed Files Tracker
    "ProcessedFileRecord",
    "InMemoryDatabase",
    "ProcessedFilesTracker",
]
