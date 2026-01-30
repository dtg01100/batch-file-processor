"""
Comprehensive unit tests for record_error.py module.

Tests the do() function for error logging functionality.
"""

import os
import sys
import time
import unittest
from io import BytesIO, StringIO
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import record_error
from record_error import do


class TestRecordErrorDo(unittest.TestCase):
    """Tests for record_error.do() function."""

    def test_basic_error_logging(self):
        """Test basic error logging to both logs."""
        run_log = BytesIO()
        errors_log = StringIO()
        error_message = "Test error message"
        filename = "/path/to/file.txt"
        error_source = "TestModule"

        do(run_log, errors_log, error_message, filename, error_source)

        # Check run_log contents (bytes)
        run_log.seek(0)
        run_content = run_log.read().decode('utf-8')
        self.assertIn("Test error message", run_content)
        self.assertIn("TestModule", run_content)
        self.assertIn("/path/to/file.txt", run_content)

        # Check errors_log contents (string)
        errors_content = errors_log.getvalue()
        self.assertIn("Test error message", errors_content)
        self.assertIn("TestModule", errors_content)
        self.assertIn("/path/to/file.txt", errors_content)

    def test_error_logging_timestamp(self):
        """Test that timestamp is included in error log."""
        run_log = BytesIO()
        errors_log = StringIO()

        with patch('record_error.time.ctime') as mock_ctime:
            mock_ctime.return_value = "Mon Jan 01 12:00:00 2024"
            do(run_log, errors_log, "error", "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("Mon Jan 01 12:00:00 2024", errors_content)
        self.assertIn("At:", errors_content)

    def test_error_logging_multiline_message(self):
        """Test error logging with multiline message."""
        run_log = BytesIO()
        errors_log = StringIO()
        error_message = "Line 1\nLine 2\nLine 3"

        do(run_log, errors_log, error_message, "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("Line 1", errors_content)
        self.assertIn("Line 2", errors_content)
        self.assertIn("Line 3", errors_content)

    def test_error_logging_special_characters(self):
        """Test error logging with special characters."""
        run_log = BytesIO()
        errors_log = StringIO()
        error_message = "Error with special chars: äöü € 日本語"

        do(run_log, errors_log, error_message, "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("äöü", errors_content)

    def test_error_logging_empty_message(self):
        """Test error logging with empty message."""
        run_log = BytesIO()
        errors_log = StringIO()

        do(run_log, errors_log, "", "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("From module: Module", errors_content)
        self.assertIn("Error Message is:", errors_content)

    def test_error_logging_long_filename(self):
        """Test error logging with very long filename."""
        run_log = BytesIO()
        errors_log = StringIO()
        long_filename = "/very/long/path/" + "x" * 200 + "/file.txt"

        do(run_log, errors_log, "error", long_filename, "Module")

        errors_content = errors_log.getvalue()
        self.assertIn(long_filename, errors_content)

    def test_error_logging_exception_object(self):
        """Test error logging with exception object as message."""
        run_log = BytesIO()
        errors_log = StringIO()
        exception = ValueError("Invalid value provided")

        do(run_log, errors_log, exception, "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("Invalid value provided", errors_content)


class TestRecordErrorThreaded(unittest.TestCase):
    """Tests for threaded error logging mode."""

    def test_threaded_mode_returns_lists(self):
        """Test threaded mode returns modified lists."""
        run_log = []
        errors_log = []
        error_message = "Threaded error"
        filename = "file.txt"
        error_source = "TestModule"

        result = do(
            run_log, errors_log, error_message, filename, error_source, threaded=True
        )

        # Should return the lists
        self.assertIsNotNone(result)
        result_run_log, result_errors_log = result
        self.assertIsInstance(result_run_log, list)
        self.assertIsInstance(result_errors_log, list)
        # Lists should have the message appended
        self.assertEqual(len(result_run_log), 1)
        self.assertEqual(len(result_errors_log), 1)
        self.assertIn("Threaded error", result_run_log[0])
        self.assertIn("Threaded error", result_errors_log[0])

    def test_threaded_mode_preserves_existing(self):
        """Test threaded mode preserves existing log entries."""
        run_log = ["Existing entry 1", "Existing entry 2"]
        errors_log = ["Existing error 1"]

        result = do(
            run_log, errors_log, "New error", "file.txt", "Module", threaded=True
        )

        self.assertIsNotNone(result)
        result_run_log, result_errors_log = result
        # Should preserve existing entries
        self.assertEqual(len(result_run_log), 3)
        self.assertEqual(len(result_errors_log), 2)
        self.assertIn("Existing entry 1", result_run_log)
        self.assertIn("Existing error 1", result_errors_log)

    def test_threaded_mode_with_empty_lists(self):
        """Test threaded mode with empty initial lists."""
        run_log = []
        errors_log = []

        result = do(
            run_log, errors_log, "Error message", "file.txt", "Module", threaded=True
        )

        self.assertIsNotNone(result)
        result_run_log, result_errors_log = result
        self.assertEqual(len(result_run_log), 1)
        self.assertEqual(len(result_errors_log), 1)

    def test_threaded_vs_non_threaded_difference(self):
        """Test that threaded and non-threaded modes behave differently."""
        # Non-threaded: writes to file-like objects
        run_log_bytes = BytesIO()
        errors_log_str = StringIO()

        non_threaded_result = do(run_log_bytes, errors_log_str, "error", "file.txt", "Module", threaded=False)

        # Threaded: appends to lists
        run_log_list = []
        errors_log_list = []

        threaded_result = do(
            run_log_list, errors_log_list, "error", "file.txt", "Module", threaded=True
        )

        # Non-threaded should have written to BytesIO and return None
        run_log_bytes.seek(0)
        self.assertGreater(len(run_log_bytes.read()), 0)
        self.assertIsNone(non_threaded_result)

        # Threaded should have appended to list and returned tuple
        self.assertIsNotNone(threaded_result)
        result_run, result_errors = threaded_result
        self.assertEqual(len(result_run), 1)


class TestRecordErrorFormatting(unittest.TestCase):
    """Tests for error log message formatting."""

    def test_message_structure(self):
        """Test the structure of the logged message."""
        run_log = BytesIO()
        errors_log = StringIO()

        with patch('record_error.time.ctime') as mock_ctime:
            mock_ctime.return_value = "Test Timestamp"
            do(run_log, errors_log, "The error", "the_file.txt", "TheModule")

        errors_content = errors_log.getvalue()

        # Verify message structure
        expected_parts = [
            "At: Test Timestamp",
            "From module: TheModule",
            "For object: the_file.txt",
            "Error Message is:",
            "The error",
        ]

        for part in expected_parts:
            self.assertIn(part, errors_content)

    def test_line_endings(self):
        """Test that messages use CRLF line endings."""
        run_log = BytesIO()
        errors_log = StringIO()

        do(run_log, errors_log, "error", "file.txt", "Module")

        errors_content = errors_log.getvalue()

        # Should have CRLF line endings
        self.assertIn("\r\n", errors_content)

    def test_run_log_encoding(self):
        """Test that run_log is written as bytes (encoded)."""
        run_log = BytesIO()
        errors_log = StringIO()

        do(run_log, errors_log, "error", "file.txt", "Module")

        run_log.seek(0)
        content = run_log.read()

        # Should be bytes, not str
        self.assertIsInstance(content, bytes)


class TestRecordErrorEdgeCases(unittest.TestCase):
    """Edge case tests for record_error."""

    def test_none_error_message(self):
        """Test with None as error message."""
        run_log = BytesIO()
        errors_log = StringIO()

        # Should handle None gracefully
        do(run_log, errors_log, None, "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("None", errors_content)

    def test_integer_error_message(self):
        """Test with integer as error message."""
        run_log = BytesIO()
        errors_log = StringIO()

        do(run_log, errors_log, 404, "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("404", errors_content)

    def test_very_long_error_message(self):
        """Test with very long error message."""
        run_log = BytesIO()
        errors_log = StringIO()
        long_message = "A" * 10000

        do(run_log, errors_log, long_message, "file.txt", "Module")

        errors_content = errors_log.getvalue()
        self.assertIn("A" * 10000, errors_content)

    def test_error_source_with_special_chars(self):
        """Test error source with special characters."""
        run_log = BytesIO()
        errors_log = StringIO()

        do(run_log, errors_log, "error", "file.txt", "Module-With_Dots.Special")

        errors_content = errors_log.getvalue()
        self.assertIn("Module-With_Dots.Special", errors_content)


if __name__ == '__main__':
    unittest.main()
