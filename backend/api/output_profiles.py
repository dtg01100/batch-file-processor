"""Output Profiles API - Manage reusable output configurations

Output profiles allow users to save and reuse different output
configurations for file processing (CSV, EDI, eStore eInvoice, etc.)
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/output-profiles", tags=["output-profiles"])


class OutputProfileCreate(BaseModel):
    """Output profile creation model"""

    name: str
    alias: str
    description: Optional[str] = ""
    output_format: str  # csv, edi, estore-einvoice, fintech, scannerware, scansheet-type-a, simplified-csv, stewart-custom, yellowdog-csv
    edi_tweaks: Optional[str] = "{}"
    custom_settings: Optional[str] = "{}"


class OutputProfileUpdate(BaseModel):
    """Output profile update model"""

    name: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    output_format: Optional[str] = None
    edi_tweaks: Optional[str] = None
    custom_settings: Optional[str] = None


@router.get("/")
def list_profiles():
    """
    List all output profiles

    Returns list of all profiles including default
    """
    db = get_database()
    profiles_table = db["output_profiles"]
    profiles = list(profiles_table.all())
    return profiles


@router.get("/{profile_id}")
def get_profile(profile_id: int):
    """
    Get specific output profile by ID

    Returns profile dict or 404 if not found
    """
    db = get_database()
    profiles_table = db["output_profiles"]
    profile = profiles_table.find_one(id=profile_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Output profile not found")

    return profile


@router.post("/")
def create_profile(profile: OutputProfileCreate):
    """
    Create new output profile

    Creates a new output profile with specified configuration
    Returns created profile with ID
    """
    db = get_database()
    profiles_table = db["output_profiles"]

    # Check if alias already exists
    existing = profiles_table.find_one(alias=profile.alias)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Profile with alias '{profile.alias}' already exists",
        )

    # Check if is_default is set, only allow one default
    # For now, create with is_default=False
    # User can set one as default later

    profile_id = profiles_table.insert(
        {
            "name": profile.name,
            "alias": profile.alias,
            "description": profile.description,
            "output_format": profile.output_format,
            "edi_tweaks": profile.edi_tweaks,
            "custom_settings": profile.custom_settings,
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )

    logger.info(f"Output profile created: {profile.alias} (ID: {profile_id})")
    return {"id": profile_id, **profile.dict()}


@router.put("/{profile_id}")
def update_profile(profile_id: int, profile: OutputProfileUpdate):
    """
    Update existing output profile

    Updates profile fields, cannot change created_at
    Returns updated profile
    """
    db = get_database()
    profiles_table = db["output_profiles"]

    # Check if profile exists
    existing_profile = profiles_table.find_one(id=profile_id)
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Output profile not found")

    update_dict = profile.dict(exclude_unset=True)

    # Prevent changing created_at
    if "created_at" in update_dict:
        del update_dict["created_at"]

    # Check if new alias conflicts with another profile
    if "alias" in update_dict:
        alias_conflict = profiles_table.find_one(
            alias=update_dict["alias"], id={"!": profile_id}
        )
        if alias_conflict:
            raise HTTPException(
                status_code=400,
                detail=f"Profile with alias '{update_dict['alias']}' already exists",
            )

    # Add updated_at
    update_dict["updated_at"] = datetime.now()

    profiles_table.update(update_dict, ["id"])

    logger.info(f"Output profile updated: {profile_id}")
    return {"message": "Output profile updated successfully"}


@router.delete("/{profile_id}")
def delete_profile(profile_id: int):
    """
    Delete output profile

    Deletes profile unless it's the default profile
    Cannot delete default profile
    """
    db = get_database()
    profiles_table = db["output_profiles"]

    profile = profiles_table.find_one(id=profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Output profile not found")

    # Prevent deleting default profile
    if profile.get("is_default"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default profile",
        )

    profiles_table.delete(id=profile_id)

    logger.info(f"Output profile deleted: {profile_id}")
    return {"message": "Output profile deleted successfully"}


@router.post("/{profile_id}/set-default")
def set_default_profile(profile_id: int):
    """
    Set profile as default

    Sets specified profile as default and unsets previous default
    """
    db = get_database()
    profiles_table = db["output_profiles"]

    profile = profiles_table.find_one(id=profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Output profile not found")

    # Unset previous default
    profiles_table.update({"is_default": False}, ["id"])

    # Set new default
    profiles_table.update(
        {"id": profile_id, "is_default": True, "updated_at": datetime.now()}, ["id"]
    )

    logger.info(f"Default profile set: {profile_id}")
    return {"message": "Default profile updated successfully"}


@router.get("/default")
def get_default_profile():
    """
    Get default output profile

    Returns profile marked as default or null if none set
    """
    db = get_database()
    profiles_table = db["output_profiles"]

    default_profile = profiles_table.find_one(is_default=True)
    if not default_profile:
        # Return standard CSV if no default set
        return {
            "id": 1,
            "name": "Standard CSV Output",
            "alias": "standard-csv",
            "description": "Default CSV output format",
            "output_format": "csv",
            "edi_tweaks": "{}",
            "custom_settings": "{}",
            "is_default": True,
        }

    return default_profile


@router.get("/formats")
def list_output_formats():
    """
    List all available output formats

    Returns list of supported output formats with descriptions
    """
    formats = [
        {
            "format": "csv",
            "name": "CSV",
            "description": "Standard CSV format",
        },
        {
            "format": "edi",
            "name": "EDI",
            "description": "Electronic Data Interchange format",
        },
        {
            "format": "estore-einvoice",
            "name": "eStore eInvoice",
            "description": "eStore e-invoice format",
        },
        {
            "format": "fintech",
            "name": "Fintech",
            "description": "Fintech banking format",
        },
        {
            "format": "scannerware",
            "name": "Scannerware",
            "description": "Scannerware integration",
        },
        {
            "format": "scansheet-type-a",
            "name": "Scansheet Type A",
            "description": "Scansheet type A format",
        },
        {
            "format": "simplified-csv",
            "name": "Simplified CSV",
            "description": "Simplified CSV output",
        },
        {
            "format": "stewart-custom",
            "name": "Stewart Custom",
            "description": "Stewart custom format",
        },
        {
            "format": "yellowdog-csv",
            "name": "Yellowdog CSV",
            "description": "Yellowdog CSV format",
        },
    ]

    return formats
