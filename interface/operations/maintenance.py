"""
Maintenance operations module for interface.py refactoring.

This module contains maintenance functions like mark_active_as_processed,
remove_inactive_folders, etc.
Refactored from interface.py (lines 2975-3147).

Usage:
    from interface.operations.maintenance import MaintenanceOperations
    operations = MaintenanceOperations(db_manager)
    operations.mark_all_as_processed()
"""

import datetime
import hashlib
import os
from typing import Any, Dict, List, Optional

from interface.database.database_manager import DatabaseManager


class MaintenanceOperations:
    """
    Class for managing maintenance operations.

    Provides methods for database maintenance tasks including:
    - Marking files as processed
    - Removing inactive folder configurations
    - Clearing queues and flags
    - Import/export folder configurations

    Attributes:
        db_manager: DatabaseManager instance for database operations
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize MaintenanceOperations with a database manager.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager

    def mark_all_as_processed(self, folder_id: Optional[int] = None) -> int:
        """Mark all files in active folders as processed.

        Scans active folders (or specific folder) and adds all files to the
        processed files table to prevent reprocessing.

        Args:
            folder_id: Optional specific folder ID, if None processes all active folders

        Returns:
            Number of files marked as processed
        """
        if (
            self.db_manager.folders_table is None
            or self.db_manager.processed_files is None
        ):
            return 0

        starting_folder = os.getcwd()
        folder_count = 0

        # Build list of folders to process
        if folder_id is None:
            folders_list = list(
                self.db_manager.folders_table.find(folder_is_active="True")
            )
        else:
            folder = self.db_manager.folders_table.find_one(id=folder_id)
            folders_list = [folder] if folder else []

        folder_total = len(folders_list)
        files_processed = 0

        for params_dict in folders_list:
            folder_count += 1
            os.chdir(os.path.abspath(params_dict["folder_name"]))

            # Get files in directory
            files = [f for f in os.listdir(".") if os.path.isfile(f)]
            file_total = len(files)

            # Filter out already processed files
            filtered_files = []
            for f in files:
                existing = self.db_manager.processed_files.find_one(
                    file_name=os.path.join(os.getcwd(), f),
                    file_checksum=hashlib.md5(open(f, "rb").read()).hexdigest(),
                )
                if existing is None:
                    filtered_files.append(f)

            # Add files to processed table
            for filename in filtered_files:
                self.db_manager.processed_files.insert(
                    {
                        "file_name": str(os.path.abspath(filename)),
                        "file_checksum": hashlib.md5(
                            open(filename, "rb").read()
                        ).hexdigest(),
                        "folder_id": params_dict["id"],
                        "folder_alias": params_dict["alias"],
                        "copy_destination": "N/A",
                        "ftp_destination": "N/A",
                        "email_destination": "N/A",
                        "sent_date_time": datetime.datetime.now(),
                        "resend_flag": False,
                    }
                )
                files_processed += 1

        os.chdir(starting_folder)
        return files_processed

    def remove_inactive_folders(self) -> int:
        """Remove all inactive folder configurations.

        Deletes folder configurations marked as inactive along with their
        related processed files and email queue entries.

        Returns:
            Number of folders removed
        """
        if self.db_manager.folders_table is None:
            return 0

        folders_to_remove = list(
            self.db_manager.folders_table.find(folder_is_active="False")
        )
        folders_count = len(folders_to_remove)

        for folder in folders_to_remove:
            folder_id = folder["id"]
            # Delete related records
            if self.db_manager.processed_files is not None:
                self.db_manager.processed_files.delete(folder_id=folder_id)
            if self.db_manager.emails_table is not None:
                self.db_manager.emails_table.delete(folder_id=folder_id)
            # Delete the folder
            self.db_manager.folders_table.delete(id=folder_id)

        return folders_count

    def set_all_active(self) -> int:
        """Set all folders to active state.

        Returns:
            Number of folders updated
        """
        if (
            self.db_manager.folders_table is None
            or self.db_manager.database_connection is None
        ):
            return 0
        active_count = self.db_manager.folders_table.count(folder_is_active="True")
        self.db_manager.database_connection.query(
            'update folders set folder_is_active="True" where folder_is_active="False"'
        )
        return (
            self.db_manager.folders_table.count(folder_is_active="True") - active_count
        )

    def set_all_inactive(self) -> int:
        """Set all folders to inactive state.

        Returns:
            Number of folders updated
        """
        if (
            self.db_manager.folders_table is None
            or self.db_manager.database_connection is None
        ):
            return 0
        inactive_count = self.db_manager.folders_table.count(folder_is_active="False")
        self.db_manager.database_connection.query(
            'update folders set folder_is_active="False" where folder_is_active="True"'
        )
        return (
            self.db_manager.folders_table.count(folder_is_active="False")
            - inactive_count
        )

    def clear_resend_flags(self) -> int:
        """Clear all resend flags in processed files.

        Returns:
            Number of flags cleared
        """
        if (
            self.db_manager.processed_files is None
            or self.db_manager.database_connection is None
        ):
            return 0
        before_count = self.db_manager.processed_files.count(resend_flag=True)
        self.db_manager.database_connection.query(
            "update processed_files set resend_flag=0 where resend_flag=1"
        )
        after_count = self.db_manager.processed_files.count(resend_flag=True)
        return before_count - after_count

    def clear_emails_queue(self) -> int:
        """Clear all queued emails.

        Returns:
            Number of emails cleared
        """
        if self.db_manager.emails_table is None:
            return 0
        count = self.db_manager.emails_table.count()
        self.db_manager.emails_table.delete()
        return count

    def clear_processed_files(self, days: Optional[int] = None) -> int:
        """Clear processed file records older than specified days.

        Args:
            days: Number of days to retain records. If None, clears all.

        Returns:
            Number of records deleted
        """
        if self.db_manager.processed_files is None:
            return 0

        if days is None:
            count = self.db_manager.processed_files.count()
            self.db_manager.processed_files.delete()
            return count

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        count = 0

        # Iterate and delete old records
        old_records = self.db_manager.processed_files.all()
        for record in old_records:
            if isinstance(record.get("sent_date_time"), datetime.datetime):
                if record["sent_date_time"] < cutoff_date:
                    self.db_manager.processed_files.delete(id=record["id"])
                    count += 1

        return count

    def clear_all_processed_files(self) -> int:
        """Clear all processed file records.

        Returns:
            Number of records deleted
        """
        if self.db_manager.processed_files is None:
            return 0
        count = self.db_manager.processed_files.count()
        self.db_manager.processed_files.delete()
        return count

    def resend_failed_files(self) -> int:
        """Mark failed files for resend by setting resend flag.

        Returns:
            Number of files marked for resend
        """
        if self.db_manager.processed_files is None:
            return 0
        count = 0
        failed_files = self.db_manager.processed_files.find(resend_flag=True)
        for record in failed_files:
            self.db_manager.processed_files.update(
                {"id": record["id"], "resend_flag": True}, ["id"]
            )
            count += 1
        return count

    def get_processed_files_count(self) -> int:
        """Get the count of processed files.

        Returns:
            Number of processed file records
        """
        if self.db_manager.processed_files is None:
            return 0
        return self.db_manager.processed_files.count()

    def get_inactive_folders_count(self) -> int:
        """Get the count of inactive folders.

        Returns:
            Number of inactive folders
        """
        if self.db_manager.folders_table is None:
            return 0
        return self.db_manager.folders_table.count(folder_is_active="False")

    def get_active_folders_count(self) -> int:
        """Get the count of active folders.

        Returns:
            Number of active folders
        """
        if self.db_manager.folders_table is None:
            return 0
        return self.db_manager.folders_table.count(folder_is_active="True")

    def get_pending_emails_count(self) -> int:
        """Get the count of pending emails in queue.

        Returns:
            Number of pending emails
        """
        if self.db_manager.emails_table is None:
            return 0
        return self.db_manager.emails_table.count()

    def get_resend_files_count(self) -> int:
        """Get the count of files marked for resend.

        Returns:
            Number of files marked for resend
        """
        if self.db_manager.processed_files is None:
            return 0
        return self.db_manager.processed_files.count(resend_flag=True)
