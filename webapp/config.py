"""Webapp configuration, resolved from the environment.

The two knobs:

- ``BFS_BASE_DIR`` — the root all configured folder paths resolve against.
  Default ``./data`` when running from source; ``/data`` in Docker.
- ``BFS_DATA_DIR`` — where ``folders.db`` (and error/log artifacts) live.
  Default ``<base-dir>/config``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Keys persisted in the database's kv_settings table during import.
BASE_DIRECTORY_KEY = "webapp.base_directory"
SOURCE_PLATFORM_KEY = "webapp.source_platform"


@dataclass(frozen=True)
class Settings:
    """Resolved webapp settings."""

    base_dir: Path
    data_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        base = Path(os.environ.get("BFS_BASE_DIR", "./data")).resolve()
        data = Path(os.environ.get("BFS_DATA_DIR", str(base / "config"))).resolve()
        return cls(base_dir=base, data_dir=data)

    @property
    def database_path(self) -> Path:
        """Path to the webapp's active ``folders.db``."""
        return self.data_dir / "folders.db"

    @property
    def errors_dir(self) -> Path:
        return self.data_dir / "errors"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def ensure_dirs(self) -> None:
        """Create the data directory tree if missing."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
