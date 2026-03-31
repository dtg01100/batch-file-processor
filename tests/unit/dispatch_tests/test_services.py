"""Tests for dispatch/services/ module."""

import logging
import sys
from io import StringIO
from unittest.mock import MagicMock

import pytest

from dispatch.services.progress_reporter import (
    CLIProgressReporter,
    LoggingProgressReporter,
    NullProgressReporter,
    ProgressReporter,
)
from dispatch.services.upc_service import UPCLookupService


class _StubQueryRunner:
    """Stub query runner that returns fixed rows."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self.closed = False

    def run_query(self, query, params=None):
        return self._rows

    def close(self):
        self.closed = True


class TestUPCLookupService:
    """Tests for UPCLookupService class."""

    def test_init_empty_settings(self):
        """Service initialises with empty settings and empty cache."""
        service = UPCLookupService({})
        assert service.settings == {}
        assert service.upc_dict == {}
        assert service.last_error is None

    def test_get_dictionary_returns_empty_when_no_credentials(self):
        """get_dictionary returns {} when AS400 credentials are absent."""
        service = UPCLookupService({})
        result = service.get_dictionary()
        assert result == {}
        assert service.last_error is not None
        assert "missing AS400 settings" in service.last_error

    def test_get_dictionary_uses_cached_dict(self):
        """get_dictionary returns cached dict without hitting the database."""
        service = UPCLookupService({})
        service.upc_dict = {1: ["CAT", "UPC", "a", "b", "c"]}
        result = service.get_dictionary()
        assert result == {1: ["CAT", "UPC", "a", "b", "c"]}

    def test_get_dictionary_via_stub_runner_tuple_rows(self, monkeypatch):
        """get_dictionary parses positional tuple rows from the database."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        rows = [(100, "ELEC", "123456789012", "desc", "brand", "item")]
        stub = _StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub,
        )
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
        }
        service = UPCLookupService(settings)
        result = service.get_dictionary()
        assert 100 in result
        assert result[100] == ["ELEC", "123456789012", "desc", "brand", "item"]
        assert stub.closed is True

    def test_get_dictionary_via_stub_runner_dict_rows(self, monkeypatch):
        """get_dictionary parses dict rows with uppercase column names."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        rows = [
            {
                "ANBACD": "999",
                "ANBBCD": "CAT2",
                "ANBGCD": "11111",
                "ANBHCD": "22222",
                "ANBICD": "33333",
                "ANBJCD": "44444",
            }
        ]
        stub = _StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub,
        )
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
        }
        service = UPCLookupService(settings)
        result = service.get_dictionary()
        assert 999 in result
        assert result[999] == ["CAT2", "11111", "22222", "33333", "44444"]

    def test_get_dictionary_uses_injected_upc_service(self):
        """get_dictionary delegates to an injected external UPC service."""
        external = MagicMock()
        external.get_dictionary.return_value = {42: ["X", "Y", "Z", "A", "B"]}
        service = UPCLookupService({})
        result = service.get_dictionary(upc_service=external)
        assert result == {42: ["X", "Y", "Z", "A", "B"]}
        external.get_dictionary.assert_called_once()

    def test_last_error_set_when_no_rows_returned(self, monkeypatch):
        """last_error is populated when the fallback query returns no rows."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        stub = _StubQueryRunner([])
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub,
        )
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
        }
        service = UPCLookupService(settings)
        result = service.get_dictionary()
        assert result == {}
        assert service.last_error is not None
        assert "no rows" in service.last_error

    def test_last_error_set_when_rows_unparseable(self, monkeypatch):
        """last_error describes the failure when rows cannot be parsed."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        stub = _StubQueryRunner([{"bad_key": "bad_value"}])
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub,
        )
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
        }
        service = UPCLookupService(settings)
        result = service.get_dictionary()
        assert result == {}
        assert service.last_error is not None

    def test_strict_db_mode_raises_when_no_rows(self, monkeypatch):
        """strict database_lookup_mode raises LookupError when query has no rows."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        stub = _StubQueryRunner([])
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub,
        )
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
            "database_lookup_mode": "strict",
        }
        service = UPCLookupService(settings)
        with pytest.raises(LookupError):
            service.get_dictionary(strict_db_mode=True)

    def test_clear_cache_resets_dict(self):
        """clear_cache empties upc_dict so next call re-fetches."""
        service = UPCLookupService({})
        service.upc_dict = {1: ["a", "b", "c", "d", "e"]}
        service.clear_cache()
        assert service.upc_dict == {}

    def test_multiple_items_parsed_correctly(self, monkeypatch):
        """Multiple rows are all parsed into the returned dictionary."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        rows = [
            (1, "CAT1", "UPC1", "a", "b", "c"),
            (2, "CAT2", "UPC2", "d", "e", "f"),
        ]
        stub = _StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub,
        )
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
        }
        service = UPCLookupService(settings)
        result = service.get_dictionary()
        assert len(result) == 2
        assert 1 in result
        assert 2 in result


class TestProgressReporterProtocol:
    """Tests for ProgressReporter protocol."""

    def test_protocol_exists(self):
        """Test that ProgressReporter protocol exists."""
        assert ProgressReporter is not None


class TestNullProgressReporter:
    """Tests for NullProgressReporter class."""

    def test_update_does_nothing(self):
        """Test that update does nothing."""
        reporter = NullProgressReporter()

        reporter.update(
            message="Test",
            folder_num=1,
            folder_total=5,
            file_num=1,
            file_total=10,
            footer="Footer",
        )

    def test_update_with_empty_values(self):
        """Test update with empty values."""
        reporter = NullProgressReporter()

        reporter.update(
            message="",
            folder_num=0,
            folder_total=0,
            file_num=0,
            file_total=0,
            footer="",
        )


class TestCLIProgressReporter:
    """Tests for CLIProgressReporter class."""

    def test_output_format(self):
        """Test CLI output format."""
        output = StringIO()
        reporter = CLIProgressReporter(output)

        reporter.update(
            message="Processing file",
            folder_num=2,
            folder_total=5,
            file_num=3,
            file_total=10,
            footer="Status: OK",
        )

        output.seek(0)
        content = output.read()

        assert "Processing file" in content
        assert "Folder 2 of 5" in content
        assert "File 3 of 10" in content
        assert "Status: OK" in content

    def test_output_without_footer(self):
        """Test CLI output without footer."""
        output = StringIO()
        reporter = CLIProgressReporter(output)

        reporter.update(
            message="Processing",
            folder_num=1,
            folder_total=3,
            file_num=5,
            file_total=20,
            footer="",
        )

        output.seek(0)
        content = output.read()

        assert "Processing" in content
        assert "Folder 1 of 3" in content

    def test_finish_writes_newline(self):
        """Test that finish writes a newline."""
        output = StringIO()
        reporter = CLIProgressReporter(output)

        reporter.finish()

        output.seek(0)
        content = output.read()

        assert content == "\n"

    def test_default_output_is_stdout(self):
        """Test that default output is sys.stdout."""
        reporter = CLIProgressReporter()

        assert reporter._output is sys.stdout


class TestLoggingProgressReporter:
    """Tests for LoggingProgressReporter class."""

    def test_logs_info_message(self):
        """Test that update logs info message."""
        logger = MagicMock(spec=logging.Logger)
        reporter = LoggingProgressReporter(logger)

        reporter.update(
            message="Processing file",
            folder_num=1,
            folder_total=5,
            file_num=3,
            file_total=10,
            footer="Status: OK",
        )

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]

        assert "Processing file" in call_args
        assert "Folder 1/5" in call_args
        assert "File 3/10" in call_args
        assert "Status: OK" in call_args

    def test_logs_without_footer(self):
        """Test logging without footer - pipe still present but no footer text."""
        logger = MagicMock(spec=logging.Logger)
        reporter = LoggingProgressReporter(logger)

        reporter.update(
            message="Processing",
            folder_num=1,
            folder_total=3,
            file_num=5,
            file_total=20,
            footer="",
        )

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0][0]

        assert "Processing" in call_args
        assert "Folder 1/3" in call_args
