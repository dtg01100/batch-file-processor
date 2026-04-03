"""
db2ssh — Query IBM i Db2 databases over SSH (vendored).

DB-API 2.0 (PEP 249) driver using paramiko and the remote 'db2' command.
No ibm_db installation required.

This is a vendored copy of https://github.com/dtg01100/db2ssh v1.0.0
 vendored for use as a local adapter.

Usage:
    from adapters.db2ssh import connect
    conn = connect(host="your-ibm-i.example.com", user="myuser", password="mypass")
    cur = conn.cursor()
    cur.execute("SELECT TABLE_NAME FROM QSYS2.SYSTABLES FETCH FIRST 5 ROWS ONLY")
    for row in cur.fetchall():
        print(row)
    conn.close()
"""

import os
import uuid

import paramiko

__version__ = "1.0.0"

# DB-API 2.0 module-level attributes
apilevel = "2.0"
threadsafety = 1
paramstyle = "qmark"


# --- DB-API 2.0 Exceptions ---


class Warning(Exception):
    """Exception raised for important warnings (e.g., data truncation)."""


class Error(Exception):
    """Base exception class for all database errors."""


class InterfaceError(Error):
    """Exception raised for errors related to the database interface, not the database itself."""


class DatabaseError(Error):
    """Base exception class for errors related to the database operation."""


class OperationalError(DatabaseError):
    """Exception raised for operational errors outside control (connection failure, memory error)."""


class ProgrammingError(DatabaseError):
    """Exception raised for programming errors (syntax error, table not found)."""


class IntegrityError(DatabaseError):
    """Exception raised when relational integrity is affected (foreign key violation)."""


class DataError(DatabaseError):
    """Exception raised for data processing errors (division by zero, value out of range)."""


class NotSupportedError(DatabaseError):
    """Exception raised when an unsupported database method was called."""


# --- Output Parsing ---


def _parse_db2_output(output: str) -> tuple[list[str], list[tuple]]:
    """Parse db2 columnar output into (description, rows).

    Args:
        output: Raw string output from db2 command execution.

    Returns:
        Tuple of (column_names, rows) where column_names is a list of
        header strings and rows is a list of tuples containing cell values.

    """
    lines = output.splitlines()

    sep_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and all(c in "- " for c in stripped):
            sep_idx = i
            break

    if sep_idx is None:
        return [], []

    sep_line = lines[sep_idx]
    header_line = lines[sep_idx - 1] if sep_idx > 0 else ""

    col_starts = []
    j = 0
    while j < len(sep_line):
        if sep_line[j] == "-":
            col_starts.append(j)
            while j < len(sep_line) and sep_line[j] == "-":
                j += 1
        else:
            j += 1

    if not col_starts:
        return [], []

    col_slices = []
    for k, start in enumerate(col_starts):
        end = col_starts[k + 1] if k + 1 < len(col_starts) else None
        col_slices.append((start, end))

    description = []
    for start, end in col_slices:
        name = header_line[start:end].strip() if start < len(header_line) else ""
        description.append(name)

    rows = []
    for line in lines[sep_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if "RECORD(S) SELECTED" in stripped:
            continue
        row = []
        for start, end in col_slices:
            val = line[start:end].strip() if start < len(line) else ""
            row.append(val)
        rows.append(tuple(row))

    return description, rows


def _parse_error(output: str) -> str:
    """Extract error message from db2 error output.

    Scans output lines for SQLSTATE, NATIVE ERROR markers, or common
    error keywords to construct a concise error message.

    Args:
        output: Raw string output from failed db2 command execution.

    Returns:
        Extracted error message string, or the full output if no
        specific error pattern is found.

    """
    lines = output.strip().splitlines()
    messages = []
    for line in lines:
        line = line.strip()
        if line.startswith("SQLSTATE:") or line.startswith("NATIVE ERROR"):
            messages.append(line)
        elif "not found" in line.lower() or "error" in line.lower():
            messages.append(line)
    return "; ".join(messages) if messages else output.strip()


def _qmark_to_positional(sql: str, params: tuple) -> tuple[str, list]:
    """Replace ? placeholders with escaped literal values.

    This is a workaround for db2ssh not supporting parameterized queries.
    Values are escaped and embedded directly into the SQL string.

    Warning:
        This approach is vulnerable to SQL injection if params come from
        untrusted sources. Always validate inputs when possible.

    Args:
        sql: SQL query string with ? placeholders.
        params: Tuple of parameter values to substitute.

    Returns:
        Tuple of (sql_with_literals, empty_list).

    Raises:
        ProgrammingError: If the number of ? placeholders doesn't match params length.

    """
    if not params:
        return sql, []
    parts = sql.split("?")
    if len(parts) - 1 != len(params):
        raise ProgrammingError(
            f"Expected {len(parts) - 1} parameters, got {len(params)}"
        )
    result = parts[0]
    for i, param in enumerate(params):
        if param is None:
            result += "NULL"
        elif isinstance(param, (int, float)):
            result += str(param)
        elif isinstance(param, str):
            escaped = param.replace("'", "''")
            result += f"'{escaped}'"
        else:
            escaped = str(param).replace("'", "''")
            result += f"'{escaped}'"
        result += parts[i + 1]
    return result, []


# --- SSH Query Execution ---


def _run_query(ssh: paramiko.SSHClient, sql: str) -> tuple[str, str, int]:
    """Execute SQL on IBM i via qsh db2.

    Writes the SQL to a temporary file on the remote system, executes it
    via `qsh -c "db2 -f ..."`, then cleans up the temp file.

    Args:
        ssh: Active paramiko SSH client connected to the IBM i system.
        sql: SQL query string to execute.

    Returns:
        Tuple of (stdout_output, stderr_output, exit_status_code).

    """
    remote_sql = f"/tmp/.db2ssh_{uuid.uuid4().hex}.sql"

    # Ensure SQL ends with semicolon (required for db2 -t flag)
    sql = sql.rstrip()
    if not sql.endswith(";"):
        sql = sql + ";"

    escaped_sql = sql.replace("\\", "\\\\").replace("'", "'\\''")
    ssh.exec_command(f"printf '%s\\n' '{escaped_sql}' > {remote_sql}")

    try:
        # Use -t flag for semicolon-terminated statements (allows multiline SQL)
        cmd = f'qsh -c "db2 -f {remote_sql} -t"'
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        error = stderr.read().decode()
        exit_status = stdout.channel.recv_exit_status()
    finally:
        ssh.exec_command(f"rm -f {remote_sql}")

    return output, error, exit_status


# --- DB-API 2.0 Cursor ---


class Cursor:
    """DB-API 2.0 cursor for IBM i Db2 over SSH."""

    description = None
    rowcount = -1
    arraysize = 1

    def __init__(self, connection: "Connection") -> None:
        """Initialize the cursor.

        Args:
            connection: DB-API Connection object to execute queries against.

        """
        self._connection = connection
        self._rows: list[tuple] = []
        self._pos = 0
        self.description = None
        self.rowcount = -1

    def execute(self, operation: str, parameters: tuple | None = None) -> "Cursor":
        """Execute a database operation (query or command).

        Args:
            operation: SQL query string, may contain ? placeholders.
            parameters: Optional tuple of parameters to substitute.

        Returns:
            Self, for method chaining.

        Raises:
            InterfaceError: If the connection is closed.
            ProgrammingError: If the SQL execution fails.

        """
        if self._connection._closed:
            raise InterfaceError("Connection is closed")

        if parameters:
            operation, _ = _qmark_to_positional(operation, parameters)

        ssh = self._connection._ssh
        output, error, exit_status = _run_query(ssh, operation)

        if exit_status != 0:
            msg = _parse_error(output)
            raise ProgrammingError(msg)

        desc, rows = _parse_db2_output(output)

        self.description = (
            [(name, None, None, None, None, None, None) for name in desc]
            if desc
            else None
        )
        self._rows = rows
        self._pos = 0
        self.rowcount = len(rows)
        return self

    def executemany(self, operation: str, seq_of_parameters: list[tuple]) -> None:
        """Execute the same operation against multiple parameter sets.

        Args:
            operation: SQL query string with ? placeholders.
            seq_of_parameters: List of parameter tuples, one per execution.

        """
        for params in seq_of_parameters:
            self.execute(operation, params)

    def fetchone(self) -> tuple | None:
        """Fetch the next row of a query result set.

        Returns:
            Next row as a tuple, or None if no more rows are available.

        """
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchmany(self, size: int | None = None) -> list[tuple]:
        """Fetch the next set of rows of a query result set.

        Args:
            size: Number of rows to fetch. Defaults to self.arraysize if None.

        Returns:
            List of row tuples.

        """
        if size is None:
            size = self.arraysize
        result = self._rows[self._pos : self._pos + size]
        self._pos += len(result)
        return result

    def fetchall(self) -> list[tuple]:
        """Fetch all remaining rows of a query result set.

        Returns:
            List of all remaining row tuples.

        """
        result = self._rows[self._pos :]
        self._pos = len(self._rows)
        return result

    def close(self) -> None:
        """Close the cursor and release resources."""
        self._connection = None
        self._rows = []
        self.description = None

    def setinputsizes(self, sizes: list) -> None:
        """Set input sizes (no-op, not supported by db2ssh)."""
        pass

    def setoutputsize(self, size: int, column: int | None = None) -> None:
        """Set output size for a column (no-op, not supported by db2ssh)."""
        pass

    def __iter__(self):
        return self

    def __next__(self):
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row


# --- DB-API 2.0 Connection ---


class Connection:
    """DB-API 2.0 connection for IBM i Db2 over SSH."""

    def __init__(
        self,
        host: str,
        user: str,
        password: str | None = None,
        key_filename: str | None = None,
        port: int = 22,
        timeout: int = 10,
    ) -> None:
        """Establish an SSH connection to IBM i.

        Args:
            host: IBM i hostname or IP address.
            user: IBM i username for authentication.
            password: IBM i password (optional if using key-based auth).
            key_filename: Path to SSH private key file (optional).
            port: SSH port number (default: 22).
            timeout: Connection timeout in seconds (default: 10).

        Raises:
            OperationalError: If authentication fails or SSH connection cannot be established.

        """
        self._host = host
        self._user = user
        self._closed = False
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._ssh.connect(
                host,
                port=port,
                username=user,
                password=password,
                key_filename=key_filename,
                timeout=timeout,
            )
        except paramiko.AuthenticationException:
            raise OperationalError(f"Authentication failed for {user}@{host}")
        except paramiko.SSHException as e:
            raise OperationalError(f"SSH connection failed: {e}")
        except Exception as e:
            raise OperationalError(f"Connection failed: {e}")

    def cursor(self) -> Cursor:
        """Create a new cursor for executing queries.

        Returns:
            New Cursor object for executing SQL queries.

        Raises:
            InterfaceError: If the connection is closed.

        """
        if self._closed:
            raise InterfaceError("Connection is closed")
        return Cursor(self)

    def commit(self) -> None:
        """Commit pending transactions (no-op for db2ssh over SSH)."""
        pass

    def rollback(self) -> None:
        """Rollback pending transactions.

        Raises:
            NotSupportedError: Rollback is not supported over the SSH db2 interface.

        """
        raise NotSupportedError("Rollback not supported over SSH db2 interface")

    def close(self) -> None:
        """Close the SSH connection."""
        if not self._closed:
            self._ssh.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# --- Public API ---


def connect(
    host: str,
    user: str,
    password: str | None = None,
    key_filename: str | None = None,
    port: int = 22,
    timeout: int = 10,
    **kwargs,
) -> Connection:
    """Connect to IBM i Db2 via SSH.

    Authentication is attempted in this order:
        1. Password (explicit or DB2_PASSWORD env var)
        2. SSH agent
        3. Default key files (~/.ssh/id_rsa, etc.)
        4. Explicit key_filename

    Args:
        host: IBM i hostname or IP address.
        user: IBM i username.
        password: IBM i password (or set DB2_PASSWORD env var).
        key_filename: Path to private key file for key-based auth.
        port: SSH port (default: 22).
        timeout: Connection timeout in seconds (default: 10).

    Returns:
        DB-API 2.0 Connection object.

    Raises:
        InterfaceError: If username is not provided.
        OperationalError: If connection or authentication fails.

    """
    if password is None:
        password = os.environ.get("DB2_PASSWORD")
    if password == "":
        password = None
    if not user:
        raise InterfaceError("user is required")
    return Connection(
        host,
        user,
        password=password,
        key_filename=key_filename,
        port=port,
        timeout=timeout,
    )
