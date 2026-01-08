"""Settings API endpoints with JAR file upload support"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from backend.core.database import get_database
from backend.core.encryption import encrypt_password


logger = logging.getLogger(__name__)

# No prefix here - included as /api/settings in main.py
router = APIRouter(tags=["settings"])


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
    """
    Get current settings

    Returns settings dict with passwords masked
    """
    db = get_database()
    settings_table = db["settings"]
    settings = settings_table.find_one(id=1)

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Mask sensitive fields
    result = dict(settings)
    if result.get("email_password"):
        result["email_password"] = "***"
    if result.get("as400_password"):
        result["as400_password"] = "***"
    if result.get("jdbc_password"):
        result["jdbc_password"] = "***"

    return result


@router.put("/")
async def update_settings(settings: SettingsUpdate):
    """
    Update settings

    Accepts partial settings update and saves to database
    """
    db = get_database()
    settings_table = db["settings"]

    update_dict = settings.dict(exclude_unset=True)

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

    logger.info("Settings updated successfully")
    return {"message": "Settings updated successfully"}


@router.post("/upload-jar")
async def upload_jar_file(file: UploadFile = File(...)):
    """
    Upload JDBC driver JAR file

    Accepts .jar files and stores them in /app/drivers/ directory
    Returns path to uploaded file

    Args:
        file: JAR file to upload

    Returns:
        JSON with file path and name

    Raises:
        HTTPException: If file is invalid
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(".jar"):
        raise HTTPException(
            status_code=400,
            detail="Only JAR files are allowed (.jar extension required)",
        )

    # Create drivers directory if it doesn't exist
    drivers_dir = Path("/app/drivers")
    drivers_dir.mkdir(parents=True, exist_ok=True)

    # Generate safe filename
    filename = file.filename
    # Remove path traversal attempts
    filename = os.path.basename(filename)

    file_path = drivers_dir / filename

    # Check if file already exists
    if file_path.exists():
        # Append timestamp to avoid overwriting
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        file_path = drivers_dir / filename

    # Save file
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error(f"Failed to save JAR file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    file_size = len(contents)
    logger.info(f"JAR file uploaded successfully: {filename} ({file_size} bytes)")

    return {
        "filename": filename,
        "path": f"/app/drivers/{filename}",
        "size": file_size,
    }


@router.get("/jars")
def list_jar_files():
    """
    List all uploaded JDBC driver JAR files

    Returns list of available JAR files in /app/drivers/
    """
    drivers_dir = Path("/app/drivers")

    if not drivers_dir.exists():
        return {"jars": []}

    jar_files = []
    for file in drivers_dir.glob("*.jar"):
        stat = file.stat()
        jar_files.append(
            {
                "name": file.name,
                "path": str(file),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        )

    return {"jars": jar_files}


@router.delete("/jars/{filename}")
def delete_jar_file(filename: str):
    """
    Delete a JDBC driver JAR file

    Args:
        filename: Name of JAR file to delete

    Returns:
        Success message

    Raises:
        HTTPException: If file not found or deletion fails
    """
    # Security: Remove path traversal attempts
    filename = os.path.basename(filename)

    drivers_dir = Path("/app/drivers")
    file_path = drivers_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="JAR file not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a valid file")

    try:
        file_path.unlink()
        logger.info(f"JAR file deleted: {filename}")
        return {"message": f"JAR file {filename} deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete JAR file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
