"""
ProcessedFile domain model.

Represents a record in the processed_files table.
"""

from dataclasses import dataclass


@dataclass
class ProcessedFile:
    """A record indicating that a specific file has been processed.

    Attributes:
        file_checksum: Checksum string uniquely identifying the file
            content (md5/sha256/etc — content fingerprint only).
        folder_id: Foreign key to the folders table.
        filename: Original filename (for audit/display purposes).
        id: Primary key, assigned by the database on insert.

    """

    file_checksum: str
    folder_id: int
    filename: str
    id: int | None = None
