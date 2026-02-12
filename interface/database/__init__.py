"""Database module for interface layer.

This module provides database-related components for the
batch file processor application.
"""

from interface.database.database_obj import (
    DatabaseObj,
    DatabaseConnectionProtocol,
    TableProtocol,
)

__all__ = [
    "DatabaseObj",
    "DatabaseConnectionProtocol",
    "TableProtocol",
]
