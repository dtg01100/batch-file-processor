"""Core exceptions for the batch file processor.

This module defines custom exceptions used across the codebase.
"""


class CustomerLookupError(Exception):
    """Raised when a customer lookup fails.

    This exception is typically raised during EDI conversion when
    a customer cannot be found in the order history database.
    """
