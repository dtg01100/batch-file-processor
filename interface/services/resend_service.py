"""Resend service for managing file resend flags.

This module provides toolkit-agnostic business logic for the resend interface.
"""

import os
from operator import itemgetter
from typing import Any, Dict, List, Optional, Tuple


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
        self._folder_alias_cache: Dict[int, str] = {}

    @staticmethod
    def _get_sent_timestamp(processed_line: Dict[str, Any]) -> Any:
        """Return the best available resend timestamp for a processed file."""
        return processed_line.get("sent_date_time") or processed_line.get(
            "processed_at"
        )

    def has_processed_files(self) -> bool:
        """Check if there are any processed files."""
        return self._processed_files.count() > 0

    def get_total_file_count(self) -> int:
        """Get total count of unique processed files.

        Returns:
            Total number of unique processed files.
        """
        rows = list(self._processed_files.find(order_by=None))
        seen = set()
        for row in rows:
            seen.add((row["file_name"], row["folder_id"]))
        return len(seen)

    def _get_folder_alias_batch(self, folder_ids: List[int]) -> Dict[int, str]:
        """Get folder aliases for multiple folder IDs in a single query.

        Args:
            folder_ids: List of folder IDs to look up

        Returns:
            Dictionary mapping folder_id to alias
        """
        result = {
            fid: alias
            for fid, alias in self._folder_alias_cache.items()
            if fid in folder_ids
        }
        missing_ids = [fid for fid in folder_ids if fid not in result]

        if not missing_ids:
            return result

        placeholders = ",".join("?" * len(missing_ids))
        sql = f"SELECT id, alias FROM folders WHERE id IN ({placeholders})"
        rows = self._db.query(sql)

        for row in rows:
            fid = row["id"]
            alias = row["alias"]
            result[fid] = alias
            self._folder_alias_cache[fid] = alias

        return result

    def get_folder_list(self) -> List[Tuple[int, str]]:
        """Get list of folders that have processed files.

        Returns:
            Sorted list of (folder_id, alias) tuples
        """
        folder_ids = [
            row["folder_id"] for row in self._processed_files.distinct("folder_id")
        ]
        folder_aliases = self._get_folder_alias_batch(folder_ids)
        folder_list = [
            (fid, folder_aliases.get(fid, "Unknown"))
            for fid in folder_ids
            if fid in folder_aliases
        ]
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

    def set_resend_flags_batch(self, file_ids: List[int], resend_flag: bool) -> int:
        """Set the resend flag for multiple processed files in a single query.

        Args:
            file_ids: List of processed file record IDs
            resend_flag: Whether to enable resend

        Returns:
            Number of files updated
        """
        if not file_ids:
            return 0

        placeholders = ",".join("?" * len(file_ids))
        sql = f"UPDATE processed_files SET resend_flag=? WHERE id IN ({placeholders})"
        self._db.raw_connection.execute(
            sql, (1 if resend_flag else 0,) + tuple(file_ids)
        )
        self._db.raw_connection.commit()
        return len(file_ids)

    def _get_files_with_ordering(
        self,
        check_file_exists: bool = True,
        limit: int = 1000,
        offset: int = 0,
        search_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get files sorted by sent_date_time (most recent first), with processed_at fallback."""
        where_clause = ""
        params: List[Any] = []
        if search_text:
            where_clause = "WHERE (file_name LIKE ? OR invoice_numbers LIKE ?)"
            params = [f"%{search_text}%", f"%{search_text}%"]

        sql = f"""
            SELECT * FROM processed_files
            {where_clause}
            ORDER BY processed_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cur = self._db.raw_connection.execute(sql, params)
        processed_lines = [dict(row) for row in cur.fetchall()]

        folder_ids = list(set(line["folder_id"] for line in processed_lines))
        folder_aliases = self._get_folder_alias_batch(folder_ids)

        file_list = []
        seen_files = set()
        for processed_line in processed_lines:
            file_key = (processed_line["file_name"], processed_line["folder_id"])
            if file_key in seen_files:
                continue

            folder_id = processed_line["folder_id"]
            folder_alias = folder_aliases.get(folder_id, "Unknown")

            file_exists = True
            if check_file_exists:
                file_exists = os.path.exists(processed_line["file_name"])

            file_list.append(
                {
                    "id": processed_line["id"],
                    "folder_id": folder_id,
                    "folder_alias": folder_alias,
                    "file_name": processed_line["file_name"],
                    "resend_flag": processed_line["resend_flag"],
                    "sent_date_time": self._get_sent_timestamp(processed_line),
                    "invoice_numbers": processed_line.get("invoice_numbers", ""),
                    "file_exists": file_exists,
                }
            )
            seen_files.add(file_key)

        return file_list

    def get_all_files_for_resend(
        self, check_file_exists: bool = True, limit: int = 1000, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all processable files across all folders for resend interface.

        Args:
            check_file_exists: If True, checks if file exists on disk and marks
                it in the result. If False, skips the check for faster loading.
            limit: Maximum number of files to return.
            offset: Number of files to skip (for pagination).

        Returns:
            List of dicts with keys: id, folder_id, folder_alias, file_name,
            resend_flag, sent_date_time, file_exists
        """
        return self._get_files_with_ordering(
            check_file_exists=check_file_exists,
            limit=limit,
            offset=offset,
        )

    def search_files_for_resend(
        self, search_text: str, limit: int = 1000, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search processable files by file name or invoice numbers.

        Args:
            search_text: Text to search for in file_name or invoice_numbers
            limit: Maximum number of files to return
            offset: Number of files to skip (for pagination)

        Returns:
            List of dicts with keys: id, folder_id, folder_alias, file_name,
            resend_flag, sent_date_time, file_exists, invoice_numbers
        """
        return self._get_files_with_ordering(
            check_file_exists=True,
            limit=limit,
            offset=offset,
            search_text=search_text,
        )
