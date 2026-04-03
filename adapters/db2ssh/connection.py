"""
DB2SSHConnection — DatabaseConnectionProtocol adapter using db2ssh.

This module provides a DB2SSHConnection class that adapts the vendored
db2ssh library to the DatabaseConnectionProtocol interface used by
QueryRunner in core.database.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Any

from core.structured_logging import get_logger, log_database_call

from . import connect as db2ssh_connect


@dataclass
class DB2SSHConnectionConfig:
    """Configuration for DB2SSH connection.

    Attributes:
        host: IBM i hostname or IP address (maps to as400_address)
        user: IBM i username (maps to as400_username)
        password: IBM i password (maps to as400_password)
        database: Database/library name (default: QGPL)
        key_filename: Path to SSH private key file (optional)
        port: SSH port (default 22)
        timeout: Connection timeout in seconds (default 10)
    """

    host: str
    user: str
    password: str | None = None
    database: str = "QGPL"
    key_filename: str | None = None
    port: int = 22
    timeout: int = 10


class DB2SSHConnection:
    """DB2SSH connection implementation of DatabaseConnectionProtocol.

    This class wraps the db2ssh library and provides a clean interface
    for executing queries through the QueryRunner abstraction.
    """

    def __init__(self, config: DB2SSHConnectionConfig) -> None:
        """Initialize the connection with configuration.

        Args:
            config: Connection configuration containing credentials and host
        """
        self.config = config
        self._connection = None
        self._connection_id = uuid.uuid4().hex[:8]
        self._logger = get_logger(__name__)

    def _ensure_connection(self) -> Any:
        """Establish the SSH connection if not already connected.

        Returns:
            The underlying db2ssh connection object.

        """
        if self._connection is None:
            self._connect()
        return self._connection

    def _connect(self) -> Any:
        """Establish the database connection via SSH.

        Creates a new paramiko-based SSH connection to the IBM i system
        and initializes the db2ssh session. Logs connection duration
        and success/failure metrics.

        Returns:
            db2ssh Connection object for executing queries.

        Raises:
            ConnectionError: If the SSH connection cannot be established.

        """
        start_time = time.perf_counter()
        try:
            self._connection = db2ssh_connect(
                host=self.config.host,
                user=self.config.user,
                password=self.config.password,
                key_filename=self.config.key_filename,
                port=self.config.port,
                timeout=self.config.timeout,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_database_call(
                self._logger,
                "connect",
                table=self.config.database,
                duration_ms=duration_ms,
                success=True,
                connection_id=self._connection_id,
            )
        except Exception as exc:
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
                f"Failed to connect via SSH to {self.config.host!r} "
                f"as {self.config.user!r}: {exc}"
            ) from exc
        return self._connection

    def execute(self, query: str, params: tuple | None = None) -> list[dict]:
        """Execute a query and return results as list of dicts.

        Args:
            query: SQL query string to execute on the IBM i database.
            params: Optional parameters for parameterized queries (qmark style).

        Returns:
            List of dictionaries with column names as keys.
            Returns empty list for non-SELECT statements or no-result queries.

        Raises:
            ConnectionError: If the underlying SSH connection fails.

        """
        start_time = time.perf_counter()
        conn = self._ensure_connection()

        try:
            cursor = conn.cursor()
            try:
                if params is not None:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if cursor.description is None:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    log_database_call(
                        self._logger,
                        "execute",
                        table=self.config.database,
                        duration_ms=duration_ms,
                        success=True,
                        connection_id=self._connection_id,
                    )
                    return []

                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    results.append(row_dict)

                duration_ms = (time.perf_counter() - start_time) * 1000
                log_database_call(
                    self._logger,
                    "execute",
                    table=self.config.database,
                    row_count=len(results),
                    duration_ms=duration_ms,
                    success=True,
                    connection_id=self._connection_id,
                )
                return results
            finally:
                cursor.close()
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log_database_call(
                self._logger,
                "execute",
                table=self.config.database,
                duration_ms=duration_ms,
                success=False,
                error=exc,
                connection_id=self._connection_id,
            )
            raise

    def close(self) -> None:
        """Close the SSH connection if open."""
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
