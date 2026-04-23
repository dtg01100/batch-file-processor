"""Resend service for managing file resend flags.

This module provides toolkit-agnostic business logic for the resend interface.
"""

import os
from collections import OrderedDict
from operator import itemgetter
from typing import Any

MAX_FOLDER_ALIAS_CACHE_SIZE = 1000


class ResendService:
    """Business logic for managing resend flags, decoupled from UI.

    This service handles all database operations related to resend functionality.
    """

    def __init__(self, database_connection) -> None:
        """Initialize with database connection.

        Args:
            database_connection: The dataset database connection

        """
        self._db = database_connection
        self._processed_files = database_connection["processed_files"]
        self._folders = database_connection["folders"]
        self._folder_alias_cache: OrderedDict[int, str] = OrderedDict()

    @staticmethod
    def _get_sent_timestamp(processed_line: dict[str, Any]) -> Any:
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
        sql = (
        "SELECT COUNT(DISTINCT file_name || '-' || folder_id)"
        " AS cnt FROM processed_files"
    )
        cur = self._db.raw_connection.execute(sql, [])
        row = cur.fetchone()
        return row["cnt"] if row else 0

    def _get_folder_alias_batch(self, folder_ids: list[int]) -> dict[int, str]:
        """Get folder aliases for multiple folder IDs in a single query.

        Args:
            folder_ids: List of folder IDs to look up

        Returns:
            Dictionary mapping folder_id to alias

        """
        result = {}
        for fid in folder_ids:
            if fid in self._folder_alias_cache:
                result[fid] = self._folder_alias_cache[fid]
        missing_ids = [fid for fid in folder_ids if fid not in result]

        if not missing_ids:
            return result

        placeholders = ",".join("?" * len(missing_ids))
        sql = f"SELECT id, alias FROM folders WHERE id IN ({placeholders})"
        cur = self._db.raw_connection.execute(sql, missing_ids)
        rows = [dict(r) for r in cur.fetchall()]

        for row in rows:
            fid = row["id"]
            alias = row["alias"]
            result[fid] = alias
            self._folder_alias_cache[fid] = alias

        if len(self._folder_alias_cache) > MAX_FOLDER_ALIAS_CACHE_SIZE:
            keys_to_remove = list(self._folder_alias_cache.keys())[
                : MAX_FOLDER_ALIAS_CACHE_SIZE // 4
            ]
            for key in keys_to_remove:
                del self._folder_alias_cache[key]

        return result

    def get_folder_list(self) -> list[tuple[int, str]]:
        """Get list of folders that have processed files.

        Returns:
            Sorted list of (folder_id, alias) tuples

        """
        folder_rows = list(self._processed_files.distinct("folder_id"))
        folder_ids = [row["folder_id"] for row in folder_rows]
        folder_aliases = self._get_folder_alias_batch(folder_ids)

        folder_list = []
        for fid in folder_ids:
            if fid in folder_aliases:
                folder_list.append((fid, folder_aliases[fid]))
            else:
                # Folder was deleted; fall back to the denormalized alias stored
                # in the most recent processed_files row for this folder_id.
                row = self._processed_files.find_one(folder_id=fid)
                fallback = (row.get("folder_alias") if row else None) or "Unknown"
                folder_list.append((fid, fallback))

        return sorted(folder_list, key=itemgetter(1))

    def get_files_for_folder(
        self, folder_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
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

    def set_resend_flag(self, file_id: int, *, resend_flag: bool) -> None:
        """Set the resend flag for a processed file.

        Args:
            file_id: The processed file record ID
            resend_flag: Whether to enable resend

        """
        self._processed_files.update(dict(resend_flag=resend_flag, id=file_id), ["id"])

    def set_resend_flags_batch(self, file_ids: list[int], *, resend_flag: bool) -> int:
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
        *,
        check_file_exists: bool = True,
        limit: int = 1000,
        offset: int = 0,
        search_text: str | None = None,
        search_field: str = "all",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get files sorted by sent_date_time (most recent first),
        with processed_at fallback."""
        where_clauses = []
        params: list[Any] = []

        if search_text:
            search_value = f"%{search_text}%"
            if search_field == "file_name":
                where_clauses.append("pf.file_name LIKE ?")
                params = [search_value]
            elif search_field == "invoice_numbers":
                where_clauses.append("pf.invoice_numbers LIKE ?")
                params = [search_value]
            elif search_field == "folder":
                where_clauses.append("COALESCE(f.alias, pf.folder_alias, '') LIKE ?")
                params = [search_value]
            else:
                where_clauses.append(
                    (
                    "(pf.file_name LIKE ? OR pf.invoice_numbers LIKE ?"
                    " OR COALESCE(f.alias, pf.folder_alias, '') LIKE ?)"
                )
                )
                params = [search_value, search_value, search_value]

        if date_from:
            where_clauses.append("COALESCE(pf.sent_date_time, pf.processed_at) >= ?")
            params.append(date_from)

        if date_to:
            where_clauses.append("COALESCE(pf.sent_date_time, pf.processed_at) <= ?")
            params.append(date_to)

        where_clause = self._build_where_clause(where_clauses)

        sql = f"""
            SELECT pf.*, COALESCE(f.alias, pf.folder_alias, '') AS resolved_folder_alias
            FROM processed_files pf
            LEFT JOIN folders f ON f.id = pf.folder_id
            {where_clause}
            ORDER BY pf.processed_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cur = self._db.raw_connection.execute(sql, params)
        processed_lines = [dict(row) for row in cur.fetchall()]

        folder_ids = list(dict.fromkeys(line["folder_id"] for line in processed_lines))
        folder_aliases = self._get_folder_alias_batch(folder_ids)

        return self._build_file_list(processed_lines, folder_aliases, check_file_exists)

    def _build_where_clause(self, clauses: list[str]) -> str:
        """Build SQL WHERE clause from individual clauses."""
        if not clauses:
            return ""
        return "WHERE " + " AND ".join(clauses)

    def _build_file_list(
        self,
        processed_lines: list[dict[str, Any]],
        folder_aliases: dict[int, str],
        check_file_exists: bool,
    ) -> list[dict[str, Any]]:
        """Construct the deduplicated file list from processed lines."""
        file_list: list[dict[str, Any]] = []
        seen_files = set()
        for processed_line in processed_lines:
            file_key = (processed_line["file_name"], processed_line["folder_id"])
            if file_key in seen_files:
                continue

            folder_id = processed_line["folder_id"]
            folder_alias = folder_aliases.get(
                folder_id,
                processed_line.get("resolved_folder_alias")
                or processed_line.get("folder_alias")
                or "Unknown",
            )

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
        self,
        *,
        check_file_exists: bool = True,
        limit: int = 1000,
        offset: int = 0,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
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
            date_from=date_from,
            date_to=date_to,
        )

    def search_files_for_resend(
        self,
        search_text: str,
        limit: int = 1000,
        offset: int = 0,
        search_field: str = "all",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search processable files by one specific field or all fields.

        Args:
            search_text: Text to search for in file_name, invoice_numbers, or
                folder alias
            limit: Maximum number of files to return
            offset: Number of files to skip (for pagination)
            search_field: Field key to filter by. Supported values are
                "all", "folder", "file_name", and "invoice_numbers".

        Returns:
            List of dicts with keys: id, folder_id, folder_alias, file_name,
            resend_flag, sent_date_time, file_exists, invoice_numbers

        """
        return self._get_files_with_ordering(
            check_file_exists=True,
            limit=limit,
            offset=offset,
            search_text=search_text,
            search_field=search_field,
            date_from=date_from,
            date_to=date_to,
        )
