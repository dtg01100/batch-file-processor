"""
Processed file model for interface.py refactoring.

This module contains the ProcessedFile model for tracking processed files.
Refactored from interface.py processed file tracking (lines 330-360).
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ProcessedFile:
    """Processed file tracking model."""
    
    id: Optional[int] = None
    folder_id: int = 0
    filename: str = ""
    original_path: str = ""
    processed_path: Optional[str] = None
    status: str = "pending"  # pending, processed, failed, sent
    error_message: Optional[str] = None
    convert_format: Optional[str] = None
    sent_to: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    # Status constants
    STATUS_PENDING = "pending"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"
    STATUS_SENT = "sent"
    
    @classmethod
    def get_by_folder(cls, db_manager, folder_id: int) -> List['ProcessedFile']:
        """
        Get all processed files for a specific folder.
        
        Args:
            db_manager: Database manager instance.
            folder_id: Folder ID to filter by.
            
        Returns:
            List of ProcessedFile instances.
        """
        try:
            results = db_manager.execute(
                "SELECT * FROM processed_files WHERE folder_id = ? ORDER BY created_at DESC",
                (folder_id,)
            ).fetchall()
            return [cls.from_dict(dict(row)) for row in results]
        except Exception:
            return []
    
    @classmethod
    def get_by_status(cls, db_manager, status: str) -> List['ProcessedFile']:
        """
        Get all processed files with a specific status.
        
        Args:
            db_manager: Database manager instance.
            status: Status to filter by.
            
        Returns:
            List of ProcessedFile instances.
        """
        try:
            results = db_manager.execute(
                "SELECT * FROM processed_files WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
            return [cls.from_dict(dict(row)) for row in results]
        except Exception:
            return []
    
    @classmethod
    def mark_as_processed(cls, db_manager, file_id: int, processed_path: str) -> bool:
        """
        Mark a file as successfully processed.
        
        Args:
            db_manager: Database manager instance.
            file_id: ID of the file to update.
            processed_path: Path to the processed file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            db_manager.execute(
                "UPDATE processed_files SET status = ?, processed_path = ?, processed_at = ? WHERE id = ?",
                (cls.STATUS_PROCESSED, processed_path, datetime.now(), file_id)
            )
            db_manager.commit()
            return True
        except Exception:
            return False
    
    @classmethod
    def mark_as_failed(cls, db_manager, file_id: int, error: str) -> bool:
        """
        Mark a file as failed.
        
        Args:
            db_manager: Database manager instance.
            file_id: ID of the file to update.
            error: Error message describing the failure.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            db_manager.execute(
                "UPDATE processed_files SET status = ?, error_message = ?, processed_at = ? WHERE id = ?",
                (cls.STATUS_FAILED, error, datetime.now(), file_id)
            )
            db_manager.commit()
            return True
        except Exception:
            return False
    
    @classmethod
    def mark_as_sent(cls, db_manager, file_id: int, sent_to: str) -> bool:
        """
        Mark a file as sent to destination.
        
        Args:
            db_manager: Database manager instance.
            file_id: ID of the file to update.
            sent_to: Destination the file was sent to.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            db_manager.execute(
                "UPDATE processed_files SET status = ?, sent_to = ?, processed_at = ? WHERE id = ?",
                (cls.STATUS_SENT, sent_to, datetime.now(), file_id)
            )
            db_manager.commit()
            return True
        except Exception:
            return False
    
    @classmethod
    def create(cls, db_manager, folder_id: int, filename: str, original_path: str) -> Optional[int]:
        """
        Create a new processed file record.
        
        Args:
            db_manager: Database manager instance.
            folder_id: ID of the folder this file belongs to.
            filename: Name of the file.
            original_path: Original path of the file.
            
        Returns:
            ID of the created record or None if failed.
        """
        try:
            cursor = db_manager.execute(
                "INSERT INTO processed_files (folder_id, filename, original_path, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (folder_id, filename, original_path, cls.STATUS_PENDING, datetime.now())
            )
            db_manager.commit()
            return cursor.lastrowid
        except Exception:
            return None
    
    def to_dict(self) -> dict:
        """
        Convert ProcessedFile instance to dictionary.
        
        Returns:
            Dictionary representation of the ProcessedFile instance.
        """
        return {
            'id': self.id,
            'folder_id': self.folder_id,
            'filename': self.filename,
            'original_path': self.original_path,
            'processed_path': self.processed_path,
            'status': self.status,
            'error_message': self.error_message,
            'convert_format': self.convert_format,
            'sent_to': self.sent_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedFile':
        """
        Create a ProcessedFile instance from a dictionary.
        
        Args:
            data: Dictionary containing processed file data.
            
        Returns:
            New ProcessedFile instance.
        """
        created_at = None
        processed_at = None
        
        if isinstance(data.get('created_at'), str):
            created_at = datetime.fromisoformat(data['created_at'])
        elif isinstance(data.get('created_at'), datetime):
            created_at = data['created_at']
            
        if isinstance(data.get('processed_at'), str):
            processed_at = datetime.fromisoformat(data['processed_at'])
        elif isinstance(data.get('processed_at'), datetime):
            processed_at = data['processed_at']
        
        return cls(
            id=data.get('id'),
            folder_id=data.get('folder_id', 0),
            filename=data.get('filename', ''),
            original_path=data.get('original_path', ''),
            processed_path=data.get('processed_path'),
            status=data.get('status', cls.STATUS_PENDING),
            error_message=data.get('error_message'),
            convert_format=data.get('convert_format'),
            sent_to=data.get('sent_to'),
            created_at=created_at,
            processed_at=processed_at,
        )
