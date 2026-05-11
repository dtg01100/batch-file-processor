"""Core exceptions for the batch file processor.

This module defines custom exceptions used across the codebase.
"""


class CustomerLookupError(Exception):
    """Raised when a customer lookup fails.

    This exception is typically raised during EDI conversion when
    a customer cannot be found in the order history database.
    """


class BackendSendError(Exception):
    """Raised when a backend send operation fails.

    This exception is used by backend implementations to signal
    that a file could not be sent to the destination.
    """


class DataIntegrityError(Exception):
    """Raised when data integrity checks fail.

    This exception is used when validation of data consistency
    reveals mismatches, such as line counts or record counts
    not matching expected values.
    """
