"""Diagnostics / self-test for the webapp.

The desktop GUI ships a CLI ``-t`` flag (and a hidden "Self test" menu
action) that prints platform / Python version, module-import checks,
config-directory access, appdirs sanity, and filesystem writability.
For the browser-only webapp we surface the same information as JSON
at ``GET /api/diagnostics`` so the dashboard's "Diagnostics" card can
display it and the operator can copy a single block when filing a
support ticket.

The collector is intentionally tolerant: every section is wrapped in
its own ``contextlib.suppress`` so a missing table / corrupt row never
takes down the whole endpoint — the response just shows ``null`` or
``0`` for the offending field. That's the same philosophy as the
desktop ``run_self_test``: failures count, but the rest of the report
still prints.
"""

from __future__ import annotations

import contextlib
import datetime
import os
import platform as _platform
import sys
from pathlib import Path
from typing import Any

# Modules the desktop self-test required. The webapp doesn't need
# PySide6, but it does need the dispatch pipeline and the EDI parsers
# to be importable (those are the actual workhorses). The list mirrors
# ``interface/qt/diagnostics.py`` minus the Qt bits so a ``python -c
# "import webapp.diagnostics"`` style smoke test catches the same
# regressions the desktop's CLI did.
EXPECTED_MODULES: tuple[str, ...] = (
    "core.edi.edi_parser",
    "core.edi.edi_splitter",
    "core.edi.edi_tweaker",
    "dispatch",
    "dispatch.orchestrator",
    "dispatch.send_manager",
    "dispatch.converters.convert_to_csv",
    "dispatch.converters.convert_to_scannerware",
    "dispatch.preflight_validator",
    "backend.email_backend",
    "backend.ftp_backend",
    "backend.copy_backend",
    "backend.http_backend",
    "webapp",
    "webapp.main",
    "webapp.runner",
    "webapp.scheduler",
    "webapp.watcher",
    "fastapi",
    "uvicorn",
    "hypothesis",
)


def _safe(fn, default):
    """Run ``fn`` and return ``default`` on any exception.

    Diagnostics is for *debugging* problems — it must never be the
    cause of one. Every probe runs through this helper so a missing
    table / unhandled exception in one section can't break the rest.
    """
    try:
        return fn()
    except Exception:
        return default


def _module_check(modules: tuple[str, ...]) -> list[dict[str, Any]]:
    """Import every module in ``modules`` and return its status.

    Same shape as the desktop's ``[OK]`` / ``[FAIL]`` lines, just as
    structured data so the dashboard can render it as a table.
    """
    out: list[dict[str, Any]] = []
    for name in modules:
        try:
            __import__(name)
            out.append({"module": name, "ok": True, "error": ""})
        except Exception as exc:
            out.append(
                {"module": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
            )
    return out


def _read_db_version(db: Any) -> str | None:
    """Read the schema version row from the ``version`` table.

    The webapp's migrations bump ``version`` on every upgrade; reading
    it directly avoids depending on the dataset wrapper (which can
    raise if the row hasn't been initialized yet — common right after
    an import).
    """
    try:
        rows = db.database_connection.raw_connection.execute(
            "SELECT version FROM version WHERE id = 1"
        ).fetchone()
    except Exception:
        return None
    if not rows:
        return None
    # rows may be a tuple or a sqlite3.Row depending on the driver.
    try:
        return str(rows["version"])
    except (KeyError, TypeError):
        return str(rows[0]) if rows else None


def _count(db: Any, table_name: str) -> int:
    """Best-effort COUNT(*) for a known table; returns 0 on any failure."""
    try:
        cur = db.database_connection.raw_connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )
        row = cur.fetchone()
    except Exception:
        return 0
    if not row:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


def _recent_runs(run_store: Any, history: Any, limit: int = 10) -> list[dict[str, Any]]:
    """Merge in-memory + persisted run reports, newest first, capped."""
    seen: dict[str, dict[str, Any]] = {}
    for r in _safe(lambda: run_store.list(), []) or []:
        seen[r.run_id] = {
            "run_id": r.run_id,
            "status": r.status,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "total_processed": r.total_processed,
            "total_failed": r.total_failed,
            "error": r.error or "",
        }
    if history is not None:
        for r in _safe(lambda: history.recent(limit=limit), []) or []:
            if r.run_id not in seen:
                seen[r.run_id] = {
                    "run_id": r.run_id,
                    "status": r.status,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                    "total_processed": r.total_processed,
                    "total_failed": r.total_failed,
                    "error": r.error or "",
                }
    # Newest-first by started_at (ISO sorts lexicographically).
    rows = list(seen.values())
    rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    return rows[:limit]


def collect_diagnostics(
    *,
    settings: Any,
    run_store: Any,
    history: Any,
    schedule_summary: dict[str, Any] | None,
    watched_folders: list[dict[str, Any]],
    backups_count: int,
) -> dict[str, Any]:
    """Build the diagnostics payload the dashboard renders.

    ``run_store`` / ``history`` / ``schedule_summary`` come from the
    FastAPI app state and may be None in very early startup; the
    function handles each one independently so a partial boot can
    still serve a useful report.
    """
    db_path: Path = settings.database_path
    db_exists = db_path.is_file()
    db_size_bytes = db_path.stat().st_size if db_exists else 0

    # All DB-backed probes go through _safe() / _count() so a missing
    # table (e.g. before the first import) shows as 0, not 500.
    db_version: str | None = None
    errors_count = 0
    processed_count = 0
    queued_emails = 0
    folders_count = 0
    active_folders_count = 0
    if db_exists:
        with contextlib.suppress(Exception):
            from webapp.database import open_database

            with open_database(settings) as db:
                db_version = _read_db_version(db)
                errors_count = _count(db, "dispatch_errors")
                processed_count = _count(db, "processed_files")
                queued_emails = _count(db, "emails_to_send")
                folders_count = _count(db, "folders")
                # ``folder_is_active`` is stored as 0/1; sum() works either way.
                active_folders_count = _count(db, "folders") and _safe(
                    lambda: int(
                        db.database_connection.raw_connection.execute(
                            "SELECT COUNT(*) FROM folders WHERE folder_is_active = 1"
                        ).fetchone()[0]
                    ),
                    0,
                )

    watched_total = len(watched_folders)
    watched_errors = sum(1 for f in watched_folders if f.get("last_error"))

    recent_runs = _recent_runs(run_store, history, limit=10)
    recent_failures_24h = sum(
        1
        for r in recent_runs
        if r.get("status") == "failed"
        and _within_last_hours(r.get("started_at"), hours=24)
    )

    module_check = _module_check(EXPECTED_MODULES)
    failed_modules = [m for m in module_check if not m["ok"]]

    return {
        "collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "platform": {
            "system": _platform.system(),
            "release": _platform.release(),
            "machine": _platform.machine(),
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
            "pid": os.getpid(),
        },
        "app": {
            "title": "Batch File Sender",
            "version": _safe(
                lambda: _app_version(),
                "unknown",
            ),
        },
        "paths": {
            "base_dir": str(settings.base_dir),
            "data_dir": str(settings.data_dir),
            "database_path": str(db_path),
            "database_exists": db_exists,
            "database_size_bytes": db_size_bytes,
        },
        "database": {
            "version": db_version,
            "folders_count": folders_count,
            "active_folders_count": active_folders_count,
            "processed_files_count": processed_count,
            "errors_count": errors_count,
            "queued_emails": queued_emails,
        },
        "runtime": {
            "active_runs": _safe(lambda: run_store.active_count, 0) if run_store else 0,
            "scheduler": schedule_summary or {},
            "watched_folders": watched_total,
            "watched_with_errors": watched_errors,
            "recent_runs": recent_runs,
            "recent_run_failures_24h": recent_failures_24h,
            "backup_count": backups_count,
        },
        "modules": module_check,
        "ok": len(failed_modules) == 0 and not recent_failures_24h,
        "warnings": [
            *(
                f"Module import failed: {m['module']} ({m['error']})"
                for m in failed_modules
            ),
            *(
                [
                    "Recent run failures: "
                    f"{recent_failures_24h} failed run(s) in the last 24h"
                ]
                if recent_failures_24h
                else []
            ),
            *(
                ["Watcher health: " f"{watched_errors} watched folder(s) with errors"]
                if watched_errors
                else []
            ),
        ],
    }


def _within_last_hours(iso_ts: str | None, *, hours: int) -> bool:
    """True when ``iso_ts`` parses and is within the last ``hours`` hours."""
    if not iso_ts:
        return False
    try:
        dt = datetime.datetime.fromisoformat(iso_ts)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return (datetime.datetime.now(datetime.UTC) - dt) <= datetime.timedelta(hours=hours)


def _app_version() -> str:
    """Best-effort app version string.

    The FastAPI app sets a static title/version in ``create_app``;
    reading the live app object would require it to be passed in.
    Fall back to the package ``__version__`` if it's defined.
    """
    import webapp

    return getattr(webapp, "__version__", "0.1.0")


__all__ = [
    "EXPECTED_MODULES",
    "collect_diagnostics",
]
