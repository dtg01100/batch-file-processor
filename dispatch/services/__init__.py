"""Services for dispatch processing.

This module contains service classes that provide specialized functionality
for the dispatch pipeline.
"""

from dispatch.services.file_processor import (
    FileProcessor,
    FileProcessorInterface,
    FileProcessorResult,
    MockFileProcessor,
)
from dispatch.services.progress_reporter import (
    CLIProgressReporter,
    LoggingProgressReporter,
    NullProgressReporter,
    ProgressReporter,
    UIProgressReporter,
)
from dispatch.services.upc_service import (
    MockQueryRunner,
    QueryRunnerProtocol,
    UPCService,
    UPCServiceResult,
)

__all__ = [
    # UPC Service
    "QueryRunnerProtocol",
    "UPCServiceResult",
    "MockQueryRunner",
    "UPCService",
    # Progress Reporter
    "ProgressReporter",
    "UIProgressReporter",
    "CLIProgressReporter",
    "NullProgressReporter",
    "LoggingProgressReporter",
    # File Processor
    "FileProcessorResult",
    "FileProcessorInterface",
    "MockFileProcessor",
    "FileProcessor",
]
