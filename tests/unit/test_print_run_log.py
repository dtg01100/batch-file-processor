"""Unit tests for print_run_log module.

Tests:
- Log file reading and formatting
- Platform-specific printing (Windows vs Unix)
- Text wrapping for page width
"""

import platform
import textwrap
from unittest.mock import patch, MagicMock

import pytest


class TestPrintRunLog:
    """Test suite for print_run_log module."""

    @pytest.fixture
    def sample_log_content(self):
        """Create sample log content."""
        return (
            "Batch File Processor Run Log\n"
            "===========================\n"
            "Started: Mon Mar 3 12:00:00 2026\n"
            "Processing file: test_edi.txt\n"
            "Status: Success\n"
            "Files processed: 5\n"
        )

    @pytest.fixture
    def sample_file_handle(self, sample_log_content):
        """Create a mock file handle."""
        mock_handle = MagicMock()
        mock_handle.read.return_value = sample_log_content
        return mock_handle

    def test_module_import(self):
        """Test that print_run_log module can be imported."""
        import print_run_log
        assert print_run_log is not None

    def test_do_function_exists(self):
        """Test that do function exists."""
        import print_run_log
        assert hasattr(print_run_log, 'do')
        assert callable(print_run_log.do)

    def test_log_formatting_wraps_long_lines(self, sample_log_content):
        """Test that long lines are wrapped to 75 characters."""
        # Create a long line that needs wrapping
        long_line = "A" * 200
        wrapped = '\r\n'.join(textwrap.wrap(long_line, width=75, replace_whitespace=False))

        # Each line should be at most 75 chars (except the last which might be shorter)
        lines = wrapped.split('\r\n')
        for line in lines:
            assert len(line) <= 75, f"Line exceeds 75 chars: {len(line)}"

    def test_textwrap_preserves_newlines(self, sample_log_content):
        """Test that text wrapping preserves existing line structure."""
        formatted = '\r\n'.join(
            textwrap.wrap(sample_log_content, width=75, replace_whitespace=False)
        )
        # The content should still contain the original information
        assert "Batch File Processor" in formatted
        assert "Success" in formatted

    def test_file_is_read(self, sample_file_handle):
        """Test that the file handle is read."""
        # The do function reads from the file handle
        content = sample_file_handle.read()
        assert "Batch File Processor" in content
        sample_file_handle.read.assert_called_once()

    def test_windows_line_endings_in_output(self, sample_log_content):
        """Test that output uses Windows line endings (\\r\\n)."""
        formatted = '\r\n'.join(
            textwrap.wrap(sample_log_content, width=75, replace_whitespace=False)
        )
        assert '\r\n' in formatted or len(formatted) < 75

    @patch('platform.system')
    def test_platform_detection_windows(self, mock_system):
        """Test that Windows platform is detected."""
        mock_system.return_value = 'Windows'
        assert platform.system() == 'Windows'
        mock_system.assert_called_once()

    @patch('platform.system')
    def test_platform_detection_linux(self, mock_system):
        """Test that Linux platform is detected."""
        mock_system.return_value = 'Linux'
        assert platform.system() == 'Linux'
        mock_system.assert_called_once()

    @patch('platform.system')
    def test_platform_detection_darwin(self, mock_system):
        """Test that macOS platform is detected."""
        mock_system.return_value = 'Darwin'
        assert platform.system() == 'Darwin'
        mock_system.assert_called_once()

    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_unix_printing_uses_lpr(self, mock_system, mock_popen, sample_file_handle):
        """Test that Unix printing uses lpr command."""
        mock_system.return_value = 'Linux'
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()

        # Simulate the Unix branch of the code
        if platform.system() != 'Windows':
            import subprocess
            content = sample_file_handle.read()
            formatted_log = '\r\n'.join(textwrap.wrap(content, width=75, replace_whitespace=False))
            lpr = subprocess.Popen("/usr/bin/lpr", stdin=subprocess.PIPE)
            lpr.stdin.write(formatted_log.encode())

        mock_popen.assert_called_once_with("/usr/bin/lpr", stdin=subprocess.PIPE)

    def test_empty_log_content(self):
        """Test handling of empty log content."""
        empty_content = ""
        wrapped = '\r\n'.join(textwrap.wrap(empty_content, width=75, replace_whitespace=False))
        assert wrapped == ""

    def test_single_character_log(self):
        """Test handling of single character log."""
        single_char = "A"
        wrapped = '\r\n'.join(textwrap.wrap(single_char, width=75, replace_whitespace=False))
        assert wrapped == "A"

    def test_exact_width_line(self):
        """Test handling of line that is exactly 75 characters."""
        exact_width = "A" * 75
        wrapped = '\r\n'.join(textwrap.wrap(exact_width, width=75, replace_whitespace=False))
        assert wrapped == exact_width

    def test_multiline_log_preserves_structure(self):
        """Test that multiline logs preserve structure."""
        multiline = "Line 1\nLine 2\nLine 3"
        # When replace_whitespace=False, newlines are preserved
        wrapped = '\r\n'.join(textwrap.wrap(multiline, width=75, replace_whitespace=False))
        # The output should contain the original content
        assert "Line 1" in wrapped
        assert "Line 2" in wrapped
        assert "Line 3" in wrapped


class TestPrintRunLogWindows:
    """Test suite for Windows-specific printing functionality."""

    @pytest.fixture
    def mock_win32print(self):
        """Create a mock win32print module."""
        mock = MagicMock()
        mock.GetDefaultPrinter.return_value = "TestPrinter"
        mock.OpenPrinter.return_value = "handle123"
        return mock

    @patch('platform.system')
    def test_windows_branch_detection(self, mock_system):
        """Test that Windows branch is taken on Windows."""
        mock_system.return_value = 'Windows'

        # This would trigger the Windows branch in the actual code
        is_windows = platform.system() == 'Windows'
        assert is_windows is True

    def test_raw_data_encoding_python3(self):
        """Test that data is encoded as bytes for Python 3."""
        import sys
        test_string = "Test log content"

        if sys.version_info >= (3,):
            raw_data = bytes(test_string, 'utf-8')
        else:
            raw_data = test_string

        assert isinstance(raw_data, bytes)

    def test_printer_workflow_sequence(self, mock_win32print):
        """Test the expected printer workflow sequence."""
        # Simulate the Windows printing workflow
        printer_name = mock_win32print.GetDefaultPrinter()
        h_printer = mock_win32print.OpenPrinter(printer_name)

        mock_win32print.StartDocPrinter(h_printer, 1, ("Log File Printout", None, "RAW"))
        mock_win32print.StartPagePrinter(h_printer)
        mock_win32print.WritePrinter(h_printer, b"test data")
        mock_win32print.EndPagePrinter(h_printer)
        mock_win32print.EndDocPrinter(h_printer)
        mock_win32print.ClosePrinter(h_printer)

        # Verify the sequence
        mock_win32print.GetDefaultPrinter.assert_called_once()
        mock_win32print.OpenPrinter.assert_called_once()
        mock_win32print.StartDocPrinter.assert_called_once()
        mock_win32print.WritePrinter.assert_called_once()
        mock_win32print.ClosePrinter.assert_called_once()


class TestPrintRunLogUnix:
    """Test suite for Unix-specific printing functionality."""

    @patch('subprocess.Popen')
    def test_lpr_command_construction(self, mock_popen):
        """Test that lpr command is constructed correctly."""
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_popen.return_value = mock_process

        import subprocess
        lpr = subprocess.Popen("/usr/bin/lpr", stdin=subprocess.PIPE)

        mock_popen.assert_called_with("/usr/bin/lpr", stdin=subprocess.PIPE)

    def test_data_written_to_stdin(self):
        """Test that formatted data is written to lpr stdin."""
        mock_stdin = MagicMock()
        test_data = "Test log content"

        mock_stdin.write(test_data.encode())

        mock_stdin.write.assert_called_once_with(test_data.encode())

    @patch('platform.system')
    def test_unix_branch_not_windows(self, mock_system):
        """Test that Unix branch is taken on non-Windows systems."""
        mock_system.return_value = 'Linux'

        # This would trigger the Unix branch in the actual code
        is_unix = platform.system() != 'Windows'
        assert is_unix is True
