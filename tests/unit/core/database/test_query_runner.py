"""Unit tests for core.database.query_runner module."""

import pytest

from core.database.query_runner import (
    DatabaseConnectionProtocol,
    MockConnection,
    QueryRunner,
    assert_read_only_sql,
    create_query_runner,
)


class TestMockConnection:
    """Tests for MockConnection class."""

    def test_execute_records_query(self):
        """Test that execute records queries for verification."""
        conn = MockConnection()
        conn.execute("SELECT * FROM test", ("param",))
        assert len(conn.executed_queries) == 1
        assert conn.executed_queries[0] == ("SELECT * FROM test", ("param",))

    def test_execute_returns_preset_results(self):
        """Test that execute returns preset results."""
        conn = MockConnection()
        conn.results = [[{"id": 1, "name": "test"}]]
        result = conn.execute("SELECT * FROM test")
        assert result == [{"id": 1, "name": "test"}]

    def test_execute_returns_empty_list_when_no_results(self):
        """Test that execute returns empty list when no preset results."""
        conn = MockConnection()
        result = conn.execute("SELECT * FROM test")
        assert result == []

    def test_multiple_executes_return_sequential_results(self):
        """Test that multiple executes return results in order."""
        conn = MockConnection()
        conn.results = [[{"id": 1}], [{"id": 2}], [{"id": 3}]]
        assert conn.execute("SELECT 1") == [{"id": 1}]
        assert conn.execute("SELECT 2") == [{"id": 2}]
        assert conn.execute("SELECT 3") == [{"id": 3}]

    def test_add_results_appends_to_queue(self):
        """Test add_results method."""
        conn = MockConnection()
        conn.add_results([{"id": 1}])
        conn.add_results([{"id": 2}])
        assert conn.execute("SELECT 1") == [{"id": 1}]
        assert conn.execute("SELECT 2") == [{"id": 2}]

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
            "SELECT * FROM test WHERE id = ?",
            (1,),
        )

    def test_run_query_single_returns_first_result(self):
        """Test that run_query_single returns first result."""
        mock_conn = MockConnection()
        mock_conn.results = [[{"id": 1}, {"id": 2}]]
        runner = QueryRunner(mock_conn)
        result = runner.run_query_single("SELECT * FROM test")
        assert result == {"id": 1}

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


class TestCreateQueryRunner:
    """Tests for create_query_runner factory function."""

    def test_creates_query_runner_instance(self):
        """Test that factory creates a QueryRunner instance."""
        runner = create_query_runner("user", "pass", "TEST")
        assert isinstance(runner, QueryRunner)


class TestReadOnlySqlPolicy:
    """Tests for read-only SQL contract."""

    def test_assert_read_only_accepts_select(self):
        """SELECT statements should be accepted."""
        assert_read_only_sql("SELECT * FROM my_table")

    def test_assert_read_only_accepts_with(self):
        """WITH CTE statements should be accepted."""
        assert_read_only_sql("WITH cte AS (SELECT 1 AS id) SELECT * FROM cte")

    def test_assert_read_only_rejects_update(self):
        """Mutating statements must be rejected."""
        with pytest.raises(ValueError, match="Mutating SQL is forbidden"):
            assert_read_only_sql("UPDATE my_table SET col = 1")

    def test_query_runner_rejects_insert_before_execution(self):
        """QueryRunner should block INSERT statements before delegating."""
        mock_conn = MockConnection()
        runner = QueryRunner(mock_conn)

        with pytest.raises(ValueError, match="Mutating SQL is forbidden"):
            runner.run_query("INSERT INTO x (a) VALUES (1)")

        assert mock_conn.executed_queries == []


class TestProtocolCompliance:
    """Tests for Protocol compliance."""

    def test_mock_connection_satisfies_protocol(self):
        """Test that MockConnection satisfies DatabaseConnectionProtocol."""
        conn = MockConnection()
        assert isinstance(conn, DatabaseConnectionProtocol)

    def test_query_runner_accepts_protocol(self):
        """Test that QueryRunner accepts any protocol implementation."""
        mock_conn = MockConnection()
        runner = QueryRunner(mock_conn)
        assert runner.connection is mock_conn


def test_db_enabled_converter_connect_db_uses_core_database_create_query_runner(
    monkeypatch,
):
    """Ensure DBEnabledConverter resolves create_query_runner at call-time."""
    from dispatch.converters.convert_base import DBEnabledConverter

    called = {}

    def fake_create_query_runner(**kwargs):
        called["called"] = True
        return QueryRunner(MockConnection())

    monkeypatch.setattr("core.database.create_query_runner", fake_create_query_runner)

    class DummyDBEnabledConverter(DBEnabledConverter):
        def process_record_a(self, record):
            pass

        def process_record_b(self, record):
            pass

        def process_record_c(self, record):
            pass

    converter = DummyDBEnabledConverter(
        "input.edi",
        "output",
        {"as400_username": "u", "as400_password": "p", "as400_address": "host"},
        {},
        {},
    )

    converter.connect_db()

    assert called.get("called", False)
    assert converter.query_object is not None
    assert converter._db_connected is True


def test_crec_generator_db_connect_uses_core_database_create_query_runner(monkeypatch):
    """Ensure CRecGenerator resolves create_query_runner at call-time."""
    from core.utils.utils import CRecGenerator

    called = {}

    def fake_create_query_runner(**kwargs):
        called["called"] = True
        return QueryRunner(MockConnection())

    monkeypatch.setattr("core.database.create_query_runner", fake_create_query_runner)

    cri = CRecGenerator(
        {"as400_username": "u", "as400_password": "p", "as400_address": "host"}
    )
    cri._db_connect()

    assert called.get("called", False)
    assert cri.query_object is not None
