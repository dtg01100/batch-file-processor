"""
Folders API endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging

from backend.core.database import get_database
from backend.core.encryption import encrypt_password, decrypt_password
from backend.remote_fs.factory import create_file_system

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models
class ConnectionParams(BaseModel):
    """Connection parameters (varies by type)"""

    type: str  # local, smb, sftp, ftp
    params: Dict[str, Any]


class FolderCreate(BaseModel):
    """Folder creation model"""

    alias: str
    folder_name: str
    folder_is_active: bool = True
    connection_type: str = "local"
    connection_params: Dict[str, Any] = {}
    schedule: str = ""  # Cron expression
    enabled: bool = False

    # Processing settings (preserve all existing options)
    process_edi: bool = False
    convert_to_format: str = "csv"
    process_backend_copy: bool = False
    process_backend_ftp: bool = False
    process_backend_email: bool = False


class FolderUpdate(BaseModel):
    """Folder update model"""

    alias: Optional[str] = None
    folder_name: Optional[str] = None
    folder_is_active: Optional[bool] = None
    connection_type: Optional[str] = None
    connection_params: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None

    # Processing settings
    process_edi: Optional[bool] = None
    convert_to_format: Optional[str] = None
    process_backend_copy: Optional[bool] = None
    process_backend_ftp: Optional[bool] = None
    process_backend_email: Optional[bool] = None


@router.get("/")
def list_folders():
    """List all folders"""
    db = get_database()
    folders_table = db["folders"]

    folders = []
    for folder in folders_table.find():
        # Decrypt connection params if present
        if folder.get("connection_params"):
            try:
                connection_params = json.loads(folder["connection_params"])
                # Decrypt sensitive fields
                if "password" in connection_params:
                    connection_params["password"] = (
                        "***"  # Don't return actual password
                    )
                folder["connection_params"] = connection_params
            except Exception:
                pass
        folders.append(dict(folder))

    return folders


@router.get("/{folder_id}")
def get_folder(folder_id: int):
    """Get a specific folder by ID"""
    db = get_database()
    folders_table = db["folders"]

    folder = folders_table.find_one(id=folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Decrypt connection params
    if folder.get("connection_params"):
        try:
            connection_params = json.loads(folder["connection_params"])
            if "password" in connection_params:
                connection_params["password"] = "***"
            folder["connection_params"] = connection_params
        except Exception:
            pass

    return dict(folder)


@router.post("/")
def create_folder(folder: FolderCreate):
    """Create a new folder"""
    db = get_database()
    folders_table = db["folders"]

    # Encrypt passwords in connection params
    if "password" in folder.connection_params:
        folder.connection_params["password"] = encrypt_password(
            folder.connection_params["password"]
        )

    # Convert to dict for dataset
    folder_dict = folder.dict()
    folder_dict["connection_params"] = json.dumps(folder_dict.pop("connection_params"))

    # Insert into database
    folder_id = folders_table.insert(folder_dict)

    logger.info(f"Created folder: {folder.alias} (ID: {folder_id})")
    return {**folder_dict, "id": folder_id}


@router.put("/{folder_id}")
def update_folder(folder_id: int, folder: FolderUpdate):
    """Update an existing folder"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    existing = folders_table.find_one(id=folder_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Build update dict with only non-None values
    update_dict = {}
    for key, value in folder.dict().items():
        if value is not None:
            update_dict[key] = value

    # Encrypt passwords if updating connection params
    if (
        "connection_params" in update_dict
        and "password" in update_dict["connection_params"]
    ):
        update_dict["connection_params"]["password"] = encrypt_password(
            update_dict["connection_params"]["password"]
        )

    # Convert to JSON for storage
    if "connection_params" in update_dict:
        update_dict["connection_params"] = json.dumps(
            update_dict.pop("connection_params")
        )

    # Update folder
    folders_table.update(update_dict, ["id"])
    logger.info(f"Updated folder ID: {folder_id}")

    return {**dict(existing), **update_dict}


@router.delete("/{folder_id}")
def delete_folder(folder_id: int):
    """Delete a folder"""
    db = get_database()
    folders_table = db["folders"]

    # Check if folder exists
    existing = folders_table.find_one(id=folder_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Delete folder
    folders_table.delete(id=folder_id)
    logger.info(f"Deleted folder: {existing.get('alias', 'Unknown')}")

    return {"message": "Folder deleted successfully"}
