"""ProcessedFilesTracker for tracking sent files.

This module provides a refactored, testable implementation of file tracking,
using Protocol interfaces for dependency injection and database abstraction.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessedFileRecord:
    """Represents a record of a processed/sent file.
    
    Attributes:
        file_name: Name of the file
        folder_id: ID of the folder the file belongs to
        file_checksum: MD5 or other checksum of the file
        sent_date_time: When the file was sent
        resend_flag: Whether the file is marked for resending
        additional_data: Any additional metadata
    """
    file_name: str
    folder_id: int
    file_checksum: str
    sent_date_time: datetime
    resend_flag: bool = False
    additional_data: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert the record to a dictionary for database storage.
        
        Returns:
            Dictionary representation of the record
        """
        return {
            'file_name': self.file_name,
            'folder_id': self.folder_id,
            'file_checksum': self.file_checksum,
            'sent_date_time': self.sent_date_time.isoformat() if self.sent_date_time else None,
            'resend_flag': self.resend_flag,
            'additional_data': self.additional_data
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedFileRecord':
        """Create a record from a dictionary.
        
        Args:
            data: Dictionary with record data
            
        Returns:
            ProcessedFileRecord instance
        """
        sent_date_time = data.get('sent_date_time')
        if isinstance(sent_date_time, str):
            sent_date_time = datetime.fromisoformat(sent_date_time)
        elif not isinstance(sent_date_time, datetime):
            sent_date_time = sent_date_time or datetime.now()
        
        return cls(
            file_name=data.get('file_name', ''),
            folder_id=data.get('folder_id', 0),
            file_checksum=data.get('file_checksum', ''),
            sent_date_time=sent_date_time,
            resend_flag=data.get('resend_flag', False),
            additional_data=data.get('additional_data', {})
        )


@runtime_checkable
class DatabaseProtocol(Protocol):
    """Protocol for database operations.
    
    Implementations should provide CRUD operations for tracking records.
    """
    
    def insert(self, table: str, record: dict) -> None:
        """Insert a record into a table.
        
        Args:
            table: Table name
            record: Record dictionary to insert
        """
        ...
    
    def find(self, table: str, **kwargs) -> list[dict]:
        """Find records matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            List of matching records
        """
        ...
    
    def find_one(self, table: str, **kwargs) -> Optional[dict]:
        """Find a single record matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            Single matching record or None
        """
        ...
    
    def update(self, table: str, record: dict, keys: list) -> None:
        """Update a record.
        
        Args:
            table: Table name
            record: Record with updated values
            keys: List of field names to use as keys
        """
        ...
    
    def delete(self, table: str, **kwargs) -> None:
        """Delete records matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
        """
        ...
    
    def count(self, table: str, **kwargs) -> int:
        """Count records matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            Number of matching records
        """
        ...


class InMemoryDatabase:
    """In-memory database implementation for testing.
    
    Stores records in memory with simple query capabilities.
    """
    
    def __init__(self):
        """Initialize the in-memory database."""
        self._tables: dict[str, list[dict]] = {}
    
    def _ensure_table(self, table: str) -> list[dict]:
        """Ensure a table exists and return its records.
        
        Args:
            table: Table name
            
        Returns:
            List of records in the table
        """
        if table not in self._tables:
            self._tables[table] = []
        return self._tables[table]
    
    def insert(self, table: str, record: dict) -> None:
        """Insert a record.
        
        Args:
            table: Table name
            record: Record to insert
        """
        records = self._ensure_table(table)
        # Create a copy to avoid mutation issues
        records.append(dict(record))
    
    def find(self, table: str, **kwargs) -> list[dict]:
        """Find records matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            List of matching records
        """
        records = self._ensure_table(table)
        if not kwargs:
            return list(records)
        
        results = []
        for record in records:
            match = True
            for key, value in kwargs.items():
                if record.get(key) != value:
                    match = False
                    break
            if match:
                results.append(dict(record))
        return results
    
    def find_one(self, table: str, **kwargs) -> Optional[dict]:
        """Find a single record matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            Single matching record or None
        """
        results = self.find(table, **kwargs)
        return results[0] if results else None
    
    def update(self, table: str, record: dict, keys: list) -> None:
        """Update a record.
        
        Args:
            table: Table name
            record: Record with updated values
            keys: List of field names to use as keys
        """
        records = self._ensure_table(table)
        
        for i, existing in enumerate(records):
            match = True
            for key in keys:
                if existing.get(key) != record.get(key):
                    match = False
                    break
            if match:
                # Update the record
                records[i] = dict(record)
                return
    
    def delete(self, table: str, **kwargs) -> None:
        """Delete records matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
        """
        records = self._ensure_table(table)
        
        if not kwargs:
            self._tables[table] = []
            return
        
        self._tables[table] = [
            record for record in records
            if not all(record.get(k) == v for k, v in kwargs.items())
        ]
    
    def count(self, table: str, **kwargs) -> int:
        """Count records matching criteria.
        
        Args:
            table: Table name
            **kwargs: Field name/value pairs to filter by
            
        Returns:
            Number of matching records
        """
        return len(self.find(table, **kwargs))
    
    def clear(self, table: Optional[str] = None) -> None:
        """Clear all records from a table or all tables.
        
        Args:
            table: Optional table name, or None to clear all
        """
        if table:
            self._tables[table] = []
        else:
            self._tables.clear()


class ProcessedFilesTracker:
    """Service for tracking processed/sent files.
    
    This class coordinates the tracking of files that have been processed,
    using an injected database for testability.
    """
    
    TABLE_NAME = 'processed_files'
    
    def __init__(self, database: DatabaseProtocol):
        """Initialize the processed files tracker.
        
        Args:
            database: Database for storing tracking records
        """
        self.database = database
    
    def record_sent_file(self, record: ProcessedFileRecord) -> None:
        """Record a file that has been sent.
        
        Args:
            record: The processed file record to store
        """
        self.database.insert(self.TABLE_NAME, record.to_dict())
        logger.info(f"Recorded sent file: {record.file_name} for folder {record.folder_id}")
    
    def record_sent_file_simple(self, file_name: str, folder_id: int, 
                                file_checksum: str, 
                                sent_date_time: Optional[datetime] = None) -> None:
        """Record a sent file with simple parameters.
        
        Args:
            file_name: Name of the file
            folder_id: ID of the folder
            file_checksum: Checksum of the file
            sent_date_time: When the file was sent (defaults to now)
        """
        record = ProcessedFileRecord(
            file_name=file_name,
            folder_id=folder_id,
            file_checksum=file_checksum,
            sent_date_time=sent_date_time or datetime.now()
        )
        self.record_sent_file(record)
    
    def get_files_by_folder(self, folder_id: int) -> list[ProcessedFileRecord]:
        """Get all processed files for a folder.
        
        Args:
            folder_id: The folder ID to search for
            
        Returns:
            List of processed file records for the folder
        """
        results = self.database.find(self.TABLE_NAME, folder_id=folder_id)
        return [ProcessedFileRecord.from_dict(r) for r in results]
    
    def get_files_by_checksum(self, checksum: str) -> list[ProcessedFileRecord]:
        """Get all processed files with a specific checksum.
        
        Args:
            checksum: The checksum to search for
            
        Returns:
            List of processed file records with the checksum
        """
        results = self.database.find(self.TABLE_NAME, file_checksum=checksum)
        return [ProcessedFileRecord.from_dict(r) for r in results]
    
    def get_file_by_name_and_folder(self, file_name: str, 
                                     folder_id: int) -> Optional[ProcessedFileRecord]:
        """Get a specific file record by name and folder.
        
        Args:
            file_name: Name of the file
            folder_id: ID of the folder
            
        Returns:
            The processed file record, or None if not found
        """
        result = self.database.find_one(
            self.TABLE_NAME, 
            file_name=file_name, 
            folder_id=folder_id
        )
        return ProcessedFileRecord.from_dict(result) if result else None
    
    def mark_for_resend(self, file_name: str, folder_id: int) -> bool:
        """Mark a file for resending.
        
        Args:
            file_name: Name of the file
            folder_id: ID of the folder
            
        Returns:
            True if the file was found and marked, False otherwise
        """
        record = self.database.find_one(
            self.TABLE_NAME,
            file_name=file_name,
            folder_id=folder_id
        )
        
        if not record:
            logger.warning(f"File not found for resend marking: {file_name}")
            return False
        
        record['resend_flag'] = True
        self.database.update(
            self.TABLE_NAME,
            record,
            keys=['file_name', 'folder_id']
        )
        
        logger.info(f"Marked file for resend: {file_name}")
        return True
    
    def clear_resend_flag(self, file_name: str, folder_id: int) -> bool:
        """Clear the resend flag for a file.
        
        Args:
            file_name: Name of the file
            folder_id: ID of the folder
            
        Returns:
            True if the file was found and updated, False otherwise
        """
        record = self.database.find_one(
            self.TABLE_NAME,
            file_name=file_name,
            folder_id=folder_id
        )
        
        if not record:
            return False
        
        record['resend_flag'] = False
        self.database.update(
            self.TABLE_NAME,
            record,
            keys=['file_name', 'folder_id']
        )
        
        return True
    
    def get_files_for_resend(self, folder_id: Optional[int] = None) -> list[ProcessedFileRecord]:
        """Get all files marked for resending.
        
        Args:
            folder_id: Optional folder ID to filter by
            
        Returns:
            List of files marked for resending
        """
        if folder_id is not None:
            results = self.database.find(
                self.TABLE_NAME,
                folder_id=folder_id,
                resend_flag=True
            )
        else:
            results = self.database.find(self.TABLE_NAME, resend_flag=True)
        
        return [ProcessedFileRecord.from_dict(r) for r in results]
    
    def file_exists(self, file_name: str, folder_id: int) -> bool:
        """Check if a file has been recorded.
        
        Args:
            file_name: Name of the file
            folder_id: ID of the folder
            
        Returns:
            True if the file exists in tracking, False otherwise
        """
        return self.database.count(
            self.TABLE_NAME,
            file_name=file_name,
            folder_id=folder_id
        ) > 0
    
    def count_files(self, folder_id: Optional[int] = None) -> int:
        """Count processed files.
        
        Args:
            folder_id: Optional folder ID to filter by
            
        Returns:
            Number of processed files
        """
        if folder_id is not None:
            return self.database.count(self.TABLE_NAME, folder_id=folder_id)
        return self.database.count(self.TABLE_NAME)
    
    def delete_file_record(self, file_name: str, folder_id: int) -> None:
        """Delete a file record.
        
        Args:
            file_name: Name of the file
            folder_id: ID of the folder
        """
        self.database.delete(
            self.TABLE_NAME,
            file_name=file_name,
            folder_id=folder_id
        )
        logger.info(f"Deleted file record: {file_name}")


def create_processed_files_tracker(database: Optional[DatabaseProtocol] = None) -> ProcessedFilesTracker:
    """Factory function to create a ProcessedFilesTracker.
    
    Args:
        database: Optional database instance (creates InMemoryDatabase if not provided)
        
    Returns:
        Configured ProcessedFilesTracker instance
    """
    if database is None:
        database = InMemoryDatabase()
    return ProcessedFilesTracker(database=database)
