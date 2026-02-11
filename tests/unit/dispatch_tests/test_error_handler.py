"""Tests for dispatch/error_handler.py module."""

import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from dispatch.error_handler import ErrorHandler, do, RealFileSystem


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.records = []
    
    def insert(self, record: dict) -> None:
        self.records.append(record)
    
    def find(self, **kwargs) -> list[dict]:
        return self.records


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self):
        self.files = {}
        self.dirs = set()
    
    def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
        self.files[path] = data
    
    def dir_exists(self, path: str) -> bool:
        return path in self.dirs
    
    def makedirs(self, path: str) -> None:
        self.dirs.add(path)


class TestErrorHandler:
    """Tests for ErrorHandler class."""
    
    def test_init_default(self):
        """Test initialization with defaults."""
        handler = ErrorHandler()
        
        assert handler.db is None
        assert handler.log_path is None
        assert handler.errors == []
    
    def test_init_with_database(self):
        """Test initialization with database."""
        db = MockDatabase()
        handler = ErrorHandler(database=db)
        
        assert handler.db is db
    
    def test_init_with_log_path(self):
        """Test initialization with log path."""
        handler = ErrorHandler(log_path='/var/log/errors.log')
        
        assert handler.log_path == '/var/log/errors.log'
    
    def test_record_error_basic(self):
        """Test basic error recording."""
        handler = ErrorHandler()
        
        handler.record_error(
            folder='/data/input',
            filename='/data/input/file.edi',
            error=Exception("Test error")
        )
        
        assert len(handler.errors) == 1
        assert handler.errors[0]['folder'] == '/data/input'
        assert handler.errors[0]['filename'] == '/data/input/file.edi'
        assert handler.errors[0]['error_message'] == 'Test error'
    
    def test_record_error_with_context(self):
        """Test error recording with context."""
        handler = ErrorHandler()
        
        handler.record_error(
            folder='/data/input',
            filename='file.edi',
            error=ValueError("Invalid value"),
            context={'line_number': 42, 'operation': 'parse'}
        )
        
        assert handler.errors[0]['context']['line_number'] == 42
        assert handler.errors[0]['context']['operation'] == 'parse'
    
    def test_record_error_with_source(self):
        """Test error recording with source."""
        handler = ErrorHandler()
        
        handler.record_error(
            folder='/data/input',
            filename='file.edi',
            error=Exception("Error"),
            error_source="EDI Parser"
        )
        
        assert handler.errors[0]['error_source'] == "EDI Parser"
    
    def test_record_error_to_database(self):
        """Test error persistence to database."""
        db = MockDatabase()
        handler = ErrorHandler(database=db)
        
        handler.record_error(
            folder='/data/input',
            filename='file.edi',
            error=Exception("Test error")
        )
        
        assert len(db.records) == 1
        assert db.records[0]['error_message'] == 'Test error'
    
    def test_record_error_to_logs_non_threaded(self):
        """Test error recording to logs (non-threaded)."""
        handler = ErrorHandler()
        run_log = MagicMock()
        errors_log = StringIO()
        
        handler.record_error_to_logs(
            run_log=run_log,
            errors_log=errors_log,
            error_message="Test error",
            filename="file.edi",
            error_source="Test Source",
            threaded=False
        )
        
        # run_log.write should be called with encoded message
        run_log.write.assert_called_once()
        # errors_log should contain the message
        assert "Test error" in errors_log.getvalue()
    
    def test_record_error_to_logs_threaded(self):
        """Test error recording to logs (threaded mode)."""
        handler = ErrorHandler()
        run_log = []
        errors_log = []
        
        result = handler.record_error_to_logs(
            run_log=run_log,
            errors_log=errors_log,
            error_message="Test error",
            filename="file.edi",
            error_source="Test Source",
            threaded=True
        )
        
        assert len(run_log) == 1
        assert len(errors_log) == 1
        assert "Test error" in run_log[0]
    
    def test_format_error_message(self):
        """Test error message formatting."""
        handler = ErrorHandler()
        
        with patch('dispatch.error_handler.time') as mock_time:
            mock_time.ctime.return_value = "Mon Jan 15 10:30:00 2024"
            
            message = handler._format_error_message(
                error_message="File not found",
                filename="/data/file.edi",
                error_source="FileReader"
            )
        
        assert "Mon Jan 15 10:30:00 2024" in message
        assert "FileReader" in message
        assert "/data/file.edi" in message
        assert "File not found" in message
    
    def test_get_errors(self):
        """Test getting all errors."""
        handler = ErrorHandler()
        
        handler.record_error('folder1', 'file1', Exception("Error 1"))
        handler.record_error('folder2', 'file2', Exception("Error 2"))
        
        errors = handler.get_errors()
        
        assert len(errors) == 2
        assert errors[0]['error_message'] == 'Error 1'
        assert errors[1]['error_message'] == 'Error 2'
    
    def test_get_error_log(self):
        """Test getting error log contents."""
        handler = ErrorHandler()
        
        handler.record_error('folder', 'file', Exception("Test error"))
        
        log = handler.get_error_log()
        
        assert "Test error" in log
    
    def test_clear_errors(self):
        """Test clearing errors."""
        handler = ErrorHandler()
        
        handler.record_error('folder', 'file', Exception("Error"))
        handler.clear_errors()
        
        assert handler.errors == []
        assert handler.get_error_log() == ''
    
    def test_has_errors(self):
        """Test has_errors method."""
        handler = ErrorHandler()
        
        assert handler.has_errors() is False
        
        handler.record_error('folder', 'file', Exception("Error"))
        
        assert handler.has_errors() is True
    
    def test_get_error_count(self):
        """Test getting error count."""
        handler = ErrorHandler()
        
        assert handler.get_error_count() == 0
        
        handler.record_error('folder1', 'file1', Exception("Error 1"))
        handler.record_error('folder2', 'file2', Exception("Error 2"))
        
        assert handler.get_error_count() == 2
    
    def test_write_error_log_file(self):
        """Test writing error log to file."""
        mock_fs = MockFileSystem()
        handler = ErrorHandler(file_system=mock_fs)
        
        handler.record_error('folder', 'file', Exception("Test error"))
        
        result = handler.write_error_log_file('/var/log/error.log', version='1.0.0')
        
        assert result is True
        assert '/var/log/error.log' in mock_fs.files
        assert '1.0.0' in mock_fs.files['/var/log/error.log']
        assert 'Test error' in mock_fs.files['/var/log/error.log']
    
    def test_write_error_log_file_creates_directory(self):
        """Test writing error log creates directory if needed."""
        mock_fs = MockFileSystem()
        handler = ErrorHandler(file_system=mock_fs)
        
        handler.record_error('folder', 'file', Exception("Error"))
        
        result = handler.write_error_log_file('/var/log/subdir/error.log')
        
        assert result is True
        assert '/var/log/subdir' in mock_fs.dirs


class TestDoFunction:
    """Tests for backward-compatible do function."""
    
    def test_do_non_threaded(self):
        """Test do function in non-threaded mode."""
        run_log = MagicMock()
        errors_log = StringIO()
        
        do(
            run_log=run_log,
            errors_log=errors_log,
            error_message="Test error",
            filename="file.edi",
            error_source="Test",
            threaded=False
        )
        
        run_log.write.assert_called_once()
        assert "Test error" in errors_log.getvalue()
    
    def test_do_threaded(self):
        """Test do function in threaded mode."""
        run_log = []
        errors_log = []
        
        result = do(
            run_log=run_log,
            errors_log=errors_log,
            error_message="Test error",
            filename="file.edi",
            error_source="Test",
            threaded=True
        )
        
        assert len(run_log) == 1
        assert len(errors_log) == 1
        assert "Test error" in run_log[0]


class TestRealFileSystem:
    """Tests for RealFileSystem class in error_handler module."""
    
    def test_write_file_text(self):
        """Test writing text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = RealFileSystem()
            path = os.path.join(tmpdir, 'test.txt')
            
            fs.write_file_text(path, "content")
            
            with open(path, 'r') as f:
                assert f.read() == "content"
    
    def test_dir_exists(self):
        """Test directory existence check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = RealFileSystem()
            
            assert fs.dir_exists(tmpdir) is True
            assert fs.dir_exists('/nonexistent') is False
    
    def test_makedirs(self):
        """Test creating directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = RealFileSystem()
            nested = os.path.join(tmpdir, 'a', 'b', 'c')
            
            fs.makedirs(nested)
            
            assert os.path.isdir(nested)


class TestErrorHandlerEdgeCases:
    """Edge case tests for ErrorHandler."""
    
    def test_database_insert_failure(self):
        """Test that database insert failure doesn't raise."""
        class FailingDatabase:
            def insert(self, record):
                raise Exception("Database error")
        
        handler = ErrorHandler(database=FailingDatabase())
        
        # Should not raise
        handler.record_error('folder', 'file', Exception("Error"))
        
        # Error should still be in memory
        assert len(handler.errors) == 1
    
    def test_multiple_errors_same_file(self):
        """Test recording multiple errors for same file."""
        handler = ErrorHandler()
        
        handler.record_error('folder', 'file.edi', Exception("Error 1"))
        handler.record_error('folder', 'file.edi', Exception("Error 2"))
        handler.record_error('folder', 'file.edi', Exception("Error 3"))
        
        assert handler.get_error_count() == 3
    
    def test_error_with_special_characters(self):
        """Test error with special characters in message."""
        handler = ErrorHandler()
        
        handler.record_error(
            folder='/data/folder',
            filename='file.edi',
            error=Exception("Error with special chars: \n\t\r\"'")
        )
        
        log = handler.get_error_log()
        
        assert "Error with special chars" in log
    
    def test_error_with_unicode(self):
        """Test error with unicode characters."""
        handler = ErrorHandler()
        
        handler.record_error(
            folder='/data/folder',
            filename='file.edi',
            error=Exception("Unicode error: 你好 世界 🌍")
        )
        
        log = handler.get_error_log()
        
        assert "你好 世界" in log
    
    def test_empty_error_message(self):
        """Test error with empty message."""
        handler = ErrorHandler()
        
        handler.record_error(
            folder='folder',
            filename='file',
            error=Exception("")
        )
        
        assert len(handler.errors) == 1
        assert handler.errors[0]['error_message'] == ''
    
    def test_very_long_error_message(self):
        """Test error with very long message."""
        handler = ErrorHandler()
        
        long_message = "Error: " + "x" * 10000
        
        handler.record_error(
            folder='folder',
            filename='file',
            error=Exception(long_message)
        )
        
        assert len(handler.errors[0]['error_message']) == 10007


class TestErrorHandlerIntegration:
    """Integration tests for ErrorHandler."""
    
    def test_full_error_workflow(self):
        """Test full error handling workflow."""
        db = MockDatabase()
        handler = ErrorHandler(database=db)
        
        # Record multiple errors
        for i in range(3):
            handler.record_error(
                folder=f'/data/folder{i}',
                filename=f'file{i}.edi',
                error=Exception(f"Error {i}"),
                error_source=f"Source{i}"
            )
        
        # Check state
        assert handler.has_errors()
        assert handler.get_error_count() == 3
        assert len(db.records) == 3
        
        # Get errors
        errors = handler.get_errors()
        assert all(e['error_message'].startswith('Error') for e in errors)
        
        # Clear
        handler.clear_errors()
        assert not handler.has_errors()
        assert handler.get_error_count() == 0
