"""
Runs (run history) API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from backend.core.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def list_runs(
    folder_id: Optional[int] = None, status: Optional[str] = None, limit: int = 50
):
    """
    List run history

    Args:
        folder_id: Filter by folder ID
        status: Filter by status (running, completed, failed)
        limit: Maximum number of runs to return
    """
    db = get_database()
    runs_table = db["runs"]

    # Build query
    query_dict = {}
    if folder_id:
        query_dict["folder_id"] = folder_id
    if status:
        query_dict["status"] = status

    # Get runs with ordering
    runs = []
    for run in runs_table.find(**query_dict, order_by="-started_at", _limit=limit):
        runs.append(dict(run))

    return runs


@router.get("/{run_id}")
def get_run(run_id: int):
    """Get a specific run by ID"""
    db = get_database()
    runs_table = db["runs"]

    run = runs_table.find_one(id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return dict(run)


@router.get("/{run_id}/logs")
def get_run_logs(run_id: int):
    """Get logs for a specific run"""
    db = get_database()
    runs_table = db["runs"]

    # Get run details
    run = runs_table.find_one(id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Try to read run log file
    # Note: Run logs are stored in /app/logs directory
    # Log filename format: {folder_alias} errors.{timestamp}.txt
    import os
    from pathlib import Path

    logs_dir = Path("/app/logs")
    if not logs_dir.exists():
        raise HTTPException(status_code=404, detail="Logs directory not found")

    # Look for log files matching this run
    run_time = run["started_at"]
    if run_time:
        time_str = run_time.strftime("%a %b %d %H %M %S %Y").replace(":", "-")
        log_files = list(logs_dir.glob(f"*{run['folder_alias']}*{time_str}*"))
    else:
        log_files = list(logs_dir.glob(f"*{run['folder_alias']}*"))

    if not log_files:
        return {"logs": [], "message": "No logs found for this run"}

    # Read log files
    logs = []
    for log_file in sorted(log_files, reverse=True)[:5]:  # Last 5 matching logs
        try:
            with open(log_file, "r") as f:
                logs.append({"filename": log_file.name, "content": f.read()})
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")

    return {"run_id": run_id, "folder_alias": run["folder_alias"], "logs": logs}
