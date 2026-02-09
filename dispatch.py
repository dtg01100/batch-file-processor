"""
Legacy dispatch module - Forward compatibility wrapper.

This module provides forward compatibility for imports that expect the legacy
dispatch.py module. All functionality has been moved to the modern dispatch/
package structure.

DEPRECATED: Use the modern dispatch/ package instead.
"""

# Import all the modern dispatch components for backward compatibility
from dispatch.coordinator import DispatchCoordinator, ProcessingContext
from dispatch.file_processor import FileDiscoverer, HashGenerator, FileFilter
from dispatch.edi_validator import EDIValidator
from dispatch.edi_processor import EDISplitter, EDIConverter, EDITweaker, FileNamer
from dispatch.send_manager import SendManager
from dispatch.error_handler import ErrorHandler, ErrorLogger
from dispatch.db_manager import DBManager

# Legacy function compatibility wrappers
from dispatch.file_processor import generate_match_lists, generate_file_hash

# For legacy imports that expect the 'process' function
def process(*args, **kwargs):
    """Legacy process function wrapper.
    
    This forwards to the modern processing system.
    """
    from dispatch.coordinator import DispatchCoordinator
    coordinator = DispatchCoordinator()
    return coordinator.process(*args, **kwargs)

# Export everything for backward compatibility
__all__ = [
    'DispatchCoordinator', 'ProcessingContext',
    'FileDiscoverer', 'HashGenerator', 'FileFilter',
    'EDIValidator', 'EDISplitter', 'EDIConverter', 'EDITweaker', 'FileNamer',
    'SendManager', 'ErrorHandler', 'ErrorLogger', 'DBManager',
    'generate_match_lists', 'generate_file_hash', 'process'
]