"""Resend operations for the webapp.

The desktop app's ``interface/services/resend_service.py`` already
implements the full feature (set_resend_flag, batch flagging, run-once
sweep, search). The webapp version is a slim copy because:

- the dataset wrapper's ``distinct`` / ``order_by`` SQL syntax doesn't
  match what we want to expose over HTTP,
- the resend *execution* flow (sweep flagged rows through the dispatch
  pipeline) is a different code path on the webapp because runs are
  scheduled by HTTP, not by an operator clicking a button,
- the webapp resend is read-only via the UI: operators can flag rows
  for resend, the dispatcher ignores them on normal runs, and a
  separate ``POST /api/resend`` triggers the re-dispatch.

The desktop service is left in place for any future caller; this
module deliberately does not re-implement its caching, batch APIs, or
search-by-string features. The webapp's resend table UI just shows
recent files per folder.
"""

from __future__ import annotations

import datetime
from typing import Any


def _next_day(iso_date: str) -> str:
    """Return ``YYYY-MM-DD`` for the day after ``iso_date``.

    Used by the ``date_to`` upper-bound of the processed-files filter
    so a calendar day is matched inclusively without resorting to
    ``2026-08-14 23:59:59`` — SQLite's lexicographic string compare
    treats ``' '`` (space) as less than ``'T'``, so a space-padded
    end-of-day sorts BEFORE any timestamp on that day.
    """
    d = datetime.date.fromisoformat(iso_date)
    return (d + datetime.timedelta(days=1)).isoformat()


def _processed_files_where(
    *,
    folder_id: int | None,
    only_resend_flagged: bool,
    search: str | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[str, list[Any]]:
    """Build the shared ``WHERE`` clause + params for the two processed-files
    queries (the paginated ``SELECT`` and the unpaginated ``COUNT``).

    Returning both pieces keeps the row + total filters in lockstep —
    if you change one you have to change the other or the Load-More
    affordance will claim there are more pages when there aren't (or
    stop offering more when there are).
    """
    clauses: list[str] = []
    params: list[Any] = []
    if folder_id is not None:
        clauses.append("folder_id = ?")
        params.append(folder_id)
    if only_resend_flagged:
        clauses.append("resend_flag = 1")
    if search:
        like = f"%{search.lower()}%"
        # SQLite's LIKE is case-insensitive for ASCII by default; the
        # lower() wrappers are belt-and-braces against a future ICU
        # collation change.
        clauses.append(
            "(lower(file_name) LIKE ? OR lower(folder_alias) LIKE ? OR "
            "lower(ifnull(invoice_numbers, '')) LIKE ?)"
        )
        params.extend([like, like, like])
    if date_from:
        clauses.append("processed_at >= ?")
        params.append(date_from)
    if date_to:
        # The column stores ISO timestamps like ``2026-08-14T15:59:51``;
        # the operator's date_to is a calendar day. Compare against
        # the *next* day so the day itself is included without us
        # having to know the exact end-of-day string. SQLite string
        # comparison is lexicographic, so ``2026-08-15`` sorts after
        # every timestamp whose date is ``2026-08-14``.
        next_day = _next_day(date_to)
        clauses.append("processed_at < ?")
        params.append(next_day)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def list_processed_files(
    db: Any,
    *,
    folder_id: int | None = None,
    limit: int = 200,
    only_resend_flagged: bool = False,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return recent processed-files rows, newest first.

    Args:
        db: An open ``DatabaseObj``.
        folder_id: When non-None, only rows for that folder.
        limit: Maximum number of rows.
        only_resend_flagged: When True, only rows whose ``resend_flag``
            is truthy. Used by the resend dispatcher to find rows that
            have been explicitly marked for re-send.
        search: When non-empty, match the substring against
            ``file_name``, ``folder_alias``, and ``invoice_numbers``
            (case-insensitive ``LIKE``).
        date_from: ISO date (``YYYY-MM-DD``) lower bound on
            ``processed_at``. Inclusive.
        date_to: ISO date upper bound. Inclusive — the API appends a
            day so the operator can pass the same value for both.
        offset: Number of rows to skip (for "Load More" pagination).
            Must be non-negative; out-of-range offsets simply return
            an empty list.

    Returns:
        A list of row dicts. Each row contains at least ``id``,
        ``file_name``, ``folder_alias``, ``folder_id``,
        ``processed_at``, ``status``, ``sent_to``,
        ``invoice_numbers``, and ``resend_flag``.

    """
    where, params = _processed_files_where(
        folder_id=folder_id,
        only_resend_flagged=only_resend_flagged,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    sql = (
        "SELECT id, file_name, folder_id, folder_alias, processed_at, "
        "status, sent_to, invoice_numbers, resend_flag "
        "FROM processed_files"
        f"{where} "
        "ORDER BY id DESC LIMIT ? OFFSET ?"
    )
    params.extend([limit, max(0, offset)])
    raw = db.database_connection.raw_connection.execute(sql, params).fetchall()
    return [dict(r) for r in raw]


def count_processed_files(
    db: Any,
    *,
    folder_id: int | None = None,
    only_resend_flagged: bool = False,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    """Return the total number of processed-files rows matching the same
    filters as :func:`list_processed_files`, ignoring limit/offset.

    Used by the dashboard's "Load More" affordance: ``total`` tells it
    whether more pages remain after the current page is rendered.
    """
    where, params = _processed_files_where(
        folder_id=folder_id,
        only_resend_flagged=only_resend_flagged,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    sql = f"SELECT COUNT(*) AS n FROM processed_files{where}"
    raw = db.database_connection.raw_connection.execute(sql, params).fetchone()
    return int(raw["n"]) if raw else 0


def set_resend_flag(db: Any, file_id: int, *, resend: bool) -> bool:
    """Set or clear the resend_flag on one processed-files row.

    Args:
        db: An open ``DatabaseObj``.
        file_id: The processed-files row id.
        resend: True to flag for resend, False to clear the flag.

    Returns:
        True if the row existed and was updated, False otherwise.

    """
    rows = list(db.processed_files.find(id=file_id))
    if not rows:
        return False
    row = dict(rows[0])
    row["resend_flag"] = bool(resend)
    db.processed_files.update(row, ["id"])
    return True


def set_resend_flag_batch(db: Any, file_ids: list[int], *, resend: bool) -> int:
    """Set or clear the resend_flag on many rows.

    Args:
        db: An open ``DatabaseObj``.
        file_ids: Row ids to update.
        resend: True to flag, False to clear.

    Returns:
        The number of rows actually updated.

    """
    updated = 0
    for fid in file_ids:
        if set_resend_flag(db, fid, resend=resend):
            updated += 1
    return updated


def clear_resend_flags(db: Any, file_ids: list[int]) -> int:
    """Clear the resend_flag on the given rows.

    Args:
        db: An open ``DatabaseObj``.
        file_ids: Row ids to clear.

    Returns:
        The number of rows updated.

    """
    return set_resend_flag_batch(db, file_ids, resend=False)


def delete_processed_rows(db: Any, file_ids: list[int]) -> int:
    """Hard-delete processed-files rows by id.

    Used by the resend dispatcher after a successful re-send so the
    same file isn't re-sent on the next normal run.

    Args:
        db: An open ``DatabaseObj``.
        file_ids: Row ids to remove.

    Returns:
        The number of rows removed.

    """
    removed = 0
    for fid in file_ids:
        rows = list(db.processed_files.find(id=fid))
        if not rows:
            continue
        db.processed_files.delete(id=fid)
        removed += 1
    return removed


__all__ = [
    "clear_resend_flags",
    "count_processed_files",
    "delete_processed_rows",
    "list_processed_files",
    "set_resend_flag",
    "set_resend_flag_batch",
]
