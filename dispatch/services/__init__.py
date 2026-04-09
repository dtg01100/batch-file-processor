"""Services for dispatch processing.

This module contains service classes that provide specialized functionality
for the dispatch pipeline.
"""

from dispatch.services.file_processor import (
    FileProcessor,
    FileResult,
    ProcessingContext,
)
from dispatch.services.folder_discovery import FolderDiscoveryService
from dispatch.services.progress_reporter import (
    CLIProgressReporter,
    LoggingProgressReporter,
    NullProgressReporter,
    ProgressReporter,
    UIProgressReporter,
)
from dispatch.services.progress_reporting import ProgressReportingService
from dispatch.services.upc_service import UPCLookupService

__all__ = [
    # File Processor
    "FileProcessor",
    "FileResult",
    "ProcessingContext",
    # Folder Discovery
    "FolderDiscoveryService",
    # Progress Reporting
    "ProgressReportingService",
    # UPC Service
    "UPCLookupService",
    # Progress Reporter
    "ProgressReporter",
    "UIProgressReporter",
    "CLIProgressReporter",
    "NullProgressReporter",
    "LoggingProgressReporter",
]
