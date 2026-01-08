"""
Settings API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from backend.core.database import get_database
from backend.core.encryption import encrypt_password, decrypt_password

logger = logging.getLogger(__name__)
router = APIRouter()


class SettingsUpdate(BaseModel):
    """Settings update model"""

    # Connection method
    connection_method: Optional[str] = None  # "jdbc" or "odbc"

    # Email settings
    enable_email: Optional[bool] = None
    email_address: Optional[str] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None

    # Backup settings
    enable_interval_backups: Optional[bool] = None
    backup_counter_maximum: Optional[int] = None

    # ODBC settings (legacy)
    odbc_driver: Optional[str] = None
    as400_address: Optional[str] = None
    as400_username: Optional[str] = None
    as400_password: Optional[str] = None

    # JDBC settings (preferred)
    jdbc_url: Optional[str] = None
    jdbc_driver_class: Optional[str] = (
        None  # e.g., "com.ibm.as400.access.AS400JDBCDriver"
    )
    jdbc_jar_path: Optional[str] = None  # Path to JDBC driver JAR
    jdbc_username: Optional[str] = None
    jdbc_password: Optional[str] = None


@router.get("/")
def get_settings():
    """Get all global settings"""
    db = get_database()
    settings_table = db["settings"]

    settings = settings_table.find_one(id=1)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Decrypt sensitive fields
    result = dict(settings)
    if result.get("email_password"):
        result["email_password"] = "***"
    if result.get("as400_password"):
        result["as400_password"] = "***"
    if result.get("jdbc_password"):
        result["jdbc_password"] = "***"

    return result


@router.put("/")
def update_settings(settings: SettingsUpdate):
    """Update global settings"""
    db = get_database()
    settings_table = db["settings"]

    # Check if settings exist
    existing = settings_table.find_one(id=1)
    if not existing:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Build update dict with only non-None values
    update_dict = {}
    for key, value in settings.dict().items():
        if value is not None:
            update_dict[key] = value

    # Encrypt passwords
    if "email_password" in update_dict:
        update_dict["email_password"] = encrypt_password(update_dict["email_password"])
    if "as400_password" in update_dict:
        update_dict["as400_password"] = encrypt_password(update_dict["as400_password"])
    if "jdbc_password" in update_dict:
        update_dict["jdbc_password"] = encrypt_password(update_dict["jdbc_password"])

    # Update settings (include id for matching)
    update_dict["id"] = 1
    settings_table.update(update_dict, ["id"])

    logger.info("Settings updated")
    return {**dict(existing), **update_dict}
