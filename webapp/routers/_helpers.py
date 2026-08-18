"""Cross-router payload builders.

These were ``_folder_summary`` / ``_config_payload`` / ``_run_summary`` /
``dataclass_to_dict`` inside ``webapp/main.py``'s create_app body. They
are pure functions over already-loaded data, so they live here as
imports rather than ``Depends()``-injected services.

Keeping them in one place means the endpoint at ``GET /api/folders``
(``system``) and the one at ``GET /api/folders/{id}`` (``folders``)
can't drift on how a folder row is serialised.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

from core.structured_logging import get_logger
from webapp.config import Settings
from webapp.database import get_base_directory, get_source_platform, lock, open_database
from webapp.importer import ImportResult
from webapp.paths import resolve
from webapp.runner import RunReport

logger = get_logger(__name__)


def folder_summary(row: dict, base_dir: str) -> dict:
    """Build the API representation of a folder row.

    Used by ``GET /api/folders`` (list) and ``GET /api/folders/{id}``
    (single-folder edit view via ``folder_row_to_schema`` in
    ``webapp.folder_schema``).
    """
    relative = str(row.get("folder_name") or "")
    resolved = resolve(base_dir, relative)
    backends = [
        name
        for name, key in (
            ("copy", "process_backend_copy"),
            ("ftp", "process_backend_ftp"),
            ("email", "process_backend_email"),
            ("http", "process_backend_http"),
        )
        if str(row.get(key, "")).lower() in ("1", "true")
    ]
    # Per-format plugin configuration (read-only audit view). Normalized
    # to a dict so the payload is JSON-safe even for legacy rows that
    # stored the column as JSON text.
    plugin_config = row.get("plugin_configurations") or {}
    if isinstance(plugin_config, str):
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            plugin_config = json.loads(plugin_config)
    if not isinstance(plugin_config, dict):
        plugin_config = {}
    return {
        "id": row.get("id"),
        "folder_name": relative,
        "resolved_path": resolved,
        "path_exists": bool(resolved) and Path(resolved).is_dir(),
        "alias": row.get("alias") or "",
        "is_active": str(row.get("folder_is_active", "")).lower() in ("1", "true"),
        "backends": backends,
        # Normalized lowercase, matching merge_plugin_config's lookup.
        "convert_to_format": str(row.get("convert_to_format") or "").strip().lower(),
        "plugin_configurations": plugin_config,
    }


def config_payload(settings: Settings) -> dict:
    """Build the ``/api/config`` payload, tolerating a missing/corrupt DB.

    A missing/corrupt database should not take down ``/api/config``;
    the payload already reports ``database_exists=False``. We log for
    operators instead of failing the endpoint.
    """
    source_platform = ""
    stored_base = ""
    folders_count = 0
    active_count = 0
    try:
        with lock():
            db = open_database(settings)
            with contextlib.suppress(Exception):
                source_platform = get_source_platform(db)
                stored_base = get_base_directory(db, settings)
                rows = list(db.folders_table.all()) if db.folders_table else []
                folders_count = len(rows)
                active_count = sum(
                    1
                    for r in rows
                    if str(r.get("folder_is_active", "")).lower() in ("1", "true")
                )
            with contextlib.suppress(Exception):
                db.close()
    except Exception:
        logger.debug("api/config tolerated an unreadable database", exc_info=True)
    return {
        "base_dir": str(settings.base_dir),
        "data_dir": str(settings.data_dir),
        "database_exists": settings.database_path.is_file(),
        "imported_base_dir": stored_base,
        "source_platform": source_platform,
        "folders_count": folders_count,
        "active_count": active_count,
    }


def run_summary(report: RunReport, *, include_log: bool = False) -> dict:
    """Serialize a ``RunReport`` for the API (folder detail + optional log)."""
    data = {
        "run_id": report.run_id,
        "status": report.status,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "total_processed": report.total_processed,
        "total_failed": report.total_failed,
        "error": report.error,
        # Phase 5.3: computed at completion (0.0 on the running placeholder).
        "duration_seconds": report.duration_seconds,
        "files_per_second": report.files_per_second,
        "folders": [
            {
                "alias": f.alias,
                "relative_path": f.relative_path,
                "resolved_path": f.resolved_path,
                "files_processed": f.files_processed,
                "files_failed": f.files_failed,
                "success": f.success,
                "errors": f.errors,
                # Phase 5.3 follow-up: per-folder timing + threshold warning.
                "duration_seconds": f.duration_seconds,
                "warning": f.warning,
            }
            for f in report.folders
        ],
    }
    if include_log:
        data["run_log"] = "\n".join(f.run_log for f in report.folders)
    return data


def dataclass_to_dict(result: ImportResult) -> dict:
    """Flatten an ``ImportResult`` to a JSON-safe dict for ``POST /api/import``.

    The import endpoint adds ``duration_seconds`` on top of this — kept
    out of here because the timer is an endpoint concern, not a payload
    concern.
    """
    return {
        "folders_imported": result.folders_imported,
        "active_folders": result.active_folders,
        "rebased_paths": result.rebased_paths,
        "source_platform": result.source_platform,
        "database_path": result.database_path,
        "base_directory": result.base_directory,
    }
