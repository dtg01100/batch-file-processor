"""
Jobs API endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from backend.core.database import get_database
from backend.core.scheduler import (
    add_job,
    remove_job,
    get_jobs,
    get_next_run_time,
    validate_cron_expression,
    scheduler,
)
from backend.core.encryption import decrypt_password
import json

logger = logging.getLogger(__name__)
router = APIRouter()


class JobCreate(BaseModel):
    """Job creation model"""

    folder_id: int
    cron_expression: str
    enabled: bool = True


class JobUpdate(BaseModel):
    """Job update model"""

    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("/")
def list_jobs():
    """List all scheduled jobs"""
    db = get_database()
    folders_table = db["folders"]

    jobs = []
    # Get all folders with schedules
    for folder in folders_table.find(enabled=True):
        job_info = {
            "id": folder["id"],
            "folder_alias": folder["alias"],
            "folder_name": folder["folder_name"],
            "connection_type": folder.get("connection_type", "local"),
            "schedule": folder.get("schedule", ""),
            "enabled": folder.get("enabled", False),
            "folder_is_active": folder.get("folder_is_active", False),
        }

        # Get next run time from scheduler
        next_run = get_next_run_time(folder["id"], folder["alias"])
        job_info["next_run"] = next_run

        jobs.append(job_info)

    return jobs


@router.get("/{folder_id}")
def get_job(folder_id: int):
    """Get a specific job by folder ID"""
    db = get_database()
    folders_table = db["folders"]

    folder = folders_table.find_one(id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = {
        "id": folder["id"],
        "folder_alias": folder["alias"],
        "folder_name": folder["folder_name"],
        "connection_type": folder.get("connection_type", "local"),
        "schedule": folder.get("schedule", ""),
        "enabled": folder.get("enabled", False),
        "folder_is_active": folder.get("folder_is_active", False),
    }

    # Get next run time
    next_run = get_next_run_time(folder["id"], folder["alias"])
    job_info["next_run"] = next_run

    return job_info


@router.post("/")
def create_job(job: JobCreate):
    """Create a new scheduled job"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    folder = folders_table.find_one(id=job.folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Validate cron expression
    if not validate_cron_expression(job.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")

    # Update folder with schedule and enabled status
    folders_table.update(
        {"schedule": job.cron_expression, "enabled": job.enabled}, ["id"]
    )

    # Add job to scheduler if enabled
    if job.enabled:
        from backend.schedulers.job_executor import execute_folder_job

        job_id = add_job(
            folder["id"], folder["alias"], job.cron_expression, execute_folder_job
        )
        logger.info(f"Created job for folder {folder['alias']} (ID: {job_id})")
    else:
        logger.info(f"Created disabled job for folder {folder['alias']}")

    return {
        "folder_id": folder["id"],
        "folder_alias": folder["alias"],
        "schedule": job.cron_expression,
        "enabled": job.enabled,
    }


@router.put("/{folder_id}")
def update_job(folder_id: int, job: JobUpdate):
    """Update an existing job"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    folder = folders_table.find_one(id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build update dict with only non-None values
    update_dict = {}
    for key, value in job.dict().items():
        if value is not None:
            update_dict[key] = value

    # Validate cron expression if updating
    if "cron_expression" in update_dict:
        if not validate_cron_expression(update_dict["cron_expression"]):
            raise HTTPException(status_code=400, detail="Invalid cron expression")

    # Update folder
    folders_table.update(update_dict, ["id"])
    logger.info(f"Updated job for folder {folder['alias']}")

    # Update scheduler if enabled/disabled changed
    from backend.schedulers.job_executor import execute_folder_job

    # Remove existing job
    remove_job(folder["id"], folder["alias"])

    # Add job if enabled
    if update_dict.get("enabled", folder.get("enabled", False)):
        if "cron_expression" in update_dict:
            cron_expr = update_dict["cron_expression"]
        else:
            cron_expr = folder.get("schedule", "")

        if cron_expr:
            add_job(folder["id"], folder["alias"], cron_expr, execute_folder_job)
            logger.info(f"Job enabled for folder {folder['alias']}")

    return {**dict(folder), **update_dict}


@router.delete("/{folder_id}")
def delete_job(folder_id: int):
    """Delete (disable) a job"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    folder = folders_table.find_one(id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove from scheduler
    remove_job(folder["id"], folder["alias"])

    # Disable job in database
    folders_table.update({"enabled": False}, ["id"])

    logger.info(f"Deleted job for folder {folder['alias']}")

    return {"message": "Job deleted successfully"}


@router.post("/{folder_id}/run")
def run_job(folder_id: int, background_tasks: BackgroundTasks):
    """Manually trigger a job to run now"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    folder = folders_table.find_one(id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if not folder.get("folder_is_active", False):
        raise HTTPException(status_code=400, detail="Folder is not active")

    # Decrypt connection params
    connection_params = {}
    if folder.get("connection_params"):
        try:
            connection_params = json.loads(folder["connection_params"])
            if "password" in connection_params:
                connection_params["password"] = decrypt_password(
                    connection_params["password"]
                )
        except Exception as e:
            logger.error(f"Failed to decrypt connection params: {e}")

    # Execute job in background
    from backend.schedulers.job_executor import execute_folder_job

    background_tasks.add_task(
        execute_folder_job, folder_id, folder["alias"], connection_params, folder
    )

    logger.info(f"Manually triggered job for folder {folder['alias']}")
    return {"message": "Job started", "folder_alias": folder["alias"]}


@router.post("/{folder_id}/toggle")
def toggle_job(folder_id: int):
    """Enable/disable a scheduled job"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    folder = folders_table.find_one(id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Job not found")

    # Toggle enabled status
    new_status = not folder.get("enabled", False)
    folders_table.update({"enabled": new_status}, ["id"])

    # Update scheduler
    from backend.schedulers.job_executor import execute_folder_job

    # Remove existing job
    remove_job(folder["id"], folder["alias"])

    # Add job if enabled
    if new_status and folder.get("schedule"):
        add_job(folder["id"], folder["alias"], folder["schedule"], execute_folder_job)
        logger.info(f"Job enabled for folder {folder['alias']}")
    else:
        logger.info(f"Job disabled for folder {folder['alias']}")

    return {"enabled": new_status, "folder_alias": folder["alias"]}
