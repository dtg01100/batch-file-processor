"""Query runner module with dependency injection support.

This module provides a flexible database query runner that supports
dependency injection through the Protocol pattern, enabling easy testing
and loose coupling from the underlying database implementation.
"""

from typing import Protocol, runtime_checkable, Any, Optional
from dataclasses import dataclass
import contextlib


@dataclass
class ConnectionConfig:
    """Configuration for database connection.
    
    Attributes:
        username: Database username
        password: Database password
        dsn: Data Source Name for ODBC connection
        database: Database name (default: QGPL)
    """
    username: str
    password: str
    dsn: str
    database: str = 'QGPL'


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
    
    def _connect(self):
        """Establish the database connection.
        
        Returns:
            pyodbc connection object
        """
        import pyodbc
        conn_str = (
            f"DSN={self.config.dsn};"
            f"DATABASE={self.config.database};"
            f"UID={self.config.username};"
            f"PWD={self.config.password}"
        )
        self._connection = pyodbc.connect(conn_str)
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
        conn = self._ensure_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Get column names from cursor description
        columns = [column[0] for column in cursor.description] if cursor.description else []
        
        # Convert rows to dictionaries
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            results.append(row_dict)
        
        cursor.close()
        return results
    
    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection:
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
        pass
    
    def add_results(self, results: list[dict]) -> None:
        """Add preset results to be returned by execute.
        
        Args:
            results: List of dictionaries to return on next execute call
        """
        self.results.append(results)


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
    
    def close(self) -> None:
        """Close the underlying connection."""
        self.connection.close()


def create_query_runner(
    username: str,
    password: str,
    dsn: str,
    database: str = 'QGPL'
) -> QueryRunner:
    """Create a QueryRunner with real pyodbc connection.
    
    This factory function provides backward compatibility with
    existing code that creates query runners directly.
    
    Args:
        username: Database username
        password: Database password
        dsn: Data Source Name for ODBC connection
        database: Database name (default: QGPL)
        
    Returns:
        QueryRunner instance with PyODBCConnection
    """
    config = ConnectionConfig(username, password, dsn, database)
    connection = PyODBCConnection(config)
    return QueryRunner(connection)
