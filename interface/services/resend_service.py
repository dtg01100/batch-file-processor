"""Resend service for managing file resend flags.

This module provides toolkit-agnostic business logic for the resend interface.
"""

import os
from operator import itemgetter
from typing import Any, Dict, List, Tuple


class ResendService:
    """Business logic for managing resend flags, decoupled from UI.

    This service handles all database operations related to resend functionality.
    """

    def __init__(self, database_connection):
        """Initialize with database connection.

        Args:
            database_connection: The dataset database connection
        """
        self._db = database_connection
        self._processed_files = database_connection["processed_files"]
        self._folders = database_connection["folders"]

    @staticmethod
    def _get_sent_timestamp(processed_line: Dict[str, Any]) -> Any:
        """Return the best available resend timestamp for a processed file."""
        return processed_line.get("sent_date_time") or processed_line.get(
            "processed_at"
        )

    def has_processed_files(self) -> bool:
        """Check if there are any processed files."""
        return self._processed_files.count() > 0

    def get_folder_list(self) -> List[Tuple[int, str]]:
        """Get list of folders that have processed files.

        Returns:
            Sorted list of (folder_id, alias) tuples
        """
        folder_list = []
        seen_folder_ids = set()
        for line in self._processed_files.distinct("folder_id"):
            folder_id = line["folder_id"]
            # Skip if we've already added this folder
            if folder_id in seen_folder_ids:
                continue
            seen_folder_ids.add(folder_id)
            folder_alias_dict = self._folders.find_one(id=folder_id)
            if folder_alias_dict is not None:
                folder_list.append((folder_id, folder_alias_dict["alias"]))
        return sorted(folder_list, key=itemgetter(1))

    def get_files_for_folder(
        self, folder_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get list of processable files for a folder.

        Args:
            folder_id: The folder ID to get files for
            limit: Maximum number of files to return

        Returns:
            List of dicts with keys: file_name, resend_flag, id, sent_date_time
        """
        file_list = []
        file_name_list = []
        processed_lines = list(
            self._processed_files.find(folder_id=folder_id, order_by="-processed_at")
        )
        for processed_line in processed_lines[:limit]:
            if processed_line["file_name"] not in file_name_list and os.path.exists(
                processed_line["file_name"]
            ):
                file_list.append(
                    {
                        "file_name": processed_line["file_name"],
                        "resend_flag": processed_line["resend_flag"],
                        "id": processed_line["id"],
                        "sent_date_time": self._get_sent_timestamp(processed_line),
                    }
                )
                file_name_list.append(processed_line["file_name"])
        return file_list

    def count_files_for_folder(self, folder_id: int) -> int:
        """Count unique existing files for a folder.

        Args:
            folder_id: The folder ID

        Returns:
            Count of unique existing files
        """
        file_name_list = []
        for processed_line in self._processed_files.find(
            folder_id=folder_id, order_by="-processed_at"
        ):
            if processed_line["file_name"] not in file_name_list and os.path.exists(
                processed_line["file_name"]
            ):
                file_name_list.append(processed_line["file_name"])
        return len(file_name_list)

    def set_resend_flag(self, file_id: int, resend_flag: bool) -> None:
        """Set the resend flag for a processed file.

        Args:
            file_id: The processed file record ID
            resend_flag: Whether to enable resend
        """
        self._processed_files.update(dict(resend_flag=resend_flag, id=file_id), ["id"])

    def get_all_files_for_resend(self) -> List[Dict[str, Any]]:
        """Get all processable files across all folders for resend interface.

        Returns:
            List of dicts with keys: id, folder_id, folder_alias, file_name, resend_flag, sent_date_time
        """
        file_list = []
        processed_lines = list(self._processed_files.find(order_by="-processed_at"))

        # Group by file_name and folder to avoid duplicates
        seen_files = set()
        for processed_line in processed_lines:
            file_key = (processed_line["file_name"], processed_line["folder_id"])
            if file_key in seen_files:
                continue
            if os.path.exists(processed_line["file_name"]):
                # Get folder alias
                folder_info = self._folders.find_one(id=processed_line["folder_id"])
                folder_alias = folder_info["alias"] if folder_info else "Unknown"

                file_list.append(
                    {
                        "id": processed_line["id"],
                        "folder_id": processed_line["folder_id"],
                        "folder_alias": folder_alias,
                        "file_name": processed_line["file_name"],
                        "resend_flag": processed_line["resend_flag"],
                        "sent_date_time": self._get_sent_timestamp(processed_line),
                    }
                )
                seen_files.add(file_key)

        return file_list
