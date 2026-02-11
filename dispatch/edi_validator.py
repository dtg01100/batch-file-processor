"""EDI Validator component for dispatch processing.

This module provides a testable wrapper around the EDI validation functionality,
using dependency injection for file system operations.
"""

from io import StringIO
from typing import Optional, Protocol, runtime_checkable

from dispatch.interfaces import FileSystemInterface, ValidatorInterface


class EDIValidator:
    """EDI file validator with dependency injection support.
    
    This class wraps the EDI validation functionality, allowing for
    testable validation through injected file system interfaces.
    
    Attributes:
        fs: File system interface for file operations
        errors: StringIO buffer for error messages
        has_errors: Flag indicating if validation errors occurred
        has_minor_errors: Flag indicating if minor errors occurred
    """
    
    def __init__(self, file_system: Optional[FileSystemInterface] = None):
        """Initialize the EDI validator.
        
        Args:
            file_system: Optional file system interface (uses RealFileSystem if None)
        """
        self.fs = file_system or RealFileSystem()
        self.errors: StringIO = StringIO()
        self.has_errors: bool = False
        self.has_minor_errors: bool = False
    
    def validate(self, file_path: str) -> tuple[bool, list[str]]:
        """Validate an EDI file.
        
        Args:
            file_path: Path to the EDI file to validate
            
        Returns:
            Tuple of (is_valid, errors) where errors is a list of
            error messages (empty if valid)
        """
        self.errors = StringIO()
        self.has_errors = False
        self.has_minor_errors = False
        error_list: list[str] = []
        
        try:
            # First check if file is valid EDI format
            is_valid_edi, check_line = self._check_edi_format(file_path)
            
            if not is_valid_edi:
                self.has_errors = True
                error_msg = f"EDI check failed on line number: {check_line}"
                self.errors.write(error_msg + "\r\n")
                error_list.append(error_msg)
                return False, error_list
            
            # Check for specific EDI issues
            issues = self._check_edi_issues(file_path)
            error_list.extend(issues)
            
            return not self.has_errors, error_list
            
        except Exception as e:
            self.has_errors = True
            error_msg = f"Validation error: {str(e)}"
            self.errors.write(error_msg + "\r\n")
            error_list.append(error_msg)
            return False, error_list
    
    def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
        """Validate an EDI file and return both errors and warnings.
        
        Args:
            file_path: Path to the EDI file to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = StringIO()
        self.has_errors = False
        self.has_minor_errors = False
        errors: list[str] = []
        warnings: list[str] = []
        
        try:
            is_valid_edi, check_line = self._check_edi_format(file_path)
            
            if not is_valid_edi:
                self.has_errors = True
                error_msg = f"EDI check failed on line number: {check_line}"
                self.errors.write(error_msg + "\r\n")
                errors.append(error_msg)
                return False, errors, warnings
            
            # Check for issues and categorize them
            self._check_edi_issues_with_warnings(file_path, errors, warnings)
            
            return not self.has_errors, errors, warnings
            
        except Exception as e:
            self.has_errors = True
            error_msg = f"Validation error: {str(e)}"
            self.errors.write(error_msg + "\r\n")
            errors.append(error_msg)
            return False, errors, warnings
    
    def _check_edi_format(self, file_path: str) -> tuple[bool, int]:
        """Check if file is a valid EDI format.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            Tuple of (is_valid, line_number) where line_number is the
            line where validation failed (0 if valid)
        """
        try:
            content = self.fs.read_file_text(file_path)
            lines = content.split('\n')
            
            # Check first character is 'A'
            if not lines or len(lines[0]) == 0 or lines[0][0] != 'A':
                return False, 1
            
            # Check each line starts with valid record type
            for line_num, line in enumerate(lines, start=1):
                if not line:
                    continue
                first_char = line[0] if line else ''
                if first_char not in ('A', 'B', 'C', ''):
                    return False, line_num
                
                # Validate B records
                if first_char == 'B':
                    if len(line) != 77 and len(line) != 71:
                        return False, line_num
                    
                    # Check item number is numeric
                    try:
                        _ = int(line[1:12])
                    except ValueError:
                        if line[1:12] != "           ":
                            return False, line_num
                    
                    # Check for missing pricing in 71-char lines
                    if len(line) == 71 and line[51:67] != "                ":
                        return False, line_num
            
            return True, len(lines)
            
        except Exception:
            return False, 0
    
    def _check_edi_issues(self, file_path: str) -> list[str]:
        """Check for specific EDI issues.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            List of issue messages
        """
        issues: list[str] = []
        
        try:
            content = self.fs.read_file_text(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, start=1):
                if not line or line[0] != 'B':
                    continue
                
                proposed_upc = line[1:12]
                stripped_upc = str(proposed_upc).strip()
                
                # Check for suppressed UPC (8 chars)
                if len(stripped_upc) == 8:
                    self.has_minor_errors = True
                    issues.append(f"Suppressed UPC in line {line_num}")
                
                # Check for truncated UPC (1-10 chars)
                elif 0 < len(stripped_upc) < 11:
                    self.has_minor_errors = True
                    issues.append(f"Truncated UPC in line {line_num}")
                
                # Check for blank UPC
                if line[1:12] == "           ":
                    self.has_minor_errors = True
                    issues.append(f"Blank UPC in line {line_num}")
                
                # Check for missing pricing
                if len(line) == 71:
                    self.has_minor_errors = True
                    issues.append(f"Missing pricing information in line {line_num}")
            
            return issues
            
        except Exception as e:
            self.has_errors = True
            issues.append(f"Error checking EDI issues: {str(e)}")
            return issues
    
    def _check_edi_issues_with_warnings(
        self,
        file_path: str,
        errors: list[str],
        warnings: list[str]
    ) -> None:
        """Check for EDI issues and categorize as errors or warnings.
        
        Args:
            file_path: Path to the file to check
            errors: List to append error messages to
            warnings: List to append warning messages to
        """
        try:
            content = self.fs.read_file_text(file_path)
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, start=1):
                if not line or line[0] != 'B':
                    continue
                
                proposed_upc = line[1:12]
                stripped_upc = str(proposed_upc).strip()
                
                # Warnings (minor errors)
                if len(stripped_upc) == 8:
                    self.has_minor_errors = True
                    warnings.append(f"Suppressed UPC in line {line_num}")
                elif 0 < len(stripped_upc) < 11:
                    self.has_minor_errors = True
                    warnings.append(f"Truncated UPC in line {line_num}")
                
                if line[1:12] == "           ":
                    self.has_minor_errors = True
                    warnings.append(f"Blank UPC in line {line_num}")
                
                if len(line) == 71:
                    self.has_minor_errors = True
                    warnings.append(f"Missing pricing information in line {line_num}")
                    
        except Exception as e:
            self.has_errors = True
            errors.append(f"Error checking EDI issues: {str(e)}")
    
    def get_error_log(self) -> str:
        """Get the current error log contents.
        
        Returns:
            Error log as string
        """
        return self.errors.getvalue()
    
    def clear(self) -> None:
        """Clear the validator state."""
        self.errors = StringIO()
        self.has_errors = False
        self.has_minor_errors = False


class RealFileSystem:
    """Real file system implementation for production use.
    
    This class provides direct file system access, suitable for
    production use but difficult to test.
    """
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file contents as text.
        
        Args:
            path: Path to the file
            encoding: Text encoding (default: utf-8)
            
        Returns:
            File contents as string
        """
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    
    def read_file(self, path: str) -> bytes:
        """Read file contents as bytes.
        
        Args:
            path: Path to the file
            
        Returns:
            File contents as bytes
        """
        with open(path, 'rb') as f:
            return f.read()
    
    def write_file(self, path: str, data: bytes) -> None:
        """Write bytes to a file.
        
        Args:
            path: Path to the file
            data: Bytes to write
        """
        with open(path, 'wb') as f:
            f.write(data)
    
    def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
        """Write text to a file.
        
        Args:
            path: Path to the file
            data: String to write
            encoding: Text encoding (default: utf-8)
        """
        with open(path, 'w', encoding=encoding) as f:
            f.write(data)
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        import os
        return os.path.isfile(path)
    
    def dir_exists(self, path: str) -> bool:
        """Check if a directory exists."""
        import os
        return os.path.isdir(path)
    
    def list_files(self, path: str) -> list[str]:
        """List all files in a directory."""
        import os
        if not os.path.isdir(path):
            return []
        return [
            os.path.abspath(os.path.join(path, f))
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f))
        ]
    
    def mkdir(self, path: str) -> None:
        """Create a directory."""
        import os
        os.mkdir(path)
    
    def makedirs(self, path: str) -> None:
        """Create a directory and all parent directories."""
        import os
        os.makedirs(path, exist_ok=True)
    
    def copy_file(self, src: str, dst: str) -> None:
        """Copy a file."""
        import shutil
        shutil.copyfile(src, dst)
    
    def remove_file(self, path: str) -> None:
        """Remove a file."""
        import os
        os.remove(path)
    
    def get_absolute_path(self, path: str) -> str:
        """Get the absolute path."""
        import os
        return os.path.abspath(path)
