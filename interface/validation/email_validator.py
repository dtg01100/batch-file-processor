"""Email validation utilities.

This module provides email validation functions and the EmailValidator class
for validating email addresses with configurable patterns.

The functions are pure and have no external dependencies, making them
easy to test and reuse.
"""

import re
from typing import Optional, Tuple, List


# Default email regex pattern
DEFAULT_EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'


def validate_email(email: str, pattern: Optional[str] = None) -> bool:
    """Validate an email address format.
    
    Uses a regex pattern to check if the email address has a valid format.
    Does not check if the email actually exists.
    
    Args:
        email: Email address to validate
        pattern: Optional custom regex pattern to use
        
    Returns:
        True if valid format, False otherwise
        
    Example:
        >>> validate_email("test@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    if not email:
        return False
    
    regex = pattern or DEFAULT_EMAIL_PATTERN
    return bool(re.fullmatch(regex, email))


def validate_email_list(
    emails: str, 
    separator: str = ", ", 
    pattern: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Validate a list of email addresses.
    
    Splits the email string by the separator and validates each address.
    
    Args:
        emails: String of email addresses separated by separator
        separator: Separator between addresses (default: ", ")
        pattern: Optional custom regex pattern to use
        
    Returns:
        Tuple of (all_valid, invalid_addresses)
        - all_valid: True if all emails are valid
        - invalid_addresses: List of invalid email addresses
        
    Example:
        >>> validate_email_list("a@test.com, b@test.com")
        (True, [])
        >>> validate_email_list("a@test.com, invalid")
        (False, ['invalid'])
    """
    if not emails:
        return True, []
    
    email_list = [e.strip() for e in emails.split(separator)]
    invalid = [e for e in email_list if not validate_email(e, pattern)]
    
    return len(invalid) == 0, invalid


def normalize_email(email: str) -> str:
    """Normalize an email address.
    
    Converts to lowercase and strips whitespace.
    
    Args:
        email: Email to normalize
        
    Returns:
        Normalized email string
        
    Example:
        >>> normalize_email("  TEST@EXAMPLE.COM  ")
        'test@example.com'
    """
    if not email:
        return ""
    return email.strip().lower()


class EmailValidator:
    """Email validation with configurable patterns.
    
    Provides an object-oriented interface to email validation with
    a configurable pattern that can be set once and reused.
    
    Attributes:
        pattern: The regex pattern used for validation
    
    Example:
        >>> validator = EmailValidator()
        >>> validator.validate("test@example.com")
        True
        >>> validator.validate_list("a@test.com; b@test.com", separator="; ")
        (True, [])
    """
    
    def __init__(self, pattern: Optional[str] = None):
        """Initialize the email validator.
        
        Args:
            pattern: Optional custom regex pattern for validation.
                     If not provided, uses DEFAULT_EMAIL_PATTERN.
        """
        self.pattern = pattern or DEFAULT_EMAIL_PATTERN
    
    def validate(self, email: str) -> bool:
        """Validate a single email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid format, False otherwise
        """
        return validate_email(email, self.pattern)
    
    def validate_list(
        self, 
        emails: str, 
        separator: str = "; "
    ) -> Tuple[bool, List[str]]:
        """Validate a list of email addresses.
        
        Args:
            emails: String of email addresses
            separator: Separator between addresses (default: "; ")
            
        Returns:
            Tuple of (is_valid, invalid_emails)
        """
        return validate_email_list(emails, separator, self.pattern)
    
    def normalize(self, email: str) -> str:
        """Normalize an email address.
        
        Args:
            email: Email to normalize
            
        Returns:
            Lowercase, stripped email
        """
        return normalize_email(email)
    
    def validate_and_normalize(self, email: str) -> Tuple[bool, str]:
        """Validate and normalize an email address.
        
        Args:
            email: Email address to validate and normalize
            
        Returns:
            Tuple of (is_valid, normalized_email)
        """
        normalized = self.normalize(email)
        is_valid = self.validate(normalized)
        return is_valid, normalized
    
    def filter_valid(self, emails: List[str]) -> List[str]:
        """Filter a list to only include valid emails.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of valid email addresses
        """
        return [e for e in emails if self.validate(e)]
    
    def filter_invalid(self, emails: List[str]) -> List[str]:
        """Filter a list to only include invalid emails.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of invalid email addresses
        """
        return [e for e in emails if not self.validate(e)]
