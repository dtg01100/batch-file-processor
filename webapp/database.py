"""Database access for the webapp.

The webapp reuses the existing SQLite layer untouched: ``DatabaseObj``
creates/migrates ``folders.db`` and exposes the same table wrappers the
desktop app used. Each call site opens its own ``DatabaseObj`` (the
underlying ``sqlite_wrapper.Database`` uses ``check_same_thread=False``),
which is the safe pattern for a threaded FastAPI process.
"""

from __future__ import annotations

import platform as _platform
import threading

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


def open_database(settings: Settings) -> DatabaseObj:
    """Open (creating + migrating if needed) the webapp's ``folders.db``.

    Args:
        settings: Resolved webapp settings.

    Returns:
        An open ``DatabaseObj`` with the current schema.

    """
    settings.ensure_dirs()
    return DatabaseObj(
        database_path=str(settings.database_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(settings.data_dir),
        running_platform=_platform.system(),
    )


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
