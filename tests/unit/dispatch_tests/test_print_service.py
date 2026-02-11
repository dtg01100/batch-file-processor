"""Tests for the PrintService.

This module tests the refactored print service with mock implementations.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock

from dispatch.print_service import (
    PrintServiceProtocol,
    BasePrintService,
    WindowsPrintService,
    UnixPrintService,
    MockPrintService,
    NullPrintService,
    RunLogPrinter,
    create_print_service,
    create_run_log_printer,
)


class TestMockPrintService:
    """Tests for MockPrintService."""
    
    def test_print_file_records_file(self):
        """Test that print_file records the file path."""
        service = MockPrintService()
        
        result = service.print_file("/tmp/test.log")
        
        assert result is True
        assert "/tmp/test.log" in service.printed_files
        assert service.get_last_printed_file() == "/tmp/test.log"
    
    def test_print_content_records_content(self):
        """Test that print_content records the content."""
        service = MockPrintService()
        
        result = service.print_content("Test log content")
        
        assert result is True
        assert "Test log content" in service.printed_content
        assert service.get_last_printed_content() == "Test log content"
    
    def test_print_file_can_fail(self):
        """Test that print_file can be configured to fail."""
        service = MockPrintService(should_fail=True)
        
        result = service.print_file("/tmp/test.log")
        
        assert result is False
        assert len(service.printed_files) == 0
    
    def test_print_content_can_fail(self):
        """Test that print_content can be configured to fail."""
        service = MockPrintService(should_fail=True)
        
        result = service.print_content("Test content")
        
        assert result is False
        assert len(service.printed_content) == 0
    
    def test_is_available_always_true(self):
        """Test that mock service is always available."""
        service = MockPrintService()
        
        assert service.is_available() is True
    
    def test_reset_clears_records(self):
        """Test that reset clears all recorded data."""
        service = MockPrintService()
        service.print_file("/tmp/test.log")
        service.print_content("Content")
        
        service.reset()
        
        assert len(service.printed_files) == 0
        assert len(service.printed_content) == 0
    
    def test_get_last_printed_file_none_when_empty(self):
        """Test get_last_printed_file returns None when no files printed."""
        service = MockPrintService()
        
        assert service.get_last_printed_file() is None
    
    def test_get_last_printed_content_none_when_empty(self):
        """Test get_last_printed_content returns None when no content printed."""
        service = MockPrintService()
        
        assert service.get_last_printed_content() is None
    
    def test_multiple_prints(self):
        """Test multiple print operations."""
        service = MockPrintService()
        
        service.print_file("/tmp/log1.txt")
        service.print_file("/tmp/log2.txt")
        service.print_content("Content 1")
        service.print_content("Content 2")
        
        assert len(service.printed_files) == 2
        assert len(service.printed_content) == 2
        assert service.get_last_printed_file() == "/tmp/log2.txt"
        assert service.get_last_printed_content() == "Content 2"


class TestNullPrintService:
    """Tests for NullPrintService."""
    
    def test_print_file_returns_true(self):
        """Test that print_file always returns True."""
        service = NullPrintService()
        
        result = service.print_file("/tmp/test.log")
        
        assert result is True
    
    def test_print_content_returns_true(self):
        """Test that print_content always returns True."""
        service = NullPrintService()
        
        result = service.print_content("Test content")
        
        assert result is True
    
    def test_is_available_returns_true(self):
        """Test that null service is always available."""
        service = NullPrintService()
        
        assert service.is_available() is True


class TestBasePrintService:
    """Tests for BasePrintService formatting."""
    
    def test_format_content_wraps_lines(self):
        """Test that format_content wraps long lines."""
        service = MockPrintService(line_width=20)
        
        long_line = "This is a very long line that should be wrapped to multiple lines"
        formatted = service.format_content(long_line)
        
        # Check that lines are wrapped
        lines = formatted.split('\r\n')
        for line in lines:
            assert len(line) <= 20
    
    def test_format_content_preserves_newlines(self):
        """Test that format_content preserves existing newlines."""
        service = MockPrintService(line_width=75)
        
        content = "Line 1\nLine 2\nLine 3"
        formatted = service.format_content(content)
        
        # The content should still have line breaks
        assert "Line 1" in formatted
        assert "Line 2" in formatted
        assert "Line 3" in formatted


class TestWindowsPrintService:
    """Tests for WindowsPrintService."""
    
    def test_is_available_on_windows_with_win32print(self):
        """Test is_available returns True on Windows with win32print."""
        service = WindowsPrintService()
        
        # Mock sys.platform and win32print import
        with patch.object(sys, 'platform', 'win32'):
            with patch.dict('sys.modules', {'win32print': MagicMock()}):
                # Force re-evaluation
                service._win32print = None
                result = service.is_available()
                assert result is True
    
    def test_is_available_on_non_windows(self):
        """Test is_available returns False on non-Windows."""
        service = WindowsPrintService()
        
        with patch.object(sys, 'platform', 'linux'):
            service._win32print = None
            result = service.is_available()
            assert result is False
    
    def test_print_content_returns_false_without_win32print(self):
        """Test print_content returns False if win32print unavailable."""
        service = WindowsPrintService()
        service._win32print = None
        
        with patch.object(sys, 'platform', 'win32'):
            result = service.print_content("Test content")
            assert result is False
    
    def test_print_file_returns_false_for_missing_file(self):
        """Test print_file returns False for missing file."""
        service = WindowsPrintService()
        
        result = service.print_file("/nonexistent/file.txt")
        assert result is False


class TestUnixPrintService:
    """Tests for UnixPrintService."""
    
    def test_is_available_on_unix_with_lpr(self, tmp_path):
        """Test is_available returns True on Unix with lpr."""
        # Create a fake lpr
        fake_lpr = tmp_path / "lpr"
        fake_lpr.write_text("")
        
        service = UnixPrintService(lpr_path=str(fake_lpr))
        
        with patch.object(sys, 'platform', 'linux'):
            result = service.is_available()
            assert result is True
    
    def test_is_available_on_windows(self):
        """Test is_available returns False on Windows."""
        service = UnixPrintService()
        
        with patch.object(sys, 'platform', 'win32'):
            result = service.is_available()
            assert result is False
    
    def test_is_available_without_lpr(self):
        """Test is_available returns False if lpr doesn't exist."""
        service = UnixPrintService(lpr_path="/nonexistent/lpr")
        
        with patch.object(sys, 'platform', 'linux'):
            result = service.is_available()
            assert result is False
    
    def test_print_file_returns_false_for_missing_file(self):
        """Test print_file returns False for missing file."""
        service = UnixPrintService()
        
        result = service.print_file("/nonexistent/file.txt")
        assert result is False
    
    def test_print_content_with_subprocess(self, tmp_path):
        """Test print_content uses subprocess for printing."""
        fake_lpr = tmp_path / "lpr"
        fake_lpr.write_text("#!/bin/bash\necho 'printed'")
        fake_lpr.chmod(0o755)
        
        service = UnixPrintService(lpr_path=str(fake_lpr))
        
        with patch.object(sys, 'platform', 'linux'):
            result = service.print_content("Test content")
            # Should succeed since we have a valid lpr
            assert result is True


class TestRunLogPrinter:
    """Tests for RunLogPrinter."""
    
    def test_print_run_log_success(self, tmp_path):
        """Test printing a run log file."""
        log_file = tmp_path / "run.log"
        log_file.write_text("Run log content")
        
        mock_service = MockPrintService()
        printer = RunLogPrinter(print_service=mock_service)
        
        result = printer.print_run_log(str(log_file))
        
        assert result is True
        assert str(log_file) in mock_service.printed_files
    
    def test_print_run_log_content(self):
        """Test printing run log content directly."""
        mock_service = MockPrintService()
        printer = RunLogPrinter(print_service=mock_service)
        
        result = printer.print_run_log_content("Log content here")
        
        assert result is True
        assert "Log content here" in mock_service.printed_content
    
    def test_print_run_log_unavailable_service(self):
        """Test printing when service is unavailable."""
        # Create a service that's not available
        class UnavailableService:
            def is_available(self):
                return False
            def print_file(self, path):
                return True
            def print_content(self, content):
                return True
        
        printer = RunLogPrinter(print_service=UnavailableService())
        
        result = printer.print_run_log("/tmp/test.log")
        
        assert result is False
    
    def test_print_run_log_content_unavailable_service(self):
        """Test printing content when service is unavailable."""
        class UnavailableService:
            def is_available(self):
                return False
            def print_file(self, path):
                return True
            def print_content(self, content):
                return True
        
        printer = RunLogPrinter(print_service=UnavailableService())
        
        result = printer.print_run_log_content("Content")
        
        assert result is False
    
    def test_custom_line_width(self):
        """Test RunLogPrinter with custom line width."""
        mock_service = MockPrintService(line_width=50)
        printer = RunLogPrinter(print_service=mock_service, line_width=50)
        
        assert printer.line_width == 50


class TestCreatePrintService:
    """Tests for factory function."""
    
    def test_create_print_service_windows(self):
        """Test creating print service on Windows."""
        with patch.object(sys, 'platform', 'win32'):
            service = create_print_service()
            assert isinstance(service, WindowsPrintService)
    
    def test_create_print_service_unix(self):
        """Test creating print service on Unix."""
        with patch.object(sys, 'platform', 'linux'):
            service = create_print_service()
            assert isinstance(service, UnixPrintService)
    
    def test_create_print_service_custom_line_width(self):
        """Test creating print service with custom line width."""
        service = create_print_service(line_width=100)
        
        # Check line_width is set (implementation-specific)
        if hasattr(service, 'line_width'):
            assert service.line_width == 100


class TestCreateRunLogPrinter:
    """Tests for factory function."""
    
    def test_create_run_log_printer(self):
        """Test creating a RunLogPrinter."""
        printer = create_run_log_printer()
        
        assert isinstance(printer, RunLogPrinter)
        assert printer.print_service is not None
    
    def test_create_run_log_printer_custom_width(self):
        """Test creating RunLogPrinter with custom line width."""
        printer = create_run_log_printer(line_width=80)
        
        assert printer.line_width == 80


class TestPrintServiceProtocol:
    """Tests for Protocol compliance."""
    
    def test_mock_print_service_implements_protocol(self):
        """Test that MockPrintService implements PrintServiceProtocol."""
        service = MockPrintService()
        
        # Check protocol compliance
        assert isinstance(service, PrintServiceProtocol)
    
    def test_null_print_service_implements_protocol(self):
        """Test that NullPrintService implements PrintServiceProtocol."""
        service = NullPrintService()
        
        assert isinstance(service, PrintServiceProtocol)
    
    def test_windows_print_service_implements_protocol(self):
        """Test that WindowsPrintService implements PrintServiceProtocol."""
        service = WindowsPrintService()
        
        assert isinstance(service, PrintServiceProtocol)
    
    def test_unix_print_service_implements_protocol(self):
        """Test that UnixPrintService implements PrintServiceProtocol."""
        service = UnixPrintService()
        
        assert isinstance(service, PrintServiceProtocol)
