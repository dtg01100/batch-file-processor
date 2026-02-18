"""Resend service for managing file resend flags.

This module provides toolkit-agnostic business logic for the resend interface.
"""
import os
from typing import Any, Dict, List, Optional, Tuple
from operator import itemgetter


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
        self._processed_files = database_connection['processed_files']
        self._folders = database_connection['folders']
    
    def has_processed_files(self) -> bool:
        """Check if there are any processed files."""
        return self._processed_files.count() > 0
    
    def get_folder_list(self) -> List[Tuple[int, str]]:
        """Get list of folders that have processed files.
        
        Returns:
            Sorted list of (folder_id, alias) tuples
        """
        folder_list = []
        for line in self._processed_files.distinct('folder_id'):
            folder_alias = self._folders.find_one(id=line['folder_id'])
            if folder_alias is not None:
                folder_list.append((line['folder_id'], folder_alias['alias']))
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
            self._processed_files.find(
                folder_id=folder_id, order_by="-sent_date_time"
            )
        )
        for processed_line in processed_lines[:limit]:
            if (
                processed_line['file_name'] not in file_name_list
                and os.path.exists(processed_line['file_name'])
            ):
                file_list.append({
                    'file_name': processed_line['file_name'],
                    'resend_flag': processed_line['resend_flag'],
                    'id': processed_line['id'],
                    'sent_date_time': processed_line['sent_date_time'],
                })
                file_name_list.append(processed_line['file_name'])
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
            folder_id=folder_id, order_by="-sent_date_time"
        ):
            if (
                processed_line['file_name'] not in file_name_list
                and os.path.exists(processed_line['file_name'])
            ):
                file_name_list.append(processed_line['file_name'])
        return len(file_name_list)
    
    def set_resend_flag(self, file_id: int, resend_flag: bool) -> None:
        """Set the resend flag for a processed file.
        
        Args:
            file_id: The processed file record ID
            resend_flag: Whether to enable resend
        """
        self._processed_files.update(
            dict(resend_flag=resend_flag, id=file_id), ['id']
        )
