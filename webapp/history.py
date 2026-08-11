"""Persistent run history for the webapp.

The in-memory ``RunStore`` is fine for live runs (a worker thread
mutates a ``RunReport`` while the browser polls), but it loses
history on container restart. This module persists completed
``RunReport`` objects to a SQLite table (``run_history``) so the
``/api/runs`` endpoint can return the most recent N runs even
after a restart.

Schema (created on first use):

    CREATE TABLE run_history (
        run_id          TEXT PRIMARY KEY,
        kind            TEXT,             -- 'normal' | 'resend'
        status          TEXT,             -- 'running' | 'completed' | 'failed'
        started_at      TEXT,
        finished_at     TEXT,
        total_processed INTEGER,
        total_failed    INTEGER,
        error           TEXT,
        report_json     TEXT             -- full RunReport serialised
    )

The ``report_json`` column holds the whole thing so the API can
return the same shape as the in-memory version without a JOIN +
re-aggregation.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import threading
from pathlib import Path
from typing import Any

from webapp.config import Settings
from webapp.database import open_database
from webapp.runner import FolderRunReport, RunReport

# Maximum number of runs kept in the history table. Anything older
# is deleted when a new run is appended.
MAX_HISTORY_ROWS = 100

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS run_history (
    run_id          TEXT PRIMARY KEY,
    kind            TEXT,
    status          TEXT,
    started_at      TEXT,
    finished_at     TEXT,
    total_processed INTEGER,
    total_failed    INTEGER,
    error           TEXT,
    report_json     TEXT
)
"""


def _ensure_table(db: Any) -> None:
    """Create the run_history table if it doesn't exist."""
    # ``raw_connection.execute`` accepts multi-statement SQL; the
    # ``database_connection.execute`` wrapper doesn't.
    raw = db.database_connection.raw_connection
    raw.execute(_CREATE_SQL)
    raw.commit()


def _report_to_json(report: RunReport) -> str:
    """Serialise a RunReport (dataclasses) to JSON."""
    return json.dumps(dataclasses.asdict(report), default=str)


def _json_to_report(text: str) -> RunReport:
    """Deserialise JSON back into a RunReport."""
    payload = json.loads(text)
    folders = [
        FolderRunReport(**f) for f in payload.pop("folders", [])
    ]
    return RunReport(folders=folders, **payload)


class RunHistory:
    """SQLite-backed persistent run history.

    Concurrent worker threads can append via ``append``; the read
    APIs (``recent``, ``get``) return copies decoupled from any
    in-flight mutation.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._ensure_table_once()

    def _ensure_table_once(self) -> None:
        """Try once to create the table; tolerate failure (no DB yet)."""
        try:
            settings = self._settings
            settings.ensure_dirs()
            db = open_database(settings)
            try:
                _ensure_table(db)
            finally:
                db.close()
        except Exception:
            pass

    def append(self, report: RunReport, *, kind: str = "normal") -> None:
        """Persist a finished (or in-flight) RunReport.

        Trims older rows to keep the table bounded by MAX_HISTORY_ROWS.
        """
        with self._lock:
            try:
                settings = self._settings
                settings.ensure_dirs()
                db = open_database(settings)
                try:
                    _ensure_table(db)
                    payload = _report_to_json(report)
                    con = db.database_connection.raw_connection
                    con.execute(
                        """
                        INSERT OR REPLACE INTO run_history (
                            run_id, kind, status, started_at, finished_at,
                            total_processed, total_failed, error, report_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            report.run_id,
                            kind,
                            report.status,
                            report.started_at,
                            report.finished_at,
                            report.total_processed,
                            report.total_failed,
                            report.error,
                            payload,
                        ),
                    )
                    con.commit()
                    # Trim the oldest rows beyond the cap.
                    con.execute(
                        """
                        DELETE FROM run_history
                        WHERE run_id NOT IN (
                            SELECT run_id FROM run_history
                            ORDER BY started_at DESC
                            LIMIT ?
                        )
                        """,
                        (MAX_HISTORY_ROWS,),
                    )
                    con.commit()
                finally:
                    db.close()
            except Exception:
                # Persistence is best-effort; the in-memory store still
                # has the run for the duration of this process.
                pass

    def recent(self, limit: int = 50) -> list[RunReport]:
        """Return the most-recent ``limit`` runs, newest first."""
        with self._lock:
            try:
                settings = self._settings
                settings.ensure_dirs()
                db = open_database(settings)
                try:
                    _ensure_table(db)
                    con = db.database_connection.raw_connection
                    rows = list(
                        con.execute(
                            "SELECT report_json FROM run_history "
                            "ORDER BY started_at DESC LIMIT ?",
                            (limit,),
                        ).fetchall()
                    )
                finally:
                    db.close()
            except Exception:
                return []
        return [_json_to_report(r[0]) for r in rows]

    def get(self, run_id: str) -> RunReport | None:
        """Return one run by id, or None if not in history."""
        with self._lock:
            try:
                settings = self._settings
                settings.ensure_dirs()
                db = open_database(settings)
                try:
                    _ensure_table(db)
                    con = db.database_connection.raw_connection
                    row = con.execute(
                        "SELECT report_json FROM run_history WHERE run_id = ?",
                        (run_id,),
                    ).fetchone()
                finally:
                    db.close()
            except Exception:
                return None
        if row is None:
            return None
        return _json_to_report(row[0])


__all__ = ["MAX_HISTORY_ROWS", "RunHistory"]


def _unused_path_settings() -> Path:
    """Stub for test setups that want a Settings object."""
    return Path("/tmp/webapp-history-test")


# ``_ = ...`` keeps ruff from flagging the unused import that the
# type hint at the top of this file pulls in.
_ = (Settings,)
_ = (datetime,)
