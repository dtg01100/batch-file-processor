"""
Validation utilities module for interface.py refactoring.

This module contains email validation and other input validation functions.
Refactored from interface.py validation functions (lines 1460-1550).
"""

import re
from typing import Optional, Tuple
import os


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_folder_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate folder path exists and is accessible.
    
    Args:
        path: Folder path to validate.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    if not path:
        return False, "Path is empty"
    
    if not os.path.exists(path):
        return False, f"Path does not exist: {path}"
    
    if not os.access(path, os.R_OK | os.W_OK):
        return False, f"Path is not accessible: {path}"
    
    return True, None


def validate_ftp_host(host: str) -> bool:
    """
    Validate FTP host format.
    
    Args:
        host: FTP host to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    if not host:
        return False
    
    # Pattern for hostname or IP address
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$|^(\d{1,3}\.){3}\d{1,3}$'
    return bool(re.match(pattern, host))


def validate_port(port: int) -> bool:
    """
    Validate port number.
    
    Args:
        port: Port number to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    return isinstance(port, int) and 1 <= port <= 65535


def validate_positive_integer(value: int) -> bool:
    """
    Validate positive integer.
    
    Args:
        value: Value to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    return isinstance(value, int) and value > 0


def validate_non_negative_integer(value: int) -> bool:
    """
    Validate non-negative integer.
    
    Args:
        value: Value to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    return isinstance(value, int) and value >= 0


def validate_folder_exists(path: str) -> bool:
    """
    Check if a folder path exists.
    
    Args:
        path: Folder path to check.
        
    Returns:
        True if exists, False otherwise.
    """
    if not path:
        return False
    return os.path.isdir(path)


def sanitize_input(value: str, max_length: int = 255) -> str:
    """
    Sanitize user input.
    
    Args:
        value: Input value to sanitize.
        max_length: Maximum allowed length.
        
    Returns:
        Sanitized string.
    """
    if value is None:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(value))
    
    # Limit length
    return sanitized[:max_length]


def validate_numeric(value: str, allow_decimal: bool = False) -> bool:
    """
    Validate that a string is numeric.
    
    Args:
        value: String to validate.
        allow_decimal: Whether to allow decimal points.
        
    Returns:
        True if valid, False otherwise.
    """
    if not value:
        return False
    
    if allow_decimal:
        try:
            float(value)
            return True
        except ValueError:
            return False
    else:
        try:
            int(value)
            return True
        except ValueError:
            return False


def validate_boolean(value: str) -> Optional[bool]:
    """
    Validate and convert a string to boolean.
    
    Args:
        value: String value to validate.
        
    Returns:
        Boolean or None if invalid.
    """
    if not value:
        return None
    
    value_lower = value.lower()
    if value_lower in ('true', '1', 'yes', 'on'):
        return True
    elif value_lower in ('false', '0', 'no', 'off'):
        return False
    return None


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    if not url:
        return False
    
    pattern = r'^https?://[^\s]+$'
    return bool(re.match(pattern, url))


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address format.
    
    Args:
        ip: IP address to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    if not ip:
        return False
    
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    # Check each octet is in valid range
    octets = ip.split('.')
    for octet in octets:
        if int(octet) > 255:
            return False
    
    return True
