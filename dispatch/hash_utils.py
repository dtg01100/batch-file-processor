"""Hash utility functions for file processing.

This module contains pure functions for generating and managing file hashes,
extracted from dispatch.py for testability.
"""

import hashlib
import os
import time
from typing import Optional


def generate_match_lists(processed_files: list[dict]) -> tuple[list, list, set]:
    """Extract hash lists from processed files.
    
    Args:
        processed_files: List of dicts with file_name, file_checksum, resend_flag
        
    Returns:
        tuple of (hash_dict, name_dict, resend_set)
        - hash_dict: List of (file_name, file_checksum) tuples
        - name_dict: List of (file_checksum, file_name) tuples
        - resend_set: Set of checksums marked for resend
    """
    hash_dict = []
    name_dict = []
    resend_set = set()
    
    for entry in processed_files:
        hash_dict.append((entry['file_name'], entry['file_checksum']))
        name_dict.append((entry['file_checksum'], entry['file_name']))
        if entry.get('resend_flag') is True:
            resend_set.add(entry['file_checksum'])
    
    return hash_dict, name_dict, resend_set


def generate_file_hash(
    file_path: str,
    max_retries: int = 5,
    retry_delay_base: float = 1.0
) -> str:
    """Generate MD5 hash of file contents with retry logic.
    
    Args:
        file_path: Absolute or relative path to the file
        max_retries: Maximum number of retry attempts (default: 5)
        retry_delay_base: Base for exponential backoff delay (default: 1.0)
        
    Returns:
        Hexadecimal MD5 hash string of file contents
        
    Raises:
        FileNotFoundError: If file does not exist after retries
        PermissionError: If file cannot be read due to permissions
        IOError: If file cannot be read after max retries
    """
    absolute_path = os.path.abspath(file_path)
    generated_checksum: Optional[str] = None
    checksum_attempt = 1
    last_error: Optional[Exception] = None
    
    while generated_checksum is None:
        try:
            with open(absolute_path, 'rb') as f:
                generated_checksum = hashlib.md5(f.read()).hexdigest()
        except Exception as error:
            last_error = error
            if checksum_attempt <= max_retries:
                # Exponential backoff: 1s, 4s, 9s, 16s, 25s
                time.sleep(retry_delay_base * checksum_attempt * checksum_attempt)
                checksum_attempt += 1
            else:
                raise
    
    return generated_checksum


def check_file_against_processed(
    file_path: str,
    file_checksum: str,
    name_dict: dict[str, str],
    resend_set: set[str]
) -> tuple[bool, bool]:
    """Check if file should be sent based on processed files records.
    
    Args:
        file_path: Path to the file being checked
        file_checksum: MD5 checksum of the file
        name_dict: Dictionary mapping checksums to file names
        resend_set: Set of checksums marked for resend
        
    Returns:
        tuple of (match_found, should_send)
        - match_found: True if checksum exists in name_dict
        - should_send: True if file should be sent (new or resend)
    """
    match_found = file_checksum in name_dict
    should_send = not match_found or file_checksum in resend_set
    
    return match_found, should_send


def process_file_hash_entry(
    source_file_struct: tuple
) -> tuple[str, str, int, bool]:
    """Process a single file hash entry from the hash thread structure.
    
    This function replicates the behavior of the original generate_file_hash
    function from dispatch.py lines 37-67.
    
    Args:
        source_file_struct: Tuple of (file_path, index_number, processed_files_list,
                          hash_dict, name_dict, resend_set)
        
    Returns:
        tuple of (file_name, file_checksum, index_number, send_file)
    """
    file_path, index_number, processed_files_list, hash_dict, name_dict, resend_set = source_file_struct
    
    file_name = os.path.abspath(file_path)
    file_checksum = generate_file_hash(file_name)
    
    # Check if file matches existing processed files
    match_found = file_checksum in name_dict
    
    # Determine if file should be sent
    send_file = False
    if not match_found:
        send_file = True
    if file_checksum in resend_set:
        send_file = True
    
    return file_name, file_checksum, index_number, send_file


def build_hash_dictionaries(
    folder_temp_processed_files_list: list[dict]
) -> tuple[dict[str, str], dict[str, str], set[str]]:
    """Build hash dictionaries from processed files list.
    
    Converts the output of generate_match_lists into dictionary format
    for efficient lookups.
    
    Args:
        folder_temp_processed_files_list: List of processed file records
        
    Returns:
        tuple of (folder_hash_dict, folder_name_dict, resend_flag_set)
        - folder_hash_dict: Maps file_name -> checksum
        - folder_name_dict: Maps checksum -> file_name
        - resend_flag_set: Set of checksums needing resend
    """
    hash_list, name_list, resend_set = generate_match_lists(folder_temp_processed_files_list)
    
    folder_hash_dict = dict(hash_list)
    folder_name_dict = dict(name_list)
    
    return folder_hash_dict, folder_name_dict, resend_set
