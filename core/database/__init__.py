"""Core database module.

This module provides database abstraction components including:
- ConnectionConfig: Dataclass for database connection configuration
- DatabaseConnectionProtocol: Protocol for database connection abstraction
- QueryRunner: Main query runner with injectable connection
- MockConnection: Mock connection for testing
- query_runner: Legacy class for backward compatibility (DEPRECATED)
"""

import warnings

from core.database.query_runner import (
    ConnectionConfig,
    DatabaseConnectionProtocol,
    MockConnection,
    PyODBCConnection,
    QueryRunner,
    create_query_runner,
)


# Legacy query_runner class for backward compatibility
# This maintains the original interface for existing code
class query_runner:
    """Legacy query_runner class for backward compatibility.

    .. deprecated:: 1.0
        Use `QueryRunner` from `core.database.query_runner` instead.
        This class will be removed in version 2.0.

        Migration:
            OLD: from core.database import query_runner
                 qr = query_runner(username, password, hostname, driver)

            NEW: from core.database import QueryRunner, create_query_runner
                 qr = create_query_runner(username, password, dsn=hostname)

    This class maintains the original interface for existing code.
    New code should use QueryRunner from core.database.query_runner.

    Attributes:
        connection: The pyodbc connection object
        username: Username (legacy, not used)
        password: Password (legacy, not used)
        host: Host (legacy, not used)
    """

    def __init__(self, username: str, password: str, as400_hostname: str, driver: str):
        """Initialize the legacy query runner.

        .. deprecated:: 1.0
            Use `create_query_runner()` instead.

        Args:
            username: Database username
            password: Database password
            as400_hostname: AS/400 hostname (used as DSN)
            driver: ODBC driver name (not used in new implementation)
        """
        warnings.warn(
            "query_runner is deprecated. Use QueryRunner or create_query_runner() "
            "from core.database instead. This class will be removed in version 2.0.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Create a new-style runner internally
        self._runner = create_query_runner(
            username=username, password=password, dsn=as400_hostname, database="QGPL"
        )

        # Legacy attributes for backward compatibility
        self.connection = self._runner.connection._connection
        self.username = ""
        self.password = ""
        self.host = ""
        self._driver = driver

    def run_query(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results as list of dicts.

        This method implements the QueryRunnerProtocol interface
        for compatibility with core.edi.inv_fetcher.InvFetcher.

        Args:
            query: SQL query string
            params: Optional query parameters (not used in legacy implementation)

        Returns:
            List of dictionaries representing query results
        """
        results = self.run_arbitrary_query(query)
        # Convert tuple results to dicts for protocol compatibility
        if results and isinstance(results[0], tuple):
            # Return as list of dicts with numeric keys for simplicity
            return [dict(enumerate(row)) for row in results]
        return results

    def run_arbitrary_query(self, query_string: str, params: tuple = None) -> list:
        """Execute an arbitrary query and return results.

        Args:
            query_string: SQL query to execute
            params: Optional query parameters for parameterized queries

        Returns:
            List of query results (legacy format as tuples)
        """
        # Use the new runner's connection directly for legacy tuple format
        if self.connection is None:
            self.connection = self._runner.connection._connect()

        cursor = self.connection.cursor()
        if params is not None:
            query_results = cursor.execute(query_string, params)
        else:
            query_results = cursor.execute(query_string)
        query_return_list = []
        for entry in query_results:
            query_return_list.append(entry)
        return query_return_list


__all__ = [
    "ConnectionConfig",
    "DatabaseConnectionProtocol",
    "PyODBCConnection",
    "MockConnection",
    "QueryRunner",
    "create_query_runner",
    "query_runner",
]
