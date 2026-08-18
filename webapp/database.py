"""Database access for the webapp.

The webapp reuses the existing SQLite layer untouched: ``DatabaseObj``
creates/migrates ``folders.db`` and exposes the same table wrappers the
desktop app used. Each call site opens its own ``DatabaseObj`` (the
underlying ``sqlite_wrapper.Database`` uses ``check_same_thread=False``),
which is the safe pattern for a threaded FastAPI process.
"""

from __future__ import annotations

import contextlib
import platform as _platform
import threading
from typing import Any

from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from webapp.config import Settings

# Serialises access to the SQLite database across API request threads and
# the background run thread. SQLite itself serialises writers, but the
# dataset-style wrapper can trip "database is locked" under concurrent
# writes without a process-level guard.
_DB_LOCK = threading.RLock()


def lock() -> threading.RLock:
    """Return the process-wide database lock."""
    return _DB_LOCK


def _ensure_columns(db: Any) -> None:
    """Idempotent column/table additions for newer features.

    Older database files (pre-v52 webapp) lack columns that the
    webapp now writes to. This helper ALTER TABLEs them in if
    they're missing, so the schema migrates in place without
    forcing a full migration cycle.

    It also creates the error ledger table (``dispatch_errors``),
    which the webapp writes through ``ErrorHandler._persist_to_database``
    but which no migration version has ever created.
    """
    needed = [
        ("watch_enabled", "TEXT DEFAULT ''"),
        ("watch_interval_seconds", "INTEGER DEFAULT 30"),
        # The v32 desktop DB (and the v32→v51 migration) never had this
        # column; the webapp's PUT /api/folders/{id} writes it, so a
        # missing column broke folder editing after import with
        # ``no such column: alert_on_failure``. Default 1 = enabled,
        # matching the desktop's ``alert_on_failure INTEGER`` semantics.
        ("alert_on_failure", "INTEGER DEFAULT 1"),
        # Phase 5.2 watcher health — updated every tick by the watcher
        # thread; the Watching card reads them via ``list_watched``.
        ("last_tick_at", "TEXT DEFAULT ''"),
        ("last_run_id", "TEXT DEFAULT ''"),
        ("last_error", "TEXT DEFAULT ''"),
        # Phase 5.3 follow-up: per-folder run-warning thresholds (0/'' =
        # no limit). The runner compares each folder's run duration +
        # failure rate against these and stamps a warning on the run card.
        ("max_duration_seconds", "TEXT DEFAULT ''"),
        ("max_failure_rate_percent", "TEXT DEFAULT ''"),
    ]
    with contextlib.suppress(Exception):
        con = db.database_connection.raw_connection
        # Phase 5.1 error ledger — the dispatch pipeline INSERTs into this
        # table whenever ``ErrorHandler`` is given a ``database``. Created
        # idempotently so pre-5.1 databases pick it up on next open.
        con.execute(
            "CREATE TABLE IF NOT EXISTS dispatch_errors ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "timestamp TEXT, "
            "folder TEXT, "
            "filename TEXT, "
            "error_message TEXT, "
            "error_type TEXT, "
            "error_source TEXT, "
            "stack_trace TEXT, "
            "created_at TEXT, "
            "error_file TEXT DEFAULT '', "
            "severity TEXT DEFAULT '')"
        )
        # Phase 6.4: soft-delete tombstone table. ``DELETE
        # /api/folders/{id}`` moves the row here (with the original
        # row JSON-serialized) and ``POST /api/folders/{id}/restore``
        # moves it back. A periodic trim job (driven by
        # ``SoftDeleteTrimSupervisor``) purges expired rows after the
        # operator-configured TTL. Idempotent — pre-6.4 databases pick
        # this up on next open without a migration version bump.
        con.execute(
            "CREATE TABLE IF NOT EXISTS folders_deleted ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "folder_id INTEGER NOT NULL, "
            "deleted_at TEXT NOT NULL, "
            "expires_at TEXT NOT NULL, "
            "original_row_json TEXT NOT NULL)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS folders_deleted_expires_idx "
            "ON folders_deleted(expires_at)"
        )
        existing = {
            row[1] for row in con.execute("PRAGMA table_info(folders)").fetchall()
        }
        for col, decl in needed:
            if col not in existing:
                con.execute(f"ALTER TABLE folders ADD COLUMN {col} {decl}")
        # Open question #2 resolution: ledger rows link to the raw error
        # text file the runner writes per folder-run. Idempotent ALTER so
        # pre-resolution databases pick up the column on next open.
        err_existing = {
            row[1]
            for row in con.execute("PRAGMA table_info(dispatch_errors)").fetchall()
        }
        if "error_file" not in err_existing:
            con.execute(
                "ALTER TABLE dispatch_errors ADD COLUMN error_file TEXT DEFAULT ''"
            )
        # Phase 5.5: EDI validation problems are now recorded in the ledger
        # with a major/minor classification (matching the original desktop
        # validator). Backfill the column idempotently for pre-5.5 DBs.
        if "severity" not in err_existing:
            con.execute(
                "ALTER TABLE dispatch_errors ADD COLUMN severity TEXT DEFAULT ''"
            )
        # The v32 desktop DB (and its migration) never had the settings
        # columns the webapp writes through GET/PUT /api/settings
        # (``ssh_key_filename`` arrived in a post-v32 migration). Without
        # a backfill, saving settings on an imported DB fails with
        # ``no such column: ssh_key_filename``.
        settings_needed = [("ssh_key_filename", "TEXT DEFAULT ''")]
        with contextlib.suppress(Exception):
            settings_existing = {
                row[1]
                for row in con.execute("PRAGMA table_info(settings)").fetchall()
            }
            for col, decl in settings_needed:
                if col not in settings_existing:
                    con.execute(
                        f"ALTER TABLE settings ADD COLUMN {col} {decl}"
                    )
        con.commit()


def open_database(settings: Settings) -> DatabaseObj:
    """Open (creating + migrating if needed) the webapp's ``folders.db``.

    Args:
        settings: Resolved webapp settings.

    Returns:
        An open ``DatabaseObj`` with the current schema.

    """
    settings.ensure_dirs()
    obj = DatabaseObj(
        database_path=str(settings.database_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(settings.data_dir),
        running_platform=_platform.system(),
    )
    # Idempotent column additions for newer features.
    _ensure_columns(obj)
    return obj


def get_source_platform(db: DatabaseObj, default: str = "Windows") -> str:
    """Return the platform the imported database came from."""
    value = db.get_setting("webapp.source_platform")
    return value or default


def get_base_directory(db: DatabaseObj, settings: Settings) -> str:
    """Return the base-dir the imported paths are relative to.

    The import-time base-dir is stored in the database; the environment
    (``BFS_BASE_DIR``) is the live value. The stored value is informational
    — the runner always resolves against ``settings.base_dir``.
    """
    stored = db.get_setting("webapp.base_directory")
    return stored or str(settings.base_dir)
