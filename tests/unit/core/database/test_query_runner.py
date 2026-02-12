"""Unit tests for core.database.query_runner module."""

import pytest
from core.database.query_runner import (
    ConnectionConfig,
    DatabaseConnectionProtocol,
    PyODBCConnection,
    MockConnection,
    QueryRunner,
    create_query_runner,
)


class TestConnectionConfig:
    """Tests for ConnectionConfig dataclass."""
    
    def test_create_config_with_defaults(self):
        """Test creating config with default database."""
        config = ConnectionConfig(username='user', password='pass', dsn='TEST')
        assert config.username == 'user'
        assert config.password == 'pass'
        assert config.dsn == 'TEST'
        assert config.database == 'QGPL'
    
    def test_create_config_with_custom_database(self):
        """Test creating config with custom database."""
        config = ConnectionConfig(
            username='user',
            password='pass',
            dsn='TEST',
            database='CUSTOM'
        )
        assert config.database == 'CUSTOM'
    
    def test_config_is_frozen_safe(self):
        """Test that config attributes are accessible."""
        config = ConnectionConfig(username='user', password='pass', dsn='TEST')
        # Dataclasses allow attribute access
        assert config.username == 'user'
        assert config.password == 'pass'
        assert config.dsn == 'TEST'


class TestMockConnection:
    """Tests for MockConnection class."""
    
    def test_execute_records_query(self):
        """Test that execute records queries for verification."""
        conn = MockConnection()
        conn.execute("SELECT * FROM test", ('param',))
        assert len(conn.executed_queries) == 1
        assert conn.executed_queries[0] == ("SELECT * FROM test", ('param',))
    
    def test_execute_returns_preset_results(self):
        """Test that execute returns preset results."""
        conn = MockConnection()
        conn.results = [[{'id': 1, 'name': 'test'}]]
        result = conn.execute("SELECT * FROM test")
        assert result == [{'id': 1, 'name': 'test'}]
    
    def test_execute_returns_empty_list_when_no_results(self):
        """Test that execute returns empty list when no preset results."""
        conn = MockConnection()
        result = conn.execute("SELECT * FROM test")
        assert result == []
    
    def test_multiple_executes_return_sequential_results(self):
        """Test that multiple executes return results in order."""
        conn = MockConnection()
        conn.results = [
            [{'id': 1}],
            [{'id': 2}],
            [{'id': 3}]
        ]
        assert conn.execute("SELECT 1") == [{'id': 1}]
        assert conn.execute("SELECT 2") == [{'id': 2}]
        assert conn.execute("SELECT 3") == [{'id': 3}]
    
    def test_add_results_appends_to_queue(self):
        """Test add_results method."""
        conn = MockConnection()
        conn.add_results([{'id': 1}])
        conn.add_results([{'id': 2}])
        assert conn.execute("SELECT 1") == [{'id': 1}]
        assert conn.execute("SELECT 2") == [{'id': 2}]
    
    def test_close_does_nothing(self):
        """Test that close is a no-op."""
        conn = MockConnection()
        conn.close()  # Should not raise


class TestQueryRunner:
    """Tests for QueryRunner class."""
    
    def test_run_query_delegates_to_connection(self):
        """Test that run_query delegates to the connection."""
        mock_conn = MockConnection()
        runner = QueryRunner(mock_conn)
        runner.run_query("SELECT 1")
        assert len(mock_conn.executed_queries) == 1
        assert mock_conn.executed_queries[0] == ("SELECT 1", None)
    
    def test_run_query_passes_params(self):
        """Test that run_query passes parameters to connection."""
        mock_conn = MockConnection()
        runner = QueryRunner(mock_conn)
        runner.run_query("SELECT * FROM test WHERE id = ?", (1,))
        assert mock_conn.executed_queries[0] == (
            "SELECT * FROM test WHERE id = ?", (1,)
        )
    
    def test_run_query_single_returns_first_result(self):
        """Test that run_query_single returns first result."""
        mock_conn = MockConnection()
        mock_conn.results = [[{'id': 1}, {'id': 2}]]
        runner = QueryRunner(mock_conn)
        result = runner.run_query_single("SELECT * FROM test")
        assert result == {'id': 1}
    
    def test_run_query_single_returns_none_for_empty(self):
        """Test that run_query_single returns None for empty results."""
        mock_conn = MockConnection()
        mock_conn.results = [[]]
        runner = QueryRunner(mock_conn)
        result = runner.run_query_single("SELECT * FROM test")
        assert result is None
    
    def test_close_delegates_to_connection(self):
        """Test that close delegates to connection."""
        mock_conn = MockConnection()
        runner = QueryRunner(mock_conn)
        runner.close()  # Should not raise


class TestPyODBCConnection:
    """Tests for PyODBCConnection class."""
    
    def test_init_stores_config(self):
        """Test that init stores configuration."""
        config = ConnectionConfig(
            username='user',
            password='pass',
            dsn='TEST',
            database='MYDB'
        )
        conn = PyODBCConnection(config)
        assert conn.config == config
        assert conn._connection is None
    
    def test_close_handles_none_connection(self):
        """Test that close handles None connection gracefully."""
        config = ConnectionConfig(username='user', password='pass', dsn='TEST')
        conn = PyODBCConnection(config)
        conn.close()  # Should not raise


class TestCreateQueryRunner:
    """Tests for create_query_runner factory function."""
    
    def test_creates_runner_with_config(self):
        """Test that factory creates QueryRunner with PyODBCConnection."""
        runner = create_query_runner('user', 'pass', 'TEST', 'DB')
        assert isinstance(runner, QueryRunner)
        assert isinstance(runner.connection, PyODBCConnection)
    
    def test_creates_runner_with_default_database(self):
        """Test that factory uses default database when not specified."""
        runner = create_query_runner('user', 'pass', 'TEST')
        assert isinstance(runner, QueryRunner)
        # Cast to PyODBCConnection to access config
        assert isinstance(runner.connection, PyODBCConnection)
        assert runner.connection.config.database == 'QGPL'


class TestProtocolCompliance:
    """Tests for Protocol compliance."""
    
    def test_mock_connection_satisfies_protocol(self):
        """Test that MockConnection satisfies DatabaseConnectionProtocol."""
        conn = MockConnection()
        assert isinstance(conn, DatabaseConnectionProtocol)
    
    def test_pyodbc_connection_satisfies_protocol(self):
        """Test that PyODBCConnection satisfies DatabaseConnectionProtocol."""
        config = ConnectionConfig(username='user', password='pass', dsn='TEST')
        conn = PyODBCConnection(config)
        assert isinstance(conn, DatabaseConnectionProtocol)
    
    def test_query_runner_accepts_protocol(self):
        """Test that QueryRunner accepts any protocol implementation."""
        # Using MockConnection
        mock_conn = MockConnection()
        runner1 = QueryRunner(mock_conn)
        assert runner1.connection is mock_conn
        
        # Using PyODBCConnection
        config = ConnectionConfig(username='user', password='pass', dsn='TEST')
        pyodbc_conn = PyODBCConnection(config)
        runner2 = QueryRunner(pyodbc_conn)
        assert runner2.connection is pyodbc_conn
