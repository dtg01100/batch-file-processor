"""Processed-files endpoints.

Endpoints
---------
- ``GET  /api/processed-files``              paginated list (filters + total)
- ``GET  /api/processed-files/flagged``      all rows carrying ``resend_flag``
- ``POST /api/processed-files/{id}/resend``  flag a single row
- ``POST /api/processed-files/resend-batch`` flag many rows in one call
- ``POST /api/processed-files/clear-flags``  clear every ``resend_flag``

The bulk operations live here (not in ``maintenance``) because they
target the ``processed_files`` table only — ``maintenance`` is for
app-wide housekeeping (move-all-active, drop queued emails, etc.).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.resend import (
    clear_resend_flags,
    count_processed_files,
    list_processed_files,
    set_resend_flag,
    set_resend_flag_batch,
)
from webapp.routers._deps import get_settings

router = APIRouter()


@router.get("/api/processed-files")
def api_processed_files(
    folder_id: int | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 200,
    offset: int = 0,
    settings: Settings = Depends(get_settings),
) -> dict:
    """List recent processed-files rows.

    Query params (all optional):
        folder_id: restrict to one folder.
        search: substring match against file_name / folder_alias /
            invoice_numbers (case-insensitive).
        date_from: ISO date lower bound on processed_at.
        date_to: ISO date upper bound (inclusive — the day itself is
            included).
        limit: maximum rows to return (default 200, capped at 10000
            to prevent expensive full-history dumps).
        offset: number of matching rows to skip (for "Load More"
            pagination). Must be non-negative; capped at 10000 to
            mirror the limit guard.

    The response includes ``total`` — the count of rows that match
    the filters ignoring ``limit`` / ``offset`` — so the dashboard
    knows whether more pages remain. ``count`` is the size of the
    current page.
    """
    if limit < 1:
        limit = 200
    if limit > 10000:
        limit = 10000
    if offset < 0:
        offset = 0
    if offset > 10000:
        offset = 10000
    with lock():
        db = open_database(settings)
        try:
            total = count_processed_files(
                db,
                folder_id=folder_id,
                search=search or None,
                date_from=date_from or None,
                date_to=date_to or None,
            )
            rows = list_processed_files(
                db,
                folder_id=folder_id,
                search=search or None,
                date_from=date_from or None,
                date_to=date_to or None,
                limit=limit,
                offset=offset,
            )
        finally:
            db.close()
    return {
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "files": rows,
    }


@router.get("/api/processed-files/flagged")
def api_processed_files_flagged(
    folder_id: int | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """List every processed-files row, optionally filtered by folder."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    with lock():
        db = open_database(settings)
        try:
            rows = list_processed_files(db, folder_id=folder_id, limit=500)
        finally:
            db.close()
    return {"count": len(rows), "files": rows}


@router.post("/api/processed-files/{file_id}/resend")
def api_flag_for_resend(
    file_id: int,
    resend: bool = True,  # noqa: FBT001,FBT002
    settings: Settings = Depends(get_settings),
) -> dict:
    """Set or clear the resend flag on one processed-files row."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    with lock():
        db = open_database(settings)
        try:
            ok = set_resend_flag(db, file_id, resend=resend)
        finally:
            db.close()
    if not ok:
        raise HTTPException(status_code=404, detail=f"Row {file_id} not found")
    return {"id": file_id, "resend_flag": resend}


@router.post("/api/processed-files/resend-batch")
def api_flag_batch(
    file_ids: list[int],
    resend: bool = True,  # noqa: FBT001,FBT002
    settings: Settings = Depends(get_settings),
) -> dict:
    """Set/clear the resend flag on many rows in one call."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    with lock():
        db = open_database(settings)
        try:
            updated = set_resend_flag_batch(db, file_ids, resend=resend)
        finally:
            db.close()
    return {"updated": updated}


@router.post("/api/processed-files/clear-flags")
def api_clear_flags(
    settings: Settings = Depends(get_settings),
) -> dict:
    """Clear every ``resend_flag`` in the database."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=503, detail="No database imported yet")
    settings.ensure_dirs()
    with lock():
        db = open_database(settings)
        try:
            rows = list_processed_files(db, limit=10000)
            ids = [r["id"] for r in rows if r.get("resend_flag")]
            cleared = clear_resend_flags(db, ids)
        finally:
            db.close()
    return {"cleared": cleared}
