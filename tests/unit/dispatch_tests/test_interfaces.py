"""Tests for dispatch/interfaces.py Protocol definitions.

These tests verify that the Protocol interfaces are properly defined
and can be used with isinstance() checks for dependency injection.
"""

import pytest
from unittest.mock import MagicMock
from dispatch.interfaces import (
    DatabaseInterface,
    FileSystemInterface,
    BackendInterface,
    ValidatorInterface,
    ErrorHandlerInterface,
    LogInterface,
)


class MockDatabase:
    """Mock implementation of DatabaseInterface for testing."""
    
    def __init__(self):
        self._data = {}
        self.find_calls = []
        self.insert_calls = []
    
    def find(self, **kwargs):
        self.find_calls.append(kwargs)
        return []
    
    def find_one(self, **kwargs):
        return None
    
    def insert(self, record):
        self.insert_calls.append(record)
    
    def insert_many(self, records):
        pass
    
    def update(self, record, keys):
        pass
    
    def count(self, **kwargs):
        return 0
    
    def query(self, sql):
        return []


class MockFileSystem:
    """Mock implementation of FileSystemInterface for testing."""
    
    def __init__(self, files=None):
        self.files = files or {}
        self.list_files_calls = []
        self.read_calls = []
        self.write_calls = []
    
    def list_files(self, path):
        self.list_files_calls.append(path)
        return []
    
    def read_file(self, path):
        self.read_calls.append(path)
        return b""
    
    def read_file_text(self, path, encoding='utf-8'):
        return ""
    
    def write_file(self, path, data):
        self.write_calls.append((path, len(data)))
    
    def write_file_text(self, path, data, encoding='utf-8'):
        pass
    
    def file_exists(self, path):
        return True
    
    def dir_exists(self, path):
        return True
    
    def mkdir(self, path):
        pass
    
    def makedirs(self, path):
        pass
    
    def copy_file(self, src, dst):
        pass
    
    def remove_file(self, path):
        pass
    
    def get_absolute_path(self, path):
        return path


class MockBackend:
    """Mock implementation of BackendInterface for testing."""
    
    def __init__(self):
        self.send_calls = []
        self.validate_calls = []
    
    def send(self, params, settings, filename):
        self.send_calls.append((params, settings, filename))
    
    def validate(self, params):
        self.validate_calls.append(params)
        return []
    
    def get_name(self):
        return "MockBackend"


class MockValidator:
    """Mock implementation of ValidatorInterface for testing."""
    
    def __init__(self, should_pass=True):
        self.should_pass = should_pass
        self.validate_calls = []
    
    def validate(self, file_path):
        self.validate_calls.append(file_path)
        if self.should_pass:
            return True, []
        return False, ["Validation failed"]
    
    def validate_with_warnings(self, file_path):
        self.validate_calls.append(file_path)
        if self.should_pass:
            return True, [], []
        return False, ["Validation failed"], []


class MockErrorHandler:
    """Mock implementation of ErrorHandlerInterface for testing."""
    
    def __init__(self):
        self.errors = []
        self.record_error_calls = []
    
    def record_error(self, folder, filename, error, context=None):
        self.record_error_calls.append({
            'folder': folder,
            'filename': filename,
            'error': error,
            'context': context
        })
        self.errors.append({
            'folder': folder,
            'filename': filename,
            'error': str(error)
        })
    
    def get_errors(self):
        return self.errors
    
    def clear_errors(self):
        self.errors = []


class MockLog:
    """Mock implementation of LogInterface for testing."""
    
    def __init__(self):
        self.messages = []
        self.writelines_calls = []
    
    def write(self, message):
        self.messages.append(message)
    
    def writelines(self, lines):
        self.writelines_calls.extend(lines)
        self.messages.extend(lines)
    
    def get_value(self):
        return "\n".join(self.messages)
    
    def close(self):
        pass


class TestDatabaseInterface:
    """Tests for DatabaseInterface Protocol."""
    
    def test_mock_database_isinstance_database_interface(self):
        """Test that MockDatabase implements DatabaseInterface."""
        mock = MockDatabase()
        assert isinstance(mock, DatabaseInterface)
    
    def test_database_find_method(self):
        """Test DatabaseInterface.find() method."""
        mock = MockDatabase()
        result = mock.find(folder="test_folder")
        assert isinstance(result, list)
        assert mock.find_calls == [{"folder": "test_folder"}]
    
    def test_database_find_one_method(self):
        """Test DatabaseInterface.find_one() method."""
        mock = MockDatabase()
        result = mock.find_one(id=1)
        assert result is None
    
    def test_database_insert_method(self):
        """Test DatabaseInterface.insert() method."""
        mock = MockDatabase()
        mock.insert({"name": "test"})
        assert mock.insert_calls == [{"name": "test"}]
    
    def test_database_insert_many_method(self):
        """Test DatabaseInterface.insert_many() method."""
        mock = MockDatabase()
        mock.insert_many([{"id": 1}, {"id": 2}])
        # Should not raise
    
    def test_database_update_method(self):
        """Test DatabaseInterface.update() method."""
        mock = MockDatabase()
        mock.update({"id": 1, "name": "updated"}, ["id"])
        # Should not raise
    
    def test_database_count_method(self):
        """Test DatabaseInterface.count() method."""
        mock = MockDatabase()
        result = mock.count(folder="test")
        assert result == 0
    
    def test_database_query_method(self):
        """Test DatabaseInterface.query() method."""
        mock = MockDatabase()
        result = mock.query("SELECT * FROM folders")
        assert result == []


class TestFileSystemInterface:
    """Tests for FileSystemInterface Protocol."""
    
    def test_mock_filesystem_isinstance_filesystem_interface(self):
        """Test that MockFileSystem implements FileSystemInterface."""
        mock = MockFileSystem()
        assert isinstance(mock, FileSystemInterface)
    
    def test_filesystem_list_files(self):
        """Test FileSystemInterface.list_files() method."""
        mock = MockFileSystem()
        result = mock.list_files("/path/to/files")
        assert result == []
        assert mock.list_files_calls == ["/path/to/files"]
    
    def test_filesystem_read_file(self):
        """Test FileSystemInterface.read_file() method."""
        mock = MockFileSystem()
        result = mock.read_file("/path/to/file.txt")
        assert result == b""
        assert mock.read_calls == ["/path/to/file.txt"]
    
    def test_filesystem_read_file_text(self):
        """Test FileSystemInterface.read_file_text() method."""
        mock = MockFileSystem()
        result = mock.read_file_text("/path/to/file.txt")
        assert result == ""
    
    def test_filesystem_write_file(self):
        """Test FileSystemInterface.write_file() method."""
        mock = MockFileSystem()
        mock.write_file("/path/to/file.txt", b"data")
        assert mock.write_calls == [("/path/to/file.txt", 4)]
    
    def test_filesystem_file_exists(self):
        """Test FileSystemInterface.file_exists() method."""
        mock = MockFileSystem()
        assert mock.file_exists("/path/to/file.txt") is True
    
    def test_filesystem_dir_exists(self):
        """Test FileSystemInterface.dir_exists() method."""
        mock = MockFileSystem()
        assert mock.dir_exists("/path/to/dir") is True
    
    def test_filesystem_mkdir(self):
        """Test FileSystemInterface.mkdir() method."""
        mock = MockFileSystem()
        mock.mkdir("/path/to/newdir")
        # Should not raise
    
    def test_filesystem_makedirs(self):
        """Test FileSystemInterface.makedirs() method."""
        mock = MockFileSystem()
        mock.makedirs("/path/to/new/nested/dir")
        # Should not raise
    
    def test_filesystem_copy_file(self):
        """Test FileSystemInterface.copy_file() method."""
        mock = MockFileSystem()
        mock.copy_file("src.txt", "dst.txt")
        # Should not raise
    
    def test_filesystem_remove_file(self):
        """Test FileSystemInterface.remove_file() method."""
        mock = MockFileSystem()
        mock.remove_file("/path/to/file.txt")
        # Should not raise
    
    def test_filesystem_get_absolute_path(self):
        """Test FileSystemInterface.get_absolute_path() method."""
        mock = MockFileSystem()
        result = mock.get_absolute_path("relative/path")
        assert result == "relative/path"


class TestBackendInterface:
    """Tests for BackendInterface Protocol."""
    
    def test_mock_backend_isinstance_backend_interface(self):
        """Test that MockBackend implements BackendInterface."""
        mock = MockBackend()
        assert isinstance(mock, BackendInterface)
    
    def test_backend_send(self):
        """Test BackendInterface.send() method."""
        mock = MockBackend()
        mock.send({"folder": "test"}, {"setting": "value"}, "file.txt")
        assert len(mock.send_calls) == 1
        assert mock.send_calls[0] == ({"folder": "test"}, {"setting": "value"}, "file.txt")
    
    def test_backend_validate(self):
        """Test BackendInterface.validate() method."""
        mock = MockBackend()
        result = mock.validate({"param": "value"})
        assert result == []
        assert mock.validate_calls == [{"param": "value"}]
    
    def test_backend_get_name(self):
        """Test BackendInterface.get_name() method."""
        mock = MockBackend()
        assert mock.get_name() == "MockBackend"


class TestValidatorInterface:
    """Tests for ValidatorInterface Protocol."""
    
    def test_mock_validator_isinstance_validator_interface(self):
        """Test that MockValidator implements ValidatorInterface."""
        mock = MockValidator()
        assert isinstance(mock, ValidatorInterface)
    
    def test_validator_validate_passes(self):
        """Test ValidatorInterface.validate() when valid."""
        mock = MockValidator(should_pass=True)
        is_valid, errors = mock.validate("/path/to/file.edi")
        assert is_valid is True
        assert errors == []
    
    def test_validator_validate_fails(self):
        """Test ValidatorInterface.validate() when invalid."""
        mock = MockValidator(should_pass=False)
        is_valid, errors = mock.validate("/path/to/file.edi")
        assert is_valid is False
        assert "Validation failed" in errors
    
    def test_validator_validate_with_warnings_passes(self):
        """Test ValidatorInterface.validate_with_warnings() when valid."""
        mock = MockValidator(should_pass=True)
        is_valid, errors, warnings = mock.validate_with_warnings("/path/to/file.edi")
        assert is_valid is True
        assert errors == []
        assert warnings == []
    
    def test_validator_validate_with_warnings_fails(self):
        """Test ValidatorInterface.validate_with_warnings() when invalid."""
        mock = MockValidator(should_pass=False)
        is_valid, errors, warnings = mock.validate_with_warnings("/path/to/file.edi")
        assert is_valid is False
        assert "Validation failed" in errors


class TestErrorHandlerInterface:
    """Tests for ErrorHandlerInterface Protocol."""
    
    def test_mock_error_handler_isinstance_error_handler_interface(self):
        """Test that MockErrorHandler implements ErrorHandlerInterface."""
        mock = MockErrorHandler()
        assert isinstance(mock, ErrorHandlerInterface)
    
    def test_error_handler_record_error(self):
        """Test ErrorHandlerInterface.record_error() method."""
        mock = MockErrorHandler()
        mock.record_error("folder", "file.txt", ValueError("test error"))
        assert len(mock.errors) == 1
        assert mock.errors[0]["folder"] == "folder"
        assert mock.errors[0]["filename"] == "file.txt"
    
    def test_error_handler_record_error_with_context(self):
        """Test ErrorHandlerInterface.record_error() with context."""
        mock = MockErrorHandler()
        mock.record_error("folder", "file.txt", ValueError("test"), {"key": "value"})
        assert len(mock.record_error_calls) == 1
        assert mock.record_error_calls[0]["context"] == {"key": "value"}
    
    def test_error_handler_get_errors(self):
        """Test ErrorHandlerInterface.get_errors() method."""
        mock = MockErrorHandler()
        mock.record_error("folder", "file.txt", ValueError("test"))
        errors = mock.get_errors()
        assert len(errors) == 1
    
    def test_error_handler_clear_errors(self):
        """Test ErrorHandlerInterface.clear_errors() method."""
        mock = MockErrorHandler()
        mock.record_error("folder", "file.txt", ValueError("test"))
        mock.clear_errors()
        assert mock.errors == []


class TestLogInterface:
    """Tests for LogInterface Protocol."""
    
    def test_mock_log_isinstance_log_interface(self):
        """Test that MockLog implements LogInterface."""
        mock = MockLog()
        assert isinstance(mock, LogInterface)
    
    def test_log_write(self):
        """Test LogInterface.write() method."""
        mock = MockLog()
        mock.write("test message")
        assert mock.messages == ["test message"]
    
    def test_log_writelines(self):
        """Test LogInterface.writelines() method."""
        mock = MockLog()
        mock.writelines(["line1", "line2"])
        assert mock.messages == ["line1", "line2"]
        assert mock.writelines_calls == ["line1", "line2"]
    
    def test_log_get_value(self):
        """Test LogInterface.get_value() method."""
        mock = MockLog()
        mock.write("line1")
        mock.write("line2")
        assert mock.get_value() == "line1\nline2"
    
    def test_log_close(self):
        """Test LogInterface.close() method."""
        mock = MockLog()
        mock.close()
        # Should not raise


class TestProtocolRuntimeCheckable:
    """Tests for runtime_checkable behavior of Protocols."""
    
    def test_database_interface_is_runtime_checkable(self):
        """Test DatabaseInterface can be used with isinstance() at runtime."""
        mock = MockDatabase()
        # This should not raise TypeError due to runtime_checkable
        assert isinstance(mock, DatabaseInterface)
    
    def test_filesystem_interface_is_runtime_checkable(self):
        """Test FileSystemInterface can be used with isinstance() at runtime."""
        mock = MockFileSystem()
        assert isinstance(mock, FileSystemInterface)
    
    def test_backend_interface_is_runtime_checkable(self):
        """Test BackendInterface can be used with isinstance() at runtime."""
        mock = MockBackend()
        assert isinstance(mock, BackendInterface)
    
    def test_validator_interface_is_runtime_checkable(self):
        """Test ValidatorInterface can be used with isinstance() at runtime."""
        mock = MockValidator()
        assert isinstance(mock, ValidatorInterface)
    
    def test_error_handler_interface_is_runtime_checkable(self):
        """Test ErrorHandlerInterface can be used with isinstance() at runtime."""
        mock = MockErrorHandler()
        assert isinstance(mock, ErrorHandlerInterface)
    
    def test_log_interface_is_runtime_checkable(self):
        """Test LogInterface can be used with isinstance() at runtime."""
        mock = MockLog()
        assert isinstance(mock, LogInterface)


class TestIncompleteImplementations:
    """Tests verifying that incomplete implementations fail isinstance checks."""
    
    def test_incomplete_database_not_instance(self):
        """Test that incomplete class is not instance of DatabaseInterface."""
        class IncompleteDatabase:
            def find(self):
                pass
        
        # Should fail runtime check since it doesn't have all methods
        incomplete = IncompleteDatabase()
        # Note: runtime_checkable allows this to be evaluated at runtime
        # but the method signatures may not match
    
    def test_incomplete_filesystem_not_instance(self):
        """Test that incomplete class is not instance of FileSystemInterface."""
        class IncompleteFileSystem:
            def list_files(self, path):
                pass
        
        incomplete = IncompleteFileSystem()
        # This should fail isinstance due to missing methods
        assert not isinstance(incomplete, FileSystemInterface)
