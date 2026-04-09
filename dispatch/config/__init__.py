"""Dispatch configuration modules.

This package provides typed configuration classes for the dispatch system,
replacing raw dictionary usage with proper dataclasses and validation.
"""

from dispatch.config.folder_config import FolderProcessingConfig

__all__ = [
    "FolderProcessingConfig",
]
