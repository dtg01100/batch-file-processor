"""Backend module for batch file processor.

This module contains the core backend services including:
- Database access and management
- File operations
- FTP/SMTP clients
- Remote filesystem operations
"""

from backend.database import (
    Database,
    DatabaseConnectionProtocol,
    DatabaseObj,
    Table,
    TableProtocol,
    connect,
)

__all__ = [
    "Database",
    "Table",
    "connect",
    "DatabaseObj",
    "DatabaseConnectionProtocol",
    "TableProtocol",
    "file_operations",
    "ftp_client",
    "smtp_client",
    "protocols",
]
