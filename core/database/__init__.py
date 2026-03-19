"""Core database module.

This module provides database abstraction components including:
- ConnectionConfig: Dataclass for database connection configuration
- DatabaseConnectionProtocol: Protocol for database connection abstraction
- QueryRunner: Main query runner with injectable connection
- MockConnection: Mock connection for testing
- query_runner: Legacy class for backward compatibility (DEPRECATED)
- LegacyQueryRunnerAdapter: Adapter for migrating from legacy tuple-based API
"""

import warnings

from core.database.query_runner import (
    ConnectionConfig,
    DatabaseConnectionProtocol,
    MockConnection,
    PyODBCConnection,
    QueryRunner,
    SQLiteConnection,
    assert_read_only_sql,
    create_query_runner,
)


class LegacyQueryRunnerAdapter:
    """Adapter that provides legacy tuple-based API on top of QueryRunner.

    This adapter allows incremental migration from the legacy query_runner
    class (which returns tuples) to the new QueryRunner (which returns dicts).
    It wraps a QueryRunner and converts dict results back to tuples.

    .. deprecated:: 1.0
        This adapter is a migration aid. Update code to use dict results
        from QueryRunner directly, then remove this adapter.

    Example migration:
        OLD:
            from core.database import query_runner
            qr = query_runner(user, pass, host, driver)
            results = qr.run_arbitrary_query("SELECT ...")

        NEW (with adapter):
            from core.database import create_query_runner, LegacyQueryRunnerAdapter
            runner = create_query_runner(user, pass, dsn=host)
            qr = LegacyQueryRunnerAdapter(runner)
            results = qr.run_arbitrary_query("SELECT ...")

        NEW (direct, preferred):
            from core.database import create_query_runner
            runner = create_query_runner(user, pass, dsn=host)
            results = runner.run_query("SELECT ...")  # Returns list[dict]
    """

    def __init__(self, runner: QueryRunner):
        """Initialize the adapter.

        Args:
            runner: QueryRunner instance to wrap
        """
        self._runner = runner
        # Expose connection for legacy code that accesses it directly
        self.connection = runner.connection

    def run_arbitrary_query(self, query_string: str, params: tuple = None) -> list:
        """Execute query and return results as tuples (legacy format).

        Args:
            query_string: SQL query to execute
            params: Optional query parameters

        Returns:
            List of tuples (legacy format)
        """
        results = self._runner.run_query(query_string, params)
        if not results:
            return []
        # Convert list[dict] to list[tuple] for backward compatibility
        if isinstance(results[0], dict):
            return [tuple(row.values()) for row in results]
        return results

    def run_query(self, query: str, params: tuple = None) -> list:
        """Execute query and return results as tuples (legacy format).

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of tuples (legacy format)
        """
        return self.run_arbitrary_query(query, params)


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

        # Create a new-style runner internally, passing driver through
        self._runner = create_query_runner(
            username=username,
            password=password,
            dsn=as400_hostname,
            database="QGPL",
            odbc_driver=driver,
        )

        # Legacy attributes for backward compatibility
        self.connection = None  # Populated lazily on first query
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
        assert_read_only_sql(query_string)

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
    "SQLiteConnection",
    "create_query_runner",
    "query_runner",
    "LegacyQueryRunnerAdapter",
]
