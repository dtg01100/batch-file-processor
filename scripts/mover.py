"""Database migration utilities.

This module provides utilities for migrating and merging database files.
It has been refactored to remove tkinter dependencies.
"""

import os
import threading
import time
from typing import Callable, Optional

import scripts.backup_increment as backup_increment
import migrations.folders_database_migrator
from core.structured_logging import get_logger
from backend.database import sqlite_wrapper

logger = get_logger(__name__)


class DbMigrationThing:
    """Database migration handler.

    This class handles the migration of folder data between database files.
    It has been refactored to use callback-based progress reporting instead
    of tkinter variables.

    Attributes:
        original_folder_path: Path to the original database file
        new_folder_path: Path to the new database file to import from
    """

    def __init__(self, original_folder_path: str, new_folder_path: str) -> None:
        self.original_folder_path = original_folder_path
        self.new_folder_path = new_folder_path
        self.number_of_folders: int = 0
        self.progress_of_folders: int = 0

    def do_migrate(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        original_database_path: Optional[str] = None,
    ) -> None:
        """Perform the database migration.

        Args:
            progress_callback: Optional callback function(progress, maximum) for
                reporting progress. Replaces tkinter progress_bar parameter.
            original_database_path: Path to the original database file. If not
                provided, uses self.original_folder_path.
        """
        if original_database_path is None:
            original_database_path = self.original_folder_path

        _thread_result: dict = {"modified_new_folder_path": None, "error": None}

        def database_preimport_operations():
            try:
                original_database_connection_for_migrate = (
                    sqlite_wrapper.Database.connect(original_database_path)
                )
                backup_increment.do_backup(self.original_folder_path)
                _thread_result["modified_new_folder_path"] = backup_increment.do_backup(
                    self.new_folder_path
                )
                original_db_version = original_database_connection_for_migrate[
                    "version"
                ]
                original_db_version_dict = original_db_version.find_one(id=1)
                _new_db_conn = sqlite_wrapper.Database.connect(
                    _thread_result["modified_new_folder_path"]
                )
                new_db_version = _new_db_conn["version"]
                new_db_version_dict = new_db_version.find_one(id=1)
                if int(new_db_version_dict["version"]) < int(
                    original_db_version_dict["version"]
                ):
                    logger.info("db needs upgrading")
                    folders_database_migrator.upgrade_database(
                        _new_db_conn, None, "Null"
                    )
            except Exception as exc:
                _thread_result["error"] = exc

        preimport_operations_thread_object = threading.Thread(
            target=database_preimport_operations
        )
        preimport_operations_thread_object.start()

        # Report indeterminate progress
        if progress_callback:
            progress_callback(0, 100)

        while preimport_operations_thread_object.is_alive():
            # Process events if needed (for Qt compatibility)
            try:
                from PyQt6.QtWidgets import QApplication

                QApplication.processEvents()
            except ImportError:
                pass
            time.sleep(0.1)

        # Report determinate progress
        if progress_callback:
            progress_callback(0, 100)

        if _thread_result["error"] is not None:
            raise _thread_result["error"]

        modified_new_folder_path = _thread_result["modified_new_folder_path"]
        new_database_connection = sqlite_wrapper.Database.connect(
            modified_new_folder_path
        )
        new_folders_table = new_database_connection["folders"]
        original_database_connection = sqlite_wrapper.Database.connect(
            original_database_path
        )
        old_folders_table = original_database_connection["folders"]

        # Count folders for progress
        active_folders = list(new_folders_table.find(folder_is_active=1))

        self.number_of_folders = len(active_folders)
        self.progress_of_folders = 0

        if progress_callback and self.number_of_folders > 0:
            progress_callback(0, self.number_of_folders)

        def _get_active_folders(table):
            """Get active folders."""
            return list(table.find(folder_is_active=1))

        def test_line_for_match(line):
            line_match = False
            new_db_line = None
            for db_line in _get_active_folders(old_folders_table):
                try:
                    if os.path.samefile(db_line["folder_name"], line["folder_name"]):
                        new_db_line = db_line
                        line_match = True
                        break
                except (OSError, TypeError, ValueError):
                    # Path may not exist on this system; compare as strings
                    if db_line["folder_name"] == line["folder_name"]:
                        new_db_line = db_line
                        line_match = True
                        break
            return line_match, new_db_line

        for line in _get_active_folders(new_folders_table):
            try:
                line_match, new_db_line = test_line_for_match(line)
                logger.debug("line_match=%s", line_match)
                if line_match is True:
                    update_db_line = new_db_line
                    if line.get("process_backend_copy") in (True, 1, "True"):
                        logger.info("merging copy backend settings")
                        update_db_line.update(
                            dict(
                                process_backend_copy=line["process_backend_copy"],
                                copy_to_directory=line["copy_to_directory"],
                                id=new_db_line["id"],
                            )
                        )
                    if line.get("process_backend_ftp") in (True, 1, "True"):
                        logger.info("merging ftp backend settings")
                        update_db_line.update(
                            dict(
                                ftp_server=line["ftp_server"],
                                ftp_folder=line["ftp_folder"],
                                ftp_username=line["ftp_username"],
                                ftp_password=line["ftp_password"],
                                ftp_port=line["ftp_port"],
                                id=new_db_line["id"],
                            )
                        )
                    if line.get("process_backend_email") in (True, 1, "True"):
                        logger.info("merging email backend settings")
                        update_db_line.update(
                            dict(
                                email_to=line["email_to"],
                                email_subject_line=line["email_subject_line"],
                                id=new_db_line["id"],
                            )
                        )
                    old_folders_table.update(update_db_line, ["id"])

                else:
                    logger.info("adding line")
                    logger.debug("line data: %s", line)
                    del line["id"]
                    old_folders_table.insert(line)
            except Exception as error:
                logger.error("import of folder failed with %s", error)

            self.progress_of_folders += 1
            if progress_callback:
                progress_callback(self.progress_of_folders, self.number_of_folders)
