"""Copy backend for local file copies.

This module copies files to local directories with
injectable file operations support for testing.
"""

from typing import Optional

from backend.protocols import FileOperationsProtocol
from backend.file_operations import RealFileOperations, create_file_operations


# this is a testing module for local file copies
# note: process_parameters is a dict from a row in the database, passed into this module


def do(
    process_parameters: dict,
    settings_dict: dict,
    filename: str,
    file_ops: Optional[FileOperationsProtocol] = None
) -> bool:
    """Copy a file to a local directory.
    
    Args:
        process_parameters: Dictionary containing:
            - copy_to_directory: Destination directory path
        settings_dict: Settings dictionary (not used by copy backend)
        filename: Local file path to copy
        file_ops: Optional injectable file operations for testing.
                 If None, uses real file operations.
    
    Returns:
        True if file was copied successfully
        
    Raises:
        IOError: If file cannot be copied after 10 retries
    """
    file_pass = False
    counter = 0
    
    # Use provided file operations or create real ones
    if file_ops is None:
        file_ops = create_file_operations()
    
    while not file_pass:
        try:
            file_ops.copy(filename, process_parameters['copy_to_directory'])
            file_pass = True
        except IOError:
            if counter == 10:
                raise
            counter += 1
    
    return file_pass


class CopyBackend:
    """Copy backend class for object-oriented usage.
    
    Provides an object-oriented interface to the copy backend
    with injectable file operations support.
    
    Attributes:
        file_ops: File operations instance (injectable for testing)
    """
    
    def __init__(self, file_ops: Optional[FileOperationsProtocol] = None):
        """Initialize copy backend.
        
        Args:
            file_ops: Optional injectable file operations for testing.
        """
        self.file_ops = file_ops
    
    def copy(
        self,
        process_parameters: dict,
        settings_dict: dict,
        filename: str
    ) -> bool:
        """Copy a file to a local directory.
        
        Args:
            process_parameters: Copy parameters
            settings_dict: Settings dictionary
            filename: File to copy
            
        Returns:
            True if successful
        """
        return do(process_parameters, settings_dict, filename, self.file_ops)
    
    @staticmethod
    def create_file_ops() -> FileOperationsProtocol:
        """Create a file operations instance.
        
        Returns:
            File operations instance
        """
        return create_file_operations()
