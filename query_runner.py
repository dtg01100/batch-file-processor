"""Legacy query_runner module - backward compatibility layer.

This module provides backward compatibility with existing code that uses
the legacy query_runner interface. New code should use core.database.query_runner.

Example legacy usage:
    runner = query_runner(username, password, hostname, driver)
    results = runner.run_arbitrary_query("SELECT * FROM table")

Example new usage:
    from core.database import create_query_runner, QueryRunner, MockConnection
    runner = create_query_runner(username, password, dsn, database)
    results = runner.run_query("SELECT * FROM table")
"""

# Import new components for backward compatibility
from core.database.query_runner import (
    create_query_runner,
    QueryRunner,
    ConnectionConfig,
    DatabaseConnectionProtocol,
    PyODBCConnection,
    MockConnection,
)

# Legacy class for backward compatibility with existing code
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
    # New API exports
    'create_query_runner',
    'QueryRunner',
    'ConnectionConfig',
    'DatabaseConnectionProtocol',
    'PyODBCConnection',
    'MockConnection',
    # Legacy class
    'query_runner',
]
