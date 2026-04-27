"""
Core domain models.

These are the canonical data models for the application domain.
"""

from .folder import FolderConfiguration
from .processed_file import ProcessedFile

__all__ = [
    "FolderConfiguration",
    "ProcessedFile",
]
