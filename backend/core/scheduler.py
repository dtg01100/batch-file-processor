"""
APScheduler integration for job scheduling
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = BackgroundScheduler()


def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validate a cron expression

    Args:
        cron_expr: Cron expression (e.g., "0 9 * * *" for daily at 9am)

    Returns:
        True if valid, False otherwise
    """
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False

        # Basic validation - try to create a trigger
        CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )
        return True
    except Exception as e:
        logger.error(f"Invalid cron expression: {cron_expr}, error: {e}")
        return False


def add_job(folder_id: int, folder_alias: str, cron_expr: str, job_func):
    """
    Add a scheduled job

    Args:
        folder_id: Folder ID
        folder_alias: Folder alias (for job ID)
        cron_expr: Cron expression
        job_func: Function to execute

    Returns:
        Job ID if successful, None otherwise
    """
    if not validate_cron_expression(cron_expr):
        logger.error(f"Invalid cron expression for job {folder_alias}: {cron_expr}")
        return None

    try:
        parts = cron_expr.strip().split()
        job_id = f"folder_{folder_id}_{folder_alias}"

        # Add job to scheduler
        job = scheduler.add_job(
            job_func,
            trigger=CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            ),
            id=job_id,
            name=f"Process {folder_alias}",
            replace_existing=True,
        )

        logger.info(f"Added job {job_id} with schedule {cron_expr}")
        return job_id
    except Exception as e:
        logger.error(f"Failed to add job for folder {folder_alias}: {e}")
        return None


def remove_job(folder_id: int, folder_alias: str):
    """
    Remove a scheduled job

    Args:
        folder_id: Folder ID
        folder_alias: Folder alias (for job ID)
    """
    try:
        job_id = f"folder_{folder_id}_{folder_alias}"
        scheduler.remove_job(job_id)
        logger.info(f"Removed job {job_id}")
    except Exception as e:
        logger.error(f"Failed to remove job for folder {folder_alias}: {e}")


def get_jobs():
    """
    Get all scheduled jobs

    Returns:
        List of job info dictionaries
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
        )
    return jobs


def get_next_run_time(folder_id: int, folder_alias: str):
    """
    Get next run time for a specific job

    Args:
        folder_id: Folder ID
        folder_alias: Folder alias

    Returns:
        Next run time as datetime, or None if not found
    """
    try:
        job_id = f"folder_{folder_id}_{folder_alias}"
        job = scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None
    except Exception as e:
        logger.error(f"Failed to get next run time for {folder_alias}: {e}")
        return None


def pause_job(folder_id: int, folder_alias: str):
    """Pause a scheduled job"""
    try:
        job_id = f"folder_{folder_id}_{folder_alias}"
        scheduler.pause_job(job_id)
        logger.info(f"Paused job {job_id}")
    except Exception as e:
        logger.error(f"Failed to pause job {folder_alias}: {e}")


def resume_job(folder_id: int, folder_alias: str):
    """Resume a paused job"""
    try:
        job_id = f"folder_{folder_id}_{folder_alias}"
        scheduler.resume_job(job_id)
        logger.info(f"Resumed job {job_id}")
    except Exception as e:
        logger.error(f"Failed to resume job {folder_alias}: {e}")
