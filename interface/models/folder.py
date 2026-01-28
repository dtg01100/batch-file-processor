"""
Folder model for interface.py refactoring.

This module contains the Folder configuration model representing a monitored directory.
Refactored from interface.py folder configuration (lines 240-280).
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Folder:
    """Folder configuration model representing a monitored directory."""
    
    id: Optional[int] = None
    alias: str = ""
    path: str = ""
    active: bool = True
    processed: bool = False
    
    # Backend configurations (stored as JSON or separate fields)
    copy_to_directory: Optional[str] = None
    ftp_host: Optional[str] = None
    ftp_port: int = 21
    ftp_username: Optional[str] = None
    ftp_password: Optional[str] = None
    ftp_remote_path: Optional[str] = ""
    ftp_passive: bool = True
    
    email_to: Optional[str] = None
    email_cc: Optional[str] = None
    email_subject_prefix: Optional[str] = None
    
    # EDI and conversion settings
    convert_to_format: Optional[str] = None
    edi_format: Optional[str] = None
    edi_convert_options: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Folder instance to dictionary for database storage.
        
        Returns:
            Dictionary representation of the Folder instance.
        """
        return {
            'id': self.id,
            'alias': self.alias,
            'path': self.path,
            'active': self.active,
            'processed': self.processed,
            'copy_to_directory': self.copy_to_directory,
            'ftp_host': self.ftp_host,
            'ftp_port': self.ftp_port,
            'ftp_username': self.ftp_username,
            'ftp_password': self.ftp_password,
            'ftp_remote_path': self.ftp_remote_path,
            'ftp_passive': self.ftp_passive,
            'email_to': self.email_to,
            'email_cc': self.email_cc,
            'email_subject_prefix': self.email_subject_prefix,
            'convert_to_format': self.convert_to_format,
            'edi_format': self.edi_format,
            'edi_convert_options': self.edi_convert_options,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Folder':
        """
        Create a Folder instance from a dictionary (database row).
        
        Args:
            data: Dictionary containing folder configuration data.
            
        Returns:
            New Folder instance.
        """
        created_at = None
        updated_at = None
        
        if isinstance(data.get('created_at'), str):
            created_at = datetime.fromisoformat(data['created_at'])
        elif isinstance(data.get('created_at'), datetime):
            created_at = data['created_at']
            
        if isinstance(data.get('updated_at'), str):
            updated_at = datetime.fromisoformat(data['updated_at'])
        elif isinstance(data.get('updated_at'), datetime):
            updated_at = data['updated_at']
        
        return cls(
            id=data.get('id'),
            alias=data.get('alias', ''),
            path=data.get('path', ''),
            active=data.get('active', True),
            processed=data.get('processed', False),
            copy_to_directory=data.get('copy_to_directory'),
            ftp_host=data.get('ftp_host'),
            ftp_port=data.get('ftp_port', 21),
            ftp_username=data.get('ftp_username'),
            ftp_password=data.get('ftp_password'),
            ftp_remote_path=data.get('ftp_remote_path', ''),
            ftp_passive=data.get('ftp_passive', True),
            email_to=data.get('email_to'),
            email_cc=data.get('email_cc'),
            email_subject_prefix=data.get('email_subject_prefix'),
            convert_to_format=data.get('convert_to_format'),
            edi_format=data.get('edi_format'),
            edi_convert_options=data.get('edi_convert_options', {}),
            created_at=created_at,
            updated_at=updated_at,
        )
    
    def is_valid(self) -> bool:
        """
        Validate folder configuration.
        
 True if configuration        Returns:
            is valid, False otherwise.
        """
        if not self.path:
            return False
        if not self.alias:
            return False
        return True
