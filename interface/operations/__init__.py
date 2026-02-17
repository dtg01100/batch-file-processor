"""Operations package for interface module.

This package contains operation classes that handle business logic
for folder and data management.

Available operations:
- FolderManager: CRUD operations for folder configurations
- FolderDataExtractor: Extract folder data for display
"""

from interface.operations.folder_manager import FolderManager
from interface.operations.folder_data_extractor import FolderDataExtractor

__all__ = [
    "FolderManager",
    "FolderDataExtractor",
]
