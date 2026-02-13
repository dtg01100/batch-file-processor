"""
Compatibility layer for legacy dispatch imports.

This module provides backward-compatible imports with deprecation warnings.
All new code should import directly from the dispatch/ package modules.

Usage:
    # DEPRECATED (will show warning):
    from dispatch.compatibility import DispatchCoordinator
    
    # RECOMMENDED:
    from dispatch import DispatchCoordinator
    # or
    from dispatch.coordinator import DispatchCoordinator

Feature Flag:
    Set BATCH_PROCESSOR_USE_LEGACY_DISPATCH=true to use legacy behavior
    for rollback purposes. This is intended for emergency rollback only.
"""

import importlib
import os
import warnings
from typing import Any, Optional

# Feature flag for rollback capability
USE_LEGACY_DISPATCH = os.environ.get('BATCH_PROCESSOR_USE_LEGACY_DISPATCH', 'false').lower() == 'true'

# Module-level flag to track if deprecation warning has been shown
_deprecation_warning_shown = False


def _show_deprecation_warning(imported_name: str, stacklevel: int = 3) -> None:
    """Show a deprecation warning for imports from this compatibility layer.
    
    Args:
        imported_name: The name of the symbol being imported
        stacklevel: Stack level for the warning (default 3 for __getattr__)
    """
    global _deprecation_warning_shown
    
    # Only show the warning once per session to avoid spam
    if not _deprecation_warning_shown:
        _deprecation_warning_shown = True
        warnings.warn(
            f"Importing '{imported_name}' from dispatch.compatibility is deprecated. "
            f"Import directly from the dispatch package instead. "
            f"For example: 'from dispatch import {imported_name}' or "
            f"'from dispatch.coordinator import {imported_name}'.",
            DeprecationWarning,
            stacklevel=stacklevel
        )


# Define all public exports from the dispatch package
# This maps names to their source modules
_EXPORT_MAPPING = {
    # From coordinator.py
    'DispatchCoordinator': '.coordinator',
    'ProcessingContext': '.coordinator',
    'process': '.coordinator',
    
    # From file_processor.py
    'FileDiscoverer': '.file_processor',
    'HashGenerator': '.file_processor',
    'FileFilter': '.file_processor',
    'generate_match_lists': '.file_processor',
    'generate_file_hash': '.file_processor',
    
    # From edi_validator.py
    'EDIValidator': '.edi_validator',
    'ValidationResult': '.edi_validator',
    
    # From edi_processor.py
    'EDISplitter': '.edi_processor',
    'EDIConverter': '.edi_processor',
    'EDITweaker': '.edi_processor',
    'FileNamer': '.edi_processor',
    
    # From send_manager.py
    'SendManager': '.send_manager',
    'BackendFactory': '.send_manager',
    'SendResult': '.send_manager',
    
    # From error_handler.py
    'ErrorHandler': '.error_handler',
    'ErrorLogger': '.error_handler',
    'ReportGenerator': '.error_handler',
    
    # From db_manager.py
    'DBManager': '.db_manager',
    'ProcessedFilesTracker': '.db_manager',
    'ResendFlagManager': '.db_manager',
}

# All public exports
__all__ = list(_EXPORT_MAPPING.keys()) + ['USE_LEGACY_DISPATCH']


def __getattr__(name: str) -> Any:
    """Lazy import with deprecation warning.
    
    This allows importing any public API from this module while
    showing a deprecation warning directing users to the correct import path.
    
    Args:
        name: The name of the symbol to import
        
    Returns:
        The requested symbol from its source module
        
    Raises:
        AttributeError: If the name is not a public export
    """
    if name in _EXPORT_MAPPING:
        _show_deprecation_warning(name)
        
        module_name = _EXPORT_MAPPING[name]
        # Use importlib for proper relative imports
        module = importlib.import_module(module_name, package='dispatch')
        return getattr(module, name)
    
    raise AttributeError(
        f"module '{__name__}' has no attribute '{name}'. "
        f"Available exports: {', '.join(sorted(_EXPORT_MAPPING.keys()))}"
    )


def get_legacy_mode() -> bool:
    """Check if legacy mode is enabled via feature flag.
    
    Returns:
        True if BATCH_PROCESSOR_USE_LEGACY_DISPATCH=true, False otherwise
    """
    return USE_LEGACY_DISPATCH


def get_recommended_import(name: str) -> Optional[str]:
    """Get the recommended import statement for a given symbol.
    
    Args:
        name: The name of the symbol
        
    Returns:
        A string with the recommended import statement, or None if not found
    """
    if name in _EXPORT_MAPPING:
        return f"from dispatch import {name}"
    return None


def list_available_exports() -> list:
    """List all available exports from this compatibility layer.
    
    Returns:
        Sorted list of all public export names
    """
    return sorted(_EXPORT_MAPPING.keys())
