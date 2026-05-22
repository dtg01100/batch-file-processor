"""Unit tests for DB2SSHConnection adapter."""

from unittest.mock import MagicMock, patch

import pytest

from adapters.db2ssh import Connection as VendoredConnection
from adapters.db2ssh import Cursor as VendoredCursor
from adapters.db2ssh.connection import (
    DB2SSHConnection,
    DB2SSHConnectionConfig,
)
from core.database.query_runner import DatabaseConnectionProtocol


class TestDB2SSHConnectionConfig:
    def test_defaults(self):
        config = DB2SSHConnectionConfig(host="myhost", user="myuser")

        assert config.host == "myhost"
        assert config.user == "myuser"
        assert config.password is None
        assert config.database == "QGPL"
        assert config.key_filename is None
        assert config.port == 22
        assert config.timeout == 10

    def test_custom_values(self):
        config = DB2SSHConnectionConfig(
            host="myhost",
            user="myuser",
            password="mypass",
            database="MYLIB",
            key_filename="/path/to/key",
            port=2222,
            timeout=30,
        )

        assert config.host == "myhost"
        assert config.user == "myuser"
        assert config.password == "mypass"
        assert config.database == "MYLIB"
        assert config.key_filename == "/path/to/key"
        assert config.port == 2222
        assert config.timeout == 30


class TestDB2SSHConnectionConnect:
    @patch("adapters.db2ssh.connection.log_database_call")
    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_connect_success(self, mock_db2ssh_connect, mock_log):
        mock_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_connect.return_value = mock_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        result = connection._connect()

        assert result is mock_conn
        assert connection._connection is mock_conn
        mock_db2ssh_connect.assert_called_once_with(
            host="myhost",
            user="myuser",
            password=None,
            key_filename=None,
            port=22,
            timeout=10,
        )
        mock_log.assert_called_once()
        assert mock_log.call_args[0][1] == "connect"
        assert mock_log.call_args[1].get("success") is True

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_connect_raises_connection_error_on_failure(self, mock_db2ssh_connect):
        mock_db2ssh_connect.side_effect = RuntimeError("SSH connection refused")

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        with pytest.raises(ConnectionError) as exc_info:
            connection._connect()

        assert "myhost" in str(exc_info.value)
        assert "myuser" in str(exc_info.value)
        assert "SSH connection refused" in str(exc_info.value)

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_connect_lazy_ensure_connection(self, mock_db2ssh_connect):
        mock_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_connect.return_value = mock_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        assert connection._connection is None
        mock_db2ssh_connect.assert_not_called()

        result = connection._ensure_connection()

        assert result is mock_conn
        mock_db2ssh_connect.assert_called_once()

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_ensure_connection_reuses_existing(self, mock_db2ssh_connect):
        mock_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_connect.return_value = mock_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        first = connection._ensure_connection()
        second = connection._ensure_connection()

        assert first is second
        assert mock_db2ssh_connect.call_count == 1


class TestDB2SSHConnectionExecute:
    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_execute_with_params(self, mock_db2ssh_connect):
        mock_cursor = MagicMock(spec=VendoredCursor)
        mock_cursor.description = [("NAME",), ("AGE",)]
        mock_cursor.fetchall.return_value = [("Alice", 30), ("Bob", 25)]

        mock_db2ssh_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_conn.cursor.return_value = mock_cursor
        mock_db2ssh_connect.return_value = mock_db2ssh_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        results = connection.execute("SELECT * FROM USERS WHERE AGE > ?", (20,))

        assert results == [
            {"NAME": "Alice", "AGE": 30},
            {"NAME": "Bob", "AGE": 25},
        ]
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM USERS WHERE AGE > ?", (20,)
        )

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_execute_without_params(self, mock_db2ssh_connect):
        mock_cursor = MagicMock(spec=VendoredCursor)
        mock_cursor.description = [("NAME",)]
        mock_cursor.fetchall.return_value = [("Charlie",)]

        mock_db2ssh_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_conn.cursor.return_value = mock_cursor
        mock_db2ssh_connect.return_value = mock_db2ssh_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        results = connection.execute("SELECT * FROM USERS")

        assert results == [{"NAME": "Charlie"}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM USERS")

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_execute_returns_empty_for_non_select(self, mock_db2ssh_connect):
        mock_cursor = MagicMock(spec=VendoredCursor)
        mock_cursor.description = None

        mock_db2ssh_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_conn.cursor.return_value = mock_cursor
        mock_db2ssh_connect.return_value = mock_db2ssh_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        results = connection.execute("INSERT INTO USERS (NAME) VALUES ('Test')")

        assert results == []
        mock_cursor.execute.assert_called_once()

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_execute_raises_on_error(self, mock_db2ssh_connect):
        mock_cursor = MagicMock(spec=VendoredCursor)
        mock_cursor.execute.side_effect = RuntimeError("Query failed")

        mock_db2ssh_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_conn.cursor.return_value = mock_cursor
        mock_db2ssh_connect.return_value = mock_db2ssh_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        with pytest.raises(RuntimeError, match="Query failed"):
            connection.execute("SELECT * FROM USERS")

        mock_cursor.close.assert_called_once()

    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_execute_closes_cursor(self, mock_db2ssh_connect):
        mock_cursor = MagicMock(spec=VendoredCursor)
        mock_cursor.description = [("NAME",)]
        mock_cursor.fetchall.return_value = [("Alice",)]

        mock_db2ssh_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_conn.cursor.return_value = mock_cursor
        mock_db2ssh_connect.return_value = mock_db2ssh_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        connection.execute("SELECT * FROM USERS")

        mock_cursor.close.assert_called_once()


class TestDB2SSHConnectionClose:
    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_close_closes_connection(self, mock_db2ssh_connect):
        mock_db2ssh_conn = MagicMock(spec=VendoredConnection)
        mock_db2ssh_connect.return_value = mock_db2ssh_conn

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)
        connection._connect()

        connection.close()

        mock_db2ssh_conn.close.assert_called_once()
        assert connection._connection is None

    def test_close_no_op_when_not_connected(self):
        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        connection.close()

        assert connection._connection is None


class TestDB2SSHConnectionProtocol:
    @patch("adapters.db2ssh.connection.db2ssh_connect")
    def test_implements_database_connection_protocol(self, mock_db2ssh_connect):
        mock_db2ssh_connect.return_value = MagicMock(spec=VendoredConnection)

        config = DB2SSHConnectionConfig(host="myhost", user="myuser")
        connection = DB2SSHConnection(config)

        assert isinstance(connection, DatabaseConnectionProtocol)
