"""
Unit tests for vendored db2ssh driver internals.
"""

import inspect

import pytest

from adapters.db2ssh import (
    ProgrammingError,
    _parse_db2_output,
    _parse_error,
    _qmark_to_positional,
    _run_query,
)


class TestParseDb2Output:
    def test_parses_standard_output(self):
        output = (
            "NAME          AGE\n"
            "-----------   ---\n"
            "Alice         30\n"
            "Bob           25\n"
            "\n"
            "  2 RECORD(S) SELECTED\n"
        )
        desc, rows = _parse_db2_output(output)
        assert desc == ["NAME", "AGE"]
        assert rows == [("Alice", "30"), ("Bob", "25")]

    def test_returns_empty_for_no_separator(self):
        output = "NAME  |  AGE\nAlice  |  30\n"
        desc, rows = _parse_db2_output(output)
        assert desc == []
        assert rows == []

    def test_returns_empty_for_empty_input(self):
        desc, rows = _parse_db2_output("")
        assert desc == []
        assert rows == []

    def test_single_column_output(self):
        output = (
            "NAME\n"
            "----\n"
            "Alice\n"
            "Bob\n"
            "\n"
            "  2 RECORD(S) SELECTED\n"
        )
        desc, rows = _parse_db2_output(output)
        assert desc == ["NAME"]
        assert rows == [("Alice",), ("Bob",)]

    def test_handles_empty_data_section(self):
        output = (
            "NAME          AGE\n"
            "-----------   ---\n"
            "\n"
            "  0 RECORD(S) SELECTED\n"
        )
        desc, rows = _parse_db2_output(output)
        assert desc == ["NAME", "AGE"]
        assert rows == []

    def test_trims_whitespace_from_values(self):
        output = (
            "NAME          AGE\n"
            "--------      ---\n"
            "  Alice        30 \n"
            "  Bob          25 \n"
            "\n"
            "  2 RECORD(S) SELECTED\n"
        )
        desc, rows = _parse_db2_output(output)
        assert desc == ["NAME", "AGE"]
        assert rows == [("Alice", "30"), ("Bob", "25")]


class TestParseError:
    def test_extracts_sqlstate(self):
        output = (
            "SQLSTATE: 42704\n"
            "Some other text\n"
        )
        result = _parse_error(output)
        assert "SQLSTATE: 42704" in result

    def test_extracts_native_error(self):
        output = (
            "NATIVE ERROR  -204\n"
            "Some other text\n"
        )
        result = _parse_error(output)
        assert "NATIVE ERROR  -204" in result

    def test_detects_not_found(self):
        output = (
            "Some header\n"
            "TABLE not found\n"
            "More text\n"
        )
        result = _parse_error(output)
        assert "TABLE not found" in result

    def test_detects_error_keyword(self):
        output = (
            "Some output\n"
            "An error occurred during execution\n"
        )
        result = _parse_error(output)
        assert "An error occurred during execution" in result

    def test_returns_full_output_on_no_match(self):
        output = "Just some informational text\nNo problems here\n"
        result = _parse_error(output)
        assert result == output.strip()

    def test_handles_empty_output(self):
        result = _parse_error("")
        assert result == ""

    def test_joins_multiple_errors(self):
        output = (
            "SQLSTATE: 42704\n"
            "NATIVE ERROR  -204\n"
            "TABLE not found\n"
        )
        result = _parse_error(output)
        assert "SQLSTATE: 42704" in result
        assert "NATIVE ERROR  -204" in result
        assert "TABLE not found" in result


class TestQmarkToPositional:
    def test_no_params_returns_unchanged(self):
        sql, _ = _qmark_to_positional("SELECT 1 FROM SYSIBM.SYSDUMMY1", ())
        assert sql == "SELECT 1 FROM SYSIBM.SYSDUMMY1"

    def test_replaces_string_param(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE NAME = ?",
            ("Alice",),
        )
        assert sql == "SELECT * FROM USERS WHERE NAME = 'Alice'"

    def test_escapes_single_quotes_in_string(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE NAME = ?",
            ("O'Brien",),
        )
        assert sql == "SELECT * FROM USERS WHERE NAME = 'O''Brien'"

    def test_replaces_integer_param(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE ID = ?",
            (42,),
        )
        assert sql == "SELECT * FROM USERS WHERE ID = 42"

    def test_replaces_float_param(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM ITEMS WHERE PRICE = ?",
            (3.14,),
        )
        assert sql == "SELECT * FROM ITEMS WHERE PRICE = 3.14"

    def test_replaces_none_as_null(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE EMAIL = ?",
            (None,),
        )
        assert sql == "SELECT * FROM USERS WHERE EMAIL = NULL"

    def test_replaces_boolean_as_int(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE ACTIVE = ?",
            (True,),
        )
        assert sql == "SELECT * FROM USERS WHERE ACTIVE = 1"

    def test_replaces_bytes_as_utf8_string(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE NAME = ?",
            (b"hello",),
        )
        assert sql == "SELECT * FROM USERS WHERE NAME = 'hello'"

    def test_multiple_params(self):
        sql, _ = _qmark_to_positional(
            "SELECT * FROM USERS WHERE NAME = ? AND AGE = ?",
            ("Alice", 30),
        )
        assert sql == "SELECT * FROM USERS WHERE NAME = 'Alice' AND AGE = 30"

    def test_raises_on_mismatched_param_count(self):
        with pytest.raises(ProgrammingError):
            _qmark_to_positional(
                "SELECT * FROM USERS WHERE NAME = ? AND AGE = ?",
                ("Alice",),
            )

    def test_raises_on_unsupported_type(self):
        with pytest.raises(ProgrammingError):
            _qmark_to_positional(
                "SELECT * FROM USERS WHERE ID = ?",
                ([1, 2, 3],),
            )


class TestRunQuery:
    def test_ensures_trailing_semicolon(self):
        source = inspect.getsource(_run_query)
        assert 'if not sql.endswith(";")' in source

    def test_uses_t_flag_for_multiline_sql(self):
        source = inspect.getsource(_run_query)
        assert " -t" in source

    def test_uses_temp_file_pattern(self):
        source = inspect.getsource(_run_query)
        assert "/tmp/" in source
