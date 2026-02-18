"""Services for dispatch processing.

This module contains service classes that provide specialized functionality
for the dispatch pipeline.
"""

from dispatch.services.upc_service import (
    QueryRunnerProtocol,
    UPCServiceResult,
    MockQueryRunner,
    UPCService,
)

from dispatch.services.progress_reporter import (
    ProgressReporter,
    UIProgressReporter,
    CLIProgressReporter,
    NullProgressReporter,
    LoggingProgressReporter,
)

from dispatch.services.file_processor import (
    FileProcessorResult,
    FileProcessorInterface,
    MockFileProcessor,
    FileProcessor,
)

__all__ = [
    # UPC Service
    'QueryRunnerProtocol',
    'UPCServiceResult',
    'MockQueryRunner',
    'UPCService',
    # Progress Reporter
    'ProgressReporter',
    'UIProgressReporter',
    'CLIProgressReporter',
    'NullProgressReporter',
    'LoggingProgressReporter',
    # File Processor
    'FileProcessorResult',
    'FileProcessorInterface',
    'MockFileProcessor',
    'FileProcessor',
]
