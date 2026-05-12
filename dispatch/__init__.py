"""Dispatch module for batch file processing.

This module contains refactored components for the dispatch system,
designed for testability and loose coupling.

Feature Flags:
    DISPATCH_DEBUG_MODE: Set to 'true' for verbose debug logging
"""

from dispatch.feature_flags import get_debug_mode, get_feature_flags, set_feature_flag

__all__ = [
    "get_debug_mode",
    "get_feature_flags",
    "set_feature_flag",
]
