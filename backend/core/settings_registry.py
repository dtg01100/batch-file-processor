"""Composable Settings Registry System

This module provides a dynamic, schema-driven settings management system
that generates settings from output profiles and supports GUI editing.

Core Concepts:
- SettingDefinition: Metadata about a single setting
- SettingsRegistry: Registry of all available settings
- SettingsSchema: Generated schema for API/UI
- SettingsComposer: Composes settings from multiple sources
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class SettingCategory(Enum):
    """Categories for organizing settings"""

    DATABASE = "database"
    EMAIL = "email"
    BACKUP = "backup"
    PROCESSING = "processing"
    OUTPUT = "output"
    GENERAL = "general"


class SettingType(Enum):
    """Field types for settings"""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    NUMBER = "number"
    ARRAY = "array"
    OBJECT = "object"
    PASSWORD = "password"  # Special - masked in UI
    JSON = "json"  # Special - parsed as JSON


@dataclass
class ValidationRule:
    """Validation rule for a setting"""

    type: str  # min, max, pattern, enum, required
    value: Any
    message: str


@dataclass
class UIHint:
    """Hints for frontend UI generation"""

    input_type: str = "text"  # text, password, select, checkbox, textarea, file
    label: str = ""
    placeholder: str = ""
    help_text: str = ""
    options: List[Dict] = field(default_factory=list)  # For select inputs
    hidden: bool = False
    read_only: bool = False
    order: int = 100
    group: str = ""  # For grouping fields in UI
    conditional_display: Optional[Dict] = None  # {"field": "X", "value": "Y"}
    render_as: str = "input"  # input, textarea, select, checkbox, radio, file


@dataclass
class SettingDefinition:
    """
    Complete definition of a settings field

    Attributes:
        key: Unique identifier for the setting
        category: Category for grouping
        setting_type: Data type
        default: Default value if not set
        current_value: Current value (from database)
        description: Human-readable description
        validation: List of validation rules
        ui: UI rendering hints
        sensitive: Whether value should be masked
        order: Display order within category
        version: Schema version for migrations
    """

    key: str
    category: SettingCategory
    setting_type: SettingType
    default: Any
    current_value: Any = None
    description: str = ""
    validation: List[ValidationRule] = field(default_factory=list)
    ui: UIHint = field(default_factory=UIHint)
    sensitive: bool = False
    order: int = 100
    version: str = "1.0"

    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = SettingCategory(self.category)
        if isinstance(self.setting_type, str):
            self.setting_type = SettingType(self.setting_type)
        if isinstance(self.ui, dict):
            self.ui = UIHint(**self.ui)

    @property
    def value(self) -> Any:
        """Get current value or default"""
        return self.current_value if self.current_value is not None else self.default

    @value.setter
    def value(self, val: Any):
        """Set current value with validation"""
        self.current_value = val

    def to_dict(self, include_sensitive: bool = False) -> Dict:
        """Convert to dictionary for serialization"""
        data = {
            "key": self.key,
            "category": self.category.value,
            "type": self.setting_type.value,
            "default": self.default,
            "description": self.description,
            "value": self.value if not self.sensitive or include_sensitive else "***",
            "ui": asdict(self.ui) if isinstance(self.ui, UIHint) else self.ui,
            "order": self.order,
            "version": self.version,
        }
        return data

    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate a value against rules"""
        for rule in self.validation:
            if rule.type == "required" and not value:
                return False, rule.message
            if (
                rule.type == "min"
                and isinstance(value, (int, float))
                and value < rule.value
            ):
                return False, rule.message
            if (
                rule.type == "max"
                and isinstance(value, (int, float))
                and value > rule.value
            ):
                return False, rule.message
            if (
                rule.type == "pattern"
                and isinstance(value, str)
                and not re.match(rule.value, value)
            ):
                return False, rule.message
            if rule.type == "enum" and value not in rule.value:
                return False, rule.message
        return True, ""


class SettingsRegistry:
    """
    Registry for all settings definitions

    Provides:
    - Registration of new settings
    - Lookup by key, category
    - Schema generation
    - Import/export
    """

    _registry: Dict[str, SettingDefinition] = {}
    _categories: Dict[str, List[str]] = {}  # category -> [keys]
    _hooks: Dict[str, List[Callable]] = {}  # event -> [callbacks]

    @classmethod
    def register(cls, setting: SettingDefinition) -> None:
        """Register a new setting definition"""
        if setting.key in cls._registry:
            logger.warning(f"Overwriting existing setting: {setting.key}")

        cls._registry[setting.key] = setting

        # Track by category
        cat_key = setting.category.value
        if cat_key not in cls._categories:
            cls._categories[cat_key] = []
        cls._categories[cat_key].append(setting.key)

        logger.info(f"Registered setting: {setting.key} in {setting.category.value}")

        # Trigger hooks
        cls._trigger_hook("register", setting)

    @classmethod
    def unregister(cls, key: str) -> Optional[SettingDefinition]:
        """Remove a setting definition"""
        if key in cls._registry:
            setting = cls._registry.pop(key)

            # Remove from category
            cat_key = setting.category.value
            if cat_key in cls._categories and key in cls._categories[cat_key]:
                cls._categories[cat_key].remove(key)

            cls._trigger_hook("unregister", setting)
            return setting
        return None

    @classmethod
    def get(cls, key: str) -> Optional[SettingDefinition]:
        """Get a setting definition by key"""
        return cls._registry.get(key)

    @classmethod
    def list_all(cls) -> List[SettingDefinition]:
        """List all registered settings"""
        return list(cls._registry.values())

    @classmethod
    def list_by_category(cls, category: SettingCategory) -> List[SettingDefinition]:
        """List all settings in a category"""
        return [
            cls._registry[key]
            for key in cls._categories.get(category.value, [])
            if key in cls._registry
        ]

    @classmethod
    def list_categories(cls) -> Dict[str, int]:
        """Get all categories with count of settings"""
        return {cat: len(keys) for cat, keys in cls._categories.items()}

    @classmethod
    def generate_schema(cls) -> Dict:
        """Generate JSON schema for all settings"""
        schema = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "settings": {},
            "categories": {},
        }

        for key, setting in cls._registry.items():
            schema["settings"][key] = {
                "category": setting.category.value,
                "type": setting.setting_type.value,
                "default": setting.default,
                "description": setting.description,
                "ui": asdict(setting.ui)
                if isinstance(setting.ui, UIHint)
                else setting.ui,
                "order": setting.order,
                "sensitive": setting.sensitive,
                "validation": [
                    {"type": v.type, "value": v.value, "message": v.message}
                    for v in setting.validation
                ],
            }

        # Category metadata
        for cat, keys in cls._categories.items():
            schema["categories"][cat] = {
                "count": len(keys),
                "settings": [
                    cls._registry[k].to_dict()
                    for k in sorted(keys, key=lambda x: cls._registry[x].order)
                ],
            }

        return schema

    @classmethod
    def generate_ui_config(cls) -> Dict:
        """Generate frontend UI configuration"""
        ui_config = {"version": "1.0", "categories": [], "fieldsets": []}

        # Group by category and order
        categories_seen = set()
        for cat, keys in sorted(cls._categories.items()):
            setting_list = [
                cls._registry[k]
                for k in sorted(keys, key=lambda x: cls._registry[x].order)
                if k in cls._registry
            ]

            category_config = {
                "id": cat,
                "label": cat.replace("_", " ").title(),
                "icon": cls._get_category_icon(cat),
                "fields": [],
            }

            for setting in setting_list:
                field_config = {
                    "key": setting.key,
                    "type": setting.ui.input_type
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("input_type", "text"),
                    "label": setting.ui.label
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("label", setting.key),
                    "placeholder": setting.ui.placeholder
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("placeholder", ""),
                    "help_text": setting.ui.help_text
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("help_text", ""),
                    "options": setting.ui.options
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("options", []),
                    "group": setting.ui.group
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("group", ""),
                    "order": setting.order,
                    "required": any(v.type == "required" for v in setting.validation),
                    "hidden": setting.ui.hidden
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("hidden", False),
                    "read_only": setting.ui.read_only
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("read_only", False),
                    "render_as": setting.ui.render_as
                    if isinstance(setting.ui, UIHint)
                    else setting.ui.get("render_as", "input"),
                    "category": cat,
                    "sensitive": setting.sensitive,
                    "value": setting.value if not setting.sensitive else "***",
                }
                category_config["fields"].append(field_config)

            ui_config["categories"].append(category_config)

        return ui_config

    @classmethod
    def _get_category_icon(cls, category: str) -> str:
        """Get icon for category"""
        icons = {
            "database": "🗄️",
            "email": "📧",
            "backup": "💾",
            "processing": "⚙️",
            "output": "📤",
            "general": "⚡",
        }
        return icons.get(category, "📝")

    @classmethod
    def on_change(cls, event: str, callback: Callable) -> None:
        """Register a hook callback for an event"""
        if event not in cls._hooks:
            cls._hooks[event] = []
        cls._hooks[event].append(callback)

    @classmethod
    def _trigger_hook(cls, event: str, *args) -> None:
        """Trigger all callbacks for an event"""
        for callback in cls._hooks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Settings hook error: {e}")

    @classmethod
    def export_to_json(cls, path: str) -> None:
        """Export registry to JSON file"""
        with open(path, "w") as f:
            json.dump(cls.generate_schema(), f, indent=2)
        logger.info(f"Exported settings registry to {path}")

    @classmethod
    def import_from_json(cls, path: str) -> int:
        """Import settings from JSON file"""
        with open(path) as f:
            schema = json.load(f)

        count = 0
        for key, config in schema.get("settings", {}).items():
            setting = SettingDefinition(
                key=key,
                category=SettingCategory(config["category"]),
                setting_type=SettingType(config["type"]),
                default=config["default"],
                description=config.get("description", ""),
                order=config.get("order", 100),
                ui=UIHint(**config.get("ui", {})),
            )
            cls.register(setting)
            count += 1

        logger.info(f"Imported {count} settings from {path}")
        return count


class SettingsComposer:
    """
    Compose settings from multiple sources with precedence

    Sources (highest to lowest priority):
    1. Runtime overrides
    2. Database values
    3. Environment variables
    4. Registry defaults
    """

    def __init__(self, registry: SettingsRegistry = None):
        self.registry = registry or SettingsRegistry
        self.db = None  # Set later

    def set_database(self, db):
        """Set database connection"""
        self.db = db

    def load_all(self) -> Dict[str, Any]:
        """Load all settings with full precedence"""
        settings = {}

        # Start with defaults
        for setting in self.registry.list_all():
            settings[setting.key] = setting.default

        # Override with environment variables
        settings.update(self._load_from_env())

        # Override with database values
        if self.db:
            settings.update(self._load_from_db())

        return settings

    def _load_from_env(self) -> Dict:
        """Load settings from environment variables"""
        env_map = self._build_env_map()
        return {
            setting_key: os.environ[env_key]
            for env_key, setting_key in env_map.items()
            if env_key in os.environ
        }

    def _load_from_db(self) -> Dict:
        """Load settings from database"""
        if not self.db:
            return {}

        try:
            settings_table = self.db["settings"]
            db_settings = settings_table.find_one(id=1)
            if db_settings:
                # Filter to only registered settings
                return {
                    k: v
                    for k, v in db_settings.items()
                    if k != "id" and self.registry.get(k) is not None
                }
        except Exception as e:
            logger.error(f"Failed to load settings from database: {e}")

        return {}

    def _build_env_map(self) -> Dict[str, str]:
        """Build environment variable to setting key mapping"""
        return {
            f"SETTING_{setting.key.upper().replace('-', '_')}": setting.key
            for setting in self.registry.list_all()
            if setting.ui.hidden  # Only mapped if marked as env-var
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get single setting with full precedence"""
        all_settings = self.load_all()
        return all_settings.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a setting value in database"""
        if not self.db:
            logger.error("Database not set")
            return False

        setting = self.registry.get(key)
        if not setting:
            logger.warning(f"Unknown setting: {key}")
            return False

        try:
            settings_table = self.db["settings"]
            settings_table.update({key: value, "id": 1}, ["id"])
            logger.info(f"Set setting: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False


def auto_register_from_profiles(
    registry: SettingsRegistry, profiles: List[Dict]
) -> None:
    """
    Auto-generate and register settings from output profiles

    This creates settings for each profile's configuration options
    """
    for profile in profiles:
        profile_key = (
            profile.get("alias", profile.get("name", "")).lower().replace(" ", "-")
        )

        # Register profile-specific settings
        registry.register(
            SettingDefinition(
                key=f"profile_{profile_key}_enabled",
                category=SettingCategory.OUTPUT,
                setting_type=SettingType.BOOLEAN,
                default=False,
                description=f"Enable {profile['name']} profile",
                ui=UIHint(
                    input_type="checkbox",
                    label=f"Enable {profile['name']}",
                    order=10,
                    group=profile_key,
                ),
            )
        )

        registry.register(
            SettingDefinition(
                key=f"profile_{profile_key}_format",
                category=SettingCategory.OUTPUT,
                setting_type=SettingType.STRING,
                default=profile.get("output_format", "csv"),
                description=f"Output format for {profile['name']}",
                ui=UIHint(
                    input_type="select",
                    label="Output Format",
                    options=[
                        {"value": "csv", "label": "CSV"},
                        {"value": "edi", "label": "EDI"},
                        {"value": "estore-einvoice", "label": "eStore eInvoice"},
                        {"value": "fintech", "label": "Fintech"},
                        {"value": "scannerware", "label": "Scannerware"},
                        {"value": "scansheet-type-a", "label": "Scansheet Type A"},
                        {"value": "simplified-csv", "label": "Simplified CSV"},
                        {"value": "stewart-custom", "label": "Stewart Custom"},
                        {"value": "yellowdog-csv", "label": "Yellowdog CSV"},
                    ],
                    order=20,
                    group=profile_key,
                ),
            )
        )

        # EDI tweaks
        if profile.get("edi_tweaks"):
            registry.register(
                SettingDefinition(
                    key=f"profile_{profile_key}_edi_tweaks",
                    category=SettingCategory.OUTPUT,
                    setting_type=SettingType.JSON,
                    default=profile["edi_tweaks"],
                    description=f"EDI tweaks for {profile['name']}",
                    ui=UIHint(
                        input_type="textarea",
                        label="EDI Tweaks (JSON)",
                        help_text="JSON configuration for EDI processing",
                        order=30,
                        group=profile_key,
                    ),
                )
            )

        # Custom settings
        if profile.get("custom_settings"):
            registry.register(
                SettingDefinition(
                    key=f"profile_{profile_key}_custom",
                    category=SettingCategory.OUTPUT,
                    setting_type=SettingType.JSON,
                    default=profile["custom_settings"],
                    description=f"Custom settings for {profile['name']}",
                    ui=UIHint(
                        input_type="textarea",
                        label="Custom Settings (JSON)",
                        help_text="JSON configuration for custom processing",
                        order=40,
                        group=profile_key,
                    ),
                )
            )


import os
import re
