"""Compatibility layer for legacy dispatch imports.

This module provides backward-compatible imports with deprecation warnings.
All new code should import directly from dispatch package modules.

Migration Guide:
    OLD: from dispatch import process
    NEW: from dispatch import DispatchOrchestrator, DispatchConfig
         orchestrator = DispatchOrchestrator(config)
         result = orchestrator.process(...)

    OLD: from dispatch import generate_match_lists
    NEW: from dispatch.hash_utils import generate_match_lists

    OLD: from dispatch import EDIValidator
    NEW: from dispatch.edi_validator import EDIValidator

Deprecation Timeline:
    - v1.0: Compatibility layer introduced (current)
    - v1.1: Deprecation warnings added
    - v2.0: Compatibility layer removed, direct imports required
"""

import warnings
from typing import Any

# Module-level deprecation message
_DEPRECATION_MSG = (
    "Importing {name} from dispatch.compatibility is deprecated. "
    "Import directly from dispatch module instead. "
    "See dispatch/compatibility.py for migration guide."
)


def __getattr__(name: str) -> Any:
    """Lazy import with deprecation warning.
    
    This allows importing any name from dispatch.compatibility
    while issuing a deprecation warning.
    
    Args:
        name: The name to import
        
    Returns:
        The requested object from the dispatch package
        
    Raises:
        AttributeError: If the name doesn't exist in dispatch
    """
    # Map of legacy names to their new locations
    _import_map = {
        # Core components
        'DispatchOrchestrator': 'dispatch.orchestrator',
        'DispatchConfig': 'dispatch.orchestrator',
        'FolderResult': 'dispatch.orchestrator',
        'FileResult': 'dispatch.orchestrator',
        # Validators
        'EDIValidator': 'dispatch.edi_validator',
        # Managers
        'SendManager': 'dispatch.send_manager',
        'ErrorHandler': 'dispatch.error_handler',
        # Hash utilities
        'generate_match_lists': 'dispatch.hash_utils',
        'generate_file_hash': 'dispatch.hash_utils',
        # File utilities
        'build_output_filename': 'dispatch.file_utils',
        'filter_files_by_checksum': 'dispatch.file_utils',
        'do_clear_old_files': 'dispatch.file_utils',
        # Interfaces
        'DatabaseInterface': 'dispatch.interfaces',
        'FileSystemInterface': 'dispatch.interfaces',
        'BackendInterface': 'dispatch.interfaces',
        # Log Sender
        'EmailConfig': 'dispatch.log_sender',
        'LogSender': 'dispatch.log_sender',
        'LogEntry': 'dispatch.log_sender',
        'SMTPEmailService': 'dispatch.log_sender',
        'MockEmailService': 'dispatch.log_sender',
        'MockUIService': 'dispatch.log_sender',
        'NullUIService': 'dispatch.log_sender',
        # Print Service
        'PrintServiceProtocol': 'dispatch.print_service',
        'WindowsPrintService': 'dispatch.print_service',
        'UnixPrintService': 'dispatch.print_service',
        'MockPrintService': 'dispatch.print_service',
        'NullPrintService': 'dispatch.print_service',
        'RunLogPrinter': 'dispatch.print_service',
        # Processed Files Tracker
        'ProcessedFileRecord': 'dispatch.processed_files_tracker',
        'InMemoryDatabase': 'dispatch.processed_files_tracker',
        'ProcessedFilesTracker': 'dispatch.processed_files_tracker',
    }
    
    if name in _import_map:
        warnings.warn(
            _DEPRECATION_MSG.format(name=name),
            DeprecationWarning,
            stacklevel=3
        )
        module_path = _import_map[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    
    # Special case: process function
    if name == 'process':
        warnings.warn(
            _DEPRECATION_MSG.format(name='process') + 
            " Use DispatchOrchestrator.process() instead.",
            DeprecationWarning,
            stacklevel=3
        )
        from dispatch.orchestrator import DispatchOrchestrator
        return DispatchOrchestrator.process
    
    raise AttributeError(
        f"module 'dispatch.compatibility' has no attribute '{name}'"
    )


# Note: We don't use __all__ here because the lazy loading via __getattr__
# handles all exports dynamically. Static analysis tools won't see these
# exports, but they work correctly at runtime. Use dispatch/__init__.py
# for static exports.
