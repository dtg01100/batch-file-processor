"""Core database module.

This module provides database abstraction components including:
- ConnectionConfig: Dataclass for database connection configuration
- DatabaseConnectionProtocol: Protocol for database connection abstraction
- QueryRunner: Main query runner with injectable connection
- MockConnection: Mock connection for testing
- query_runner: Legacy class for backward compatibility
"""

from core.database.query_runner import (
    ConnectionConfig,
    DatabaseConnectionProtocol,
    PyODBCConnection,
    MockConnection,
    QueryRunner,
    create_query_runner,
)

# Legacy query_runner class for backward compatibility
# This maintains the original interface for existing code
class query_runner:
    """Legacy query_runner class for backward compatibility.
    
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
        
        Args:
            username: Database username
            password: Database password
            as400_hostname: AS/400 hostname (used as DSN)
            driver: ODBC driver name (not used in new implementation)
        """
        # Create a new-style runner internally
        self._runner = create_query_runner(
            username=username,
            password=password,
            dsn=as400_hostname,
            database='QGPL'
        )
        
        # Legacy attributes for backward compatibility
        self.connection = self._runner.connection._connection
        self.username = ''
        self.password = ''
        self.host = ''
        self._driver = driver
    
    def run_arbitrary_query(self, query_string: str) -> list:
        """Execute an arbitrary query and return results.
        
        Args:
            query_string: SQL query to execute
            
        Returns:
            List of query results (legacy format as tuples)
        """
        # Use the new runner's connection directly for legacy tuple format
        if self.connection is None:
            self.connection = self._runner.connection._connect()
        
        cursor = self.connection.cursor()
        query_results = cursor.execute(query_string)
        query_return_list = []
        for entry in query_results:
            query_return_list.append(entry)
        return query_return_list


__all__ = [
    'ConnectionConfig',
    'DatabaseConnectionProtocol',
    'PyODBCConnection',
    'MockConnection',
    'QueryRunner',
    'create_query_runner',
    'query_runner',
]
