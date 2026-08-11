"""Operations package for interface module.

This package contains operation classes that handle business logic
for folder and data management.

Available operations:
- FolderManager: CRUD operations for folder configurations
- FolderDataExtractor: Extract folder data for display
"""

from interface.operations.folder_data_extractor import FolderDataExtractor
from interface.operations.folder_manager import FolderManager

__all__ = ["FolderDataExtractor", "FolderManager"]
