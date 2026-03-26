"""
SQLite processed-files repository implementation.

Wraps the DatabaseObj / Table API to implement IProcessedFilesRepository.
"""

from typing import Any

from core.ports.repositories import IProcessedFilesRepository


class SqliteProcessedFilesRepository(IProcessedFilesRepository):
    """Processed-files repository backed by DatabaseObj.

    Args:
        database_obj: A ``DatabaseObj`` instance (or compatible mock).

    """

    def __init__(self, database_obj: Any) -> None:
        self._db = database_obj

    # ------------------------------------------------------------------
    # IProcessedFilesRepository implementation
    # ------------------------------------------------------------------

    def is_processed(self, file_hash: str) -> bool:
        """Return True if *file_hash* exists in the processed_files table."""
        return self._db.processed_files.find_one(file_hash=file_hash) is not None

    def mark_processed(self, file_hash: str, folder_id: int, filename: str) -> None:
        """Insert a processed-file record."""
        self._db.processed_files.insert(
            {
                "file_hash": file_hash,
                "folder_id": folder_id,
                "filename": filename,
            }
        )

    def clear_all(self) -> int:
        """Delete all records and return the count removed."""
        count = self._db.processed_files.count()
        self._db.processed_files.delete()
        return count

    def clear_for_folder(self, folder_id: int) -> int:
        """Delete processed-file records for one folder and return the count removed."""
        count = self._db.processed_files.count(folder_id=folder_id)
        self._db.processed_files.delete(folder_id=folder_id)
        return count

    def find_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        """Return the processed-file record for *file_hash*, or None."""
        return self._db.processed_files.find_one(file_hash=file_hash)
