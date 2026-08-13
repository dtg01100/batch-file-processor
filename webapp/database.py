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
            "error_file TEXT DEFAULT '')"
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
