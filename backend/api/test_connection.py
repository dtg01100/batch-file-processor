"""
Connection testing endpoint
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

from backend.remote_fs.factory import create_file_system

logger = logging.getLogger(__name__)
router = APIRouter()


class TestConnectionRequest(BaseModel):
    """Test connection request"""

    connection_type: str  # local, smb, sftp, ftp
    connection_params: Dict[str, Any]


@router.post("/test-connection")
def test_connection(request: TestConnectionRequest):
    """Test a remote file system connection"""
    fs = None
    try:
        # Create file system instance
        fs = create_file_system(request.connection_type, request.connection_params)

        # Try to list files
        files = fs.list_files(".")

        # Success
        logger.info(f"Connection test successful: {request.connection_type}")
        return {
            "success": True,
            "message": "Connection successful",
            "files_count": len(files),
        }

    except Exception as e:
        # Failure
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
    finally:
        if fs:
            try:
                fs.close()
            except Exception:
                pass
