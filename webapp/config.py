"""Webapp configuration, resolved from the environment.

The knobs:

- ``BFS_BASE_DIR`` — the root all configured folder paths resolve against.
  Default ``./data`` when running from source; ``/data`` in Docker.
- ``BFS_DATA_DIR`` — where ``folders.db`` (and error/log artifacts) live.
  Default ``<base-dir>/config``.
- ``BFS_HOST`` — interface uvicorn binds. Default ``127.0.0.1`` (Phase
  6.1 — bind-localhost-by-default; opt in to remote access with
  ``BFS_HOST=0.0.0.0`` or ``--host 0.0.0.0``).
- ``BFS_PORT`` — TCP port uvicorn binds. Default ``8000``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Keys persisted in the database's kv_settings table during import.
BASE_DIRECTORY_KEY = "webapp.base_directory"
SOURCE_PLATFORM_KEY = "webapp.source_platform"

# Default bind interface (Phase 6.1). Single-host local-first is the
# spec's stated posture (§3.4 — "no inbound network surface"); a
# fresh `python -m webapp.main` should match it. Operators who want
# remote access opt in via BFS_HOST=0.0.0.0 or `uvicorn --host 0.0.0.0`.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(frozen=True)
class Settings:
    """Resolved webapp settings."""

    base_dir: Path
    data_dir: Path
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls) -> Settings:
        base = Path(os.environ.get("BFS_BASE_DIR", "./data")).resolve()
        data = Path(os.environ.get("BFS_DATA_DIR", str(base / "config"))).resolve()
        host = os.environ.get("BFS_HOST", DEFAULT_HOST)
        port = int(os.environ.get("BFS_PORT", str(DEFAULT_PORT)))
        return cls(base_dir=base, data_dir=data, host=host, port=port)

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
