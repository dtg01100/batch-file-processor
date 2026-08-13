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

import contextlib
import datetime
import time
from pathlib import Path
from typing import Any

from dispatch.file_utils import build_error_log_filename

# Maximum number of rows kept in the ledger; the oldest rows beyond the
# cap are deleted when a new one is inserted (mirrors
# ``webapp.history.MAX_HISTORY_ROWS``). Bounds the unbounded-growth risk
# of an unattended watcher or a permanently broken folder.
MAX_ERROR_ROWS = 10_000

# Columns ``_persist_to_database`` actually writes. ``stack_trace`` and
# ``created_at`` exist in the schema for future use (e.g. watcher scan
# errors) but the dispatch layer does not populate them today.
# ``error_file`` (open question #2) is the path of the raw error-text
# file the runner writes per folder-run; the dispatch layer leaves it
# empty and the runner links it after the run.
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
    "error_file",
    "severity",
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


def write_error_artifact(
    errors_dir: str,
    *,
    alias: str,
    folder_path: str,
    timestamp: str | None,
    text: str,
) -> str:
    """Write one raw error-text file under ``errors_dir``.

    Uses the legacy ``build_error_log_filename`` naming (``<folder>/<alias>
    errors.<ts>.txt``) so watcher artifacts look the same as the dispatch
    ones the runner writes. Returns the artifact path.
    """
    try:
        ts = datetime.datetime.fromisoformat(timestamp).strftime(
            "%Y-%m-%d_%H-%M-%S"
        ) if timestamp else ""
    except (TypeError, ValueError):
        ts = ""
    if not ts:
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = build_error_log_filename(alias, errors_dir, folder_path, ts)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")
    return path


def dedupe_matches(
    db: Any,
    *,
    folder: str,
    error_message: str,
    error_type: str,
    error_source: str,
) -> bool:
    """Return True when the latest row for ``folder`` is identical to the
    given error — i.e. the next ``insert_error(dedupe=True)`` would be
    skipped. Lets the watcher decide *before* writing a raw artifact
    whether the failure is a repeat of an already-recorded episode.
    """
    con = db.database_connection.raw_connection
    last = con.execute(
        "SELECT error_message, error_type, error_source "
        "FROM dispatch_errors WHERE folder = ? ORDER BY id DESC LIMIT 1",
        (folder,),
    ).fetchone()
    return bool(
        last
        and last[0] == error_message
        and last[1] == error_type
        and last[2] == error_source
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
    error_file: str = "",
    severity: str = "",
    dedupe: bool = False,
) -> bool:
    """Insert one error-ledger row directly.

    The dispatch pipeline writes through ``ErrorHandler``; the watcher
    (phase 5.2) writes scan failures through this helper so they share
    the same ``dispatch_errors`` table and the Errors card / folder
    filter pick them up unchanged. ``severity`` carries the same
    major/minor vocabulary the dispatch layer uses for EDI validation
    problems (empty for generic scan failures).

    With ``dedupe=True`` the row is skipped when it is identical
    (same message/type/source) to the latest row already recorded for
    the same ``folder`` — a watcher that fails the same way every
    tick would otherwise spam one row per interval.

    After a successful insert the oldest rows beyond ``MAX_ERROR_ROWS``
    are trimmed (same trim-on-write pattern as ``history.py``).

    Returns:
        True if a row was inserted, False if it was deduped away.

    """
    con = db.database_connection.raw_connection
    if dedupe and dedupe_matches(
        db,
        folder=folder,
        error_message=error_message,
        error_type=error_type,
        error_source=error_source,
    ):
        return False
    con.execute(
        "INSERT INTO dispatch_errors "
        "(timestamp, folder, filename, error_message, error_type, "
        "error_source, error_file, severity) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            timestamp or time.ctime(),
            folder,
            filename,
            error_message,
            error_type,
            error_source,
            error_file,
            severity,
        ),
    )
    con.commit()
    # Trim the oldest rows beyond the cap.
    con.execute(
        "DELETE FROM dispatch_errors WHERE id NOT IN "
        "(SELECT id FROM dispatch_errors ORDER BY id DESC LIMIT ?)",
        (MAX_ERROR_ROWS,),
    )
    con.commit()
    return True


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


def max_error_id(db: Any) -> int:
    """Return the highest ledger row id (0 when the ledger is empty).

    The runner uses this to snapshot the ledger before processing a
    folder, so it can later link exactly the rows that folder's run
    produced to the raw error file it wrote.
    """
    row = db.database_connection.raw_connection.execute(
        "SELECT COALESCE(MAX(id), 0) FROM dispatch_errors"
    ).fetchone()
    return int(row[0]) if row else 0


def link_error_files(
    db: Any,
    *,
    after_id: int,
    folder: str,
    error_file: str,
) -> int:
    """Point the ledger rows one folder's run produced at its raw file.

    ``after_id`` is the ledger watermark captured before the folder was
    processed; every row inserted since then for that folder belongs to
    that run, so they all link to the same artifact.

    Returns:
        The number of rows updated.

    """
    con = db.database_connection.raw_connection
    cur = con.execute(
        "UPDATE dispatch_errors SET error_file = ? "
        "WHERE id > ? AND folder = ? AND error_file = ''",
        (error_file, after_id, folder),
    )
    con.commit()
    return cur.rowcount


def error_counts(db: Any) -> dict[int, int]:
    """Count ledger rows per folder id.

    Returns a ``{folder_id: count}`` map for every folder in the folders
    table (0 for folders with no errors). Uses the same name-based match
    as ``list_errors`` so rows the pipeline recorded with the resolved
    absolute path are counted against the stored relative name.
    """
    out: dict[int, int] = {}
    con = db.database_connection.raw_connection
    for row in db.folders_table.all() or []:
        name = str(row.get("folder_name") or "")
        if not name:
            continue
        clause, params = _folder_clause(name)
        count = con.execute(
            f"SELECT COUNT(*) FROM dispatch_errors WHERE {clause}", params
        ).fetchone()[0]
        out[row["id"]] = int(count)
    return out


def folder_error_text(
    db: Any,
    *,
    folder_id: int,
    errors_dir: str | None = None,
    limit: int = 10_000,
) -> str:
    """Concatenate one folder's full raw error text for a folder-level download.

    For every ledger row of the folder, the linked raw artifact
    (``error_file``) is included when present and readable; rows without
    an artifact fall back to a synthesized block from the row fields, so
    the download always covers the folder's whole ledger — not just the
    rows the runner linked a file to. Artifact paths are only read when
    they live under ``errors_dir`` (defense in depth on top of the
    ``GET /api/errors/file`` traversal guard).

    Args:
        db: An open ``DatabaseObj``.
        folder_id: The folder whose rows to gather.
        errors_dir: The errors directory; when None, artifacts are
            skipped (row-only fallback).
        limit: Maximum number of rows to gather (defaults to the ledger
            cap so the whole folder is included).

    Returns:
        A single text blob, newest row first (same order as the ledger).

    """
    rows = list_errors(db, folder_id=folder_id, limit=limit)
    if not rows:
        return ""
    blocks: list[str] = []
    for r in rows:
        artifact = str(r.get("error_file") or "")
        raw = ""
        if errors_dir and artifact:
            p = Path(artifact)
            try:
                p.relative_to(Path(errors_dir).resolve())
            except ValueError:
                p = None
            if p is not None and p.is_file():
                with contextlib.suppress(OSError):
                    raw = p.read_text(encoding="utf-8")
        if not raw:
            raw = (
                f"At: {r.get('timestamp') or ''}\n"
                f"For object: {r.get('filename') or ''}\n"
                f"Error Message is:\n{r.get('error_message') or ''}\n"
            )
        blocks.append(
            f"=== {r.get('error_type') or 'Error'}"
            f" ({r.get('timestamp') or '—'}) ===\n"
            f"{raw.rstrip('\n')}\n\n"
        )
    return "".join(blocks)


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
    "MAX_ERROR_ROWS",
    "LedgerDatabase",
    "clear_errors",
    "dedupe_matches",
    "error_counts",
    "folder_error_text",
    "insert_error",
    "link_error_files",
    "list_errors",
    "max_error_id",
    "write_error_artifact",
]
