"""Core database module.

This module provides database abstraction components including:
- DatabaseConnectionProtocol: Protocol for database connection abstraction
- QueryRunner: Main query runner with injectable connection
- MockConnection: Mock connection for testing
- SQLiteConnection: SQLite database connection implementation
- create_query_runner: Factory function to create QueryRunner instances
"""

from core.database.query_runner import (
    DatabaseConnectionProtocol,
    MockConnection,
    QueryRunner,
    SQLiteConnection,
    create_query_runner,
)

__all__ = [
    "DatabaseConnectionProtocol",
    "MockConnection",
    "QueryRunner",
    "SQLiteConnection",
    "create_query_runner",
]
