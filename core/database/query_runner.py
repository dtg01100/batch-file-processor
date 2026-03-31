"""Query runner module with dependency injection support.

This module provides a flexible database query runner that supports
dependency injection through the Protocol pattern, enabling easy testing
and loose coupling from the underlying database implementation.
"""

import re
from typing import Protocol, runtime_checkable

from core.structured_logging import get_logger, log_database_call

_READ_ONLY_SQL_START = {"SELECT", "WITH"}
_MUTATING_SQL_START = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "ALTER",
    "DROP",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "CALL",
    "EXEC",
    "EXECUTE",
}


def _strip_sql_leading_comments(query: str) -> str:
    """Strip leading SQL comments/whitespace for statement classification."""
    remaining = query or ""

    while True:
        stripped = remaining.lstrip()
        if not stripped:
            return ""

        if stripped.startswith("--"):
            newline_index = stripped.find("\n")
            if newline_index == -1:
                return ""
            remaining = stripped[newline_index + 1 :]
            continue

        if stripped.startswith("/*"):
            end_index = stripped.find("*/")
            if end_index == -1:
                return ""
            remaining = stripped[end_index + 2 :]
            continue

        return stripped


def assert_read_only_sql(query: str) -> None:
    """Raise ValueError when SQL is not read-only.

    This guard prevents accidental writes against database connections.
    Only statements beginning with SELECT or WITH are allowed.
    """
    normalized = _strip_sql_leading_comments(query)
    if not normalized:
        raise ValueError("Query must not be empty")

    keyword_match = re.match(r"([A-Za-z]+)", normalized)
    first_keyword = keyword_match.group(1).upper() if keyword_match else ""

    if first_keyword in _READ_ONLY_SQL_START:
        return

    if first_keyword in _MUTATING_SQL_START:
        raise ValueError(
            "Mutating SQL is forbidden. "
            f"Blocked statement starting with {first_keyword!r}."
        )

    raise ValueError(
        "Only read-only SELECT/WITH SQL is allowed. "
        f"Blocked statement starting with {first_keyword or 'unknown token'!r}."
    )


@runtime_checkable
class DatabaseConnectionProtocol(Protocol):
    """Protocol for database connection abstraction.

    Implementations should provide query execution capabilities
    with proper resource management.
    """

    def execute(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of dictionaries representing query results

        """
        ...

    def close(self) -> None:
        """Close the database connection."""
        ...


class MockConnection:
    """Mock connection for testing.

    This class provides a mock implementation that records queries
    and returns preset results for testing purposes.
    """

    def __init__(self) -> None:
        """Initialize the mock connection with empty state."""
        self.executed_queries: list[tuple[str, tuple | None]] = []
        self.results: list[list[dict]] = []

    def execute(self, query: str, params: tuple = None) -> list[dict]:
        """Record the query and return preset results.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Preset results from the results queue, or empty list if none

        """
        self.executed_queries.append((query, params))
        return self.results.pop(0) if self.results else []

    def close(self) -> None:
        """Mock close - no operation performed."""

    def add_results(self, results: list[dict]) -> None:
        """Add preset results to be returned by execute.

        Args:
            results: List of dictionaries to return on next execute call

        """
        self.results.append(results)


class SQLiteConnection:
    """SQLite connection for testing.

    This class provides a SQLite-based implementation for testing
    that implements the DatabaseConnectionProtocol. It allows tests
    to use a real database with pre-populated test data instead of mocks.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialize the SQLite connection.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory DB

        """
        self.db_path = db_path
        self._connection = None

    def _connect(self):
        """Establish the database connection.

        Returns:
            sqlite3 connection object

        """
        import sqlite3

        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def execute(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Optional query parameters for parameterized queries

        Returns:
            List of dictionaries with column names as keys

        """
        import sqlite3

        # Allow CREATE TABLE and INSERT for test setup, but not in production code paths
        # This is test-only code
        conn = self._connect()
        cursor = conn.cursor()

        try:
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names from cursor description
            columns = (
                [column[0] for column in cursor.description]
                if cursor.description
                else []
            )

            # Convert rows to dictionaries
            results = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                results.append(row_dict)
        except sqlite3.Error:
            results = []
        finally:
            cursor.close()

        return results

    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def executescript(self, script: str) -> None:
        """Execute a SQL script (for test setup).

        Args:
            script: SQL script to execute

        """

        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.executescript(script)
            conn.commit()
        finally:
            cursor.close()


class QueryRunner:
    """Main query runner with injectable connection.

    This class provides a high-level interface for running database
    queries with support for dependency injection of connections.
    """

    def __init__(self, connection: DatabaseConnectionProtocol) -> None:
        """Initialize with a database connection.

        Args:
            connection: Any object implementing DatabaseConnectionProtocol

        """
        self.connection = connection

    def run_query(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of dictionaries representing query results

        """
        assert_read_only_sql(query)
        return self.connection.execute(query, params)

    def run_query_single(self, query: str, params: tuple = None) -> dict | None:
        """Execute a query and return single result.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            First result as dictionary, or None if no results

        """
        results = self.run_query(query, params)
        return results[0] if results else None

    # Legacy alias for backward compatibility
    def run_arbitrary_query(self, query: str, params: tuple = None) -> list[dict]:
        """Legacy alias for run_query to maintain backward compatibility.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of dictionaries representing query results

        """
        return self.run_query(query, params)

    def close(self) -> None:
        """Close the underlying connection."""
        self.connection.close()


def create_query_runner(
    username: str,
    password: str,
    dsn: str,
    database: str = "QGPL",
    ssh_key_filename: str | None = None,
) -> QueryRunner:
    """Create a QueryRunner with a DB2SSH connection.

    Args:
        username: SSH username for IBM i
        password: SSH password for IBM i
        dsn: IBM i hostname or IP address
        database: Database/library name (default: QGPL)
        ssh_key_filename: Path to SSH private key file (optional)

    Returns:
        QueryRunner instance with DB2SSHConnection

    """
    from adapters.db2ssh.connection import DB2SSHConnection, DB2SSHConnectionConfig

    config = DB2SSHConnectionConfig(
        host=dsn,
        user=username,
        password=password,
        database=database,
        key_filename=ssh_key_filename if ssh_key_filename else None,
    )
    connection = DB2SSHConnection(config)
    return QueryRunner(connection)


def create_query_runner_from_settings(
    settings_dict: dict,
    database: str = "QGPL",
) -> QueryRunner:
    """Create a QueryRunner from a settings dictionary.

    Convenience wrapper that extracts AS400 connection parameters
    from the standard settings dictionary format used throughout
    the batch file processor.

    Args:
        settings_dict: Application settings dictionary containing:
            - as400_username: SSH username for IBM i
            - as400_password: SSH password for IBM i
            - as400_address: IBM i hostname or IP address
            - ssh_key_filename: Optional path to SSH private key
        database: Database/library name (default: QGPL)

    Returns:
        QueryRunner instance with DB2SSHConnection

    Raises:
        ValueError: If required settings are missing

    Example:
        >>> runner = create_query_runner_from_settings(settings_dict)
        >>> results = runner.run_query("SELECT * FROM F0001", {})

    """
    required_keys = ["as400_username", "as400_password", "as400_address"]
    missing_keys = [key for key in required_keys if not settings_dict.get(key)]
    if missing_keys:
        raise ValueError(
            f"Missing required database settings: {', '.join(missing_keys)}"
        )

    ssh_key_filename = settings_dict.get("ssh_key_filename", "")

    return create_query_runner(
        username=settings_dict["as400_username"],
        password=settings_dict["as400_password"],
        dsn=settings_dict["as400_address"],
        database=database,
        ssh_key_filename=ssh_key_filename if ssh_key_filename else None,
    )
