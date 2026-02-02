"""
Database manager module for interface.

This module re-exports the framework-agnostic database classes from core.database.
Maintains backwards compatibility for existing imports.

Note: The Qt-based implementation has been replaced with sqlite3. If Qt thread
safety is required, consider using QThread workers to call database operations.
"""

from core.database import (
    DatabaseConnection,
    DatabaseManager,
    Table,
    connect,
    connect_memory,
)

__all__ = [
    "DatabaseConnection",
    "DatabaseManager",
    "Table",
    "connect",
    "connect_memory",
]
