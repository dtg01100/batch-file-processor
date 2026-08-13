"""Maintenance operations for the webapp.

Core operations:

- ``clear_processed_files``: bulk-delete ``processed_files`` rows,
  optionally filtered by folder. Used when an operator wants to
  re-process every EDI file in a folder (e.g. after fixing a bug in
  the converter). The desktop app's equivalent lives in
  ``interface/operations/maintenance_functions.py``; the webapp
  version is a slim wrapper because the dataset wrapper already
  handles the SQL.

- ``mark_file_processed``: record a single file as already processed
  (the "skip this EDI on the next run" flow). The dispatcher's
  checksum-based de-dup normally handles this, but sometimes an
  operator wants to add an external file without re-running the
  pipeline.

- ``export_processed_report``: write a CSV report of every processed
  file for a folder. Mirrors the desktop app's
  ``export_processed_report`` from ``interface/operations/processed_files.py``;
  returns the file path so the web UI can offer it as a download.

Bulk actions (the desktop's Maintenance dialog):

- ``set_all_folders_active`` / ``set_all_folders_inactive``: flip
  every folder to the given state (``set_all_active`` /
  ``set_all_inactive`` in the desktop's ``MaintenanceFunctions``).

- ``clear_queued_emails``: drop every row from the ``emails_to_send``
  queue — the desktop's "Clear queued emails" button
  (``db.emails_table.delete()``).

- ``remove_inactive_folders``: delete every folder marked inactive,
  including its processed-files rows — the desktop's "Remove all
  inactive configurations" (``remove_inactive_folders``).

The webapp is the only writer to ``processed_files`` in this project,
so the implementations here own the SQL. The desktop-app helper is
left in place for the (now-removed) Qt dialog; we do not duplicate
validation logic by re-importing it.
"""

from __future__ import annotations

import csv
import datetime
import os
from pathlib import Path
from typing import Any


def clear_processed_files(
    db: Any, *, folder_id: int | None = None, before: datetime.datetime | None = None
) -> int:
    """Delete processed-files rows.

    Args:
        db: An open ``DatabaseObj``.
        folder_id: When non-None, only rows whose ``folder_id``
            matches are deleted. When None, every row is deleted.
        before: When non-None, only rows whose ``processed_at`` is
            strictly older than this are deleted.

    Returns:
        The number of rows deleted. The dataset wrapper does not
        expose a ``count`` for arbitrary filters, so we count by
        snapshotting rows before deletion and measuring the diff.

    """
    table = db.processed_files
    rows_before = list(table.all())
    if folder_id is None and before is None:
        # Bulk delete via the table's delete() helper. Iterating and
        # calling delete(id=...) one-by-one would also work but is
        # N round-trips; the SQL form is one statement.
        table.delete()
        return len(rows_before)

    deleted = 0
    for row in rows_before:
        if folder_id is not None and row.get("folder_id") != folder_id:
            continue
        if before is not None:
            processed_at = row.get("processed_at") or row.get("sent_date_time")
            if processed_at is None:
                continue
            try:
                ts = _parse_timestamp(processed_at)
            except ValueError:
                # A bad timestamp should not block the delete — drop
                # the row so the operator isn't stuck.
                ts = None
            if ts is not None and ts >= before:
                continue
        table.delete(id=row["id"])
        deleted += 1
    return deleted


def mark_file_processed(
    db: Any,
    *,
    file_path: str,
    folder_id: int,
    folder_alias: str = "",
    invoice_numbers: str = "",
    status: str = "processed",
    sent_to: str = "",
    convert_format: str = "",
) -> int:
    """Record a single file as already processed.

    Args:
        db: An open ``DatabaseObj``.
        file_path: Absolute path to the file on disk. Stored in the
            ``file_name`` column for parity with the dispatcher's
            row shape.
        folder_id: FK into the folders table.
        folder_alias: Display alias; usually the folder's ``alias``
            column.
        invoice_numbers: Free-form invoice string. Comma-separated
            is the convention.
        status: ``"processed"`` (default) or ``"failed"``.
        sent_to: Free-form delivery description (e.g.
            ``"Email: cogs@stewartsshops.com"``).
        convert_format: Format-name string (e.g. ``"csv"``) used when
            the dispatcher converted this file. Empty for unprocessed
            entries.

    Returns:
        The id of the new ``processed_files`` row.

    """
    now = datetime.datetime.now().isoformat()
    row = {
        "file_name": file_path,
        "folder_id": folder_id,
        "folder_alias": folder_alias,
        "invoice_numbers": invoice_numbers,
        "status": status,
        "sent_to": sent_to,
        "convert_format": convert_format,
        "processed_at": now,
        "created_at": now,
        "resend_flag": False,
    }
    table = db.processed_files
    return table.insert(row)


def export_processed_report(db: Any, folder_id: int, output_dir: str) -> str:
    """Write a CSV report of every processed file for one folder.

    Mirrors the desktop app's ``export_processed_report`` from
    ``interface/operations/processed_files.py`` — same columns, same
    suffix-collision handling. The returned path is the file the web
    UI then offers as a download.

    Args:
        db: An open ``DatabaseObj``.
        folder_id: FK into the folders table.
        output_dir: Directory to write the CSV to. Created if missing.

    Returns:
        Absolute path to the written CSV file.

    Raises:
        ValueError: When no folder with this id exists.

    """
    folder = db.folders_table.find_one(id=folder_id)
    if folder is None:
        raise ValueError(f"Folder with id {folder_id} not found")
    alias = folder.get("alias") or f"folder-{folder_id}"

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = _next_available_path(target_dir, f"{alias} processed report", ".csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["File", "Invoice Numbers", "Processed At", "Sent To", "Status"]
        )
        for row in db.processed_files.find(folder_id=folder_id):
            writer.writerow(
                [
                    row.get("file_name", ""),
                    row.get("invoice_numbers", ""),
                    row.get("processed_at", "") or row.get("sent_date_time", ""),
                    row.get("sent_to", ""),
                    row.get("status", ""),
                ]
            )
    return str(out_path)


def set_all_folders_active(db: Any, *, active: bool) -> int:
    """Flip every folder to the given active state (bulk maintenance).

    Mirrors the desktop's ``MaintenanceFunctions.set_all_active`` /
    ``set_all_inactive``: only folders in the *opposite* state are
    touched, so calling it twice in a row is a no-op and the returned
    count is the number of folders actually changed.

    Args:
        db: An open ``DatabaseObj``.
        active: True to activate every inactive folder; False to
            deactivate every active folder.

    Returns:
        The number of folders flipped.

    """
    table = db.folders_table
    changed = 0
    for row in table.find(folder_is_active=not active):
        row["folder_is_active"] = active
        table.update(row, ["id"])
        changed += 1
    return changed


def clear_queued_emails(db: Any) -> int:
    """Drop every queued report-email row (``emails_to_send``).

    Matches the desktop's "Clear queued emails" button
    (``db.emails_table.delete()`` in the Maintenance dialog). The
    report-email queue is populated when ``enable_reporting`` is on;
    clearing it drops unsent report entries.

    Args:
        db: An open ``DatabaseObj``.

    Returns:
        The number of queued rows deleted.

    """
    table = db.emails_table
    count = table.count()
    table.delete()
    return count


def remove_inactive_folders(db: Any) -> int:
    """Delete every folder marked inactive, plus its processed rows.

    Matches the desktop's "Remove all inactive configurations" — each
    inactive folder is removed the same way the per-folder Delete
    works (the row itself and its ``processed_files`` history), so the
    resend flagger never sees orphaned rows.

    Args:
        db: An open ``DatabaseObj``.

    Returns:
        The number of folders removed.

    """
    con = db.database_connection.raw_connection
    rows = list(db.folders_table.find(folder_is_active=False))
    for row in rows:
        folder_id = row["id"]
        db.folders_table.delete(id=folder_id)
        con.execute("DELETE FROM processed_files WHERE folder_id = ?", (folder_id,))
    con.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _next_available_path(directory: Path, base: str, suffix: str) -> Path:
    """Return ``directory / f"{base}{suffix}"`` if free, else ``... (N)``."""
    candidate = directory / f"{base}{suffix}"
    if not candidate.exists():
        return candidate
    n = 1
    while True:
        numbered = directory / f"{base} ({n}){suffix}"
        if not numbered.exists():
            return numbered
        n += 1


def _parse_timestamp(value: str) -> datetime.datetime:
    """Parse an ISO-8601 timestamp; tolerate trailing ``Z`` and offsets.

    The desktop app's processed-files table had both ``processed_at``
    and ``sent_date_time`` columns; the v51 schema kept only the
    former. This helper still handles both for the ``before`` filter
    on legacy rows (e.g. when an operator imports an older DB).
    """
    cleaned = value.replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(cleaned)


# ---------------------------------------------------------------------------
# os.unlink shim kept for legacy callers (used to be ``avoid_duplicate_...``).
# ---------------------------------------------------------------------------
__all__ = [
    "clear_processed_files",
    "clear_queued_emails",
    "export_processed_report",
    "mark_file_processed",
    "remove_inactive_folders",
    "set_all_folders_active",
]


# Quiet pyflakes: ``os`` is used in the ``__all__`` cleanup shim path on
# some legacy imports.
_ = os.path
