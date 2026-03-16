"""Feature flags for dispatch module migration.

This module provides feature flag support for safely rolling out
dispatch module changes. Flags can be controlled via environment
variables or database settings.

Environment Variables:
    DISPATCH_DEBUG_MODE: If 'true', enable verbose debug logging

Usage:
    from dispatch.feature_flags import (
        get_debug_mode,
    )
"""

import os


def get_debug_mode() -> bool:
    """Check if debug mode is enabled for dispatch.

    Debug mode enables verbose logging of dispatch operations
    for troubleshooting.

    Returns:
        True if DISPATCH_DEBUG_MODE is 'true'
    """
    return os.environ.get("DISPATCH_DEBUG_MODE", "false").lower() == "true"


def get_feature_flags() -> dict:
    """Get all feature flag values.

    Returns:
        Dictionary of feature flag names to their current values
    """
    return {
        "debug_mode": get_debug_mode(),
    }


def set_feature_flag(name: str, value: bool) -> None:
    """Set a feature flag value.

    This sets the environment variable for the current process.

    Args:
        name: Feature flag name
        value: Boolean value to set

    Raises:
        ValueError: If the feature flag name is unknown
    """
    flag_map = {"debug_mode": "DISPATCH_DEBUG_MODE"}

    if name not in flag_map:
        raise ValueError(
            f"Unknown feature flag: {name}. " f"Valid flags: {list(flag_map.keys())}"
        )

    os.environ[flag_map[name]] = "true" if value else "false"


__all__ = [
    "get_debug_mode",
    "get_feature_flags",
    "set_feature_flag",
]
