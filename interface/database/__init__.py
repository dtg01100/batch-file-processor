"""Database module for interface layer.

DEPRECATED: All database access has been moved to backend.database.
This module now re-exports from backend.database for backward compatibility.

Update your imports:
    OLD: from backend.database import DatabaseObj
    NEW: from backend.database import DatabaseObj
"""

# Re-export from backend for backward compatibility
from backend.database import (
    DatabaseConnectionProtocol,
    DatabaseObj,
    TableProtocol,
    sqlite_wrapper,
)

__all__ = [
    "DatabaseObj",
    "DatabaseConnectionProtocol",
    "TableProtocol",
    "sqlite_wrapper",
]
