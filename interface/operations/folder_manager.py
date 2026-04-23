"""Folder management operations extracted from main_interface.py.

This module provides the FolderManager class which handles CRUD operations
for folder configurations, separating business logic from UI code.

The class supports dependency injection through the DatabaseProtocol or
IFolderRepository, enabling testing without actual database connections.
"""

import os
from typing import Protocol, runtime_checkable

from core.ports.repositories import IFolderRepository, ISettingsRepository


@runtime_checkable
class TableProtocol(Protocol):
    """Protocol for database table operations."""

    def find_one(self, **kwargs) -> dict | None:
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

    @property
    def processed_files(self) -> TableProtocol:
        """Access processed files table."""
        ...

    @property
    def emails_table(self) -> TableProtocol:
        """Access emails table."""
        ...

    def get_oversight_or_default(self) -> dict:
        """Get oversight/defaults singleton with fallback creation."""
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

    Supports two injection modes:
    - IFolderRepository + optional ISettingsRepository (preferred)
    - DatabaseProtocol (legacy, for backward compatibility)

    Attributes:
        SKIP_LIST: List of fields to skip when copying template settings

    Example:
        >>> manager = FolderManager(folder_repo=folder_repository)
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
        "edi_converter_scratch_folder",
    ]

    def __init__(
        self,
        database: DatabaseProtocol | None = None,
        folder_repo: IFolderRepository | None = None,
        settings_repo: ISettingsRepository | None = None,
    ) -> None:
        """Initialize the folder manager.

        Args:
            database: Database object implementing DatabaseProtocol (legacy)
            folder_repo: IFolderRepository implementation (preferred)
            settings_repo: ISettingsRepository for getting defaults (optional)

        """
        if folder_repo is None and (
            database is None or not isinstance(database, DatabaseProtocol)
        ):
            raise ValueError(
                "Either folder_repo (IFolderRepository) or database (DatabaseProtocol) "
                "must be provided"
            )
        self._folder_repo = folder_repo
        self._db = database  # Always store database if provided
        # - needed for delete_folder_with_related
        self._settings_repo = settings_repo

    def add_folder(self, folder_path: str, template_data: dict | None = None) -> dict:
        """Add a folder to the database using template defaults.

        Args:
            folder_path: Path to the folder to add
            template_data: Optional template data to use instead of database defaults

        Returns:
            The inserted folder record

        """
        if template_data is None:
            if self._settings_repo is not None:
                template = self._settings_repo.get_defaults()
            else:
                template = self._db.get_oversight_or_default()
        else:
            template = template_data

        template_settings = {
            k: v for k, v in template.items() if k not in self.SKIP_LIST
        }

        folder_name = self._generate_unique_alias(folder_path)
        template_settings["folder_name"] = folder_path
        template_settings["alias"] = folder_name

        if self._folder_repo is not None:
            self._folder_repo.insert(template_settings)
        else:
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

        if self._folder_repo is not None:
            while self._folder_repo.find_by_alias(alias):
                alias = f"{base_name} {counter}"
                counter += 1
        else:
            while self._db.folders_table.find_one(alias=alias):
                alias = f"{base_name} {counter}"
                counter += 1

        return alias

    def check_folder_exists(self, folder_path: str) -> dict:
        """Check if a folder already exists in database.

        Compares normalized paths to handle different path formats.
        Returns ALL matching folders to support multiple configurations
        per source directory.

        Args:
            folder_path: Path to check

        Returns:
            Dict with keys:
                - truefalse: bool indicating if folder exists
                - matched_folder: The first matching folder dict or None
                - all_matched_folders: List of all matching folder dicts

        """
        if self._folder_repo is not None:
            all_folders = self._folder_repo.find_all()
        else:
            all_folders = self._db.folders_table.all()

        matched_folders = [
            folder
            for folder in all_folders
            if os.path.normpath(folder["folder_name"]) == os.path.normpath(folder_path)
        ]

        if matched_folders:
            return {
                "truefalse": True,
                "matched_folder": matched_folders[0],
                "all_matched_folders": matched_folders,
            }

        return {"truefalse": False, "matched_folder": None, "all_matched_folders": []}

    def get_folder_by_id(self, folder_id: int) -> dict | None:
        """Get a folder by its ID.

        Args:
            folder_id: The folder ID

        Returns:
            Folder dict or None if not found

        """
        if self._folder_repo is not None:
            return self._folder_repo.find_by_id(folder_id)
        return self._db.folders_table.find_one(id=folder_id)

    def get_folder_by_name(self, folder_name: str) -> dict | None:
        """Get a folder by its name (path).

        Args:
            folder_name: The folder path/name

        Returns:
            Folder dict or None if not found

        """
        if self._folder_repo is not None:
            return self._folder_repo.find_by_path(folder_name)
        return self._db.folders_table.find_one(folder_name=folder_name)

    def get_folder_by_alias(self, alias: str) -> dict | None:
        """Get a folder by its alias.

        Args:
            alias: The folder alias

        Returns:
            Folder dict or None if not found

        """
        if self._folder_repo is not None:
            return self._folder_repo.find_by_alias(alias)
        return self._db.folders_table.find_one(alias=alias)

    def disable_folder(self, folder_id: int) -> bool:
        """Disable a folder.

        Sets the folder_is_active field to False.

        Args:
            folder_id: The folder ID to disable

        Returns:
            True if successful, False if folder not found

        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            folder["folder_is_active"] = False
            if self._folder_repo is not None:
                self._folder_repo.update(folder)
            else:
                self._db.folders_table.update(folder, ["id"])
            return True
        return False

    def enable_folder(self, folder_id: int) -> bool:
        """Enable a folder.

        Sets the folder_is_active field to True.

        Args:
            folder_id: The folder ID to enable

        Returns:
            True if successful, False if folder not found

        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            folder["folder_is_active"] = True
            if self._folder_repo is not None:
                self._folder_repo.update(folder)
            else:
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
            if self._folder_repo is not None:
                self._folder_repo.delete(folder_id)
            else:
                self._db.folders_table.delete(id=folder_id)
            return True
        return False

    def delete_folder_with_related(self, folder_id: int) -> bool:
        """Delete a folder and all related records from the database.

        This deletes:
        - The folder configuration
        - All processed files records for this folder
        - All queued emails for this folder

        Args:
            folder_id: The folder ID to delete

        Returns:
            True if deleted, False if folder not found

        Note:
            This method requires DatabaseProtocol for processed_files and
            emails_table access.
            Will raise AttributeError if used with IFolderRepository.

        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            if self._db is None:
                raise AttributeError(
                    "delete_folder_with_related requires database access"
                )
            self._db.folders_table.delete(id=folder_id)
            self._db.processed_files.delete(folder_id=folder_id)
            self._db.emails_table.delete(folder_id=folder_id)
            return True
        return False

    def get_active_folders(self) -> list[dict]:
        """Get all active folders.

        Returns:
            List of active folder dicts

        """
        if self._folder_repo is not None:
            return self._folder_repo.find_all(active_only=True)
        return list(self._db.folders_table.find(folder_is_active=True))

    def get_inactive_folders(self) -> list[dict]:
        """Get all inactive folders.

        Returns:
            List of inactive folder dicts

        """
        if self._folder_repo is not None:
            all_folders = self._folder_repo.find_all(active_only=False)
            return [f for f in all_folders if not f.get("folder_is_active", True)]
        return list(self._db.folders_table.find(folder_is_active=False))

    def get_all_folders(self, order_by: str | None = "alias") -> list[dict]:
        """Get all folders.

        Args:
            order_by: Field to order by (passed to find) -
                only used with DatabaseProtocol

        Returns:
            List of all folder dicts

        Note:
            The order_by parameter is only supported with DatabaseProtocol.
            IFolderRepository returns unordered results.

        """
        if self._folder_repo is not None:
            return self._folder_repo.find_all()
        if order_by:
            return list(self._db.folders_table.find(order_by=order_by))
        return list(self._db.folders_table.all())

    def count_folders(self, *, active_only: bool = False) -> int:
        """Count folders.

        Args:
            active_only: If True, count only active folders

        Returns:
            Folder count

        """
        if self._folder_repo is not None:
            return self._folder_repo.count(active_only=active_only)
        if active_only:
            return self._db.folders_table.count(folder_is_active=True)
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
            if self._folder_repo is not None:
                self._folder_repo.update(folder_data)
            else:
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
            folder_data["id"] = folder["id"]
            if self._folder_repo is not None:
                self._folder_repo.update(folder_data)
            else:
                self._db.folders_table.update(folder_data, ["id"])
            return True
        return False

    def batch_add_folders(
        self, parent_path: str, *, skip_existing: bool = True
    ) -> dict:
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
