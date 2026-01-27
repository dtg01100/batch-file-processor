"""
Dispatch module for batch-file-processor.

This module provides the main dispatch functionality for processing files through
the batch-file-processor system. It coordinates file discovery, EDI validation,
EDI processing, file sending, and error handling.
"""

from .coordinator import DispatchCoordinator, process, ProcessingContext
from .file_processor import FileDiscoverer, HashGenerator, FileFilter, generate_match_lists
from .edi_validator import EDIValidator, ValidationResult
from .edi_processor import EDISplitter, EDIConverter, EDITweaker, FileNamer
from .send_manager import SendManager, BackendFactory, SendResult
from .error_handler import ErrorHandler, ErrorLogger, ReportGenerator
from .db_manager import DBManager, ProcessedFilesTracker, ResendFlagManager

# Keep backward compatible exports of the old function names
# These are now wrappers that delegate to the new classes
from .file_processor import generate_file_hash

__all__ = [
    'DispatchCoordinator',
    'process',
    'ProcessingContext',
    'FileDiscoverer',
    'HashGenerator',
    'FileFilter',
    'generate_match_lists',
    'generate_file_hash',
    'EDIValidator',
    'ValidationResult',
    'EDISplitter',
    'EDIConverter',
    'EDITweaker',
    'FileNamer',
    'SendManager',
    'BackendFactory',
    'SendResult',
    'ErrorHandler',
    'ErrorLogger',
    'ReportGenerator',
    'DBManager',
    'ProcessedFilesTracker',
    'ResendFlagManager',
]
