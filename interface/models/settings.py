"""
Settings model for interface.py refactoring.

This module contains the Settings model for global application configuration.
Refactored from interface.py settings (lines 290-320).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Settings:
    """Global settings model for application configuration."""
    
    id: Optional[int] = None
    key: str = ""
    value: str = ""
    category: str = "general"
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Common settings category constants
    AS400_HOST = "as400_host"
    AS400_LIBRARY = "as400_library"
    AS400_USER = "as400_user"
    AS400_ODBC_DRIVER = "as400_odbc_driver"
    SMTP_SERVER = "smtp_server"
    SMTP_PORT = "smtp_port"
    SMTP_USERNAME = "smtp_username"
    EMAIL_FROM = "email_from"
    BACKUP_DIRECTORY = "backup_directory"
    BACKUP_INTERVAL = "backup_interval"
    OUTPUT_FOLDER = "output_folder"
    
    @classmethod
    def get(cls, db_manager, key: str) -> Optional[str]:
        """
        Get a setting value by key.
        
        Args:
            db_manager: Database manager instance.
            key: Setting key to retrieve.
            
        Returns:
            Setting value or None if not found.
        """
        try:
            result = db_manager.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            return result[0] if result else None
        except Exception:
            return None
    
    @classmethod
    def set(cls, db_manager, key: str, value: str, category: str = "general") -> bool:
        """
        Set a setting value.
        
        Args:
            db_manager: Database manager instance.
            key: Setting key.
            value: Setting value.
            category: Setting category (default: "general").
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Check if setting exists
            existing = db_manager.execute(
                "SELECT id FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            
            if existing:
                db_manager.execute(
                    "UPDATE settings SET value = ?, category = ?, updated_at = ? WHERE key = ?",
                    (value, category, datetime.now(), key)
                )
            else:
                db_manager.execute(
                    "INSERT INTO settings (key, value, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (key, value, category, datetime.now(), datetime.now())
                )
            db_manager.commit()
            return True
        except Exception:
            return False
    
    @classmethod
    def get_as400_settings(cls, db_manager) -> Dict[str, str]:
        """
        Get all AS400 settings.
        
        Args:
            db_manager: Database manager instance.
            
        Returns:
            Dictionary of AS400 settings.
        """
        settings = {}
        keys = [
            cls.AS400_HOST,
            cls.AS400_LIBRARY,
            cls.AS400_USER,
            cls.AS400_ODBC_DRIVER,
        ]
        for key in keys:
            value = cls.get(db_manager, key)
            if value is not None:
                settings[key] = value
        return settings
    
    @classmethod
    def get_email_settings(cls, db_manager) -> Dict[str, str]:
        """
        Get all email settings.
        
        Args:
            db_manager: Database manager instance.
            
        Returns:
            Dictionary of email settings.
        """
        settings = {}
        keys = [
            cls.SMTP_SERVER,
            cls.SMTP_PORT,
            cls.SMTP_USERNAME,
            cls.EMAIL_FROM,
        ]
        for key in keys:
            value = cls.get(db_manager, key)
            if value is not None:
                settings[key] = value
        return settings
    
    @classmethod
    def get_all_by_category(cls, db_manager, category: str) -> List['Settings']:
        """
        Get all settings for a specific category.
        
        Args:
            db_manager: Database manager instance.
            category: Settings category to filter by.
            
        Returns:
            List of Settings instances.
        """
        try:
            results = db_manager.execute(
                "SELECT * FROM settings WHERE category = ? ORDER BY key",
                (category,)
            ).fetchall()
            return [cls.from_dict(dict(row)) for row in results]
        except Exception:
            return []
    
    @classmethod
    def get_all(cls, db_manager) -> List['Settings']:
        """
        Get all settings.
        
        Args:
            db_manager: Database manager instance.
            
        Returns:
            List of all Settings instances.
        """
        try:
            results = db_manager.execute(
                "SELECT * FROM settings ORDER BY category, key"
            ).fetchall()
            return [cls.from_dict(dict(row)) for row in results]
        except Exception:
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Settings instance to dictionary.
        
        Returns:
            Dictionary representation of the Settings instance.
        """
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """
        Create a Settings instance from a dictionary.
        
        Args:
            data: Dictionary containing settings data.
            
        Returns:
            New Settings instance.
        """
        created_at = None
        updated_at = None
        
        if isinstance(data.get('created_at'), str):
            created_at = datetime.fromisoformat(data['created_at'])
        elif isinstance(data.get('created_at'), datetime):
            created_at = data['created_at']
            
        if isinstance(data.get('updated_at'), str):
            updated_at = datetime.fromisoformat(data['updated_at'])
        elif isinstance(data.get('updated_at'), datetime):
            updated_at = data['updated_at']
        
        return cls(
            id=data.get('id'),
            key=data.get('key', ''),
            value=data.get('value', ''),
            category=data.get('category', 'general'),
            description=data.get('description'),
            created_at=created_at,
            updated_at=updated_at,
        )
