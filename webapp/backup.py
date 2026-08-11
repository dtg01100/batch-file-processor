"""Backup / restore for the webapp's active database.

The importer already keeps a timestamped ``folders.db.bak-<ts>`` of
the previous database every time a fresh import runs. This module
adds explicit backup / restore endpoints so an operator can:

- list the existing backups (newest first),
- download any backup file to disk,
- restore a backup as the active database (the current database is
  itself backed up before being overwritten, so the operation is
  recoverable).

The restore path-traversal-checks its argument against the data
directory the same way the export-download endpoint does.
"""

from __future__ import annotations

import datetime
import shutil
from pathlib import Path
from typing import Any

_BACKUP_PREFIX = "folders.db.bak-"


def list_backups(data_dir: Path) -> list[dict[str, Any]]:
    """Return every ``folders.db.bak-*`` file under ``data_dir``.

    Args:
        data_dir: The webapp's data directory.

    Returns:
        A list of dicts ``{name, path, size_bytes, modified_at}``,
        newest first. ``modified_at`` is an ISO-8601 timestamp.

    """
    if not data_dir.is_dir():
        return []
    backups: list[dict[str, Any]] = []
    for entry in data_dir.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.startswith(_BACKUP_PREFIX):
            continue
        stat = entry.stat()
        backups.append(
            {
                "name": entry.name,
                "path": str(entry),
                "size_bytes": stat.st_size,
                "modified_at": (
                datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
            ),
            }
        )
    backups.sort(key=lambda b: b["modified_at"], reverse=True)
    return backups


def make_backup(settings: Any) -> str:
    """Copy the current active DB to a timestamped .bak file.

    Returns:
        Absolute path to the new backup. If the active DB does not
        exist yet (e.g. no import has happened), returns "".

    """
    db_path: Path = settings.database_path
    if not db_path.is_file():
        return ""
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = settings.data_dir / f"folders.db.bak-{stamp}"
    shutil.copy2(db_path, backup_path)
    # ``copy2`` preserves the source's mtime; overwrite it with "now"
    # so list_backups (which sorts by mtime) orders backups
    # chronologically rather than by import-time.
    import os
    now = datetime.datetime.now().timestamp()
    os.utime(backup_path, (now, now))
    return str(backup_path)


def restore_backup(settings: Any, backup_path: str) -> str:
    """Replace the active DB with the contents of ``backup_path``.

    Before overwriting, the current active DB is itself backed up so
    the operator can undo the restore. The backup file passed in must
    live under the webapp's data directory.

    Args:
        settings: Webapp settings.
        backup_path: Absolute path to the backup file (must live
            under ``settings.data_dir``).

    Returns:
        The path to the new "pre-restore" backup that was created
        (the previous active DB). Useful for the operator to recover
        from a bad restore.

    Raises:
        ValueError: If the backup path is outside the data dir or
            doesn't exist.
        FileNotFoundError: If no active database exists yet.

    """
    resolved = Path(backup_path).resolve()
    allowed_root = settings.data_dir.resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("Backup path is outside the data directory") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    if not resolved.name.startswith(_BACKUP_PREFIX):
        raise ValueError("Not a recognised backup file")

    if not settings.database_path.is_file():
        raise FileNotFoundError("No active database to replace")

    pre_restore = make_backup(settings)
    shutil.copy2(resolved, settings.database_path)
    return pre_restore


__all__ = [
    "list_backups",
    "make_backup",
    "restore_backup",
]
