"""
In-memory folder repository.

Pure-Python implementation of :class:`IFolderRepository` for tests
and ephemeral contexts. The store is a process-local dict keyed by
the row's primary key; ids are auto-assigned from a monotonic counter.

This adapter is **not** thread-safe — it is intended for unit tests
and single-threaded use. Do not use it in production.
"""

import os
from typing import Any

from core.domain.models.folder import FolderConfiguration
from core.ports.repositories import IFolderRepository


class InMemoryFolderRepository(IFolderRepository):
    """Folder repository backed by an in-process dict."""

    def __init__(self) -> None:
        self._rows: dict[int, dict[str, Any]] = {}
        self._next_id: int = 1

    def _next_pk(self) -> int:
        pk = self._next_id
        self._next_id += 1
        return pk

    @staticmethod
    def _to_folder(row: dict[str, Any]) -> FolderConfiguration:
        return FolderConfiguration.from_dict(row)

    # ------------------------------------------------------------------
    # IFolderRepository
    # ------------------------------------------------------------------

    def find_all(self, *, active_only: bool = False) -> list[FolderConfiguration]:
        rows = list(self._rows.values())
        if active_only:
            rows = [r for r in rows if r.get("folder_is_active")]
        return [self._to_folder(r) for r in rows]

    def find_by_id(self, folder_id: int) -> FolderConfiguration | None:
        row = self._rows.get(folder_id)
        return self._to_folder(row) if row is not None else None

    def find_by_path(self, path: str) -> FolderConfiguration | None:
        normalised = os.path.normpath(path)
        for row in self._rows.values():
            if os.path.normpath(row.get("folder_name", "")) == normalised:
                return self._to_folder(row)
        return None

    def find_by_alias(self, alias: str) -> FolderConfiguration | None:
        for row in self._rows.values():
            if row.get("alias") == alias:
                return self._to_folder(row)
        return None

    def insert(self, folder: FolderConfiguration) -> int:
        """Insert a new folder, assign a primary key, and return it."""
        pk = self._next_pk()
        row = folder.to_dict()
        row["id"] = pk
        self._rows[pk] = row
        return pk

    def update(self, folder: FolderConfiguration, folder_id: int) -> None:
        if not isinstance(folder_id, int) or folder_id <= 0:
            raise ValueError("folder_id must be a positive int")
        if folder_id not in self._rows:
            return
        row = folder.to_dict()
        row["id"] = folder_id
        self._rows[folder_id] = row

    def delete(self, folder_id: int) -> None:
        self._rows.pop(folder_id, None)

    def count(self, *, active_only: bool = False) -> int:
        if not active_only:
            return len(self._rows)
        return sum(1 for r in self._rows.values() if r.get("folder_is_active"))
