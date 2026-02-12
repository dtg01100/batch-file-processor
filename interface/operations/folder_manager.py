"""Folder management operations extracted from main_interface.py.

This module provides the FolderManager class which handles CRUD operations
for folder configurations, separating business logic from UI code.

The class supports dependency injection through the DatabaseProtocol,
enabling testing without actual database connections.
"""

import os
from typing import Protocol, runtime_checkable, Optional, Any


@runtime_checkable
class TableProtocol(Protocol):
    """Protocol for database table operations."""
    
    def find_one(self, **kwargs) -> Optional[dict]:
        """Find a single record matching criteria."""
        ...
    
    def find(self, **kwargs) -> list[dict]:
        """Find all records matching criteria."""
        ...
    
    def all(self) -> list[dict]:
        """Get all records from the table."""
        ...
    
    def insert(self, record: dict) -> int:
        """Insert a new record."""
        ...
    
    def update(self, record: dict, keys: list) -> None:
        """Update an existing record."""
        ...
    
    def delete(self, **kwargs) -> None:
        """Delete records matching criteria."""
        ...
    
    def count(self, **kwargs) -> int:
        """Count records matching criteria."""
        ...


@runtime_checkable
class DatabaseProtocol(Protocol):
    """Protocol for database operations.
    
    This protocol defines the interface required by FolderManager,
    allowing for mock implementations in tests.
    """
    
    @property
    def folders_table(self) -> TableProtocol:
        """Access folders table."""
        ...
    
    @property
    def oversight_and_defaults(self) -> TableProtocol:
        """Access administrative table."""
        ...


class FolderManager:
    """Manages folder CRUD operations.
    
    Extracts folder management logic from main_interface.py
    for better testability and separation of concerns.
    
    This class handles:
    - Adding new folders with template defaults
    - Checking if folders exist
    - Enabling/disabling folders
    - Deleting folders
    - Retrieving folder lists
    
    Attributes:
        SKIP_LIST: List of fields to skip when copying template settings
    
    Example:
        >>> manager = FolderManager(database)
        >>> manager.add_folder("/path/to/folder")
        {'folder_name': '/path/to/folder', 'alias': 'folder', ...}
        >>> manager.check_folder_exists("/path/to/folder")
        {'truefalse': True, 'matched_folder': {...}}
    """
    
    SKIP_LIST = [
        "folder_name",
        "alias",
        "id",
        "logs_directory",
        "errors_folder",
        "enable_reporting",
        "report_printing_fallback",
        "single_add_folder_prior",
        "batch_add_folder_prior",
        "export_processed_folder_prior",
        "report_edi_errors",
    ]
    
    def __init__(self, database: DatabaseProtocol):
        """Initialize the folder manager.
        
        Args:
            database: Database object implementing DatabaseProtocol
        """
        self._db = database
    
    def add_folder(self, folder_path: str, template_data: Optional[dict] = None) -> dict:
        """Add a folder to the database using template defaults.
        
        Args:
            folder_path: Path to the folder to add
            template_data: Optional template data to use instead of database defaults
            
        Returns:
            The inserted folder record
        """
        if template_data is None:
            template = self._db.oversight_and_defaults.find_one(id=1)
        else:
            template = template_data
            
        template_settings = {
            k: v for k, v in template.items() 
            if k not in self.SKIP_LIST
        }
        
        folder_name = self._generate_unique_alias(folder_path)
        template_settings["folder_name"] = folder_path
        template_settings["alias"] = folder_name
        
        self._db.folders_table.insert(template_settings)
        return template_settings
    
    def _generate_unique_alias(self, folder_path: str) -> str:
        """Generate a unique alias for a folder.
        
        If the base name already exists as an alias, appends a counter
        to make it unique (e.g., "folder 1", "folder 2").
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            Unique alias string
        """
        base_name = os.path.basename(folder_path)
        alias = base_name
        counter = 1
        
        while self._db.folders_table.find_one(alias=alias):
            alias = f"{base_name} {counter}"
            counter += 1
        
        return alias
    
    def check_folder_exists(self, folder_path: str) -> dict:
        """Check if a folder already exists in database.
        
        Compares normalized paths to handle different path formats.
        
        Args:
            folder_path: Path to check
            
        Returns:
            Dict with keys:
                - truefalse: bool indicating if folder exists
                - matched_folder: The matching folder dict or None
        """
        folder_list = self._db.folders_table.all()
        
        for folder in folder_list:
            if os.path.normpath(folder["folder_name"]) == os.path.normpath(folder_path):
                return {"truefalse": True, "matched_folder": folder}
        
        return {"truefalse": False, "matched_folder": None}
    
    def get_folder_by_id(self, folder_id: int) -> Optional[dict]:
        """Get a folder by its ID.
        
        Args:
            folder_id: The folder ID
            
        Returns:
            Folder dict or None if not found
        """
        return self._db.folders_table.find_one(id=folder_id)
    
    def get_folder_by_name(self, folder_name: str) -> Optional[dict]:
        """Get a folder by its name (path).
        
        Args:
            folder_name: The folder path/name
            
        Returns:
            Folder dict or None if not found
        """
        return self._db.folders_table.find_one(folder_name=folder_name)
    
    def get_folder_by_alias(self, alias: str) -> Optional[dict]:
        """Get a folder by its alias.
        
        Args:
            alias: The folder alias
            
        Returns:
            Folder dict or None if not found
        """
        return self._db.folders_table.find_one(alias=alias)
    
    def disable_folder(self, folder_id: int) -> bool:
        """Disable a folder.
        
        Sets the folder_is_active field to "False".
        
        Args:
            folder_id: The folder ID to disable
            
        Returns:
            True if successful, False if folder not found
        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            folder["folder_is_active"] = "False"
            self._db.folders_table.update(folder, ["id"])
            return True
        return False
    
    def enable_folder(self, folder_id: int) -> bool:
        """Enable a folder.
        
        Sets the folder_is_active field to "True".
        
        Args:
            folder_id: The folder ID to enable
            
        Returns:
            True if successful, False if folder not found
        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            folder["folder_is_active"] = "True"
            self._db.folders_table.update(folder, ["id"])
            return True
        return False
    
    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder from the database.
        
        Args:
            folder_id: The folder ID to delete
            
        Returns:
            True if deleted, False if folder not found
        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            self._db.folders_table.delete(id=folder_id)
            return True
        return False
    
    def get_active_folders(self) -> list[dict]:
        """Get all active folders.
        
        Returns:
            List of active folder dicts
        """
        return list(self._db.folders_table.find(folder_is_active="True"))
    
    def get_inactive_folders(self) -> list[dict]:
        """Get all inactive folders.
        
        Returns:
            List of inactive folder dicts
        """
        return list(self._db.folders_table.find(folder_is_active="False"))
    
    def get_all_folders(self, order_by: Optional[str] = "alias") -> list[dict]:
        """Get all folders.
        
        Args:
            order_by: Field to order by (passed to find)
            
        Returns:
            List of all folder dicts
        """
        if order_by:
            return list(self._db.folders_table.find(order_by=order_by))
        return list(self._db.folders_table.all())
    
    def count_folders(self, active_only: bool = False) -> int:
        """Count folders.
        
        Args:
            active_only: If True, count only active folders
            
        Returns:
            Folder count
        """
        if active_only:
            return self._db.folders_table.count(folder_is_active="True")
        return self._db.folders_table.count()
    
    def update_folder(self, folder_data: dict) -> bool:
        """Update a folder configuration.
        
        Args:
            folder_data: Updated folder data (must include 'id')
            
        Returns:
            True if updated, False if folder not found
        """
        if "id" not in folder_data:
            return False
        
        folder = self.get_folder_by_id(folder_data["id"])
        if folder:
            self._db.folders_table.update(folder_data, ["id"])
            return True
        return False
    
    def update_folder_by_name(self, folder_data: dict) -> bool:
        """Update a folder configuration by name.
        
        Args:
            folder_data: Updated folder data (must include 'folder_name')
            
        Returns:
            True if updated, False if folder not found
        """
        if "folder_name" not in folder_data:
            return False
        
        folder = self.get_folder_by_name(folder_data["folder_name"])
        if folder:
            # Preserve the original ID
            folder_data["id"] = folder["id"]
            self._db.folders_table.update(folder_data, ["id"])
            return True
        return False
    
    def batch_add_folders(self, parent_path: str, skip_existing: bool = True) -> dict:
        """Add all subdirectories of a parent path as folders.
        
        Args:
            parent_path: Parent directory to scan for subdirectories
            skip_existing: If True, skip folders that already exist
            
        Returns:
            Dict with 'added' and 'skipped' counts
        """
        if not os.path.isdir(parent_path):
            return {"added": 0, "skipped": 0, "error": "Parent path is not a directory"}
        
        folders_to_add = [
            os.path.join(parent_path, folder)
            for folder in os.listdir(parent_path)
            if os.path.isdir(os.path.join(parent_path, folder))
        ]
        
        added = 0
        skipped = 0
        
        for folder_path in folders_to_add:
            if skip_existing and self.check_folder_exists(folder_path)["truefalse"]:
                skipped += 1
            else:
                self.add_folder(folder_path)
                added += 1
        
        return {"added": added, "skipped": skipped}
