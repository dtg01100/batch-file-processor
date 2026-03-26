"""
SQLite folder repository implementation.

Wraps the DatabaseObj / Table API (backend.database.database_obj) to
implement IFolderRepository.  This is the production implementation used
by both the Qt desktop app and any future non-Qt consumer (CLI, web, …).

No Qt dependencies — safe to import in any context.
"""

import os
from typing import Any

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

    def find_all(self, active_only: bool = False) -> list[dict[str, Any]]:
        """Return all folder records, optionally filtered to active only."""
        if active_only:
            return list(self._db.folders_table.find(folder_is_active=True))
        return list(self._db.folders_table.all())

    def find_by_id(self, folder_id: int) -> dict[str, Any] | None:
        """Return the folder record with the given primary key."""
        return self._db.folders_table.find_one(id=folder_id)

    def find_by_path(self, path: str) -> dict[str, Any] | None:
        """Return the folder record whose path matches, using normalised comparison.

        Path normalisation is applied so that trailing slashes and
        platform differences do not cause false negatives.
        """
        normalised = os.path.normpath(path)
        for folder in self._db.folders_table.all():
            if os.path.normpath(folder.get("folder_name", "")) == normalised:
                return folder
        return None

    def find_by_alias(self, alias: str) -> dict[str, Any] | None:
        """Return the folder record with the given alias."""
        return self._db.folders_table.find_one(alias=alias)

    def insert(self, folder_data: dict[str, Any]) -> None:
        """Insert a new folder record.

        The caller must *not* include an 'id' key — the database assigns it.
        """
        data = {k: v for k, v in folder_data.items() if k != "id"}
        self._db.folders_table.insert(data)

    def update(self, folder_data: dict[str, Any]) -> None:
        """Update an existing folder record identified by 'id'.

        Raises:
            ValueError: If 'id' is not present in *folder_data*.

        """
        if "id" not in folder_data:
            raise ValueError("folder_data must contain 'id' to update a folder")
        self._db.folders_table.update(folder_data, ["id"])

    def delete(self, folder_id: int) -> None:
        """Delete the folder record with the given primary key."""
        self._db.folders_table.delete(id=folder_id)

    def count(self, active_only: bool = False) -> int:
        """Return the number of folder records."""
        if active_only:
            return self._db.folders_table.count(folder_is_active=True)
        return self._db.folders_table.count()
