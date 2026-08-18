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
- ``BFS_API_TOKEN`` — Phase 6.2 single-user bearer-token. When set,
  every API endpoint (except ``/``, ``/api/health``, ``/docs``,
  ``/openapi.json``, ``/redoc``) requires ``Authorization: Bearer
  <token>``. When empty, auth is disabled and the webapp behaves as
  it did before Phase 6.2.
- ``FOLDERS_DELETED_TTL_DAYS`` — Phase 6.4 soft-delete restore window
  in days. Default ``30``; clamped to ``[1, 365]``.
- ``FOLDERS_DELETED_TRIM_INTERVAL_SECONDS`` — Phase 6.4 how often the
  ``SoftDeleteTrimSupervisor`` wakes up to purge expired rows.
  Default ``3600`` (1 hour). ``0`` is the synchronous-test override
  (run-once on ``start()``, no background thread). Clamped to
  ``[0, 86400]``.

The dataclass ``Settings.__init__`` signature is intentionally frozen
at the 6.1 shape (``base_dir``, ``data_dir``, ``host``, ``port``) so
the existing test fixtures that build ``Settings(base_dir=...,
data_dir=...)`` keep working without touching every call site. New
fields (``api_token``, ``folders_deleted_ttl_days``) are read from the
environment via :meth:`from_env` only; tests can pass them through
``Settings.from_env`` directly with monkey-patched env vars, or
override the module-level ``DEFAULT_*`` constants for synthetic cases.
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

# Phase 6.2: the default token is empty (auth disabled). An operator
# opts in by setting ``BFS_API_TOKEN`` to a long-lived secret; rotate
# by restarting with a new value (the in-process singleton is replaced
# on next ``create_app`` call). Long-lived is intentional — the spec
# is single-user local-first, so a JWT refresh flow would add ceremony
# for zero operational benefit.
DEFAULT_API_TOKEN = ""

# Phase 6.4: soft-delete restore window in days. Clamped to
# [1, 365] so an operator can't accidentally keep deleted folders
# forever by setting a huge TTL.
DEFAULT_FOLDERS_DELETED_TTL_DAYS = 30
MIN_FOLDERS_DELETED_TTL_DAYS = 1
MAX_FOLDERS_DELETED_TTL_DAYS = 365

# Phase 6.4: how often the soft-delete trim job wakes up to purge
# expired ``folders_deleted`` rows. ``0`` is the synchronous-test
# override — ``SoftDeleteTrimSupervisor.start()`` runs one trim
# immediately on a 0-second interval and then exits (no background
# thread), which is what the test suite needs.
DEFAULT_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS = 3600
MIN_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS = 0
MAX_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS = 24 * 3600


def _clamp_folders_deleted_ttl_days(raw: int) -> int:
    """Clamp the configured TTL into the [1, 365] window.

    The clamp is intentionally lenient — a typo of 9999 or 0 still
    produces a usable window. The clamp is also applied to the
    ``DEFAULT_FOLDERS_DELETED_TTL_DAYS`` constant (a future bump of
    the module default is the right way to change the policy).
    """
    return max(
        MIN_FOLDERS_DELETED_TTL_DAYS,
        min(MAX_FOLDERS_DELETED_TTL_DAYS, int(raw)),
    )


def _clamp_folders_deleted_trim_interval_seconds(raw: int) -> int:
    """Clamp the trim interval into the [0, 86400] window.

    ``0`` is the synchronous-test override (run-once on ``start()``,
    no background thread); values above 24 h are silly for an
    in-process trim and get pinned to 24 h to bound memory use.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS
    return max(
        MIN_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS,
        min(MAX_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS, value),
    )


@dataclass(frozen=True)
class Settings:
    """Resolved webapp settings.

    The dataclass fields are the 6.1 shape (``base_dir``, ``data_dir``,
    ``host``, ``port``) so existing fixtures that build ``Settings(
    base_dir=..., data_dir=...)`` keep working without touching every
    test. New Phase 6.2 / 6.4 knobs (``api_token``,
    ``folders_deleted_ttl_days``) live as *properties* that read the
    process environment on demand — this keeps the constructor
    stable, lets tests override values via ``monkeypatch.setenv``,
    and avoids the "every new env var adds another dataclass field"
    churn that would otherwise cascade through every fixture.
    """

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
    def api_token(self) -> str:
        """The configured bearer token, or empty string when auth is off.

        Reads ``BFS_API_TOKEN`` from the process environment on every
        access — this lets a test monkeypatch the env var without
        rebuilding the ``Settings`` instance, and avoids the
        "frozen dataclass can't be reconfigured" trap if a future
        change wants to hot-reload the token.
        """
        return os.environ.get("BFS_API_TOKEN", DEFAULT_API_TOKEN)

    @property
    def folders_deleted_ttl_days(self) -> int:
        """The configured soft-delete TTL in days, clamped to [1, 365].

        Same rationale as :attr:`api_token`: read from the environment
        so tests can override without rebuilding the ``Settings``
        instance.
        """
        raw = os.environ.get(
            "FOLDERS_DELETED_TTL_DAYS", str(DEFAULT_FOLDERS_DELETED_TTL_DAYS)
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_FOLDERS_DELETED_TTL_DAYS
        return _clamp_folders_deleted_ttl_days(value)

    @property
    def folders_deleted_trim_interval_seconds(self) -> int:
        """How often the soft-delete trim job wakes up.

        Reads ``FOLDERS_DELETED_TRIM_INTERVAL_SECONDS`` from the
        environment so tests can override without rebuilding the
        ``Settings`` instance. ``0`` is the run-once synchronous-test
        override (see :func:`_clamp_folders_deleted_trim_interval_seconds`).
        """
        raw = os.environ.get(
            "FOLDERS_DELETED_TRIM_INTERVAL_SECONDS",
            str(DEFAULT_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS),
        )
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS
        return _clamp_folders_deleted_trim_interval_seconds(value)

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


__all__ = [
    "BASE_DIRECTORY_KEY",
    "DEFAULT_API_TOKEN",
    "DEFAULT_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS",
    "DEFAULT_FOLDERS_DELETED_TTL_DAYS",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "MAX_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS",
    "MAX_FOLDERS_DELETED_TTL_DAYS",
    "MIN_FOLDERS_DELETED_TRIM_INTERVAL_SECONDS",
    "MIN_FOLDERS_DELETED_TTL_DAYS",
    "SOURCE_PLATFORM_KEY",
    "Settings",
    "_clamp_folders_deleted_trim_interval_seconds",
    "_clamp_folders_deleted_ttl_days",
]
