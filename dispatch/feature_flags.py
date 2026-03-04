"""Feature flags for dispatch module migration.

This module provides feature flag support for safely rolling out
dispatch module changes. Flags can be controlled via environment
variables or database settings.

Environment Variables:
    USE_LEGACY_DISPATCH: If 'true', use legacy dispatch behavior
    DISPATCH_PIPELINE_ENABLED: If 'false', disable new pipeline
    DISPATCH_DEBUG_MODE: If 'true', enable verbose debug logging

Usage:
    from dispatch.feature_flags import (
        is_legacy_mode,
        is_pipeline_enabled,
        get_debug_mode,
    )
    
    if is_legacy_mode():
        # Use legacy behavior
        pass
    else:
        # Use new behavior
        pass
"""

import os
from typing import Optional


def is_legacy_mode() -> bool:
    """Check if legacy dispatch mode is enabled.
    
    When true, the dispatch module uses legacy behavior for
    backward compatibility during migration.
    
    Returns:
        True if USE_LEGACY_DISPATCH environment variable is 'true'
    """
    return os.environ.get('USE_LEGACY_DISPATCH', 'false').lower() == 'true'


def is_pipeline_enabled() -> bool:
    """Check if the new pipeline architecture is enabled.
    
    The pipeline architecture provides better testability and
    separation of concerns. When disabled, the legacy monolithic
    processing path is used.
    
    Returns:
        True if pipeline is enabled (default), False otherwise
    """
    return os.environ.get('DISPATCH_PIPELINE_ENABLED', 'true').lower() == 'true'


def get_debug_mode() -> bool:
    """Check if debug mode is enabled for dispatch.
    
    Debug mode enables verbose logging of dispatch operations
    for troubleshooting.
    
    Returns:
        True if DISPATCH_DEBUG_MODE is 'true'
    """
    return os.environ.get('DISPATCH_DEBUG_MODE', 'false').lower() == 'true'


def get_feature_flags() -> dict:
    """Get all feature flag values.
    
    Returns:
        Dictionary of feature flag names to their current values
    """
    return {
        'legacy_mode': is_legacy_mode(),
        'pipeline_enabled': is_pipeline_enabled(),
        'debug_mode': get_debug_mode(),
    }


def set_feature_flag(name: str, value: bool) -> None:
    """Set a feature flag value.
    
    This sets the environment variable for the current process.
    
    Args:
        name: Feature flag name (without DISPATCH_ prefix)
        value: Boolean value to set
        
    Raises:
        ValueError: If the feature flag name is unknown
    """
    flag_map = {
        'legacy_mode': 'USE_LEGACY_DISPATCH',
        'pipeline_enabled': 'DISPATCH_PIPELINE_ENABLED',
        'debug_mode': 'DISPATCH_DEBUG_MODE',
    }
    
    if name not in flag_map:
        raise ValueError(
            f"Unknown feature flag: {name}. "
            f"Valid flags: {list(flag_map.keys())}"
        )
    
    os.environ[flag_map[name]] = 'true' if value else 'false'


__all__ = [
    'is_legacy_mode',
    'is_pipeline_enabled',
    'get_debug_mode',
    'get_feature_flags',
    'set_feature_flag',
]
