"""Services for dispatch processing.

This module contains service classes that provide specialized functionality
for the dispatch pipeline.

IMPORT NOTE (import cycle): this package eagerly re-exports its submodules,
so ANY ``import dispatch.services.<submodule>`` runs this whole file first.
That makes ``dispatch.services`` a fan-in hub: ``dispatch.results`` must not
runtime-import anything here (it uses ``TYPE_CHECKING`` for
``ProgressReporter``), and no ``dispatch.services.*`` module may
module-level-import ``dispatch.pipeline.*`` (``file_processor`` keeps those
imports function-local). Otherwise the cycle
``dispatch.results -> dispatch.services -> dispatch.pipeline ->
dispatch.results`` comes back — see ``docs/IMPORT_ARCHITECTURE.md``.
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
    "CLIProgressReporter",
    # File Processor
    "FileProcessor",
    "FileResult",
    # Folder Discovery
    "FolderDiscoveryService",
    "LoggingProgressReporter",
    "NullProgressReporter",
    "ProcessingContext",
    # Progress Reporter
    "ProgressReporter",
    # Progress Reporting
    "ProgressReportingService",
    "UIProgressReporter",
    # UPC Service
    "UPCLookupService",
]
