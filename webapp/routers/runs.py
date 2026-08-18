"""Run orchestration: start, list, detail, and the SSE log stream.

Endpoints
---------
- ``POST /api/run``                start a background run
- ``POST /api/resend``             start a background resend run
- ``POST /api/folders/{id}/run``   run a single folder
- ``GET  /api/runs``               recent runs
- ``GET  /api/runs/{run_id}``      one run (poll while running)
- ``GET  /api/runs/{run_id}/log``  SSE stream of the run's per-folder logs

The SSE endpoint at ``/api/runs/{run_id}/log`` is the only non-trivial
piece. It yields chunks of log lines as the worker thread writes them,
then a terminal ``event: done`` carrying the final status. The
underlying ``_events`` generator is intentionally simple — it polls the
``RunStore`` every second, so the connection stays open for the full
duration of a long run.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from webapp.config import Settings
from webapp.database import lock, open_database
from webapp.routers._deps import get_history, get_run_store, get_settings
from webapp.routers._helpers import run_summary

router = APIRouter()


@router.post("/api/run")
def api_run(
    settings: Settings = Depends(get_settings),
    run_store=Depends(get_run_store),
) -> dict:
    """Start a background run over every active folder."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=400, detail="No database imported yet")
    try:
        run_id = run_store.start(settings)
    except RuntimeError as exc:
        # Guardrail: refuse to start a second concurrent run.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"run_id": run_id}


@router.post("/api/resend")
def api_resend(
    settings: Settings = Depends(get_settings),
    run_store=Depends(get_run_store),
) -> dict:
    """Run the dispatcher against every flagged processed-files row."""
    if not settings.database_path.is_file():
        raise HTTPException(status_code=400, detail="No database imported yet")
    try:
        run_id = run_store.start_resend(settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"run_id": run_id}


@router.post("/api/folders/{folder_id}/run")
def api_run_folder(
    folder_id: int,
    settings: Settings = Depends(get_settings),
    run_store=Depends(get_run_store),
) -> dict:
    """Run the dispatcher against a single folder.

    Validates the folder exists up-front so a bad id returns 404
    immediately rather than spawning a worker that just reports a
    failure.
    """
    if not settings.database_path.is_file():
        raise HTTPException(status_code=400, detail="No database imported yet")
    try:
        with lock():
            db = open_database(settings)
            try:
                existing = db.folders_table.find_one(id=folder_id)
            finally:
                db.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Folder {folder_id} not found")
    try:
        run_id = run_store.start_folder(settings, folder_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"run_id": run_id}


@router.get("/api/runs")
def api_runs(
    run_store=Depends(get_run_store),
    history=Depends(get_history),
) -> list[dict]:
    """Return recent runs, newest first.

    The in-memory store hands out runs in insertion order (oldest
    first) while ``RunHistory.recent`` is newest first, so the
    in-memory slice is reversed here to keep one consistent ordering
    contract for the UI (which reverses again for display). Without
    this, the Recent-runs list would reorder after a restart.
    """
    in_memory = {r.run_id: r for r in run_store.list()}
    persisted = []
    if history is not None:
        persisted = history.recent(limit=50)
    seen: set[str] = set()
    out: list[dict] = []
    for r in reversed(list(in_memory.values())):
        out.append(run_summary(r))
        seen.add(r.run_id)
    for r in persisted:
        if r.run_id not in seen:
            out.append(run_summary(r))
            seen.add(r.run_id)
    return out


@router.get("/api/runs/{run_id}")
def api_run_detail(
    run_id: str,
    run_store=Depends(get_run_store),
    history=Depends(get_history),
) -> dict:
    """Return one run (poll this while running)."""
    report = run_store.get(run_id)
    if report is None and history is not None:
        report = history.get(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run_summary(report, include_log=True)


@router.get("/api/runs/{run_id}/log")
def api_run_log(
    run_id: str,
    run_store=Depends(get_run_store),
    history=Depends(get_history),
):
    """Server-Sent Events stream of the run's per-folder logs.

    For finished runs we replay the persisted ``run_log``. For
    in-flight runs we poll the in-memory report every second and emit
    any new lines since the last tick. The connection closes when the
    run finishes (``event: done``).
    """
    report = run_store.get(run_id)
    if report is None and history is not None:
        report = history.get(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Run not found")

    def _events():
        last_seen = 0
        yielded = False
        while True:
            # Re-fetch on every tick so we see new lines as the
            # worker writes them.
            cur = run_store.get(run_id)
            if cur is None and history is not None:
                cur = history.get(run_id)
            if cur is None:
                yield "event: done\ndata: missing\n\n"
                return
            log = "\n".join(f.run_log for f in cur.folders)
            if len(log) > last_seen:
                chunk = log[last_seen:]
                yield "event: log\ndata: " + chunk.replace("\n", "\\n") + "\n\n"
                last_seen = len(log)
                yielded = True
            if cur.status != "running":
                if not yielded:
                    # Stream the full log once before closing.
                    yield "event: log\ndata: " + log.replace("\n", "\\n") + "\n\n"
                yield f"event: done\ndata: {cur.status}\n\n"
                return
            time.sleep(1.0)

    return StreamingResponse(
        _events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
