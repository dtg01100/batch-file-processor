"""
SQLite processed-files repository implementation.

Wraps the DatabaseObj / Table API (backend.database.database_obj) to
implement :class:`core.ports.repositories.IProcessedFilesRepository`.
"""

from typing import Any

from core.domain.models.processed_file import ProcessedFile
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

    def mark_processed(self, record: ProcessedFile) -> None:
        """Insert a processed-file record.

        The record's ``id`` (if set) is ignored — the database assigns one.
        """
        data = {
            "file_hash": record.file_hash,
            "folder_id": record.folder_id,
            "filename": record.filename,
        }
        self._db.processed_files.insert(data)

    def clear_all(self) -> int:
        """Delete all records and return the count removed."""
        count = int(self._db.processed_files.count())
        self._db.processed_files.delete()
        return count

    def clear_for_folder(self, folder_id: int) -> int:
        """Delete processed-file records for one folder and return the count removed."""
        count = int(self._db.processed_files.count(folder_id=folder_id))
        self._db.processed_files.delete(folder_id=folder_id)
        return count

    def find_by_hash(self, file_hash: str) -> ProcessedFile | None:
        """Return the processed-file record for *file_hash*, or None."""
        row = self._db.processed_files.find_one(file_hash=file_hash)
        return _row_to_record(row) if row is not None else None


def _row_to_record(row: dict[str, Any]) -> ProcessedFile:
    """Map a raw processed_files row to a ProcessedFile domain object.

    The table may carry extra columns added by later migrations (status,
    sent_to, processed_path, …). The domain model only knows about the
    canonical subset; other columns are ignored.
    """
    return ProcessedFile(
        id=row.get("id"),
        file_hash=row["file_hash"],
        folder_id=int(row["folder_id"]),
        filename=row.get("filename", ""),
    )
