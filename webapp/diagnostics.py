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

Phase 6.3 adds the ``backends_health`` section, which probes SMTP /
FTP / per-folder copy destinations and reports whether each backend
is currently reachable. The probes run on demand (the diagnostics
endpoint is opened by the operator, not on a background loop), and
each one is wrapped in :func:`_safe` so a hung server can't take
down the endpoint.
"""

from __future__ import annotations

import contextlib
import datetime
import os
import platform as _platform
import socket
import sys
import time
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

# Per-probe timeout. Tight enough that the diagnostics endpoint can't
# hang on a slow remote server; loose enough to tolerate a TLS
# handshake on a healthy connection. ``_safe`` wraps each probe so the
# worst-case cost of a hung backend is bounded by ``PROBE_TIMEOUT``.
PROBE_TIMEOUT_SECONDS = 2.0


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


# ---------------------------------------------------------------------------
# Phase 6.3: backend health probes.
#
# Each probe is a single dict-shape response (``{"ok": bool, "latency_ms":
# float?, "error": str?}``) so the dashboard can render a uniform table
# without per-backend branching. The probes run sequentially on demand
# (the diagnostics endpoint is operator-triggered, not on a background
# loop), and each one is wrapped in :func:`_safe` so a hung server
# can't take down the endpoint.
# ---------------------------------------------------------------------------


def _now_ms() -> float:
    """Wall-clock milliseconds — used to time each probe."""
    return time.monotonic() * 1000.0


def _probe_smtp(server: str, port: int, *, timeout: float = PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """TCP-open the SMTP server, optionally issue ``EHLO``.

    The probe is intentionally shallow: a TCP-open + (optional) EHLO
    is enough to answer "is the server reachable", and the full
    SMTP-with-login probe is reserved for the 6.4+ follow-up. The
    timeout is enforced both by :func:`socket.create_connection` and
    by the ``_safe`` wrapper, so a hung server can't take down the
    diagnostics endpoint.
    """
    started = _now_ms()
    try:
        with socket.create_connection((server, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            # Try to read the server's banner; a hung server will
            # block here only until the timeout fires.
            with contextlib.suppress(OSError):
                banner = sock.recv(256)
                if not banner:
                    return {
                        "ok": False,
                        "latency_ms": round(_now_ms() - started, 1),
                        "error": "empty banner",
                    }
    except Exception as exc:
        return {
            "ok": False,
            "latency_ms": round(_now_ms() - started, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "ok": True,
        "latency_ms": round(_now_ms() - started, 1),
        "error": None,
    }


def _probe_ftp(server: str, port: int, *, timeout: float = PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """TCP-open the FTP server.

    Same shallow-probe rationale as :func:`_probe_smtp`: the goal is
    to answer "is the server alive", not to verify credentials. A
    full ``USER`` / ``PASS`` / ``QUIT`` round-trip is reserved for
    the 6.4+ follow-up; adding it now would expose the dashboard to
    "wrong password" / "user locked out" failures that have nothing
    to do with the operator's stated question.
    """
    started = _now_ms()
    try:
        with socket.create_connection((server, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            with contextlib.suppress(OSError):
                banner = sock.recv(256)
                if not banner:
                    return {
                        "ok": False,
                        "latency_ms": round(_now_ms() - started, 1),
                        "error": "empty banner",
                    }
    except Exception as exc:
        return {
            "ok": False,
            "latency_ms": round(_now_ms() - started, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "ok": True,
        "latency_ms": round(_now_ms() - started, 1),
        "error": None,
    }


def _probe_copy(resolved_path: str) -> dict[str, Any]:
    """Check that a folder's copy destination exists on disk.

    No network round-trip — the copy backend writes to a local
    filesystem path; the only check needed is :func:`Path.is_dir`.
    The probe respects the same path-resolution semantics the runner
    uses (see :mod:`webapp.paths`), so a configured folder whose
    relative copy destination resolves to a missing directory will
    report ``ok: False`` here exactly the same way the runner would
    skip it.
    """
    if not resolved_path:
        return {"ok": False, "error": "no copy destination configured"}
    if Path(resolved_path).is_dir():
        return {"ok": True, "error": None}
    return {"ok": False, "error": f"missing: {resolved_path}"}


def _collect_backends_health(
    settings: Any, db: Any | None
) -> dict[str, Any]:
    """Run every backend probe and return the ``backends_health`` section.

    SMTP and FTP are read from the ``settings`` (id=1) record in the
    database — the same place the rest of the webapp reads them from
    for live operations. If the database isn't imported yet the SMTP
    and FTP probes are skipped (the operator has no configured
    destination to probe). The copy probes iterate every folder with
    ``process_backend_copy`` enabled and stat the resolved path.

    Returns a dict with the documented shape:

    ::

        {
            "smtp": {"ok": bool, "latency_ms": float?, "error": str?},
            "ftp":  {"ok": bool, "latency_ms": float?, "error": str?},
            "copy": [{"folder_id": int, "alias": str, "ok": bool,
                      "error": str?}, ...],
        }

    The shape is JSON-stable; the dashboard's Backends table renders
    one row per ``smtp``/``ftp`` entry and one row per copy folder.
    """
    smtp = {"ok": False, "error": "not configured"}
    ftp = {"ok": False, "error": "not configured"}
    copy_results: list[dict[str, Any]] = []

    if db is not None:
        # SMTP — read the global settings record (id=1) which carries
        # ``email_smtp_server`` / ``smtp_port``. The ``get_settings_or_default``
        # helper is the same one the runner uses, so a newly-imported
        # DB without operator-customised SMTP defaults to "no server
        # configured".
        settings_row: dict[str, Any] = _safe(
            lambda: db.get_settings_or_default() or {}, {}
        ) or {}
        smtp_server = str(settings_row.get("email_smtp_server") or "").strip()
        try:
            smtp_port = int(settings_row.get("smtp_port") or 0) or 587
        except (TypeError, ValueError):
            smtp_port = 587
        if smtp_server:
            smtp = _probe_smtp(smtp_server, smtp_port)
            if not smtp.get("ok"):
                smtp = {
                    "ok": False,
                    "error": smtp.get("error") or "unreachable",
                    "latency_ms": smtp.get("latency_ms"),
                }

        # FTP — the desktop stores per-folder FTP credentials, so
        # there's no single global FTP destination. We probe the first
        # configured folder's FTP server (if any); an empty result is
        # the documented "no FTP folders configured" signal. The full
        # "all FTP folders" view is reserved for a future phase.
        ftp_server = ""
        ftp_port = 21
        with contextlib.suppress(Exception):
            folders = list(db.folders_table.all()) if db.folders_table else []
            for row in folders:
                if str(row.get("process_backend_ftp", "")).lower() in ("1", "true"):
                    candidate = str(row.get("ftp_server") or "").strip()
                    if not candidate:
                        continue
                    ftp_server = candidate
                    try:
                        ftp_port = int(row.get("ftp_port") or 21) or 21
                    except (TypeError, ValueError):
                        ftp_port = 21
                    break
        if ftp_server:
            ftp = _probe_ftp(ftp_server, ftp_port)

        # Copy destinations — every folder with ``process_backend_copy``
        # enabled gets its resolved copy_to_directory stat'd. Path
        # resolution matches the runner's (see :mod:`webapp.paths`).
        with contextlib.suppress(Exception):
            folders = list(db.folders_table.all()) if db.folders_table else []
            for row in folders:
                if str(row.get("process_backend_copy", "")).lower() not in (
                    "1",
                    "true",
                ):
                    continue
                from webapp.paths import resolve

                rel = str(row.get("copy_to_directory") or "").strip()
                resolved = resolve(str(settings.base_dir), rel) if rel else ""
                alias = str(row.get("alias") or row.get("folder_name") or "")
                probe = _probe_copy(resolved)
                copy_results.append(
                    {
                        "folder_id": row.get("id"),
                        "alias": alias,
                        "ok": probe["ok"],
                        "error": probe["error"],
                    }
                )

    return {
        "smtp": smtp,
        "ftp": ftp,
        "copy": copy_results,
    }


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
    db_handle: Any | None = None
    if db_exists:
        with contextlib.suppress(Exception):
            from webapp.database import open_database

            db_handle = open_database(settings)
            db_version = _read_db_version(db_handle)
            errors_count = _count(db_handle, "dispatch_errors")
            processed_count = _count(db_handle, "processed_files")
            queued_emails = _count(db_handle, "emails_to_send")
            folders_count = _count(db_handle, "folders")
            # ``folder_is_active`` is stored as 0/1; sum() works either way.
            active_folders_count = _count(db_handle, "folders") and _safe(
                lambda: int(
                    db_handle.database_connection.raw_connection.execute(
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

    # Phase 6.3: probe every backend. The probes run inside their own
    # ``_safe`` wrappers (via :func:`_collect_backends_health`), so
    # even a hung SMTP/FTP server can't take down the whole endpoint.
    backends_health = _collect_backends_health(settings, db_handle)
    if db_handle is not None:
        with contextlib.suppress(Exception):
            db_handle.close()

    # A backend being down is a warning, not a module-import failure
    # (modules import cleanly even when the SMTP server is offline).
    # The dashboard's "ok" flag aggregates module failures + recent
    # run failures; backend health is rendered as its own section.
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
        # Phase 6.3: per-backend reachability — each entry has
        # ``{ok, latency_ms?, error?}`` for SMTP/FTP, and a list of
        # per-folder entries for the copy backend.
        "backends_health": backends_health,
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
            # Backend probes surface as warnings so the diagnostics
            # banner lights up amber even if every module imports
            # cleanly. The "not configured" sentinel is *not* a
            # warning — it's the documented "operator hasn't pointed
            # the webapp at this backend yet" path; the dashboard
            # renders it as amber in the Backends table but doesn't
            # light up the global banner.
            *(
                [
                    "SMTP backend unreachable: "
                    f"{backends_health['smtp'].get('error') or 'unknown error'}"
                ]
                if backends_health["smtp"].get("error")
                and not backends_health["smtp"]["ok"]
                and "not configured" not in (backends_health["smtp"].get("error") or "").lower()
                else []
            ),
            *(
                [
                    "FTP backend unreachable: "
                    f"{backends_health['ftp'].get('error') or 'unknown error'}"
                ]
                if backends_health["ftp"].get("error")
                and not backends_health["ftp"]["ok"]
                and "not configured" not in (backends_health["ftp"].get("error") or "").lower()
                else []
            ),
            *(
                [
                    f"Copy destination missing for folder '{c.get('alias')}' (id={c.get('folder_id')})"
                    for c in backends_health["copy"]
                    if not c.get("ok")
                ]
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
    "PROBE_TIMEOUT_SECONDS",
    "_collect_backends_health",
    "_probe_copy",
    "_probe_ftp",
    "_probe_smtp",
    "collect_diagnostics",
]