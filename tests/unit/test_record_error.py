"""Unit tests for record_error module.

Tests:
- Error message formatting
- Threaded vs non-threaded operation
- Log writing behavior
"""

import io
from unittest.mock import patch

import pytest

import scripts.record_error as record_error


class TestRecordError:
    """Test suite for record_error module."""

    @pytest.fixture
    def sample_run_log(self):
        """Create a sample run log (non-threaded)."""
        return io.BytesIO()

    @pytest.fixture
    def sample_errors_log(self):
        """Create a sample errors log (non-threaded)."""
        return io.StringIO()

    @pytest.fixture
    def sample_error_message(self):
        """Create a sample error message."""
        return "File not found: test_file.txt"

    @pytest.fixture
    def sample_filename(self):
        """Create a sample filename."""
        return "test_edi_001.txt"

    @pytest.fixture
    def sample_error_source(self):
        """Create a sample error source."""
        return "ftp_backend"

    def test_module_import(self):
        """Test that record_error module can be imported."""
        assert record_error is not None

    def test_do_function_exists(self):
        """Test that do function exists."""
        assert hasattr(record_error, "do")
        assert callable(record_error.do)

    def test_basic_error_recording(
        self,
        sample_run_log,
        sample_errors_log,
        sample_error_message,
        sample_filename,
        sample_error_source,
    ):
        """Test basic error recording without threading."""
        result = record_error.do(
            sample_run_log,
            sample_errors_log,
            sample_error_message,
            sample_filename,
            sample_error_source,
            threaded=False,
        )

        # Check that run_log has content written
        sample_run_log.seek(0)
        run_log_content = sample_run_log.read().decode()
        assert "At:" in run_log_content
        assert sample_error_source in run_log_content
        assert sample_filename in run_log_content
        assert sample_error_message in run_log_content

        # Check that errors_log has content written
        sample_errors_log.seek(0)
        errors_log_content = sample_errors_log.read()
        assert "At:" in errors_log_content
        assert sample_error_source in errors_log_content

    def test_error_message_format(
        self,
        sample_run_log,
        sample_errors_log,
        sample_error_message,
        sample_filename,
        sample_error_source,
    ):
        """Test that error message is formatted correctly."""
        record_error.do(
            sample_run_log,
            sample_errors_log,
            sample_error_message,
            sample_filename,
            sample_error_source,
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()

        # Check all expected parts are present
        assert "At:" in content  # Timestamp prefix
        assert "From module:" in content
        assert "For object:" in content
        assert "Error Message is:" in content
        assert "\r\n\r\n" in content  # Double line ending

    def test_threaded_mode_returns_logs(self):
        """Test that threaded mode returns the logs."""
        run_log = []
        errors_log = []
        error_message = "Test error"
        filename = "test.txt"
        error_source = "test_module"

        result_run_log, result_errors_log = record_error.do(
            run_log, errors_log, error_message, filename, error_source, threaded=True
        )

        assert result_run_log is run_log
        assert result_errors_log is errors_log
        assert len(run_log) == 1
        assert len(errors_log) == 1

    def test_threaded_mode_appends_to_lists(self):
        """Test that threaded mode appends messages to lists."""
        run_log = []
        errors_log = []

        # Record multiple errors
        for i in range(3):
            record_error.do(
                run_log,
                errors_log,
                f"Error {i}",
                f"file_{i}.txt",
                "test_module",
                threaded=True,
            )

        assert len(run_log) == 3
        assert len(errors_log) == 3

        # Each message should be distinct
        for i in range(3):
            assert f"Error {i}" in run_log[i]
            assert f"Error {i}" in errors_log[i]

    def test_non_threaded_mode_no_return(self, sample_run_log, sample_errors_log):
        """Test that non-threaded mode returns None."""
        result = record_error.do(
            sample_run_log,
            sample_errors_log,
            "Test error",
            "test.txt",
            "test_module",
            threaded=False,
        )

        assert result is None

    def test_timestamp_included(self, sample_run_log, sample_errors_log):
        """Test that timestamp is included in error message."""
        with patch("record_error.time.ctime") as mock_ctime:
            mock_ctime.return_value = "Mon Mar  3 12:00:00 2026"

            record_error.do(
                sample_run_log,
                sample_errors_log,
                "Test error",
                "test.txt",
                "test_module",
                threaded=False,
            )

            mock_ctime.assert_called_once()

    def test_special_characters_in_error_message(
        self, sample_run_log, sample_errors_log
    ):
        """Test handling of special characters in error message."""
        special_message = "Error: 'file' not found\nLine 2\tTabbed"

        record_error.do(
            sample_run_log,
            sample_errors_log,
            special_message,
            "test.txt",
            "test_module",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()
        assert special_message in content

    def test_long_error_message(self, sample_run_log, sample_errors_log):
        """Test handling of very long error message."""
        long_message = "A" * 10000

        record_error.do(
            sample_run_log,
            sample_errors_log,
            long_message,
            "test.txt",
            "test_module",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()
        assert long_message in content

    def test_unicode_in_error_message(self, sample_run_log, sample_errors_log):
        """Test handling of unicode characters in error message."""
        unicode_message = "Error: 文件未找到 🚫"

        record_error.do(
            sample_run_log,
            sample_errors_log,
            unicode_message,
            "test.txt",
            "test_module",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()
        assert unicode_message in content

    def test_empty_error_message(self, sample_run_log, sample_errors_log):
        """Test handling of empty error message."""
        record_error.do(
            sample_run_log,
            sample_errors_log,
            "",
            "test.txt",
            "test_module",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()
        assert "Error Message is:" in content  # Header should still be there

    def test_empty_filename(self, sample_run_log, sample_errors_log):
        """Test handling of empty filename."""
        record_error.do(
            sample_run_log,
            sample_errors_log,
            "Test error",
            "",
            "test_module",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()
        assert "For object:" in content

    def test_empty_error_source(self, sample_run_log, sample_errors_log):
        """Test handling of empty error source."""
        record_error.do(
            sample_run_log,
            sample_errors_log,
            "Test error",
            "test.txt",
            "",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read().decode()
        assert "From module:" in content

    def test_multiple_errors_accumulate(self, sample_run_log, sample_errors_log):
        """Test that multiple errors accumulate in logs."""
        for i in range(5):
            record_error.do(
                sample_run_log,
                sample_errors_log,
                f"Error {i}",
                f"file_{i}.txt",
                "test_module",
                threaded=False,
            )

        sample_run_log.seek(0)
        run_content = sample_run_log.read().decode()

        sample_errors_log.seek(0)
        errors_content = sample_errors_log.read()

        # Each error should appear in both logs
        for i in range(5):
            assert f"Error {i}" in run_content
            assert f"Error {i}" in errors_content

    def test_run_log_encoded_bytes(self, sample_run_log, sample_errors_log):
        """Test that run_log receives encoded bytes."""
        record_error.do(
            sample_run_log,
            sample_errors_log,
            "Test error",
            "test.txt",
            "test_module",
            threaded=False,
        )

        sample_run_log.seek(0)
        content = sample_run_log.read()

        # run_log should contain bytes (was encoded)
        assert isinstance(content, bytes)

    def test_errors_log_string(self, sample_run_log, sample_errors_log):
        """Test that errors_log receives string content."""
        record_error.do(
            sample_run_log,
            sample_errors_log,
            "Test error",
            "test.txt",
            "test_module",
            threaded=False,
        )

        sample_errors_log.seek(0)
        content = sample_errors_log.read()

        # errors_log should contain string
        assert isinstance(content, str)


class TestRecordErrorEdgeCases:
    """Test suite for edge cases in record_error module."""

    def test_error_object_as_message(self):
        """Test that exception objects can be used as error messages."""
        run_log = []
        errors_log = []

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            record_error.do(
                run_log, errors_log, str(e), "test.txt", "test_module", threaded=True
            )

        assert len(run_log) == 1
        assert "Test exception" in run_log[0]

    def test_none_error_message(self):
        """Test handling of None error message."""
        run_log = []
        errors_log = []

        record_error.do(
            run_log, errors_log, None, "test.txt", "test_module", threaded=True
        )

        # Should not crash, message should contain "None"
        assert len(run_log) == 1
        assert "None" in run_log[0]

    def test_numeric_error_message(self):
        """Test handling of numeric error message."""
        run_log = []
        errors_log = []

        record_error.do(
            run_log, errors_log, 404, "test.txt", "test_module", threaded=True
        )

        assert len(run_log) == 1
        assert "404" in run_log[0]

    def test_path_with_special_characters(self):
        """Test handling of path with special characters."""
        run_log = []
        errors_log = []

        record_error.do(
            run_log,
            errors_log,
            "Error",
            "/path/to/file with spaces & symbols!.txt",
            "test_module",
            threaded=True,
        )

        assert len(run_log) == 1
        assert "file with spaces & symbols!" in run_log[0]
