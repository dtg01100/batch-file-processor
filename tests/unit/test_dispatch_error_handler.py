"""
Comprehensive unit tests for the dispatch error handler module.

These tests cover the ErrorLogger, ReportGenerator, and ErrorHandler classes
with extensive mocking of external dependencies.
"""

import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

# Import the module under test
from dispatch.error_handler import (
    ErrorLogger,
    ReportGenerator,
    ErrorHandler,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_run_log():
    """Create a mock run log."""
    log = MagicMock()
    log.write = MagicMock()
    return log


@pytest.fixture
def sample_errors_folder(temp_dir):
    """Create sample errors folder configuration."""
    return {"errors_folder": os.path.join(temp_dir, "errors")}


@pytest.fixture
def error_logger(sample_errors_folder, mock_run_log):
    """Create an ErrorLogger instance with mocked dependencies."""
    return ErrorLogger(sample_errors_folder["errors_folder"], mock_run_log)


@pytest.fixture
def error_handler(sample_errors_folder, mock_run_log, temp_dir):
    """Create an ErrorHandler instance with mocked dependencies."""
    return ErrorHandler(
        errors_folder=sample_errors_folder["errors_folder"],
        run_log=mock_run_log,
        run_log_directory=temp_dir
    )


# =============================================================================
# ErrorLogger Tests
# =============================================================================

class TestErrorLogger:
    """Tests for the ErrorLogger class."""

    def test_initialization(self, error_logger, sample_errors_folder, mock_run_log):
        """Test ErrorLogger initialization."""
        assert error_logger.errors_folder == sample_errors_folder["errors_folder"]
        assert error_logger.run_log is mock_run_log
        assert isinstance(error_logger.folder_errors_log, StringIO)

    def test_log_error(self, error_logger, mock_run_log):
        """Test logging a generic error."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_error("Test error message", "test_file.txt", "TestModule")

            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            assert args[0] is mock_run_log
            assert args[1] is error_logger.folder_errors_log
            assert args[2] == "Test error message"
            assert args[3] == "test_file.txt"
            assert args[4] == "TestModule"

    def test_log_folder_error(self, error_logger, mock_run_log):
        """Test logging a folder-related error."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_folder_error("Folder not found", "/test/folder")

            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            assert args[2] == "Folder not found"
            assert args[3] == "/test/folder"
            assert args[4] == "Dispatch"

    def test_log_folder_error_custom_module(self, error_logger, mock_run_log):
        """Test logging a folder error with custom module name."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_folder_error("Folder error", "/test/folder", "CustomModule")

            args = mock_record.call_args[0]
            assert args[4] == "CustomModule"

    def test_log_file_error(self, error_logger, mock_run_log):
        """Test logging a file-related error."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_file_error("File corrupted", "data.txt")

            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            assert args[2] == "File corrupted"
            assert args[3] == "data.txt"
            assert args[4] == "Dispatch"

    def test_log_file_error_custom_module(self, error_logger, mock_run_log):
        """Test logging a file error with custom module name."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_file_error("File error", "data.txt", "FileProcessor")

            args = mock_record.call_args[0]
            assert args[4] == "FileProcessor"

    def test_get_errors_empty(self, error_logger):
        """Test getting errors when none logged."""
        errors = error_logger.get_errors()

        assert errors == ""

    def test_get_errors_with_content(self, error_logger):
        """Test getting errors with logged content."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            mock_record.side_effect = lambda *args: args[1].write("Error occurred\n")

            error_logger.log_error("Error 1", "file1.txt", "Module1")
            error_logger.log_error("Error 2", "file2.txt", "Module2")

        errors = error_logger.get_errors()

        assert "Error occurred" in errors
        assert errors.count("Error occurred") == 2

    def test_has_errors_false(self, error_logger):
        """Test has_errors returns False when no errors."""
        assert error_logger.has_errors() is False

    def test_has_errors_true(self, error_logger):
        """Test has_errors returns True when errors exist."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            mock_record.side_effect = lambda *args: args[1].write("Error\n")
            error_logger.log_error("Test error", "file.txt", "Module")

        assert error_logger.has_errors() is True

    def test_close(self, error_logger):
        """Test closing the error logger."""
        error_logger.close()

        # After closing, the StringIO should be closed
        with pytest.raises(ValueError):
            error_logger.folder_errors_log.write("More error")


# =============================================================================
# ReportGenerator Tests
# =============================================================================

class TestReportGenerator:
    """Tests for the ReportGenerator class."""

    def test_generate_edi_validation_report(self):
        """Test EDI validation report generation."""
        errors = "Line 5: Invalid UPC\nLine 10: Missing field"

        with patch("dispatch.error_handler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            report = ReportGenerator.generate_edi_validation_report(errors)

            assert "EDI Validation Report" in report
            assert "2024-01-15T10-30-00" in report
            assert "=" * 50 in report
            assert "Line 5: Invalid UPC" in report
            assert "Line 10: Missing field" in report

    def test_generate_edi_validation_report_empty_errors(self):
        """Test EDI validation report with empty errors."""
        with patch("dispatch.error_handler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            report = ReportGenerator.generate_edi_validation_report("")

            assert "EDI Validation Report" in report
            assert report.endswith("\r\n")  # Ends with the separator

    def test_generate_processing_report(self):
        """Test processing report generation."""
        errors = "File processing failed\nInvalid format"
        version = "1.2.3"

        report = ReportGenerator.generate_processing_report(errors, version)

        assert "Program Version = 1.2.3" in report
        assert "Processing Errors" in report
        assert "=" * 30 in report
        assert "File processing failed" in report
        assert "Invalid format" in report

    def test_generate_processing_report_empty_errors(self):
        """Test processing report with empty errors."""
        report = ReportGenerator.generate_processing_report("", "2.0.0")

        assert "Program Version = 2.0.0" in report
        assert report.endswith("\r\n")

    def test_generate_processing_report_multiline_errors(self):
        """Test processing report with multiline errors."""
        errors = "Error 1\r\nError 2\r\nError 3"
        report = ReportGenerator.generate_processing_report(errors, "1.0.0")

        assert "Error 1" in report
        assert "Error 2" in report
        assert "Error 3" in report

    def test_generate_edi_validation_report_timestamp_format(self):
        """Test that timestamp colons are replaced with hyphens."""
        with patch("dispatch.error_handler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:45"

            report = ReportGenerator.generate_edi_validation_report("Error")

            assert "10-30-45" in report
            assert ":" not in report.split("-")[-1]  # No colons in time portion


# =============================================================================
# ErrorHandler Tests
# =============================================================================

class TestErrorHandler:
    """Tests for the ErrorHandler class."""

    def test_initialization(self, error_handler, sample_errors_folder, mock_run_log, temp_dir):
        """Test ErrorHandler initialization."""
        assert error_handler.errors_folder == sample_errors_folder["errors_folder"]
        assert error_handler.run_log is mock_run_log
        assert error_handler.run_log_directory == temp_dir
        assert isinstance(error_handler.logger, ErrorLogger)
        assert isinstance(error_handler.report_generator, ReportGenerator)

    def test_log_error_delegates_to_logger(self, error_handler):
        """Test log_error delegates to logger."""
        with patch.object(error_handler.logger, "log_error") as mock_log:
            error_handler.log_error("Test error", "file.txt", "Module")

            mock_log.assert_called_once_with("Test error", "file.txt", "Module")

    def test_log_folder_error_delegates_to_logger(self, error_handler):
        """Test log_folder_error delegates to logger."""
        with patch.object(error_handler.logger, "log_folder_error") as mock_log:
            error_handler.log_folder_error("Folder error", "/test/folder")

            mock_log.assert_called_once_with("Folder error", "/test/folder", "Dispatch")

    def test_log_file_error_delegates_to_logger(self, error_handler):
        """Test log_file_error delegates to logger."""
        with patch.object(error_handler.logger, "log_file_error") as mock_log:
            error_handler.log_file_error("File error", "data.txt")

            mock_log.assert_called_once_with("File error", "data.txt", "Dispatch")

    def test_write_validation_report(self, error_handler, temp_dir):
        """Test writing validation report to file."""
        errors = "Validation errors found"

        with patch("dispatch.error_handler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            result = error_handler.write_validation_report(errors)

            assert os.path.exists(result)
            with open(result, "r") as f:
                content = f.read()
                assert content == errors

    def test_write_validation_report_path_format(self, error_handler, temp_dir):
        """Test validation report path format."""
        with patch("dispatch.error_handler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            result = error_handler.write_validation_report("Errors")

            assert "Validator Log" in result
            assert result.startswith(temp_dir)
            assert result.endswith(".txt")

    def test_write_folder_errors_report(self, error_handler, sample_errors_folder):
        """Test writing folder errors report."""
        os.makedirs(os.path.join(sample_errors_folder["errors_folder"], "test_folder"), exist_ok=True)

        with patch.object(error_handler.logger, "get_errors") as mock_get_errors, \
             patch.object(error_handler.logger, "log_folder_error") as mock_log_error, \
             patch("dispatch.error_handler.datetime") as mock_datetime, \
             patch("dispatch.error_handler.utils.do_clear_old_files"):

            mock_get_errors.return_value = "Test error details"
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            result = error_handler.write_folder_errors_report(
                folder_name="/test/test_folder",
                folder_alias="Test Folder",
                version="1.0.0"
            )

            assert os.path.exists(result)
            with open(result, "r") as f:
                content = f.read()
                assert "Program Version = 1.0.0" in content
                assert "Test error details" in content

    def test_write_folder_errors_report_creates_directories(self, error_handler, sample_errors_folder):
        """Test that folder errors report creates necessary directories."""
        folder_path = os.path.join(sample_errors_folder["errors_folder"], "new_folder")

        with patch.object(error_handler.logger, "get_errors") as mock_get_errors, \
             patch.object(error_handler.logger, "log_folder_error"), \
             patch("dispatch.error_handler.datetime") as mock_datetime, \
             patch("dispatch.error_handler.utils.do_clear_old_files"):

            mock_get_errors.return_value = "Error"
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            error_handler.write_folder_errors_report(
                folder_name="/test/new_folder",
                folder_alias="New Folder",
                version="1.0.0"
            )

            assert os.path.exists(folder_path)

    def test_write_folder_errors_report_fallback_path(self, error_handler, temp_dir, sample_errors_folder):
        """Test fallback path when folder creation fails."""
        with patch.object(error_handler.logger, "get_errors") as mock_get_errors, \
             patch.object(error_handler.logger, "log_folder_error"), \
             patch("dispatch.error_handler.datetime") as mock_datetime, \
             patch("dispatch.error_handler.os.mkdir") as mock_mkdir, \
             patch("dispatch.error_handler.utils.do_clear_old_files"):

            mock_get_errors.return_value = "Error"
            mock_mkdir.side_effect = IOError("Permission denied")
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            result = error_handler.write_folder_errors_report(
                folder_name="/test/folder",
                folder_alias="Test",
                version="1.0.0"
            )

            # Should fall back to run_log_directory
            assert temp_dir in result

    def test_clean_filename(self, error_handler):
        """Test filename cleaning."""
        result = ErrorHandler._clean_filename("file:name:with:colons")

        assert result == "file-name-with-colons"
        assert ":" not in result

    def test_has_errors_delegates_to_logger(self, error_handler):
        """Test has_errors delegates to logger."""
        with patch.object(error_handler.logger, "has_errors") as mock_has:
            mock_has.return_value = True

            result = error_handler.has_errors()

            assert result is True
            mock_has.assert_called_once()

    def test_get_errors_delegates_to_logger(self, error_handler):
        """Test get_errors delegates to logger."""
        with patch.object(error_handler.logger, "get_errors") as mock_get:
            mock_get.return_value = "Test errors"

            result = error_handler.get_errors()

            assert result == "Test errors"
            mock_get.assert_called_once()

    def test_close_delegates_to_logger(self, error_handler):
        """Test close delegates to logger."""
        with patch.object(error_handler.logger, "close") as mock_close:
            error_handler.close()

            mock_close.assert_called_once()


# =============================================================================
# Integration Tests
# =============================================================================

class TestErrorHandlerIntegration:
    """Integration tests for error handling workflows."""

    def test_full_error_workflow(self, sample_errors_folder, mock_run_log, temp_dir):
        """Test complete error handling workflow."""
        handler = ErrorHandler(sample_errors_folder["errors_folder"], mock_run_log, temp_dir)

        # Log some errors
        handler.log_file_error("File not found", "missing.txt")
        handler.log_folder_error("Folder inaccessible", "/test/folder")

        # Verify errors are logged
        assert handler.has_errors() is True
        errors = handler.get_errors()
        assert "missing.txt" in errors
        assert "/test/folder" in errors

    def test_multiple_error_types_accumulation(self, error_handler):
        """Test accumulation of multiple error types."""
        error_handler.log_error("Generic error", "file1.txt", "Module1")
        error_handler.log_file_error("File error", "file2.txt")
        error_handler.log_folder_error("Folder error", "/test/folder")

        errors = error_handler.get_errors()

        # All errors should be accumulated
        assert error_handler.has_errors() is True
        assert len(errors) > 0


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_log_error_with_empty_message(self, error_logger):
        """Test logging error with empty message."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_error("", "file.txt", "Module")

            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            assert args[2] == ""  # Empty error message

    def test_log_error_with_unicode(self, error_logger):
        """Test logging error with unicode characters."""
        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_error("Erreur avec accents: éèà", "fichier.txt", "Module")

            mock_record.assert_called_once()

    def test_write_validation_report_with_unicode(self, error_handler, temp_dir):
        """Test writing validation report with unicode content."""
        errors = "Erreur avec accents: éèà"

        with patch("dispatch.error_handler.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            result = error_handler.write_validation_report(errors)

            with open(result, "r", encoding="utf-8") as f:
                content = f.read()
                assert "éèà" in content

    def test_very_long_error_message(self, error_logger):
        """Test logging very long error message."""
        long_message = "A" * 10000

        with patch("dispatch.error_handler.record_error.do") as mock_record:
            error_logger.log_error(long_message, "file.txt", "Module")

            mock_record.assert_called_once()

    def test_very_long_filename_in_report(self, error_handler, sample_errors_folder):
        """Test handling very long filename in folder report."""
        long_alias = "A" * 200

        os.makedirs(os.path.join(sample_errors_folder["errors_folder"], "test"), exist_ok=True)

        with patch.object(error_handler.logger, "get_errors") as mock_get_errors, \
             patch.object(error_handler.logger, "log_folder_error"), \
             patch("dispatch.error_handler.datetime") as mock_datetime, \
             patch("dispatch.error_handler.utils.do_clear_old_files"):

            mock_get_errors.return_value = "Error"
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            # Should not raise exception
            error_handler.write_folder_errors_report(
                folder_name="/test/test",
                folder_alias=long_alias,
                version="1.0.0"
            )

    def test_missing_errors_folder(self, error_handler, temp_dir):
        """Test handling when base errors folder doesn't exist."""
        with patch.object(error_handler.logger, "get_errors") as mock_get_errors, \
             patch.object(error_handler.logger, "log_folder_error") as mock_log, \
             patch("dispatch.error_handler.datetime") as mock_datetime, \
             patch("dispatch.error_handler.os.path.exists") as mock_exists, \
             patch("dispatch.error_handler.os.mkdir") as mock_mkdir, \
             patch("dispatch.error_handler.utils.do_clear_old_files"):

            mock_get_errors.return_value = "Error"
            mock_exists.return_value = False
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            error_handler.write_folder_errors_report(
                folder_name="/test/folder",
                folder_alias="Test",
                version="1.0.0"
            )

            # Should log error and create folder
            mock_log.assert_called()
            mock_mkdir.assert_called()

    def test_nested_folder_creation_failure(self, error_handler, sample_errors_folder):
        """Test handling when nested folder creation fails."""
        with patch.object(error_handler.logger, "get_errors") as mock_get_errors, \
             patch.object(error_handler.logger, "log_folder_error"), \
             patch("dispatch.error_handler.datetime") as mock_datetime, \
             patch("dispatch.error_handler.os.path.exists", return_value=True), \
             patch("dispatch.error_handler.os.mkdir") as mock_mkdir, \
             patch("dispatch.error_handler.utils.do_clear_old_files"):

            mock_get_errors.return_value = "Error"
            mock_mkdir.side_effect = IOError("Cannot create directory")
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_now.isoformat.return_value = "2024-01-15T10:30:00"

            result = error_handler.write_folder_errors_report(
                folder_name="/test/nested/deep/folder",
                folder_alias="Test",
                version="1.0.0"
            )

            # Should fall back to run_log_directory
            assert error_handler.run_log_directory in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
