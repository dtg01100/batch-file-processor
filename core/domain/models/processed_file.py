"""
ProcessedFile domain model.

Represents a record in the processed_files table.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessedFile:
    """A record indicating that a specific file has been processed.

    Attributes:
        file_hash: Hash string uniquely identifying the file content.
        folder_id: Foreign key to the folders table.
        filename: Original filename (for audit/display purposes).
        id: Primary key, assigned by the database on insert.
    """

    file_hash: str
    folder_id: int
    filename: str
    id: Optional[int] = None
