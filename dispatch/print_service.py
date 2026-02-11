"""PrintService for printing run logs.

This module provides a refactored, testable implementation of printing,
using Protocol interfaces for dependency injection and handling
platform-specific printing operations.
"""

import sys
import textwrap
import logging
from typing import Protocol, runtime_checkable, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@runtime_checkable
class PrintServiceProtocol(Protocol):
    """Protocol for print service implementations.
    
    Implementations should handle printing files to physical or virtual printers,
    abstracting away platform-specific details for testing.
    """
    
    def print_file(self, file_path: str) -> bool:
        """Print a file.
        
        Args:
            file_path: Path to the file to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        ...
    
    def print_content(self, content: str) -> bool:
        """Print text content directly.
        
        Args:
            content: Text content to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        ...
    
    def is_available(self) -> bool:
        """Check if printing is available on this platform.
        
        Returns:
            True if printing is available, False otherwise
        """
        ...


class BasePrintService(ABC):
    """Base class for print services with common functionality."""
    
    def __init__(self, line_width: int = 75):
        """Initialize the print service.
        
        Args:
            line_width: Maximum line width for text wrapping
        """
        self.line_width = line_width
    
    def format_content(self, content: str) -> str:
        """Format content for printing with word wrap.
        
        Args:
            content: Raw text content to format
            
        Returns:
            Formatted text with line wrapping
        """
        return '\r\n'.join(
            textwrap.wrap(content, width=self.line_width, replace_whitespace=False)
        )
    
    @abstractmethod
    def print_file(self, file_path: str) -> bool:
        """Print a file."""
        ...
    
    @abstractmethod
    def print_content(self, content: str) -> bool:
        """Print text content directly."""
        ...
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if printing is available."""
        ...


class WindowsPrintService(BasePrintService):
    """Print service for Windows platforms using win32print."""
    
    def __init__(self, line_width: int = 75):
        """Initialize the Windows print service.
        
        Args:
            line_width: Maximum line width for text wrapping
        """
        super().__init__(line_width=line_width)
        self._win32print = None
        self._printer_name: Optional[str] = None
    
    def _get_win32print(self):
        """Lazy import win32print to avoid import errors on non-Windows."""
        if self._win32print is None:
            try:
                import win32print
                self._win32print = win32print
            except ImportError:
                logger.warning("win32print not available")
                return None
        return self._win32print
    
    def _get_default_printer(self) -> Optional[str]:
        """Get the default printer name.
        
        Returns:
            Default printer name or None if not available
        """
        win32print = self._get_win32print()
        if win32print is None:
            return None
        try:
            return win32print.GetDefaultPrinter()
        except Exception as e:
            logger.error(f"Failed to get default printer: {e}")
            return None
    
    def print_file(self, file_path: str) -> bool:
        """Print a file on Windows.
        
        Args:
            file_path: Path to the file to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return self.print_content(content)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to read file for printing: {e}")
            return False
    
    def print_content(self, content: str) -> bool:
        """Print text content on Windows.
        
        Args:
            content: Text content to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        win32print = self._get_win32print()
        if win32print is None:
            logger.error("win32print not available")
            return False
        
        printer_name = self._get_default_printer()
        if not printer_name:
            logger.error("No default printer available")
            return False
        
        try:
            formatted_log = self.format_content(content)
            
            if sys.version_info >= (3,):
                raw_data = bytes(formatted_log, 'utf-8')
            else:
                raw_data = formatted_log
            
            h_printer = win32print.OpenPrinter(printer_name)
            try:
                _ = win32print.StartDocPrinter(
                    h_printer, 1, ("Log File Printout", None, "RAW")
                )
                try:
                    win32print.StartPagePrinter(h_printer)
                    win32print.WritePrinter(h_printer, raw_data)
                    win32print.EndPagePrinter(h_printer)
                finally:
                    win32print.EndDocPrinter(h_printer)
            finally:
                win32print.ClosePrinter(h_printer)
            
            logger.info(f"Successfully printed to {printer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to print: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Windows printing is available.
        
        Returns:
            True if running on Windows with win32print available
        """
        return sys.platform == 'win32' and self._get_win32print() is not None


class UnixPrintService(BasePrintService):
    """Print service for Unix-like platforms using lpr command."""
    
    def __init__(self, line_width: int = 75, lpr_path: str = "/usr/bin/lpr"):
        """Initialize the Unix print service.
        
        Args:
            line_width: Maximum line width for text wrapping
            lpr_path: Path to the lpr command
        """
        super().__init__(line_width=line_width)
        self.lpr_path = lpr_path
    
    def print_file(self, file_path: str) -> bool:
        """Print a file on Unix-like systems.
        
        Args:
            file_path: Path to the file to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return self.print_content(content)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to read file for printing: {e}")
            return False
    
    def print_content(self, content: str) -> bool:
        """Print text content on Unix-like systems.
        
        Args:
            content: Text content to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        import subprocess
        
        try:
            formatted_log = self.format_content(content)
            
            lpr = subprocess.Popen(
                [self.lpr_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = lpr.communicate(input=formatted_log.encode('utf-8'))
            
            if lpr.returncode != 0:
                logger.error(f"lpr command failed: {stderr.decode('utf-8')}")
                return False
            
            logger.info("Successfully printed via lpr")
            return True
            
        except FileNotFoundError:
            logger.error(f"lpr command not found at {self.lpr_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to print: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Unix printing is available.
        
        Returns:
            True if running on non-Windows with lpr available
        """
        if sys.platform == 'win32':
            return False
        
        import os
        return os.path.exists(self.lpr_path)


class MockPrintService(BasePrintService):
    """Mock print service for testing.
    
    Records all print operations for verification in tests.
    """
    
    def __init__(self, line_width: int = 75, should_fail: bool = False):
        """Initialize the mock print service.
        
        Args:
            line_width: Maximum line width for text wrapping
            should_fail: If True, all print operations will fail
        """
        super().__init__(line_width=line_width)
        self.printed_files: list[str] = []
        self.printed_content: list[str] = []
        self.should_fail = should_fail
    
    def print_file(self, file_path: str) -> bool:
        """Record a file print attempt.
        
        Args:
            file_path: Path to the file to print
            
        Returns:
            False if should_fail is True, True otherwise
        """
        if self.should_fail:
            return False
        
        self.printed_files.append(file_path)
        return True
    
    def print_content(self, content: str) -> bool:
        """Record a content print attempt.
        
        Args:
            content: Text content to print
            
        Returns:
            False if should_fail is True, True otherwise
        """
        if self.should_fail:
            return False
        
        self.printed_content.append(content)
        return True
    
    def is_available(self) -> bool:
        """Mock is always available.
        
        Returns:
            Always True for testing
        """
        return True
    
    def reset(self) -> None:
        """Clear all recorded print operations."""
        self.printed_files.clear()
        self.printed_content.clear()
    
    def get_last_printed_file(self) -> Optional[str]:
        """Get the most recently printed file.
        
        Returns:
            The last printed file path, or None if no files printed
        """
        return self.printed_files[-1] if self.printed_files else None
    
    def get_last_printed_content(self) -> Optional[str]:
        """Get the most recently printed content.
        
        Returns:
            The last printed content, or None if no content printed
        """
        return self.printed_content[-1] if self.printed_content else None


class NullPrintService(BasePrintService):
    """Null print service that does nothing.
    
    Useful for headless operation or when printing is not needed.
    """
    
    def __init__(self, line_width: int = 75):
        """Initialize the null print service."""
        super().__init__(line_width=line_width)
    
    def print_file(self, file_path: str) -> bool:
        """Do nothing, return True.
        
        Args:
            file_path: Path to the file (ignored)
            
        Returns:
            Always True
        """
        return True
    
    def print_content(self, content: str) -> bool:
        """Do nothing, return True.
        
        Args:
            content: Text content (ignored)
            
        Returns:
            Always True
        """
        return True
    
    def is_available(self) -> bool:
        """Null service is always "available".
        
        Returns:
            Always True
        """
        return True


class RunLogPrinter:
    """Service for printing run logs.
    
    This class coordinates the printing of run logs, using an injected
    print service for testability.
    """
    
    def __init__(self, print_service: PrintServiceProtocol, line_width: int = 75):
        """Initialize the run log printer.
        
        Args:
            print_service: Service for printing
            line_width: Maximum line width for text wrapping
        """
        self.print_service = print_service
        self.line_width = line_width
    
    def print_run_log(self, log_path: str) -> bool:
        """Print a run log file.
        
        Args:
            log_path: Path to the log file to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        if not self.print_service.is_available():
            logger.warning("Print service is not available")
            return False
        
        return self.print_service.print_file(log_path)
    
    def print_run_log_content(self, content: str) -> bool:
        """Print run log content directly.
        
        Args:
            content: Log content to print
            
        Returns:
            True if printing was successful, False otherwise
        """
        if not self.print_service.is_available():
            logger.warning("Print service is not available")
            return False
        
        return self.print_service.print_content(content)


def create_print_service(line_width: int = 75) -> PrintServiceProtocol:
    """Factory function to create the appropriate print service for the platform.
    
    Args:
        line_width: Maximum line width for text wrapping
        
    Returns:
        Platform-appropriate PrintService instance
    """
    if sys.platform == 'win32':
        return WindowsPrintService(line_width=line_width)
    else:
        return UnixPrintService(line_width=line_width)


def create_run_log_printer(line_width: int = 75) -> RunLogPrinter:
    """Factory function to create a RunLogPrinter with platform-appropriate service.
    
    Args:
        line_width: Maximum line width for text wrapping
        
    Returns:
        Configured RunLogPrinter instance
    """
    print_service = create_print_service(line_width=line_width)
    return RunLogPrinter(print_service=print_service, line_width=line_width)
