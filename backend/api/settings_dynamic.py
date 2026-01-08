"""Dynamic Settings API

Provides REST endpoints for the composable settings system:
- GET /api/settings/schema - Get JSON schema for all settings
- GET /api/settings/ui-config - Get frontend UI configuration
- GET /api/settings/categories - List all categories
- GET /api/settings/registry - Get raw registry
- POST /api/settings/bulk-update - Update multiple settings
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.database import get_database
from backend.core.settings_registry import (
    SettingsRegistry,
    SettingsComposer,
    SettingCategory,
    SettingType,
    SettingDefinition,
    UIHint,
    ValidationRule,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


# Initialize registry and composer
registry = SettingsRegistry
composer = SettingsComposer(registry)


def initialize_settings_registry():
    """Initialize the settings registry with all known settings"""

    # JDBC settings (optional)
    registry.register(
        SettingDefinition(
            key="jdbc_url",
            category=SettingCategory.DATABASE,
            setting_type=SettingType.STRING,
            default="",
            description="JDBC connection URL",
            ui=UIHint(
                input_type="text",
                label="JDBC URL",
                placeholder="jdbc:as400://hostname;database=dbname",
                help_text="Example: jdbc:as400://myserver.example.com;database=MYDB",
                order=20,
            ),
            order=20,
        )
    )

    registry.register(
        SettingDefinition(
            key="jdbc_driver_class",
            category=SettingCategory.DATABASE,
            setting_type=SettingType.STRING,
            default="com.ibm.as400.access.AS400JDBCDriver",
            description="Full Java class name of JDBC driver",
            ui=UIHint(
                input_type="text",
                label="JDBC Driver Class",
                placeholder="com.ibm.as400.access.AS400JDBCDriver",
                order=30,
            ),
            order=30,
        )
    )

    registry.register(
        SettingDefinition(
            key="jdbc_jar_path",
            category=SettingCategory.DATABASE,
            setting_type=SettingType.STRING,
            default="",
            description="Path to JDBC driver JAR file",
            ui=UIHint(
                input_type="text",
                label="JDBC JAR Path",
                placeholder="/app/drivers/jt400.jar",
                help_text="Absolute path to JDBC driver JAR file",
                order=40,
            ),
            order=40,
        )
    )

    registry.register(
        SettingDefinition(
            key="jdbc_username",
            category=SettingCategory.DATABASE,
            setting_type=SettingType.STRING,
            default="",
            description="Database username for JDBC connection",
            ui=UIHint(input_type="text", label="Database Username", order=50),
            order=50,
            sensitive=True,
        )
    )

    registry.register(
        SettingDefinition(
            key="jdbc_password",
            category=SettingCategory.DATABASE,
            setting_type=SettingType.PASSWORD,
            default="",
            description="Database password for JDBC connection",
            ui=UIHint(input_type="password", label="Database Password", order=60),
            order=60,
            sensitive=True,
        )
    )

    # Email settings
    registry.register(
        SettingDefinition(
            key="enable_email",
            category=SettingCategory.EMAIL,
            setting_type=SettingType.BOOLEAN,
            default=False,
            description="Enable email notifications",
            ui=UIHint(
                input_type="checkbox", label="Enable Email Notifications", order=10
            ),
            order=10,
        )
    )

    registry.register(
        SettingDefinition(
            key="email_address",
            category=SettingCategory.EMAIL,
            setting_type=SettingType.STRING,
            default="",
            description="Sender email address",
            ui=UIHint(
                input_type="email",
                label="Email Address",
                placeholder="notifications@company.com",
                order=20,
            ),
            order=20,
        )
    )

    registry.register(
        SettingDefinition(
            key="email_username",
            category=SettingCategory.EMAIL,
            setting_type=SettingType.STRING,
            default="",
            description="Email SMTP username",
            ui=UIHint(input_type="text", label="SMTP Username", order=30),
            order=30,
        )
    )

    registry.register(
        SettingDefinition(
            key="email_password",
            category=SettingCategory.EMAIL,
            setting_type=SettingType.PASSWORD,
            default="",
            description="Email SMTP password",
            ui=UIHint(input_type="password", label="SMTP Password", order=40),
            order=40,
            sensitive=True,
        )
    )

    registry.register(
        SettingDefinition(
            key="email_smtp_server",
            category=SettingCategory.EMAIL,
            setting_type=SettingType.STRING,
            default="smtp.gmail.com",
            description="SMTP server address",
            ui=UIHint(
                input_type="text",
                label="SMTP Server",
                placeholder="smtp.gmail.com",
                order=50,
            ),
            order=50,
        )
    )

    registry.register(
        SettingDefinition(
            key="smtp_port",
            category=SettingCategory.EMAIL,
            setting_type=SettingType.INTEGER,
            default=587,
            description="SMTP port number",
            ui=UIHint(input_type="number", label="SMTP Port", order=60),
            order=60,
        )
    )

    # Backup settings
    registry.register(
        SettingDefinition(
            key="enable_interval_backups",
            category=SettingCategory.BACKUP,
            setting_type=SettingType.BOOLEAN,
            default=True,
            description="Enable automatic interval backups",
            ui=UIHint(
                input_type="checkbox", label="Enable Automatic Backups", order=10
            ),
            order=10,
        )
    )

    registry.register(
        SettingDefinition(
            key="backup_counter_maximum",
            category=SettingCategory.BACKUP,
            setting_type=SettingType.INTEGER,
            default=200,
            description="Maximum number of backups to retain",
            ui=UIHint(
                input_type="number",
                label="Maximum Backup Count",
                help_text="Older backups will be deleted when limit reached",
                order=20,
            ),
            order=20,
        )
    )

    logger.info(f"Initialized {len(registry.list_all())} settings in registry")


# Initialize on module load
initialize_settings_registry()


class SettingsUpdate(BaseModel):
    """Settings update model"""

    settings: Dict[str, Any]


class BulkUpdateRequest(BaseModel):
    """Bulk update request"""

    settings: Dict[str, Any]


@router.get("/")
def get_settings():
    """
    Get current settings with values

    Returns all settings with their current values from database
    """
    db = get_database()
    settings_table = db["settings"]
    db_settings = settings_table.find_one(id=1) or {}

    # Get all settings with values
    result = {}
    for setting in registry.list_all():
        # Try database value first
        db_value = db_settings.get(setting.key)
        if db_value is not None:
            result[setting.key] = {
                **setting.to_dict(),
                "value": "***" if setting.sensitive else db_value,
            }
        else:
            result[setting.key] = setting.to_dict()

    return result


@router.get("/schema")
def get_settings_schema():
    """
    Get JSON schema for all settings

    Returns complete schema with types, defaults, validation rules
    """
    return registry.generate_schema()


@router.get("/ui-config")
def get_ui_config():
    """
    Get frontend UI configuration

    Returns complete UI configuration for rendering settings forms:
    - Categories with icons
    - Fields with types, labels, placeholders
    - Grouping and ordering
    - Validation hints
    """
    return registry.generate_ui_config()


@router.get("/categories")
def get_categories():
    """
    Get list of all categories

    Returns categories with setting counts
    """
    return registry.list_categories()


@router.get("/registry")
def get_registry():
    """
    Get raw registry contents

    Returns all setting definitions (without values)
    """
    return {
        "settings": [
            {
                "key": s.key,
                "category": s.category.value,
                "type": s.setting_type.value,
                "default": s.default,
                "description": s.description,
                "order": s.order,
                "sensitive": s.sensitive,
            }
            for s in registry.list_all()
        ],
        "categories": registry.list_categories(),
    }


@router.put("/")
async def update_settings(update: SettingsUpdate):
    """
    Update a single setting

    Updates one setting by key
    """
    db = get_database()
    settings_table = db["settings"]

    for key, value in update.settings.items():
        setting = registry.get(key)
        if not setting:
            raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")

        # Validate
        valid, error = setting.validate_value(value)
        if not valid:
            raise HTTPException(
                status_code=400, detail=f"Validation failed for {key}: {error}"
            )

        # Update database
        settings_table.update({key: value, "id": 1}, ["id"])
        logger.info(f"Updated setting: {key}")

    return {"message": "Settings updated successfully"}


@router.post("/bulk-update")
async def bulk_update(update: BulkUpdateRequest):
    """
    Bulk update multiple settings

    Updates multiple settings atomically
    """
    db = get_database()
    settings_table = db["settings"]

    update_dict = {"id": 1}

    for key, value in update.settings.items():
        setting = registry.get(key)
        if not setting:
            raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")

        # Validate
        valid, error = setting.validate_value(value)
        if not valid:
            raise HTTPException(
                status_code=400, detail=f"Validation failed for {key}: {error}"
            )

        update_dict[key] = value

    settings_table.update(update_dict, ["id"])
    logger.info(f"Bulk updated {len(update.settings)} settings")

    return {"message": f"Updated {len(update.settings)} settings"}


@router.get("/{category}")
def get_settings_by_category(category: str):
    """
    Get all settings in a category

    Returns settings filtered by category
    """
    try:
        cat_enum = SettingCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown category: {category}")

    db = get_database()
    settings_table = db["settings"]
    db_settings = settings_table.find_one(id=1) or {}

    result = {}
    for setting in registry.list_by_category(cat_enum):
        db_value = db_settings.get(setting.key)
        result[setting.key] = {
            **setting.to_dict(),
            "value": db_value if db_value is not None else setting.default,
        }

    return result


@router.post("/{key}/reset")
def reset_setting(key: str):
    """
    Reset a setting to its default value

    Removes database override, reverts to default
    """
    setting = registry.get(key)
    if not setting:
        raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")

    db = get_database()
    settings_table = db["settings"]

    # Update to null (will use default)
    settings_table.update({key: None, "id": 1}, ["id"])
    logger.info(f"Reset setting: {key}")

    return {"message": f"Setting {key} reset to default", "value": setting.default}


@router.get("/{key}/validate")
def validate_setting(key: str, value: Any):
    """
    Validate a setting value against its rules

    Returns validation result without saving
    """
    setting = registry.get(key)
    if not setting:
        raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")

    valid, error = setting.validate_value(value)
    return {"valid": valid, "error": error if not valid else None}


# Import os for SettingsComposer
import os
