"""
Database import utility with Windows path conversion
This utility imports an existing folders.db from the Tkinter interface
and converts Windows paths to remote file system configurations.
"""

import os
import shutil
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

from backend.core.database import get_database
from backend.core.encryption import encrypt_password

logger = logging.getLogger(__name__)


class DatabaseImporter:
    """Imports existing database and converts Windows paths"""

    def __init__(self, source_db_path: str, target_db_path: str):
        """
        Initialize importer

        Args:
            source_db_path: Path to source folders.db (Tkinter interface)
            target_db_path: Path to target database (web interface)
        """
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
        self.source_conn = None
        self.target_conn = None

    def connect(self):
        """Connect to both databases"""
        import dataset

        logger.info(f"Connecting to source database: {self.source_db_path}")
        self.source_conn = dataset.connect(f"sqlite:///{self.source_db_path}")
        self.target_conn = dataset.connect(f"sqlite:///{self.target_db_path}")
        logger.info("Databases connected")

    def close(self):
        """Close database connections"""
        if self.source_conn:
            self.source_conn.close()
        if self.target_conn:
            self.target_conn.close()

    def convert_windows_path_to_smb(self, path: str) -> Dict[str, Any]:
        """
        Convert Windows path to SMB configuration

        Examples:
            \\\\server\\share\\folder -> {'type': 'smb', 'host': 'server', 'share': 'share', 'folder': 'folder'}
            C:\\folder -> {'type': 'local', 'path': 'C:\\folder'}
            //server/share -> {'type': 'smb', 'host': 'server', 'share': 'share', 'folder': '/'}
        """
        result = {"type": "local", "path": path}

        # Check for UNC path (\\\\server\\share\\folder)
        if path.startswith("\\\\\\"):
            parts = path.replace("\\\\", "").split("\\\\")
            if len(parts) >= 2:
                result = {
                    "type": "smb",
                    "host": parts[0],
                    "share": parts[1],
                    "folder": "/" + "/".join(parts[2:]) if len(parts) > 2 else "/",
                }
                logger.info(f"Converted UNC path to SMB: {path} -> {result}")
                return result

        # Check for drive letter path (C:\\folder)
        if ":" in path and len(path) > 1 and path[1] == ":":
            result = {"type": "local", "path": os.path.normpath(path)}
            logger.info(f"Converted Windows path to local: {path} -> {result['path']}")
            return result

        # Check for network path (//server/share)
        if path.startswith("//"):
            parts = path[2:].split("/")
            if len(parts) >= 2:
                result = {
                    "type": "smb",
                    "host": parts[0],
                    "share": parts[1],
                    "folder": "/" + "/".join(parts[2:]) if len(parts) > 2 else "/",
                }
                logger.info(f"Converted network path to SMB: {path} -> {result}")
                return result

        return result

    def import_folders(self) -> Tuple[int, int]:
        """
        Import folders from source database to target database

        Returns:
            Tuple of (imported_count, error_count)
        """
        source_folders = self.source_conn.get_table("folders")
        target_folders = self.target_conn.get_table("folders")

        imported_count = 0
        error_count = 0

        logger.info("Starting folder import...")

        for folder in source_folders.find():
            try:
                # Convert Windows path if present
                folder_name = folder.get("folder_name", "")
                connection_config = {}

                if folder_name:
                    connection_config = self.convert_windows_path_to_smb(folder_name)

                # Import folder configuration
                import_dict = dict(folder)
                import_dict.pop("old_id", None)  # Remove old ID if present

                # Update with converted connection config
                if connection_config["type"] != "local":
                    # For remote systems, store connection params
                    import_dict["connection_type"] = connection_config["type"]
                    if connection_config["type"] == "smb":
                        import_dict["connection_params"] = json.dumps(
                            {
                                "host": connection_config.get("host", ""),
                                "share": connection_config.get("share", ""),
                                "username": "",  # Will need to be filled in UI
                                "password": "",  # Will need to be filled in UI
                                "port": 445,
                            }
                        )
                    import_dict["folder_name"] = connection_config.get(
                        "folder", folder_name
                    )
                else:
                    import_dict["connection_type"] = "local"
                    import_dict["connection_params"] = "{}"

                # Reset schedule and enabled (user needs to configure)
                import_dict["schedule"] = ""
                import_dict["enabled"] = False

                # Insert into target database
                target_folders.insert(import_dict)
                imported_count += 1
                logger.info(f"Imported folder: {import_dict.get('alias', 'Unknown')}")

            except Exception as e:
                error_count += 1
                logger.error(f"Failed to import folder: {e}")

        logger.info(
            f"Folder import complete: {imported_count} imported, {error_count} errors"
        )
        return imported_count, error_count

    def import_processed_files(self) -> Tuple[int, int]:
        """
        Import processed files from source to target database

        This preserves the duplicate detection (processed_files table)
        so users don't re-process already processed files.

        Returns:
            Tuple of (imported_count, error_count)
        """
        source_processed = self.source_conn.get_table("processed_files")
        target_processed = self.target_conn.get_table("processed_files")

        imported_count = 0
        error_count = 0

        logger.info("Starting processed files import...")

        # Get mapping of folder IDs (source -> target)
        source_folders = self.source_conn.get_table("folders")
        target_folders = self.target_conn.get_table("folders")
        folder_id_map = {}

        for s_folder in source_folders.find():
            folder_alias = s_folder.get("alias", "")
            t_folder = target_folders.find_one(alias=folder_alias)
            if t_folder:
                folder_id_map[s_folder["id"]] = t_folder["id"]

        for record in source_processed.find():
            try:
                import_dict = dict(record)
                old_id = import_dict.pop("old_id", None)
                old_folder_id = import_dict.pop("folder_id", None)

                # Map folder ID to target database
                if old_folder_id in folder_id_map:
                    import_dict["folder_id"] = folder_id_map[old_folder_id]

                # Insert into target database
                target_processed.insert(import_dict)
                imported_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Failed to import processed file: {e}")

        logger.info(
            f"Processed files import complete: {imported_count} imported, {error_count} errors"
        )
        return imported_count, error_count

    def import_settings(self) -> Tuple[int, int]:
        """
        Import settings from source database to target database

        Returns:
            Tuple of (imported_count, error_count)
        """
        source_settings = self.source_conn.get_table("settings")
        target_settings = self.target_conn.get_table("settings")

        imported_count = 0
        error_count = 0

        logger.info("Starting settings import...")

        for setting in source_settings.find():
            try:
                # Settings with id=1 are global settings
                if setting.get("id") == 1:
                    # Copy to target
                    target_settings.update(dict(setting))
                    imported_count += 1
                    logger.info(f"Imported setting: {setting.get('name', 'unknown')}")

            except Exception as e:
                error_count += 1
                logger.error(f"Failed to import setting: {e}")

        logger.info(
            f"Settings import complete: {imported_count} imported, {error_count} errors"
        )
        return imported_count, error_count

    def run_full_import(self) -> Dict[str, Any]:
        """
        Run full import (folders, processed files, settings)

        Returns:
            Summary of import results
        """
        logger.info("=" * 60)
        logger.info("Starting full database import")
        logger.info(f"Source: {self.source_db_path}")
        logger.info(f"Target: {self.target_db_path}")
        logger.info("=" * 60)

        self.connect()

        try:
            folders_imported, folders_errors = self.import_folders()
            processed_imported, processed_errors = self.import_processed_files()
            settings_imported, settings_errors = self.import_settings()

            total_imported = folders_imported + processed_imported + settings_imported
            total_errors = folders_errors + processed_errors + settings_errors

            summary = {
                "folders_imported": folders_imported,
                "folders_errors": folders_errors,
                "processed_files_imported": processed_imported,
                "processed_files_errors": processed_errors,
                "settings_imported": settings_imported,
                "settings_errors": settings_errors,
                "total_imported": total_imported,
                "total_errors": total_errors,
                "success": total_errors == 0,
                "message": f"Imported {total_imported} records with {total_errors} errors",
            }

            logger.info("=" * 60)
            logger.info("Import summary:")
            logger.info(
                f"  Folders: {folders_imported} imported, {folders_errors} errors"
            )
            logger.info(
                f"  Processed files: {processed_imported} imported, {processed_errors} errors"
            )
            logger.info(
                f"  Settings: {settings_imported} imported, {settings_errors} errors"
            )
            logger.info(f"  Total: {total_imported} imported, {total_errors} errors")
            logger.info("=" * 60)

            return summary

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return {"success": False, "message": f"Import failed: {str(e)}"}
        finally:
            self.close()


def import_database(source_db_path: str, target_db_path: str = None) -> Dict[str, Any]:
    """
    Import a source database to the target database

    Args:
        source_db_path: Path to source folders.db
        target_db_path: Path to target database (defaults to main database)

    Returns:
        Summary of import results
    """
    if target_db_path is None:
        from backend.core.database import DATABASE_PATH

        target_db_path = DATABASE_PATH

    # Backup target database if it exists
    if os.path.exists(target_db_path):
        backup_path = (
            f"{target_db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        logger.info(f"Backing up existing database to: {backup_path}")
        shutil.copy2(target_db_path, backup_path)

    importer = DatabaseImporter(source_db_path, target_db_path)
    return importer.run_full_import()
