"""Query runner module with dependency injection support.

This module provides a flexible database query runner that supports
dependency injection through the Protocol pattern, enabling easy testing
and loose coupling from the underlying database implementation.
"""

import re
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

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

    This guard prevents accidental writes against AS/400 ODBC connections.
    Only statements beginning with SELECT or WITH are allowed.
    """
    normalized = _strip_sql_leading_comments(query)
    if not normalized:
        raise ValueError("ODBC query must not be empty")

    keyword_match = re.match(r"([A-Za-z]+)", normalized)
    first_keyword = keyword_match.group(1).upper() if keyword_match else ""

    if first_keyword in _READ_ONLY_SQL_START:
        return

    if first_keyword in _MUTATING_SQL_START:
        raise ValueError(
            "Mutating SQL is forbidden for AS400 ODBC query paths. "
            f"Blocked statement starting with {first_keyword!r}."
        )

    raise ValueError(
        "Only read-only SELECT/WITH SQL is allowed for AS400 ODBC query paths. "
        f"Blocked statement starting with {first_keyword or 'unknown token'!r}."
    )


@dataclass
class ConnectionConfig:
    """Configuration for database connection.

    Attributes:
        username: Database username
        password: Database password
        dsn: AS/400 hostname or IP address (SYSTEM= in the ODBC connection string)
        database: Database/library name (default: QGPL)
        odbc_driver: ODBC driver name (default: IBM i Access ODBC Driver 64-bit)
    """

    username: str
    password: str
    dsn: str
    database: str = "QGPL"
    odbc_driver: str = "IBM i Access ODBC Driver 64-bit"


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


class PyODBCConnection:
    """Real pyodbc connection implementation.

    This class wraps pyodbc connection functionality and provides
    a clean interface for executing queries.
    """

    def __init__(self, config: ConnectionConfig):
        """Initialize the connection with configuration.

        Args:
            config: Connection configuration containing credentials and DSN
        """
        self.config = config
        self._connection = None
        self._connection_id = uuid.uuid4().hex[:8]
        self._logger = get_logger(__name__)

    def _connect(self):
        """Establish the database connection.

        Returns:
            pyodbc connection object

        Raises:
            ConnectionError: If the database connection cannot be established.
        """
        import pyodbc

        start_time = time.perf_counter()
        conn_str = (
            f"DRIVER={{{self.config.odbc_driver}}};"
            f"SYSTEM={self.config.dsn};"
            f"DATABASE={self.config.database};"
            f"UID={self.config.username};"
            f"PWD={self.config.password}"
        )
        try:
            self._connection = pyodbc.connect(conn_str)
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_database_call(
                self._logger,
                "connect",
                table=self.config.database,
                duration_ms=duration_ms,
                success=True,
                connection_id=self._connection_id,
            )
        except pyodbc.Error as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_database_call(
                self._logger,
                "connect",
                table=self.config.database,
                duration_ms=duration_ms,
                success=False,
                error=exc,
                connection_id=self._connection_id,
            )
            raise ConnectionError(
                f"Failed to connect to database SYSTEM={self.config.dsn!r} "
                f"DRIVER={self.config.odbc_driver!r}: {exc}"
            ) from exc
        return self._connection

    def _ensure_connection(self):
        """Ensure a connection is established."""
        if self._connection is None:
            self._connect()
        return self._connection

    def execute(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Optional query parameters for parameterized queries

        Returns:
            List of dictionaries with column names as keys
        """
        assert_read_only_sql(query)
        start_time = time.perf_counter()

        # Extract query type and table for logging
        query_type = self._extract_query_type(query)
        table = self._extract_table_name(query)

        conn = self._ensure_connection()
        cursor = conn.cursor()

        try:
            if params is not None:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Statements like UPDATE/INSERT/DELETE may not return rows.
            # In that case cursor.description is None and fetchall() can raise
            # for drivers that enforce result-set semantics.
            if not cursor.description:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_database_call(
                    self._logger,
                    "execute",
                    query_type=query_type,
                    table=table,
                    duration_ms=duration_ms,
                    success=True,
                    connection_id=self._connection_id,
                )
                return []

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

            duration_ms = (time.perf_counter() - start_time) * 1000
            log_database_call(
                self._logger,
                "execute",
                query_type=query_type,
                table=table,
                row_count=len(results),
                duration_ms=duration_ms,
                success=True,
                connection_id=self._connection_id,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_database_call(
                self._logger,
                "execute",
                query_type=query_type,
                table=table,
                duration_ms=duration_ms,
                success=False,
                error=exc,
                connection_id=self._connection_id,
            )
            raise
        finally:
            cursor.close()

        return results

    def _extract_query_type(self, query: str) -> str | None:
        """Extract SQL query type from query string."""
        import re

        match = re.match(r"\s*(\w+)", query.strip())
        return match.group(1).upper() if match else None

    def _extract_table_name(self, query: str) -> str | None:
        """Extract table name from SQL query string."""
        import re

        # Match FROM <table> or JOIN <table> or INTO <table> or UPDATE <table>
        patterns = [
            r'\bFROM\s+([\w`\[\]"]+)',  # SELECT FROM table
            r'\bJOIN\s+([\w`\[\]"]+)',  # JOIN table
            r'\bINTO\s+([\w`\[\]"]+)',  # INSERT INTO table
            r'\bUPDATE\s+([\w`\[\]"]+)',  # UPDATE table
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                table = match.group(1).strip('`[]"')
                return table
        return None

    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection:
            log_database_call(
                self._logger,
                "close",
                table=self.config.database,
                success=True,
                connection_id=self._connection_id,
            )
            self._connection.close()
            self._connection = None


class MockConnection:
    """Mock connection for testing.

    This class provides a mock implementation that records queries
    and returns preset results for testing purposes.
    """

    def __init__(self):
        """Initialize the mock connection with empty state."""
        self.executed_queries: list[tuple[str, Optional[tuple]]] = []
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

    def __init__(self, db_path: str = ":memory:"):
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

    def __init__(self, connection: DatabaseConnectionProtocol):
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

    def run_query_single(self, query: str, params: tuple = None) -> Optional[dict]:
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
    odbc_driver: str = "IBM i Access ODBC Driver 64-bit",
) -> QueryRunner:
    """Create a QueryRunner with real pyodbc connection.

    This factory function provides backward compatibility with
    existing code that creates query runners directly.

    Args:
        username: Database username
        password: Database password
        dsn: Data Source Name for ODBC connection
        database: Database name (default: QGPL)
        odbc_driver: ODBC driver name (default: IBM i Access ODBC Driver 64-bit)

    Returns:
        QueryRunner instance with PyODBCConnection
    """
    config = ConnectionConfig(username, password, dsn, database, odbc_driver)
    connection = PyODBCConnection(config)
    return QueryRunner(connection)
