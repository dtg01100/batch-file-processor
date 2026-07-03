"""
SQLite folder repository implementation.

Wraps the DatabaseObj / Table API (backend.database.database_obj) to
implement :class:`core.ports.repositories.IFolderRepository`.  This is
the production implementation used by both the Qt desktop app and any
future non-Qt consumer (CLI, web, …).

No Qt dependencies — safe to import in any context.
"""

import os
from typing import Any

from core.domain.models.folder import FolderConfiguration
from core.ports.repositories import IFolderRepository


class SqliteFolderRepository(IFolderRepository):
    """Folder repository backed by the existing DatabaseObj Table API.

    Args:
        database_obj: A ``backend.database.database_obj.DatabaseObj`` instance
            (or any object that exposes a ``folders_table`` attribute
            implementing the ``TableProtocol``).

    Example::

        from backend.database.database_obj import DatabaseObj
        from adapters.sqlite.repositories import SqliteFolderRepository

        db = DatabaseObj(...)
        repo = SqliteFolderRepository(db)
        folders = repo.find_all(active_only=True)

    """

    def __init__(self, database_obj: Any) -> None:
        self._db = database_obj

    # ------------------------------------------------------------------
    # IFolderRepository implementation
    # ------------------------------------------------------------------

    def find_all(self, *, active_only: bool = False) -> list[FolderConfiguration]:
        """Return all folder records, optionally filtered to active only."""
        if active_only:
            rows = list(self._db.folders_table.find(folder_is_active=True))
        else:
            rows = list(self._db.folders_table.all())
        return [_row_to_folder(row) for row in rows]

    def find_by_id(self, folder_id: int) -> FolderConfiguration | None:
        """Return the folder record with the given primary key."""
        row = self._db.folders_table.find_one(id=folder_id)
        return _row_to_folder(row) if row is not None else None

    def find_by_path(self, path: str) -> FolderConfiguration | None:
        """Return the folder record whose path matches, using normalised comparison.

        Path normalisation is applied so that trailing slashes and
        platform differences do not cause false negatives.
        """
        normalised = os.path.normpath(path)
        for row in self._db.folders_table.all():
            if os.path.normpath(row.get("folder_name", "")) == normalised:
                return _row_to_folder(row)
        return None

    def find_by_alias(self, alias: str) -> FolderConfiguration | None:
        """Return the folder record with the given alias."""
        row = self._db.folders_table.find_one(alias=alias)
        return _row_to_folder(row) if row is not None else None

    def insert(self, folder: FolderConfiguration) -> int:
        """Insert a new folder record and return the assigned primary key.

        The folder's ``id`` is intentionally ignored — the database
        assigns one.  This keeps the round-trip ``from_dict(row) → to_dict``
        lossless for non-PK fields.
        """
        data = folder.to_dict()
        # ``to_dict`` does not include 'id' for a reason; nothing to strip.
        return int(self._db.folders_table.insert(data))

    def update(self, folder: FolderConfiguration, folder_id: int) -> None:
        """Update an existing folder record identified by *folder_id*.

        Raises:
            ValueError: If folder_id is not a positive int.

        """
        if not isinstance(folder_id, int) or folder_id <= 0:
            raise ValueError("folder_id must be a positive int")
        data = folder.to_dict()
        data["id"] = folder_id
        self._db.folders_table.update(data, ["id"])

    def delete(self, folder_id: int) -> None:
        """Delete the folder record with the given primary key."""
        self._db.folders_table.delete(id=folder_id)

    def count(self, *, active_only: bool = False) -> int:
        """Return the number of folder records."""
        if active_only:
            return int(self._db.folders_table.count(folder_is_active=True))
        return int(self._db.folders_table.count())


def _row_to_folder(row: dict[str, Any]) -> FolderConfiguration:
    """Map a raw row dict to a FolderConfiguration.

    The row's ``id`` is preserved on the domain object so callers can
    round-trip a record without losing the primary key.
    """
    return FolderConfiguration.from_dict(row)
