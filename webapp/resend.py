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

from typing import Any


def list_processed_files(
    db: Any,
    *,
    folder_id: int | None = None,
    limit: int = 200,
    only_resend_flagged: bool = False,
) -> list[dict[str, Any]]:
    """Return recent processed-files rows, newest first.

    Args:
        db: An open ``DatabaseObj``.
        folder_id: When non-None, only rows for that folder.
        limit: Maximum number of rows.
        only_resend_flagged: When True, only rows whose ``resend_flag``
            is truthy. Used by the resend dispatcher to find rows that
            have been explicitly marked for re-send.

    Returns:
        A list of row dicts. Each row contains at least ``id``,
        ``file_name``, ``folder_alias``, ``folder_id``,
        ``processed_at``, ``status``, ``sent_to``,
        ``invoice_numbers``, and ``resend_flag``.

    """
    clauses: list[str] = []
    params: list[Any] = []
    if folder_id is not None:
        clauses.append("folder_id = ?")
        params.append(folder_id)
    if only_resend_flagged:
        clauses.append("resend_flag = 1")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        "SELECT id, file_name, folder_id, folder_alias, processed_at, "
        "status, sent_to, invoice_numbers, resend_flag "
        "FROM processed_files"
        f"{where} "
        "ORDER BY id DESC LIMIT ?"
    )
    params.append(limit)
    raw = db.database_connection.raw_connection.execute(sql, params).fetchall()
    return [dict(r) for r in raw]


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


def set_resend_flag_batch(
    db: Any, file_ids: list[int], *, resend: bool
) -> int:
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
    "delete_processed_rows",
    "list_processed_files",
    "set_resend_flag",
    "set_resend_flag_batch",
]
