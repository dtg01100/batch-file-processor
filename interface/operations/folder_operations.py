"""
Folder operations module for interface.py refactoring.

This module contains folder CRUD operations for managing folder configurations.
Refactored from interface.py (lines 261-410).

Usage:
    from interface.operations.folder_operations import FolderOperations
    operations = FolderOperations(db_manager)
    operations.add_folder(folder_data)
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from interface.database.database_manager import DatabaseManager


class FolderOperations:
    """
    Class for managing folder CRUD operations.

    Provides methods for adding, updating, deleting, and querying folder
    configurations in the database.

    Attributes:
        db_manager: DatabaseManager instance for database operations
    """

    # Fields to skip when copying template settings
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

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize FolderOperations with a database manager.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager

    def _get_template_settings(self) -> Dict[str, Any]:
        """Get default settings from the template.

        Returns:
            Dictionary containing template settings excluding skip list fields
        """
        if self.db_manager.oversight_and_defaults is None:
            return {}
        template = self.db_manager.oversight_and_defaults.find_one(id=1)
        if template is None:
            return {}
        return {k: v for k, v in template.items() if k not in self.SKIP_LIST}

    def add_folder(self, folder_path: str) -> Optional[int]:
        """Add a new folder to the database using default settings.

        Args:
            folder_path: Path to the folder to add

        Returns:
            ID of the newly inserted folder, or None if failed
        """
        if self.db_manager.folders_table is None:
            return None

        template_settings = self._get_template_settings()

        # Generate unique alias if needed
        folder_name = os.path.basename(folder_path)
        counter = 1
        while self.db_manager.folders_table.find_one(alias=folder_name):
            folder_name = os.path.basename(folder_path) + f" {counter}"
            counter += 1

        template_settings["folder_name"] = folder_path
        template_settings["alias"] = folder_name

        self.db_manager.folders_table.insert({**template_settings})

        # Return the ID of the newly inserted folder
        folder = self.db_manager.folders_table.find_one(folder_name=folder_path)
        return folder["id"] if folder else None

    def batch_add_folders(self, folder_paths: List[str]) -> Tuple[List[int], int, int]:
        """Add multiple folders to the database.

        Args:
            folder_paths: List of folder paths to add

        Returns:
            Tuple of (added_folder_ids, added_count, skipped_count)
        """
        added = []
        skipped = 0

        for folder_path in folder_paths:
            if self.folder_exists_by_path(folder_path):
                skipped += 1
            else:
                folder_id = self.add_folder(folder_path)
                if folder_id:
                    added.append(folder_id)

        return added, len(added), skipped

    def update_folder(self, folder_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing folder configuration.

        Args:
            folder_id: ID of the folder to update
            data: Dictionary containing updated folder data

        Returns:
            True if update was successful, False otherwise
        """
        if self.db_manager.folders_table is None:
            return False
        existing = self.db_manager.folders_table.find_one(id=folder_id)
        if not existing:
            return False

        self.db_manager.folders_table.update(data, ["id"])
        return True

    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder configuration and its related records.

        Deletes the folder configuration and also removes:
        - Processed files records for this folder
        - Email queue entries for this folder

        Args:
            folder_id: ID of the folder to delete

        Returns:
            True if deletion was successful
        """
        if self.db_manager.folders_table is None:
            return False

        # Delete related records first
        if self.db_manager.processed_files is not None:
            self.db_manager.processed_files.delete(folder_id=folder_id)
        if self.db_manager.emails_table is not None:
            self.db_manager.emails_table.delete(folder_id=folder_id)

        # Delete the folder itself
        self.db_manager.folders_table.delete(id=folder_id)
        return True

    def get_folder(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """Get a single folder by ID.

        Args:
            folder_id: ID of the folder to retrieve

        Returns:
            Folder dictionary or None if not found
        """
        if self.db_manager.folders_table is None:
            return None
        return self.db_manager.folders_table.find_one(id=folder_id)

    def get_folder_by_alias(self, alias: str) -> Optional[Dict[str, Any]]:
        """Get a single folder by alias.

        Args:
            alias: Alias of the folder to retrieve

        Returns:
            Folder dictionary or None if not found
        """
        if self.db_manager.folders_table is None:
            return None
        return self.db_manager.folders_table.find_one(alias=alias)

    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Get all folders from the database.

        Returns:
            List of all folder dictionaries, ordered by alias
        """
        if self.db_manager.folders_table is None:
            return []
        return list(self.db_manager.folders_table.find(order_by="alias"))

    def get_active_folders(self) -> List[Dict[str, Any]]:
        """Get only active folders from the database.

        Returns:
            List of active folder dictionaries
        """
        if self.db_manager.folders_table is None:
            return []
        return list(self.db_manager.folders_table.find(folder_is_active="True"))

    def get_inactive_folders(self) -> List[Dict[str, Any]]:
        """Get only inactive folders from the database.

        Returns:
            List of inactive folder dictionaries
        """
        if self.db_manager.folders_table is None:
            return []
        return list(self.db_manager.folders_table.find(folder_is_active="False"))

    def folder_exists_by_path(self, folder_path: str) -> bool:
        """Check if a folder path already exists in the database.

        Args:
            folder_path: Path to check

        Returns:
            True if folder exists, False otherwise
        """
        if self.db_manager.folders_table is None:
            return False
        return (
            self.db_manager.folders_table.find_one(
                folder_name=os.path.normpath(folder_path)
            )
            is not None
        )

    def folder_exists_by_alias(self, alias: str) -> bool:
        """Check if a folder alias already exists in the database.

        Args:
            alias: Alias to check

        Returns:
            True if alias exists, False otherwise
        """
        if self.db_manager.folders_table is None:
            return False
        return self.db_manager.folders_table.find_one(alias=alias) is not None

    def check_folder_exists(self, folder_path: str) -> Dict[str, Any]:
        """Check if folder exists and return matching folder info.

        Args:
            folder_path: Path to check

        Returns:
            Dictionary with 'truefalse' (bool) and 'matched_folder' (dict or None)
        """
        if self.db_manager.folders_table is None:
            return {"truefalse": False, "matched_folder": None}
        folder_list = self.db_manager.folders_table.all()
        for possible_folder in folder_list:
            possible_folder_string = possible_folder["folder_name"]
            if os.path.normpath(possible_folder_string) == os.path.normpath(
                folder_path
            ):
                return {"truefalse": True, "matched_folder": possible_folder}
        return {"truefalse": False, "matched_folder": None}

    def set_folder_active(self, folder_id: int, active: bool = True) -> bool:
        """Set folder active state.

        Args:
            folder_id: ID of the folder
            active: True to activate, False to deactivate

        Returns:
            True if update was successful, False otherwise
        """
        folder = self.get_folder(folder_id)
        if not folder:
            return False
        if self.db_manager.folders_table is None:
            return False

        folder["folder_is_active"] = str(active)
        self.db_manager.folders_table.update(folder, ["id"])
        return True

    def get_folder_count(self, active_only: bool = False) -> int:
        """Get the count of folders.

        Args:
            active_only: If True, count only active folders

        Returns:
            Number of folders
        """
        if self.db_manager.folders_table is None:
            return 0
        if active_only:
            return self.db_manager.folders_table.count(folder_is_active="True")
        return self.db_manager.folders_table.count()

    def disable_folder(self, folder_id: int) -> bool:
        """Disable a folder (set as inactive).

        Args:
            folder_id: ID of the folder to disable

        Returns:
            True if successful, False otherwise
        """
        return self.set_folder_active(folder_id, False)

    def enable_folder(self, folder_id: int) -> bool:
        """Enable a folder (set as active).

        Args:
            folder_id: ID of the folder to enable

        Returns:
            True if successful, False otherwise
        """
        return self.set_folder_active(folder_id, True)
