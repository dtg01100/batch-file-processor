"""Import a legacy desktop ``folders.db`` into the webapp.

What "import with a base-dir" means here:

1. A legacy database file (from the Qt desktop app) is uploaded.
2. It is migrated to the current schema (``folders_database_migrator``).
3. Every configured path — folder input dirs (``folder_name``), the copy
   backend destination (``copy_to_directory``), and the logs dir — has its
   **root stripped**, becoming a relative path under the base-dir
   (see ``webapp.paths``).
4. The migrated + rebased database becomes the webapp's active
   ``folders.db``; the base-dir and source platform are recorded in
   ``kv_settings`` so the UI can display them.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime
import platform as _platform
import shutil
import sqlite3
from pathlib import Path

from backend.database import sqlite_wrapper
from migrations import folders_database_migrator
from webapp.config import (
    BASE_DIRECTORY_KEY,
    SOURCE_PLATFORM_KEY,
    Settings,
)
from webapp.database import open_database
from webapp.paths import (
    OVERSIGHT_PATH_FIELDS,
    SETTINGS_PATH_FIELDS,
    rebase_row,
    to_relative,
)


@dataclasses.dataclass(frozen=True)
class ImportResult:
    """Summary of a completed database import."""

    folders_imported: int
    active_folders: int
    rebased_paths: int
    source_platform: str
    database_path: str
    base_directory: str


def _detect_source_platform(db) -> str:
    """Read the ``os`` column from the migrated ``version`` table."""
    try:
        row = db["version"].find_one(id=1)
        if row and row.get("os"):
            return str(row["os"])
    except (sqlite3.Error, KeyError, TypeError, ValueError):
        pass
    return "Windows"


def _rebase_all_paths(db, source_platform: str) -> int:
    """Strip roots from every path column across folders/oversight/settings.

    Returns:
        Number of path fields rewritten.
    """
    rebased = 0

    folders = db["folders"]
    for row in folders.all():
        new_row = rebase_row(row, source_platform)
        changed = any(
            new_row.get(f) != row.get(f) for f in ("folder_name", "copy_to_directory")
        )
        if changed:
            folders.update(new_row, ["id"])
            rebased += 1

    # Oversight / defaults (logs_directory) lives in the administrative
    # table; settings (copy_to_directory) lives in settings.
    for table_name, fields in (
        ("administrative", OVERSIGHT_PATH_FIELDS),
        ("settings", SETTINGS_PATH_FIELDS),
    ):
        table = db[table_name]
        for row in table.all():
            new_row = dict(row)
            for field in fields:
                if field in new_row:
                    converted = to_relative(new_row.get(field), source_platform)
                    if converted != new_row.get(field):
                        new_row[field] = converted
                        rebased += 1
            if any(new_row.get(f) != row.get(f) for f in fields):
                table.update(new_row, ["id"])

    return rebased


def import_database(
    source_path: str | Path,
    settings: Settings,
    *,
    base_dir: str | None = None,
    platform: str | None = None,
) -> ImportResult:
    """Import a legacy database as the webapp's active database.

    Args:
        source_path: Path to the uploaded legacy ``folders.db``.
        settings: Webapp settings (destination data-dir).
        base_dir: The base-dir the stored relative paths belong to. When
            None, ``settings.base_dir`` is used (and recorded).
        platform: Source platform override ("Windows"/"Linux"). When None,
            detected from the database's ``version`` table.

    Returns:
        An ``ImportResult`` summary.

    Raises:
        ValueError: If the source file is missing or not a SQLite database.
    """
    source = Path(source_path)
    if not source.is_file():
        raise ValueError(f"Source database not found: {source}")

    settings.ensure_dirs()
    effective_base = (
        str(Path(base_dir).resolve()) if base_dir else str(settings.base_dir)
    )

    # Work on a scratch copy so a failed import never corrupts the active DB.
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    work_path = settings.data_dir / f"import-work-{stamp}.db"
    shutil.copy2(source, work_path)

    db = None
    try:
        # Connect + migrate the scratch copy to the current schema. A single
        # connection is used end-to-end: reopening would leak the first one
        # and leave a hot rollback journal next to the (renamed) database.
        db = sqlite_wrapper.Database.connect(str(work_path))
        try:
            source_platform = platform or _detect_source_platform(db)
            folders_database_migrator.upgrade_database(
                db, str(settings.data_dir), source_platform
            )

            rebased_paths = _rebase_all_paths(db, source_platform)

            # The desktop app refuses to open a database stamped for a
            # different OS. The webapp now owns this database, so restamp
            # it for the current platform (the original platform is kept
            # in kv_settings as provenance).
            db["version"].update({"id": 1, "os": _platform.system()}, ["id"])

            folders_table = db["folders"]
            all_rows = list(folders_table.all())
            active = [
                r
                for r in all_rows
                if str(r.get("folder_is_active", "")).lower() in ("1", "true")
            ]

            # Record provenance so the UI can explain the paths.
            kv = db["kv_settings"]
            kv.upsert({"key": BASE_DIRECTORY_KEY, "value": effective_base}, ["key"])
            kv.upsert({"key": SOURCE_PLATFORM_KEY, "value": source_platform}, ["key"])
        finally:
            with contextlib.suppress(Exception):
                db.close()

        # Install as the active DB, keeping a timestamped backup of any
        # previous one. Copy (not rename) so a leftover rollback journal
        # next to the work file can never mismatch the target name.
        target = settings.database_path
        if target.exists():
            backup = settings.data_dir / (
                f"folders.db.bak-{datetime.datetime.now():%Y%m%d%H%M%S}"
            )
            shutil.copy2(target, backup)
        shutil.copy2(work_path, target)
        for sidecar in ("-journal", "-wal", "-shm"):
            with contextlib.suppress(Exception):
                Path(str(work_path) + sidecar).unlink(missing_ok=True)

        return ImportResult(
            folders_imported=len(all_rows),
            active_folders=len(active),
            rebased_paths=rebased_paths,
            source_platform=source_platform,
            database_path=str(target),
            base_directory=effective_base,
        )
    except Exception:
        # Clean up the scratch copy on failure.
        with contextlib.suppress(Exception):
            work_path.unlink(missing_ok=True)
        raise
    finally:
        with contextlib.suppress(Exception):
            work_path.unlink(missing_ok=True)


def count_active_folders(settings: Settings) -> int:
    """Return the number of active folders in the active database."""
    db = open_database(settings)
    try:
        rows = db.folders_table.all() if db.folders_table else []
        return sum(
            1
            for r in rows
            if str(r.get("folder_is_active", "")).lower() in ("1", "true")
        )
    finally:
        with contextlib.suppress(Exception):
            db.close()
