"""File-upload ingestion endpoints.

Endpoints
---------
- ``POST /api/preview/edi``  classify an EDI upload (parse-only preview)
- ``POST /api/import``       multipart upload of a legacy ``folders.db``
                              + optional ``base_dir`` and ``platform``
                              overrides; also reports ``duration_seconds``
                              so the dashboard can render "Imported N
                              folders in 28.4s" instead of a spinner.
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from time import perf_counter as _perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from webapp.config import Settings
from webapp.importer import ImportResult, import_database
from webapp.preview import preview_edi
from webapp.routers._deps import get_settings
from webapp.routers._helpers import dataclass_to_dict

router = APIRouter()


@router.post("/api/preview/edi")
async def api_preview_edi(
    file: Annotated[UploadFile, File()],
) -> dict:
    """Classify an EDI upload and return per-line structure.

    This is a parse-only preview; the full conversion pipeline (which
    writes its output to disk and needs UPC + DB2) is not run here.
    """
    suffix = Path(file.filename or "sample.edi").suffix or ".edi"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="w+b") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return preview_edi(tmp_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    finally:
        with contextlib.suppress(Exception):
            Path(tmp_path).unlink(missing_ok=True)


@router.post("/api/import")
async def api_import(
    file: Annotated[UploadFile, File()],
    base_dir: Annotated[str | None, Form()] = None,
    platform: Annotated[str | None, Form()] = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Import a legacy ``folders.db`` upload into the active DB.

    Phase 6 (gap 1.6): the desktop's "Cancel" button cancelled a
    QThread; the webapp doesn't expose a Cancel endpoint (import is a
    short-lived, one-time setup action and threading a cancel through
    FastAPI's request lifecycle would add a lot of code for little
    operator benefit). Instead, surface timing so the dashboard's
    import notice can show how long the import actually took — a
    30-second import on 500 folders used to be a mystery spinner; now
    it's a clear "Imported 500 folders in 28.4s".
    """
    suffix = Path(file.filename or "folders.db").suffix or ".db"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    started = _perf_counter()
    try:
        result: ImportResult = import_database(
            tmp_path,
            settings,
            base_dir=base_dir or None,
            platform=platform or None,
        )
        payload = dataclass_to_dict(result)
        payload["duration_seconds"] = round(_perf_counter() - started, 3)
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc
    finally:
        with contextlib.suppress(Exception):
            Path(tmp_path).unlink(missing_ok=True)
