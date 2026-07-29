"""Folder management operations extracted from main_interface.py.

This module provides the FolderManager class which handles CRUD operations
for folder configurations, separating business logic from UI code.
"""

import os
from typing import Any, ClassVar

from core.domain.models.folder import FolderConfiguration
from core.ports.repositories import (
    IFolderRepository,
    IProcessedFilesRepository,
    ISettingsRepository,
)


def _to_db_dict(folder: Any) -> dict[str, Any] | None:
    """Return a DB-row dict for either a FolderConfiguration or a plain dict.

    Tests and legacy callers pass plain dicts or SimpleNamespace mocks;
    production repos return FolderConfiguration instances. The folder
    manager boundary normalises all of these to the dict shape its
    public API exposes. ``id`` is merged from the source so callers can
    index the dict by primary key — ``FolderConfiguration.to_dict``
    intentionally strips it.
    """
    if folder is None:
        return None
    if isinstance(folder, FolderConfiguration):
        data = folder.to_dict()
        if folder.id is not None:
            data["id"] = folder.id
        return data
    if isinstance(folder, dict):
        return dict(folder)
    if hasattr(folder, "to_dict"):
        result = folder.to_dict()
        return result if isinstance(result, dict) else dict(result)
    raw = dict(vars(folder))
    if getattr(folder, "id", None) is not None:
        raw.setdefault("id", folder.id)
    return raw


def _is_active_folder(folder: Any) -> bool:
    """Return whether a folder-like value is active, accepting dict or object."""
    if isinstance(folder, dict):
        return bool(folder.get("folder_is_active", True))
    return bool(getattr(folder, "folder_is_active", True))


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
        >>> manager = FolderManager(folder_repo=folder_repository)
        >>> manager.add_folder("/path/to/folder")
        {'folder_name': '/path/to/folder', 'alias': 'folder', ...}
        >>> manager.check_folder_exists("/path/to/folder")
        {'truefalse': True, 'matched_folder': {...}}

    """

    SKIP_LIST: ClassVar[list[str]] = [
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
        folder_repo: IFolderRepository,
        settings_repo: ISettingsRepository | None = None,
        processed_files_repo: IProcessedFilesRepository | None = None,
    ) -> None:
        """Initialize the folder manager.

        Args:
            folder_repo: IFolderRepository implementation
            settings_repo: ISettingsRepository for getting defaults (optional)
            processed_files_repo: IProcessedFilesRepository for related record
                cleanup in delete_folder_with_related (optional)

        """
        self._folder_repo = folder_repo
        self._settings_repo = settings_repo
        self._processed_files_repo = processed_files_repo

    def add_folder(
        self, folder_path: str, template_data: dict | None = None
    ) -> dict[str, Any] | None:
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
                template = {}
        else:
            template = template_data

        template_settings = {
            k: v for k, v in template.items() if k not in self.SKIP_LIST
        }

        folder_name = self._generate_unique_alias(folder_path)
        template_settings["folder_name"] = folder_path
        template_settings["alias"] = folder_name

        folder_config = FolderConfiguration.from_dict(template_settings)
        new_id = self._folder_repo.insert(folder_config)
        return _to_db_dict(self._folder_repo.find_by_id(new_id))

    def _alias_exists(self, alias: str) -> bool:
        return bool(self._folder_repo.find_by_alias(alias))

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

        while self._alias_exists(alias):
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
        all_folders = self._folder_repo.find_all()
        normalised = os.path.normpath(folder_path)

        matched = []
        for folder in all_folders:
            name = (
                folder.get("folder_name")
                if isinstance(folder, dict)
                else folder.folder_name
            )
            if os.path.normpath(name or "") == normalised:
                matched.append(folder)

        if matched:
            return {
                "truefalse": True,
                "matched_folder": _to_db_dict(matched[0]),
                "all_matched_folders": [_to_db_dict(m) for m in matched],
            }

        return {"truefalse": False, "matched_folder": None, "all_matched_folders": []}

    def get_folder_by_id(self, folder_id: int) -> dict[str, Any] | None:
        """Get a folder by its ID.

        Args:
            folder_id: The folder ID

        Returns:
            Folder dict or None if not found

        """
        return _to_db_dict(self._folder_repo.find_by_id(folder_id))

    def get_folder_by_name(self, folder_name: str) -> dict[str, Any] | None:
        """Get a folder by its name (path).

        Args:
            folder_name: The folder path/name

        Returns:
            Folder dict or None if not found

        """
        return _to_db_dict(self._folder_repo.find_by_path(folder_name))

    def get_folder_by_alias(self, alias: str) -> dict[str, Any] | None:
        """Get a folder by its alias.

        Args:
            alias: The folder alias

        Returns:
            Folder dict or None if not found

        """
        return _to_db_dict(self._folder_repo.find_by_alias(alias))

    def set_folder_active(self, folder_id: int, *, active: bool) -> bool:
        """Set a folder's active state.

        Args:
            folder_id: The folder ID
            active: True to enable, False to disable

        Returns:
            True if successful, False if folder not found

        """
        folder = _to_db_dict(self._folder_repo.find_by_id(folder_id))
        if folder is None:
            return False
        folder["folder_is_active"] = active
        self._folder_repo.update(FolderConfiguration.from_dict(folder), folder_id)
        return True

    def disable_folder(self, folder_id: int) -> bool:
        """Disable a folder.

        Delegates to set_folder_active.

        Args:
            folder_id: The folder ID to disable

        Returns:
            True if successful, False if folder not found

        """
        return self.set_folder_active(folder_id, active=False)

    def enable_folder(self, folder_id: int) -> bool:
        """Enable a folder.

        Delegates to set_folder_active.

        Args:
            folder_id: The folder ID to enable

        Returns:
            True if successful, False if folder not found

        """
        return self.set_folder_active(folder_id, active=True)

    def delete_folder(self, folder_id: int) -> bool:
        """Delete a folder from the database.

        Args:
            folder_id: The folder ID to delete

        Returns:
            True if deleted, False if folder not found

        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            self._folder_repo.delete(folder_id)
            return True
        return False

    def delete_folder_with_related(self, folder_id: int) -> bool:
        """Delete a folder and all related records from the database.

        Deletes the folder record. Also deletes processed files for this
        folder if a ``processed_files_repo`` was provided at construction.

        Args:
            folder_id: The folder ID to delete

        Returns:
            True if deleted, False if folder not found

        """
        folder = self.get_folder_by_id(folder_id)
        if folder:
            self._folder_repo.delete(folder_id)
            if self._processed_files_repo is not None:
                self._processed_files_repo.clear_for_folder(folder_id)
            return True
        return False

    def get_active_folders(self) -> list[dict[str, Any]]:
        """Get all active folders.

        Returns:
            List of active folder dicts

        """
        return [
            result
            for f in self._folder_repo.find_all(active_only=True)
            if (result := _to_db_dict(f)) is not None
        ]

    def get_inactive_folders(self) -> list[dict[str, Any]]:
        """Get all inactive folders.

        Returns:
            List of inactive folder dicts

        """
        all_folders = self._folder_repo.find_all(active_only=False)
        return [
            result
            for f in all_folders
            if not _is_active_folder(f)
            if (result := _to_db_dict(f)) is not None
        ]

    def get_all_folders(self, _order_by: str | None = "alias") -> list[dict[str, Any]]:
        """Get all folders.

        Args:
            _order_by: Ignored; kept for backward compatibility.

        Returns:
            List of all folder dicts

        """
        return [
            result
            for f in self._folder_repo.find_all()
            if (result := _to_db_dict(f)) is not None
        ]

    def count_folders(self, *, active_only: bool = False) -> int:
        """Count folders.

        Args:
            active_only: If True, count only active folders

        Returns:
            Folder count

        """
        return self._folder_repo.count(active_only=active_only)

    def update_folder(self, folder_data: dict) -> bool:
        """Update a folder configuration.

        Args:
            folder_data: Updated folder data (must include 'id')

        Returns:
            True if updated, False if folder not found

        """
        if "id" not in folder_data:
            return False

        existing = _to_db_dict(self._folder_repo.find_by_id(folder_data["id"]))
        if existing is None:
            return False
        merged = {**existing, **folder_data}
        self._folder_repo.update(
            FolderConfiguration.from_dict(merged), folder_data["id"]
        )
        return True

    def update_folder_by_name(self, folder_data: dict) -> bool:
        """Update a folder configuration by name.

        Args:
            folder_data: Updated folder data (must include 'folder_name')

        Returns:
            True if updated, False if folder not found

        """
        if "folder_name" not in folder_data:
            return False

        existing = _to_db_dict(
            self._folder_repo.find_by_path(folder_data["folder_name"])
        )
        if existing is None:
            return False
        folder_id = existing["id"]
        merged = {**existing, **folder_data}
        self._folder_repo.update(FolderConfiguration.from_dict(merged), folder_id)
        return True

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
