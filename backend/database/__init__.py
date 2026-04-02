"""Backend database module.

This module provides the central database access layer for the batch file processor.
All database interactions should go through this module for a single source of truth.

Components:
- Database: SQLite database connection and table access
- Table: Table-level CRUD operations with boolean handling
- DatabaseObj: High-level database object for folder configuration management
- DatabaseConnectionProtocol: Protocol for database connection abstraction
- TableProtocol: Protocol for database table operations

Usage:
    from backend.database import DatabaseObj, Database

    # High-level API
    db_obj = DatabaseObj(database_path, database_version, config_folder, platform)
    folder = db_obj.folders_table.find_one(id=1)

    # Low-level API
    db = Database.connect("/path/to/database.db")
    table = db["table_name"]
    rows = table.find(column="value")
    db.close()
"""

from backend.database.database_obj import (
    DatabaseConnectionProtocol,
    DatabaseObj,
    TableProtocol,
)
from backend.database.sqlite_wrapper import Database, Table, connect

__all__ = [
    "Database",
    "Table",
    "connect",
    "DatabaseObj",
    "DatabaseConnectionProtocol",
    "TableProtocol",
]
