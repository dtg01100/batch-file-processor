"""SQL-based file filtering for processed-files deduplication.

Replaces the legacy dataset-style ``find()`` + Python set comprehension
pattern with efficient raw SQL queries.  All three callers (orchestrator,
folder_processor, folder_discovery) should use the functions in this
module instead of building their own ``skipped_checksums`` sets.

Key design decisions
--------------------
1. **Checksum is the canonical key** — filenames can be reused, so
   deduplication always uses ``file_checksum``.
2. **Resend is checksum-scoped** — if *any* record for a checksum has
   ``resend_flag=1``, that checksum must NOT be skipped.  This fixes
   the legacy bug where multiple records for the same checksum could
   silently block a resend.
3. **mtime pre-filter** — when ``file_mtime`` is available the filter
   first checks whether the on-disk mtime matches the stored value.
   If it matches the content is guaranteed unchanged and we skip the
   expensive checksum calculation entirely.
4. **mtime + resend interaction** — if a file's mtime matches but its
   checksum is NOT in the skipped set (meaning at least one record has
   resend_flag=1), the file is NOT skipped — it will be processed.
"""

from __future__ import annotations

import os
from typing import Any

from core.structured_logging import get_logger

logger = get_logger(__name__)


def _has_sql(table: Any) -> bool:
    """Return True if the table supports raw SQL execution."""
    return hasattr(table, "execute") or (
        hasattr(table, "raw_connection") and table.raw_connection is not None
    )


def get_skipped_checksums(table: Any, folder_id: int) -> set[str]:
    """Return the set of checksums that should be skipped for a folder.

    A checksum is skipped when **all** records for that checksum have
    ``resend_flag`` falsy (0, NULL, or missing).  If *any* record has
    ``resend_flag=1`` the checksum is excluded from the result so the
    file will be (re-)processed.

    Uses raw SQL when available, falls back to ``find()`` for in-memory
    and mock table implementations.

    Args:
        table: Table or DB object with SQL execution capability.
        folder_id: The folder to filter on.

    Returns:
        Set of ``file_checksum`` strings that should be skipped.
    """
    if _has_sql(table):
        return _get_skipped_checksums_sql(table, folder_id)
    return _get_skipped_checksums_find(table, folder_id)


def _get_skipped_checksums_sql(table: Any, folder_id: int) -> set[str]:
    """SQL-based skipped checksums extraction.

    Returns checksums that should be skipped — i.e. those where **no**
    record has ``resend_flag=1``.  Uses ``EXCEPT`` to subtract the
    resend-set from the full set of checksums.
    """
    sql = """
        SELECT DISTINCT file_checksum
        FROM processed_files
        WHERE folder_id = ?
          AND file_checksum IS NOT NULL
        EXCEPT
        SELECT DISTINCT file_checksum
        FROM processed_files
        WHERE folder_id = ?
          AND resend_flag = 1
    """
    if hasattr(table, "raw_connection"):
        cursor = table.raw_connection.execute(sql, (folder_id, folder_id))
    else:
        cursor = table.execute(sql, (folder_id, folder_id))
    return {row[0] for row in cursor}


def _get_skipped_checksums_find(table: Any, folder_id: int) -> set[str]:
    """Fallback: use find() for in-memory and mock tables."""
    records = table.find(folder_id=folder_id)
    resend_checksums = {
        r["file_checksum"]
        for r in records
        if r.get("file_checksum") and r.get("resend_flag")
    }
    all_checksums = {r["file_checksum"] for r in records if r.get("file_checksum")}
    return all_checksums - resend_checksums


def filter_pending_files(
    table: Any,
    folder_id: int,
    candidate_files: list[str],
    *,
    progress_reporter: Any = None,
    folder_index: int | None = None,
    folder_total: int | None = None,
) -> list[str]:
    """Filter candidate files against the processed-files table.

    Combines the mtime pre-filter with checksum-based deduplication in a
    single pass:

    1. If the file's current mtime matches the most recently stored mtime
       AND its checksum is in the skipped set, skip without calculating.
    2. If the file's mtime matches but checksum is NOT in skipped, process
       (resend_flag=1 means this checksum should be reprocessed).
    3. Otherwise calculate checksum and compare against skipped set.

    Per-file progress reporting is preserved for callers that need it.

    Args:
        table: Table or DB object with SQL execution capability.
        folder_id: The folder to filter on.
        candidate_files: File paths to evaluate.
        progress_reporter: Optional progress reporter for per-file updates.
        folder_index: Current folder index (1-based) for progress reporting.
        folder_total: Total number of folders for progress reporting.

    Returns:
        List of file paths that still need processing.
    """
    skipped = get_skipped_checksums(table, folder_id)
    mtime_map = _get_latest_mtimes(table, folder_id)

    pending: list[str] = []
    for file_index, file_path in enumerate(candidate_files, start=1):
        mtime_matches = _skip_by_mtime(file_path, mtime_map)

        if mtime_matches:
            # mtime matches - check if checksum is in skipped before skipping
            from core.utils.file_utils import calculate_file_checksum

            checksum = calculate_file_checksum(file_path)
            if checksum in skipped:
                # checksum is in skipped (all records have resend_flag=0) - skip
                if progress_reporter and hasattr(
                    progress_reporter, "update_discovery_file"
                ):
                    progress_reporter.update_discovery_file(
                        folder_num=folder_index if folder_index is not None else 0,
                        folder_total=folder_total if folder_total is not None else 0,
                        file_num=file_index,
                        file_total=len(candidate_files),
                        filename=os.path.basename(file_path),
                    )
                continue

        # Either mtime doesn't match, or checksum not in skipped (resend case)
        from core.utils.file_utils import calculate_file_checksum

        checksum = calculate_file_checksum(file_path)
        if checksum not in skipped:
            pending.append(file_path)

        if progress_reporter and hasattr(progress_reporter, "update_discovery_file"):
            progress_reporter.update_discovery_file(
                folder_num=folder_index if folder_index is not None else 0,
                folder_total=folder_total if folder_total is not None else 0,
                file_num=file_index,
                file_total=len(candidate_files),
                filename=os.path.basename(file_path),
            )

    return pending


def _get_latest_mtimes(table: Any, folder_id: int) -> dict[str, float]:
    """Build a map of file_name -> most recent stored mtime.

    Returns an empty dict if the ``file_mtime`` column does not exist
    yet (schema migration pending) or if SQL is not available.
    """
    if not _has_sql(table):
        return {}

    sql = """
        SELECT file_name, MAX(file_mtime) AS mtime
        FROM processed_files
        WHERE folder_id = ?
          AND file_mtime IS NOT NULL
        GROUP BY file_name
    """
    try:
        if hasattr(table, "raw_connection"):
            cursor = table.raw_connection.execute(sql, (folder_id,))
        else:
            cursor = table.execute(sql, (folder_id,))
        return {row[0]: float(row[1]) for row in cursor}
    except Exception:
        logger.debug("Failed to fetch file mtime map from database")
        return {}


def _skip_by_mtime(file_path: str, mtime_map: dict[str, float]) -> bool:
    """Return True if the file should be skipped because mtime matches."""
    if not mtime_map:
        return False
    stored_mtime = mtime_map.get(file_path)
    if stored_mtime is None:
        return False
    try:
        current_mtime = os.path.getmtime(file_path)
        return abs(current_mtime - stored_mtime) < 0.001
    except OSError:
        return False


def record_file_mtime(file_path: str) -> float | None:
    """Return the current mtime for *file_path*, or None on error."""
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return None
