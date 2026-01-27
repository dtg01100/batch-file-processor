"""
Integration tests for record_error module - captures current production functionality.

These tests verify error recording functionality to ensure consistency
with the current production implementation.
"""

import pytest
import sys
import os
from io import StringIO, BytesIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import record_error


@pytest.mark.integration
class TestRecordErrorBasic:
    """Tests for the record_error.do function with basic logging."""

    def test_error_logged_to_file_object(self):
        """Error messages are written to file-like objects."""
        run_log = BytesIO()
        errors_log = StringIO()
        
        error_msg = "Test error message"
        
        # Record error in non-threaded mode
        record_error.do(run_log, errors_log, error_msg, "test_file.txt", "test_module")
        
        # Check that content was written
        assert run_log.getvalue() != b""
        assert errors_log.getvalue() != ""
        
        # Check that error message is present
        assert error_msg in errors_log.getvalue()
        assert "test_file.txt" in errors_log.getvalue()
        assert "test_module" in errors_log.getvalue()

    def test_error_message_format(self):
        """Error messages contain expected components."""
        run_log = BytesIO()
        errors_log = StringIO()
        
        filename = "sample.edi"
        error_source = "convert_to_csv"
        error_message = "Invalid format detected"
        
        record_error.do(run_log, errors_log, error_message, filename, error_source)
        
        log_content = errors_log.getvalue()
        
        # Check for all expected components
        assert "At:" in log_content
        assert "From module:" in log_content
        assert error_source in log_content
        assert "For object:" in log_content
        assert filename in log_content
        assert "Error Message is:" in log_content
        assert error_message in log_content

    def test_threaded_error_logging(self):
        """Error messages are appended to lists in threaded mode."""
        run_log = []
        errors_log = []
        
        error_msg = "Threaded error"
        
        result_log, result_errors = record_error.do(
            run_log, errors_log, error_msg, "threaded_file.txt", "threaded_module", threaded=True
        )
        
        # Check that lists were updated
        assert len(result_log) > 0
        assert len(result_errors) > 0
        assert error_msg in result_errors[0]
        assert "threaded_file.txt" in result_errors[0]

    def test_multiple_errors(self):
        """Multiple errors can be logged sequentially."""
        run_log = BytesIO()
        errors_log = StringIO()
        
        errors = [
            ("file1.txt", "module1", "Error 1"),
            ("file2.txt", "module2", "Error 2"),
            ("file3.txt", "module3", "Error 3"),
        ]
        
        for filename, module, msg in errors:
            record_error.do(run_log, errors_log, msg, filename, module)
        
        log_content = errors_log.getvalue()
        
        # All errors should be present
        for _, _, msg in errors:
            assert msg in log_content
