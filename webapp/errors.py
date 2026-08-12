"""Error ledger access for the webapp (phase 5.1).

Phase 5.2 extends the module with ``insert_error``, used by the folder
watcher to record scan failures into the same ledger.


The dispatch pipeline already captures processing failures through
``dispatch.error_handler.ErrorHandler``; before phase 5.1 those errors
only landed in flat files under ``data/config/errors/`` because the
webapp runner never passed a ``database``. This module provides:

- ``LedgerDatabase``: adapts the webapp's ``DatabaseObj`` to the
  dispatch ``DatabaseInterface`` contract so ``ErrorHandler``'s
  ``_persist_to_database`` can write rows into ``dispatch_errors``.
- ``list_errors`` / ``clear_errors``: the SQL helpers the API uses to
  query and clear the ledger.

The ``dispatch_errors`` table itself is created idempotently in
``webapp.database._ensure_columns`` (no migration version bump — the
same pattern the watcher columns use).
"""

from __future__ import annotations

import time
from typing import Any

# Columns ``_persist_to_database`` actually writes. ``stack_trace`` and
# ``created_at`` exist in the schema for future use (e.g. watcher scan
# errors) but the dispatch layer does not populate them today.
LEDGER_COLUMNS = (
    "id",
    "timestamp",
    "folder",
    "filename",
    "error_message",
    "error_type",
    "error_source",
    "stack_trace",
    "created_at",
)


class LedgerDatabase:
    """Adapt a webapp ``DatabaseObj`` to the dispatch ``DatabaseInterface``.

    ``ErrorHandler._persist_to_database`` writes through ``db.raw_connection``
    when present, else falls back to ``db.insert``. ``DatabaseObj`` exposes
    its sqlite3 connection as ``database_connection.raw_connection``; this
    adapter hides that indirection so the runner can hand the error handler
    a plain object matching the dispatch contract.
    """

    def __init__(self, db: Any) -> None:
        self._db = db

    @property
    def raw_connection(self) -> Any:
        """The underlying sqlite3 connection (the ``_persist_to_database`` path)."""
        return self._db.database_connection.raw_connection

    def insert(self, record: dict) -> None:
        """Fallback insert path used when ``raw_connection`` is unavailable."""
        self._db.database_connection["dispatch_errors"].insert(record)


def _folder_name_for_id(db: Any, folder_id: int) -> str | None:
    """Return the relative folder name stored for a folder id.

    Returns None when the folder doesn't exist.
    """
    row = db.folders_table.find_one(id=folder_id)
    if row is None:
        return None
    return str(row.get("folder_name") or "")


def _folder_clause(folder_name: str) -> tuple[str, list[Any]]:
    """Build a WHERE clause matching one folder's ledger rows.

    ``record_error`` receives the *resolved* folder row (see
    ``webapp.paths.resolve_row``), whose ``folder_name`` is the absolute
    path — but the API filters by the folder's stored relative name. Match
    both the exact name and any absolute path ending in ``/<name>`` so the
    filter works regardless of base-dir.
    """
    return (
        "(folder = ? OR folder LIKE ?)",
        [folder_name, f"%/{folder_name}"],
    )


def insert_error(
    db: Any,
    *,
    folder: str = "",
    filename: str = "",
    error_message: str,
    error_type: str = "WatcherScanError",
    error_source: str = "FolderWatcher",
    timestamp: str | None = None,
) -> None:
    """Insert one error-ledger row directly.

    The dispatch pipeline writes through ``ErrorHandler``; the watcher
    (phase 5.2) writes scan failures through this helper so they share
    the same ``dispatch_errors`` table and the Errors card / folder
    filter pick them up unchanged.
    """
    con = db.database_connection.raw_connection
    con.execute(
        "INSERT INTO dispatch_errors "
        "(timestamp, folder, filename, error_message, error_type, error_source) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            timestamp or time.ctime(),
            folder,
            filename,
            error_message,
            error_type,
            error_source,
        ),
    )
    con.commit()


def list_errors(
    db: Any,
    *,
    folder_id: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return recent error-ledger rows, newest first.

    Args:
        db: An open ``DatabaseObj``.
        folder_id: When non-None, only rows for that folder (matched by
            the folder's relative name — the ``folder`` value the
            pipeline records). A folder id that doesn't exist yields
            an empty list.
        limit: Maximum number of rows.

    Returns:
        A list of row dicts with the ``LEDGER_COLUMNS`` fields.

    """
    clauses: list[str] = []
    params: list[Any] = []
    if folder_id is not None:
        folder_name = _folder_name_for_id(db, folder_id)
        if folder_name is None:
            return []
        clause, more = _folder_clause(folder_name)
        clauses.append(clause)
        params.extend(more)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        "SELECT "
        + ", ".join(LEDGER_COLUMNS)
        + " FROM dispatch_errors"
        + f"{where} ORDER BY id DESC LIMIT ?"
    )
    params.append(max(1, limit))
    raw = db.database_connection.raw_connection.execute(sql, params).fetchall()
    return [dict(r) for r in raw]


def clear_errors(db: Any, *, folder_id: int | None = None) -> int:
    """Delete ledger rows, optionally restricted to one folder.

    Args:
        db: An open ``DatabaseObj``.
        folder_id: When non-None, only rows for that folder (same
            name-based match as ``list_errors``).

    Returns:
        The number of rows deleted.

    """
    clauses: list[str] = []
    params: list[Any] = []
    if folder_id is not None:
        folder_name = _folder_name_for_id(db, folder_id)
        if folder_name is None:
            return 0
        clause, more = _folder_clause(folder_name)
        clauses.append(clause)
        params.extend(more)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    con = db.database_connection.raw_connection
    count = con.execute(
        f"SELECT COUNT(*) FROM dispatch_errors{where}", params
    ).fetchone()[0]
    con.execute(f"DELETE FROM dispatch_errors{where}", params)
    con.commit()
    return count


__all__ = [
    "LEDGER_COLUMNS",
    "LedgerDatabase",
    "clear_errors",
    "insert_error",
    "list_errors",
]
