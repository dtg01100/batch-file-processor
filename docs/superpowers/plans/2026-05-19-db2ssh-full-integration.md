# DB2 SSH Full Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the DB2 SSH adapter a fully integrated, tested, and documented first-class citizen.

**Architecture:** Bottom-up per component — vendored driver tests first, then connection adapter, then service layer, then code polish, then docs. Each task produces independently verifiable changes.

**Tech Stack:** Python 3.11, PyQt5, paramiko, pytest

---

### Task 1: Test vendored driver internals

**Files:**
- Create: `tests/unit/adapters/db2ssh/__init__.py`
- Create: `tests/unit/adapters/db2ssh/test_vendored_driver.py`

- [ ] **Step 1: Create package init**

```python
# tests/unit/adapters/db2ssh/__init__.py
```

- [ ] **Step 2: Write test for `_parse_db2_output`**

```python
"""Unit tests for the vendored db2ssh PEP 249 driver internals."""

import pytest

from adapters.db2ssh import (
    _parse_db2_output,
    _parse_error,
    _qmark_to_positional,
    ProgrammingError,
    InterfaceError,
)


class TestParseDb2Output:
    """Tests for _parse_db2_output function."""

    def test_parses_standard_output(self):
        output = (
            "COL1        COL2\n"
            "----------- -----------\n"
            "value1      value2\n"
            "value3      value4\n"
            "\n"
            "  2 RECORD(S) SELECTED\n"
        )
        description, rows = _parse_db2_output(output)
        assert description == ["COL1", "COL2"]
        assert rows == [("value1", "value2"), ("value3", "value4")]

    def test_returns_empty_for_no_separator(self):
        description, rows = _parse_db2_output("no separator line here")
        assert description == []
        assert rows == []

    def test_returns_empty_for_empty_input(self):
        description, rows = _parse_db2_output("")
        assert description == []
        assert rows == []

    def test_single_column_output(self):
        output = (
            "NAME\n"
            "-----------\n"
            "Alice\n"
            "Bob\n"
            "\n"
            "  2 RECORD(S) SELECTED\n"
        )
        description, rows = _parse_db2_output(output)
        assert description == ["NAME"]
        assert rows == [("Alice",), ("Bob",)]

    def test_handles_empty_data_section(self):
        output = (
            "COL1\n"
            "-----------\n"
            "\n"
            "  0 RECORD(S) SELECTED\n"
        )
        description, rows = _parse_db2_output(output)
        assert description == ["COL1"]
        assert rows == []

    def test_trims_whitespace_from_values(self):
        output = (
            "COL1        COL2\n"
            "----------- -----------\n"
            "  leftpad    rightpad   \n"
        )
        description, rows = _parse_db2_output(output)
        assert rows == [("leftpad", "rightpad")]

    def test_separator_line_detection(self):
        assert not _parse_db2_output("COL1\n-------\nval1\n")[1]  # only dashes, no header
```

Run: `pytest tests/unit/adapters/db2ssh/test_vendored_driver.py::TestParseDb2Output -v`
Expected: All tests PASS

- [ ] **Step 3: Write test for `_parse_error`**

```python
class TestParseError:
    """Tests for _parse_error function."""

    def test_extracts_sqlstate(self):
        output = "SQLSTATE: 42704\nSome other text\n"
        result = _parse_error(output)
        assert "SQLSTATE: 42704" in result

    def test_extracts_native_error(self):
        output = "NATIVE ERROR: -204\n"
        result = _parse_error(output)
        assert "NATIVE ERROR: -204" in result

    def test_detects_not_found(self):
        output = "Table not found in database\n"
        result = _parse_error(output)
        assert "not found" in result

    def test_detects_error_keyword(self):
        output = "Some error occurred during processing\n"
        result = _parse_error(output)
        assert "error" in result

    def test_returns_full_output_on_no_match(self):
        output = "Just some informational message\n"
        result = _parse_error(output)
        assert result == output.strip()

    def test_handles_empty_output(self):
        result = _parse_error("")
        assert result == ""

    def test_joins_multiple_errors(self):
        output = (
            "SQLSTATE: 42704\n"
            "NATIVE ERROR: -204\n"
            "Some other text\n"
        )
        result = _parse_error(output)
        assert "SQLSTATE: 42704" in result
        assert "NATIVE ERROR: -204" in result
        assert ";" in result
```

Run: `pytest tests/unit/adapters/db2ssh/test_vendored_driver.py::TestParseError -v`
Expected: All tests PASS

- [ ] **Step 4: Write test for `_qmark_to_positional`**

```python
class TestQmarkToPositional:
    """Tests for _qmark_to_positional parameter substitution."""

    def test_no_params_returns_unchanged(self):
        sql, params = _qmark_to_positional("SELECT 1 FROM DUAL", ())
        assert sql == "SELECT 1 FROM DUAL"
        assert params == []

    def test_replaces_string_param(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE name = ?", ("Alice",))
        assert sql == "SELECT * FROM T WHERE name = 'Alice'"

    def test_escapes_single_quotes_in_string(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE name = ?", ("O'Brien",))
        assert sql == "SELECT * FROM T WHERE name = 'O''Brien'"

    def test_replaces_integer_param(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE id = ?", (42,))
        assert sql == "SELECT * FROM T WHERE id = 42"

    def test_replaces_float_param(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE val = ?", (3.14,))
        assert sql == "SELECT * FROM T WHERE val = 3.14"

    def test_replaces_none_as_null(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE val = ?", (None,))
        assert sql == "SELECT * FROM T WHERE val = NULL"

    def test_replaces_boolean_as_int(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE flag = ?", (True,))
        assert sql == "SELECT * FROM T WHERE flag = 1"

    def test_replaces_bytes_as_utf8_string(self):
        sql, _ = _qmark_to_positional("SELECT * FROM T WHERE data = ?", (b"hello",))
        assert sql == "SELECT * FROM T WHERE data = 'hello'"

    def test_multiple_params(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM T WHERE id = ? AND name = ?", (1, "test")
        )
        assert sql == "SELECT * FROM T WHERE id = 1 AND name = 'test'"

    def test_raises_on_mismatched_param_count(self):
        with pytest.raises(ProgrammingError, match="Expected 2 parameters, got 1"):
            _qmark_to_positional("SELECT * FROM T WHERE a = ? AND b = ?", (1,))

    def test_raises_on_unsupported_type(self):
        with pytest.raises(ProgrammingError, match="Unsupported parameter type"):
            _qmark_to_positional("SELECT * FROM T WHERE val = ?", ([1, 2, 3],))
```

Run: `pytest tests/unit/adapters/db2ssh/test_vendored_driver.py::TestQmarkToPositional -v`
Expected: All tests PASS

- [ ] **Step 5: Write test for `_run_query` semicolon and command structure**

```python
class TestRunQuery:
    """Tests for _run_query internal function."""

    def test_ensures_trailing_semicolon(self):
        import inspect
        from adapters.db2ssh import _run_query
        source = inspect.getsource(_run_query)
        assert 'endswith(";")' in source or "endswith(';')" in source

    def test_uses_t_flag_for_multiline_sql(self):
        import inspect
        from adapters.db2ssh import _run_query
        source = inspect.getsource(_run_query)
        assert "-t" in source

    def test_uses_temp_file_pattern(self):
        import inspect
        from adapters.db2ssh import _run_query
        source = inspect.getsource(_run_query)
        assert "/tmp/" in source
```

Run: `pytest tests/unit/adapters/db2ssh/test_vendored_driver.py::TestRunQuery -v`
Expected: All tests PASS

- [ ] **Step 6: Run all vendored driver tests**

Run: `pytest tests/unit/adapters/db2ssh/test_vendored_driver.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add tests/unit/adapters/db2ssh/__init__.py tests/unit/adapters/db2ssh/test_vendored_driver.py
git commit -m "test: add vendored db2ssh driver unit tests (_parse_db2_output, _parse_error, _qmark_to_positional)"
```

---

### Task 2: Test DB2SSHConnection adapter

**Files:**
- Create: `tests/unit/adapters/db2ssh/test_db2ssh_connection.py`

- [ ] **Step 1: Write DB2SSHConnectionConfig tests**

```python
"""Unit tests for DB2SSHConnection adapter."""

import time
from unittest.mock import patch, MagicMock
import pytest

from adapters.db2ssh.connection import (
    DB2SSHConnection,
    DB2SSHConnectionConfig,
)


class TestDB2SSHConnectionConfig:
    """Tests for DB2SSHConnectionConfig dataclass."""

    def test_defaults(self):
        config = DB2SSHConnectionConfig(host="host", user="user")
        assert config.host == "host"
        assert config.user == "user"
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
```

- [ ] **Step 2: Write _connect tests**

```python
class TestDB2SSHConnectionConnect:
    """Tests for DB2SSHConnection._connect()."""

    def test_connect_success(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_db2ssh_conn = MagicMock()
        with patch("adapters.db2ssh.connection.db2ssh_connect", return_value=mock_db2ssh_conn) as mock_connect:
            result = conn._connect()

        assert result is mock_db2ssh_conn
        assert conn._connection is mock_db2ssh_conn
        mock_connect.assert_called_once_with(
            host="host",
            user="user",
            password="pass",
            key_filename=None,
            port=22,
            timeout=10,
        )

    def test_connect_raises_connection_error_on_failure(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        with patch(
            "adapters.db2ssh.connection.db2ssh_connect",
            side_effect=Exception("Connection refused"),
        ):
            with pytest.raises(ConnectionError, match="Failed to connect via SSH to 'host' as 'user'"):
                conn._connect()

    def test_connect_lazy_ensure_connection(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        assert conn._connection is None

        with patch("adapters.db2ssh.connection.db2ssh_connect") as mock_connect:
            mock_db2ssh_conn = MagicMock()
            mock_connect.return_value = mock_db2ssh_conn
            result = conn._ensure_connection()

        assert result is mock_db2ssh_conn
        mock_connect.assert_called_once()

    def test_ensure_connection_reuses_existing(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)
        existing = MagicMock()
        conn._connection = existing

        with patch("adapters.db2ssh.connection.db2ssh_connect") as mock_connect:
            result = conn._ensure_connection()

        assert result is existing
        mock_connect.assert_not_called()
```

- [ ] **Step 3: Write execute tests**

```python
class TestDB2SSHConnectionExecute:
    """Tests for DB2SSHConnection.execute()."""

    def test_execute_with_params(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_cursor = MagicMock()
        mock_cursor.description = [("COL1", None, None, None, None, None, None)]
        mock_cursor.fetchall.return_value = [("value1",)]

        mock_db2ssh_conn = MagicMock()
        mock_db2ssh_conn.cursor.return_value = mock_cursor

        with patch("adapters.db2ssh.connection.db2ssh_connect", return_value=mock_db2ssh_conn):
            results = conn.execute("SELECT ? FROM DUAL", ("hello",))

        assert results == [{"COL1": "value1"}]
        mock_cursor.execute.assert_called_once_with("SELECT ? FROM DUAL", ("hello",))

    def test_execute_without_params(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_cursor = MagicMock()
        mock_cursor.description = [("ID", None, None, None, None, None, None)]
        mock_cursor.fetchall.return_value = [(1,), (2,)]

        mock_db2ssh_conn = MagicMock()
        mock_db2ssh_conn.cursor.return_value = mock_cursor

        with patch("adapters.db2ssh.connection.db2ssh_connect", return_value=mock_db2ssh_conn):
            results = conn.execute("SELECT * FROM T")

        assert results == [{"ID": 1}, {"ID": 2}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM T")

    def test_execute_returns_empty_for_non_select(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_cursor = MagicMock()
        mock_cursor.description = None

        mock_db2ssh_conn = MagicMock()
        mock_db2ssh_conn.cursor.return_value = mock_cursor

        with patch("adapters.db2ssh.connection.db2ssh_connect", return_value=mock_db2ssh_conn):
            results = conn.execute("CALL some_proc()")

        assert results == []

    def test_execute_raises_on_error(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query failed")

        mock_db2ssh_conn = MagicMock()
        mock_db2ssh_conn.cursor.return_value = mock_cursor

        with patch("adapters.db2ssh.connection.db2ssh_connect", return_value=mock_db2ssh_conn):
            with pytest.raises(Exception, match="Query failed"):
                conn.execute("SELECT * FROM T")

    def test_execute_closes_cursor(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_cursor = MagicMock()
        mock_cursor.description = [("ID", None, None, None, None, None, None)]
        mock_cursor.fetchall.return_value = []

        mock_db2ssh_conn = MagicMock()
        mock_db2ssh_conn.cursor.return_value = mock_cursor

        with patch("adapters.db2ssh.connection.db2ssh_connect", return_value=mock_db2ssh_conn):
            conn.execute("SELECT * FROM T")

        mock_cursor.close.assert_called_once()
```

- [ ] **Step 4: Write close and lifecycle tests**

```python
class TestDB2SSHConnectionClose:
    """Tests for DB2SSHConnection.close()."""

    def test_close_closes_connection(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)

        mock_db2ssh_conn = MagicMock()
        conn._connection = mock_db2ssh_conn

        conn.close()

        mock_db2ssh_conn.close.assert_called_once()
        assert conn._connection is None

    def test_close_no_op_when_not_connected(self):
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)
        conn._connection = None

        conn.close()  # Should not raise


class TestDB2SSHConnectionProtocol:
    """Tests that DB2SSHConnection satisfies the protocol."""

    def test_implements_database_connection_protocol(self):
        from core.database import DatabaseConnectionProtocol
        config = DB2SSHConnectionConfig(
            host="host", user="user", password="pass"
        )
        conn = DB2SSHConnection(config)
        assert isinstance(conn, DatabaseConnectionProtocol)
```

- [ ] **Step 5: Run all DB2SSHConnection tests**

Run: `pytest tests/unit/adapters/db2ssh/test_db2ssh_connection.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/unit/adapters/db2ssh/test_db2ssh_connection.py
git commit -m "test: add DB2SSHConnection adapter unit tests (connect, execute, close, protocol)"
```

---

### Task 3: Test DatabaseConnector service

**Files:**
- Create: `tests/unit/dispatch/services/test_database_connector.py`

- [ ] **Step 1: Write DatabaseConnector tests**

```python
"""Unit tests for DatabaseConnector service."""

import pytest
from unittest.mock import patch, MagicMock


class TestDatabaseConnector:
    """Tests for DatabaseConnector service."""

    def test_init_connection_success(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()
        assert not connector.is_initialized
        assert connector.query_runner is None

        mock_runner = MagicMock()
        with patch(
            "dispatch.services.database_connector.create_query_runner_from_settings",
            return_value=mock_runner,
        ):
            connector.init_connection({
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "host",
            })

        assert connector.is_initialized
        assert connector.query_runner is mock_runner

    def test_init_connection_missing_keys_raises_value_error(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()

        with pytest.raises(ValueError, match="Missing required database settings"):
            connector.init_connection({
                "as400_username": "",
                "as400_address": "",
            })

        assert not connector.is_initialized

    def test_init_connection_missing_both_password_and_key_raises(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()

        with pytest.raises(ValueError, match="Either as400_password or ssh_key_filename"):
            connector.init_connection({
                "as400_username": "user",
                "as400_password": "",
                "as400_address": "host",
                "ssh_key_filename": "",
            })

        assert not connector.is_initialized

    def test_init_connection_with_ssh_key_only(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()

        mock_runner = MagicMock()
        with patch(
            "dispatch.services.database_connector.create_query_runner_from_settings",
            return_value=mock_runner,
        ):
            connector.init_connection({
                "as400_username": "user",
                "as400_password": "",
                "as400_address": "host",
                "ssh_key_filename": "/path/to/key",
            })

        assert connector.is_initialized
        assert connector.query_runner is mock_runner

    def test_double_init_is_no_op(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()
        mock_runner = MagicMock()

        with patch(
            "dispatch.services.database_connector.create_query_runner_from_settings",
            return_value=mock_runner,
        ) as mock_factory:
            connector.init_connection({
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "host",
            })
            assert mock_factory.call_count == 1

            connector.init_connection({
                "as400_username": "user2",
                "as400_password": "pass2",
                "as400_address": "host2",
            })
            assert mock_factory.call_count == 1, "Second init should be no-op"

    def test_close_closes_query_runner(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()
        mock_runner = MagicMock()

        with patch(
            "dispatch.services.database_connector.create_query_runner_from_settings",
            return_value=mock_runner,
        ):
            connector.init_connection({
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "host",
            })

        assert connector.is_initialized

        connector.close()
        mock_runner.close.assert_called_once()
        assert connector.query_runner is None
        assert not connector.is_initialized

    def test_close_safe_when_not_initialized(self):
        from dispatch.services.database_connector import DatabaseConnector

        connector = DatabaseConnector()
        connector.close()  # Should not raise
```

- [ ] **Step 2: Run DatabaseConnector tests**

Run: `pytest tests/unit/dispatch/services/test_database_connector.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/dispatch/services/test_database_connector.py
git commit -m "test: add DatabaseConnector service unit tests"
```

---

### Task 4: Code polish

**Files:**
- Modify: `adapters/db2ssh/connection.py` (context manager, thread safety)
- Modify: `dispatch/services/database_connector.py` (typed attrs, fix bare except)
- Modify: `core/database/__init__.py` (export consistency)

- [ ] **Step 1: Add context manager support and thread safety to DB2SSHConnection**

File: `adapters/db2ssh/connection.py`

Add import at top:
```python
import threading
```

Add `__enter__`/`__exit__` methods after `close()` (after line 201):

```python
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

Add lock to `__init__` (after line 57):
```python
        self._lock = threading.Lock()
```

Update `_ensure_connection` to use the lock:
```python
    def _ensure_connection(self) -> Any:
        if self._connection is None:
            with self._lock:
                if self._connection is None:
                    self._connect()
        return self._connection
```

- [ ] **Step 2: Verify context manager + thread safety tests pass**

Run: `pytest tests/unit/adapters/db2ssh/test_db2ssh_connection.py -v`
Expected: All tests still PASS

- [ ] **Step 3: Fix DatabaseConnector typed attrs and bare except**

File: `dispatch/services/database_connector.py`

Update `__init__` to declare all instance attributes:
```python
    def __init__(self):
        self._query_runner: QueryRunner | None = None
        self._db_initialized: bool = False
        self.ssh_key_filename: str | None = None
        self.as400_password: str | None = None
```

Update `init_connection` to store these as instance attributes (already done at lines 66-67, but align with new `__init__` type declarations):
```python
        self.ssh_key_filename = ssh_key_filename
        self.as400_password = as400_password
```

Update `close()` to fix the bare `except AttributeError`:
```python
    def close(self) -> None:
        if self._query_runner is not None:
            try:
                self._query_runner.close()
                logger.debug("Database connection closed")
            except Exception:
                logger.debug(
                    "Failed to close database connection (non-fatal)",
                    exc_info=True,
                )
            self._query_runner = None
            self._db_initialized = False
```

- [ ] **Step 4: Verify DatabaseConnector tests still pass**

Run: `pytest tests/unit/dispatch/services/test_database_connector.py -v`
Expected: All tests PASS

- [ ] **Step 5: Add export consistency to core/database/__init__.py**

Update `core/database/__init__.py`:

```python
from core.database.query_runner import (
    DatabaseConnectionProtocol,
    MockConnection,
    QueryRunner,
    SQLiteConnection,
    create_query_runner,
    create_query_runner_from_settings,
)

__all__ = [
    "DatabaseConnectionProtocol",
    "MockConnection",
    "QueryRunner",
    "SQLiteConnection",
    "create_query_runner",
    "create_query_runner_from_settings",
]
```

- [ ] **Step 6: Verify export works**

Run: `python -c "from core.database import create_query_runner_from_settings; print('OK')"`
Expected: Prints `OK`

- [ ] **Step 7: Run full test suite for affected modules**

Run: `pytest tests/unit/core/database/test_query_runner.py tests/unit/adapters/db2ssh/ tests/unit/dispatch/services/test_database_connector.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add adapters/db2ssh/connection.py dispatch/services/database_connector.py core/database/__init__.py
git commit -m "refactor: add context manager, thread safety, typed attrs, export consistency for db2ssh"
```

---

### Task 5: Documentation updates

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/design/COMPONENT_MAP.md`
- Modify: `docs/design/DESIGN_CORRECTIONS.md`

- [ ] **Step 1: Update AGENTS.md**

Line 91: Change `adapters/db2ssh/ (future)` to `adapters/db2ssh/ (production)`

```
| **adapters/** | Database adapters | `adapters/sqlite/` (current), `adapters/db2ssh/` (production) |
```

- [ ] **Step 2: Update COMPONENT_MAP.md**

Section 6.2: Change "DB2 SSH Adapter (Future)" to "DB2 SSH Adapter"

Remove "(Future)" from any parenthetical references in that section.

- [ ] **Step 3: Update DESIGN_CORRECTIONS.md**

Remove or update "future stub" language referencing `DB2SSHConnectionConfig`.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md docs/design/COMPONENT_MAP.md docs/design/DESIGN_CORRECTIONS.md
git commit -m "docs: update db2ssh from future/stub to production status"
```

---

### Task 6: Full verification

- [ ] **Step 1: Run all unit tests**

Run: `pytest tests/unit/adapters/db2ssh/ tests/unit/dispatch/services/test_database_connector.py tests/unit/core/database/test_query_runner.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run broader test suite**

Run: `make test-unit` (or equivalent)
Expected: No regressions
