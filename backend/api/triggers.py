"""Global Triggers API

REST endpoints for managing global triggers that run pipelines
on scheduled intervals (separate from pipeline-specific scheduling).
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


class TriggerCreate(BaseModel):
    """Trigger creation model"""

    name: str
    cron: str  # Cron expression
    enabled: bool = True
    pipeline_ids: List[int] = []  # Which pipelines to run


class TriggerUpdate(BaseModel):
    """Trigger update model"""

    name: Optional[str] = None
    cron: Optional[str] = None
    enabled: Optional[bool] = None
    pipeline_ids: Optional[List[int]] = None


@router.get("/")
def list_triggers():
    """
    List all global triggers

    Returns list of all configured triggers
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    triggers = list(triggers_table.all())

    return {
        "triggers": [
            {
                "id": t["id"],
                "name": t["name"],
                "cron": t["cron"],
                "enabled": t.get("enabled", True),
                "pipeline_ids": json.loads(t.get("pipeline_ids", "[]")),
                "created_at": t.get("created_at"),
                "updated_at": t.get("updated_at"),
            }
            for t in triggers
        ]
    }


@router.get("/{trigger_id}")
def get_trigger(trigger_id: int):
    """
    Get specific trigger by ID

    Returns full trigger configuration
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    trigger = triggers_table.find_one(id=trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    return {
        "id": trigger["id"],
        "name": trigger["name"],
        "cron": trigger["cron"],
        "enabled": trigger.get("enabled", True),
        "pipeline_ids": json.loads(trigger.get("pipeline_ids", "[]")),
        "created_at": trigger.get("created_at"),
        "updated_at": trigger.get("updated_at"),
    }


@router.post("/")
def create_trigger(trigger: TriggerCreate):
    """
    Create new global trigger

    Creates a trigger that will run specified pipelines on schedule
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    trigger_id = triggers_table.insert(
        {
            "name": trigger.name,
            "cron": trigger.cron,
            "enabled": trigger.enabled,
            "pipeline_ids": json.dumps(trigger.pipeline_ids),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )

    logger.info(f"Global trigger created: {trigger.name} (ID: {trigger_id})")

    return {
        "id": trigger_id,
        "name": trigger.name,
        "message": "Trigger created successfully",
    }


@router.put("/{trigger_id}")
def update_trigger(trigger_id: int, update: TriggerUpdate):
    """
    Update existing trigger

    Updates trigger configuration
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    trigger = triggers_table.find_one(id=trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    update_dict = {"updated_at": datetime.now()}

    if update.name is not None:
        update_dict["name"] = update.name
    if update.cron is not None:
        update_dict["cron"] = update.cron
    if update.enabled is not None:
        update_dict["enabled"] = update.enabled
    if update.pipeline_ids is not None:
        update_dict["pipeline_ids"] = json.dumps(update.pipeline_ids)

    triggers_table.update(update_dict, ["id"])

    logger.info(f"Global trigger updated: {trigger_id}")

    return {"message": "Trigger updated successfully"}


@router.delete("/{trigger_id}")
def delete_trigger(trigger_id: int):
    """
    Delete trigger

    Removes trigger from database
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    trigger = triggers_table.find_one(id=trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    triggers_table.delete(id=trigger_id)

    logger.info(f"Global trigger deleted: {trigger_id}")

    return {"message": "Trigger deleted successfully"}


@router.post("/{trigger_id}/toggle")
def toggle_trigger(trigger_id: int):
    """
    Toggle trigger enabled/disabled

    Flips the enabled state of a trigger
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    trigger = triggers_table.find_one(id=trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    new_enabled = not trigger.get("enabled", True)
    triggers_table.update(
        {"id": trigger_id, "enabled": new_enabled, "updated_at": datetime.now()}, ["id"]
    )

    status = "enabled" if new_enabled else "disabled"
    logger.info(f"Global trigger {status}: {trigger_id}")

    return {"message": f"Trigger {status}", "enabled": new_enabled}


@router.get("/{trigger_id}/next-runs")
def get_next_runs(trigger_id: int, count: int = 5):
    """
    Get next scheduled run times

    Returns next N run times for this trigger
    """
    db = get_database()
    triggers_table = db["global_triggers"]

    trigger = triggers_table.find_one(id=trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse cron expression and calculate next runs
    # This is a simplified version - in production, use a proper cron parser
    cron = trigger["cron"]

    next_runs = []
    from datetime import datetime, timedelta

    # Very basic calculation - would need proper cron library in production
    now = datetime.now()

    if cron == "0 9 * * *":  # Daily at 9am
        for i in range(count):
            run_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if run_time <= now:
                run_time += timedelta(days=1)
            next_runs.append(run_time.isoformat())
    elif cron == "0 8 * * 1":  # Weekly Monday at 8am
        for i in range(count):
            days_ahead = 7 - now.weekday()
            if days_ahead >= 7:
                days_ahead -= 7
            run_time = (now + timedelta(days=days_ahead)).replace(
                hour=8, minute=0, second=0, microsecond=0
            )
            next_runs.append(run_time.isoformat())
    else:
        # For custom cron, return basic info
        next_runs = ["Custom schedule - see cron expression"]

    return {"trigger_id": trigger_id, "cron": cron, "next_runs": next_runs}


@router.get("/cron-presets")
def get_cron_presets():
    """
    Get common cron preset options

    Returns list of predefined cron schedules
    """
    presets = [
        {
            "name": "Every Minute",
            "cron": "* * * * *",
            "description": "Runs every minute",
        },
        {
            "name": "Every Hour",
            "cron": "0 * * * *",
            "description": "Runs at the start of every hour",
        },
        {
            "name": "Daily at 9 AM",
            "cron": "0 9 * * *",
            "description": "Runs every day at 9:00 AM",
        },
        {
            "name": "Daily at Midnight",
            "cron": "0 0 * * *",
            "description": "Runs every day at midnight",
        },
        {
            "name": "Weekly on Monday at 8 AM",
            "cron": "0 8 * * 1",
            "description": "Runs every Monday at 8:00 AM",
        },
        {
            "name": "Weekly on Sunday at Midnight",
            "cron": "0 0 * * 0",
            "description": "Runs every Sunday at midnight",
        },
        {
            "name": "First Day of Month at Midnight",
            "cron": "0 0 1 * *",
            "description": "Runs on the 1st of every month at midnight",
        },
        {
            "name": "Every 15 Minutes",
            "cron": "*/15 * * * *",
            "description": "Runs every 15 minutes",
        },
        {
            "name": "Every 30 Minutes",
            "cron": "*/30 * * * *",
            "description": "Runs every 30 minutes",
        },
        {
            "name": "Business Hours (9-5 Weekdays)",
            "cron": "0 9-17 * * 1-5",
            "description": "Runs every hour from 9 AM to 5 PM on weekdays",
        },
    ]

    return {"presets": presets}
