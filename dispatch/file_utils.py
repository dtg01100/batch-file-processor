"""File utility functions for dispatch processing.

This module contains pure functions for file operations,
extracted from dispatch.py for testability.
"""

import datetime
import os
import re
from typing import Optional


def build_output_filename(
    original: str,
    format: str,
    params: dict,
    filename_prefix: str = "",
    filename_suffix: str = ""
) -> str:
    """Build output filename based on format and parameters.
    
    Args:
        original: Original filename (may include path)
        format: Output format name (e.g., "Fintech", "Simplified CSV")
        params: Dictionary of parameters including:
            - rename_file: Template for renaming (supports %datetime%)
            - Other format-specific parameters
        filename_prefix: Prefix to add to filename (from EDI splitting)
        filename_suffix: Suffix to add to filename (from EDI splitting)
        
    Returns:
        Constructed output filename (basename only, no path)
    """
    rename_template = params.get('rename_file', '').strip()
    
    if rename_template:
        date_time = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d")
        rename_file = "".join([
            filename_prefix,
            rename_template.replace("%datetime%", date_time),
            ".",
            original.split(".")[-1],
            filename_suffix
        ])
    else:
        rename_file = original
    
    # Strip invalid characters
    stripped_filename = re.sub('[^A-Za-z0-9. _]+', '', rename_file)
    
    return stripped_filename


def filter_files_by_checksum(
    files: list[str],
    checksums: set[str]
) -> list[str]:
    """Filter out files whose checksums are already in the set.
    
    Args:
        files: List of file paths
        checksums: Set of already-processed checksums
        
    Returns:
        List of file paths not in the checksum set
    """
    return [f for f in files if f not in checksums]


def build_error_log_filename(
    alias: str,
    errors_folder: str,
    folder_name: str,
    timestamp: Optional[str] = None
) -> str:
    """Build the full path for a folder error log file.
    
    Args:
        alias: Folder alias (will be cleaned of special chars)
        errors_folder: Base errors folder path
        folder_name: Name of the folder (for subdirectory)
        timestamp: Optional timestamp string (defaults to current time)
        
    Returns:
        Full path to error log file
    """
    # Strip invalid characters from alias
    cleaned_alias = re.sub('[^a-zA-Z0-9 ]', '', alias)
    
    # Generate timestamp if not provided
    if timestamp is None:
        timestamp = time.ctime().replace(":", "-")
    
    # Build filename
    log_name = f"{cleaned_alias} errors.{timestamp}.txt"
    
    # Build full path
    full_path = os.path.join(
        errors_folder,
        os.path.basename(folder_name),
        log_name
    )
    
    return full_path


def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename.
    
    Args:
        filename: Filename or path
        
    Returns:
        File extension without the dot (e.g., "txt", "edi")
    """
    return os.path.splitext(filename)[1].lstrip('.')


def strip_invalid_filename_chars(filename: str) -> str:
    """Remove invalid characters from a filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Filename with only alphanumeric, dots, spaces, and underscores
    """
    return re.sub('[^A-Za-z0-9. _]+', '', filename)


def ensure_directory_exists(path: str) -> bool:
    """Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        return True
    except (IOError, OSError):
        return False


def list_files_in_directory(
    directory: str,
    files_only: bool = True
) -> list[str]:
    """List all files in a directory.
    
    Args:
        directory: Path to directory
        files_only: If True, only return files (not subdirectories)
        
    Returns:
        List of absolute file paths
    """
    if not os.path.isdir(directory):
        return []
    
    files = []
    for item in os.listdir(path=directory):
        full_path = os.path.abspath(os.path.join(directory, item))
        if files_only:
            if os.path.isfile(full_path):
                files.append(full_path)
        else:
            files.append(full_path)
    
    return files


def build_processed_file_record(
    original_filename: str,
    folder_id: int,
    folder_alias: str,
    file_checksum: str,
    params: dict
) -> dict:
    """Build a processed file record for database insertion.
    
    Args:
        original_filename: Original file path
        folder_id: ID of the folder
        folder_alias: Alias of the folder
        file_checksum: MD5 checksum of the file
        params: Dictionary with backend settings:
            - process_backend_copy: bool
            - copy_to_directory: str
            - process_backend_ftp: bool
            - ftp_server: str
            - ftp_folder: str
            - process_backend_email: bool
            - email_to: str
            
    Returns:
        Dictionary ready for database insertion
    """
    return {
        'file_name': str(original_filename),
        'folder_id': folder_id,
        'folder_alias': folder_alias,
        'file_checksum': file_checksum,
        'sent_date_time': datetime.datetime.now(),
        'copy_destination': "N/A" if not params.get('process_backend_copy')
                          else params.get('copy_to_directory', 'N/A'),
        'ftp_destination': "N/A" if not params.get('process_backend_ftp')
                         else params.get('ftp_server', '') + params.get('ftp_folder', ''),
        'email_destination': "N/A" if not params.get('process_backend_email')
                           else params.get('email_to', 'N/A'),
        'resend_flag': False
    }


# Import time module for build_error_log_filename
import time
