"""Core database module.

This module provides database abstraction components including:
- ConnectionConfig: Dataclass for database connection configuration
- DatabaseConnectionProtocol: Protocol for database connection abstraction
- QueryRunner: Main query runner with injectable connection
- MockConnection: Mock connection for testing
"""

from core.database.query_runner import (
    ConnectionConfig,
    DatabaseConnectionProtocol,
    PyODBCConnection,
    MockConnection,
    QueryRunner,
    create_query_runner,
)

__all__ = [
    'ConnectionConfig',
    'DatabaseConnectionProtocol',
    'PyODBCConnection',
    'MockConnection',
    'QueryRunner',
    'create_query_runner',
]
