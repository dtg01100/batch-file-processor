import datetime
from typing import List, Dict, Any, Optional


class ProcessedFilesTracker:
    """Tracks processed files in the database."""
    
    def __init__(self, processed_files_db):
        self.processed_files_db = processed_files_db
    
    def get_processed_files(self) -> List[Dict[str, Any]]:
        """
        Get all processed files from the database.
        
        Returns:
            List of processed file records
        """
        return [dict(entry) for entry in self.processed_files_db.find()]
    
    def mark_as_processed(self, file_name: str, folder_id: int, folder_alias: str,
                         file_checksum: str, parameters_dict: dict) -> Dict[str, Any]:
        """
        Mark a file as processed in the database.
        
        Args:
            file_name: Name of the processed file
            folder_id: ID of the folder
            folder_alias: Alias of the folder
            file_checksum: MD5 checksum of the file
            parameters_dict: Configuration parameters
            
        Returns:
            Processed file record
        """
        record = dict(
            file_name=str(file_name),
            folder_id=folder_id,
            folder_alias=folder_alias,
            file_checksum=file_checksum,
            sent_date_time=datetime.datetime.now(),
            copy_destination="N/A" if not parameters_dict['process_backend_copy']
                            else parameters_dict['copy_to_directory'],
            ftp_destination="N/A" if not parameters_dict['process_backend_ftp']
                           else parameters_dict['ftp_server'] + parameters_dict['ftp_folder'],
            email_destination="N/A" if not parameters_dict['process_backend_email']
                             else parameters_dict['email_to'],
            resend_flag=False
        )
        return record
    
    def is_resend(self, file_name: str) -> bool:
        """
        Check if a file has a resend flag.
        
        Args:
            file_name: Name of the file
            
        Returns:
            True if file has resend flag, False otherwise
        """
        count = self.processed_files_db.count(file_name=str(file_name), resend_flag=True)
        return count > 0
    
    def clear_resend_flag(self, file_name: str):
        """
        Clear the resend flag for a file.
        
        Args:
            file_name: Name of the file
        """
        if self.is_resend(file_name):
            file_old_id = self.processed_files_db.find_one(file_name=str(file_name), resend_flag=True)
            self.processed_files_db.update(dict(resend_flag=False, id=file_old_id['id']), ['id'])
    
    def insert_many(self, records: List[Dict[str, Any]]):
        """
        Insert multiple processed file records.
        
        Args:
            records: List of records to insert
        """
        if records:
            self.processed_files_db.insert_many(records)
    
    def update_by_folder(self, folder_id: int):
        """
        Update records for a folder.
        
        Args:
            folder_id: ID of the folder
        """
        self.processed_files_db.update(dict(resend_flag=False, folder_id=folder_id), ['folder_id'])


class ResendFlagManager:
    """Manages resend flags for files."""
    
    def __init__(self, processed_files_db):
        self.processed_files_db = processed_files_db
    
    def check_resend_flag(self, file_checksum: str, resend_flag_set: set) -> bool:
        """
        Check if a file should be resent based on checksum.
        
        Args:
            file_checksum: MD5 checksum of the file
            resend_flag_set: Set of checksums with resend flag
            
        Returns:
            True if file should be resent, False otherwise
        """
        return file_checksum in resend_flag_set
    
    def get_resend_files(self, processed_files: List[Dict[str, Any]]) -> set:
        """
        Get set of checksums for files with resend flag.
        
        Args:
            processed_files: List of processed file records
            
        Returns:
            Set of checksums with resend flag
        """
        resend_set = set()
        for entry in processed_files:
            if entry.get('resend_flag') is True:
                resend_set.add(entry['file_checksum'])
        return resend_set


class DBManager:
    """Coordinates database operations."""
    
    def __init__(self, database_connection, processed_files_db, folders_db):
        self.database_connection = database_connection
        self.processed_files_db = processed_files_db
        self.folders_db = folders_db
        self.tracker = ProcessedFilesTracker(processed_files_db)
        self.resend_manager = ResendFlagManager(processed_files_db)
    
    def get_active_folders(self) -> List[Dict[str, Any]]:
        """
        Get all active folders.
        
        Returns:
            List of active folder records
        """
        parameters_dict_list = []
        for parameters_dict in self.folders_db.find(folder_is_active="True", order_by="alias"):
            try:
                parameters_dict['id'] = parameters_dict.pop('old_id')
            except KeyError:
                pass
            parameters_dict_list.append(parameters_dict)
        return parameters_dict_list
    
    def get_active_folder_count(self) -> int:
        """
        Get count of active folders.
        
        Returns:
            Number of active folders
        """
        return self.folders_db.count(folder_is_active="True")
    
    def get_processed_files(self) -> List[Dict[str, Any]]:
        """
        Get all processed files.
        
        Returns:
            List of processed file records
        """
        return self.tracker.get_processed_files()
    
    def cleanup_old_records(self, folder_id: int):
        """
        Clean up old records for a folder.
        
        Args:
            folder_id: ID of the folder
        """
        self.database_connection.query(
            "DELETE FROM processed_files WHERE ROWID IN (SELECT id FROM processed_files"
            f" WHERE folder_id={folder_id}"
            " ORDER BY id DESC LIMIT -1 OFFSET 5000)"
        )
    
    def insert_processed_files(self, records: List[Dict[str, Any]]):
        """
        Insert processed file records.
        
        Args:
            records: List of records to insert
        """
        self.tracker.insert_many(records)
    
    def update_folder_records(self, folder_id: int):
        """
        Update records for a folder.
        
        Args:
            folder_id: ID of the folder
        """
        self.tracker.update_by_folder(folder_id)
