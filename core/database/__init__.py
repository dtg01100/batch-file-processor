"""
Database module - framework-agnostic database access layer.

Uses Python's built-in sqlite3 module, no Qt dependency.

Usage:
    from core.database import DatabaseManager, DatabaseConnection, Table
"""

from .connection import DatabaseConnection, Table, connect, connect_memory
from .manager import DatabaseManager
from .schema import create_database

__all__ = [
    "DatabaseConnection",
    "Table",
    "DatabaseManager",
    "connect",
    "connect_memory",
    "create_database",
]
