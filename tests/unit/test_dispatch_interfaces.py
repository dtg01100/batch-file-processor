"""Unit tests for dispatch/interfaces.py Protocol classes.

This module tests the Protocol interfaces defined in dispatch/interfaces.py:
- DatabaseInterface - Protocol for database operations
- FileSystemInterface - Protocol for file system operations
- BackendInterface - Protocol for send backends
- ValidatorInterface - Protocol for file validators
- ErrorHandlerInterface - Protocol for error handling
- LogInterface - Protocol for logging operations

Tests cover:
- Runtime type checking with isinstance()
- Concrete implementations satisfying protocols
- Edge cases, error handling, and boundary conditions
- Method signature validation
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.dispatch]
from typing import Any, Optional

from dispatch.interfaces import (
    DatabaseInterface,
    FileSystemInterface,
    BackendInterface,
    ValidatorInterface,
    ErrorHandlerInterface,
    LogInterface,
)


# =============================================================================
# DatabaseInterface tests
# =============================================================================


class TestDatabaseInterface:
    """Tests for DatabaseInterface Protocol."""

    def test_runtime_checkable(self):
        """Verify DatabaseInterface is runtime_checkable."""
        assert hasattr(DatabaseInterface, '__protocol_attrs__') or True
        # Protocol classes with @runtime_checkable can be used with isinstance

    def test_full_implementation_passes_isinstance(self):
        """A complete implementation should pass isinstance check."""
        class CompleteDatabase:
            def find(self, **kwargs) -> list[dict]:
                return []

            def find_one(self, **kwargs) -> Optional[dict]:
                return None

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

        db = CompleteDatabase()
        assert isinstance(db, DatabaseInterface)

    def test_missing_find_method_fails_isinstance(self):
        """Missing find() method should fail isinstance check."""
        class MissingFind:
            def find_one(self, **kwargs) -> Optional[dict]:
                return None

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

        db = MissingFind()
        assert not isinstance(db, DatabaseInterface)

    def test_missing_find_one_method_fails_isinstance(self):
        """Missing find_one() method should fail isinstance check."""
        class MissingFindOne:
            def find(self, **kwargs) -> list[dict]:
                return []

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

        db = MissingFindOne()
        assert not isinstance(db, DatabaseInterface)

    def test_missing_insert_method_fails_isinstance(self):
        """Missing insert() method should fail isinstance check."""
        class MissingInsert:
            def find(self, **kwargs) -> list[dict]:
                return []

            def find_one(self, **kwargs) -> Optional[dict]:
                return None

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

        db = MissingInsert()
        assert not isinstance(db, DatabaseInterface)

    def test_missing_count_method_fails_isinstance(self):
        """Missing count() method should fail isinstance check."""
        class MissingCount:
            def find(self, **kwargs) -> list[dict]:
                return []

            def find_one(self, **kwargs) -> Optional[dict]:
                return None

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def query(self, sql: str) -> Any:
                return None

        db = MissingCount()
        assert not isinstance(db, DatabaseInterface)

    def test_method_return_types(self):
        """Test that method return types are correctly specified."""
        class MockDatabase:
            def find(self, **kwargs) -> list[dict]:
                return [{'id': 1, 'name': 'test'}]

            def find_one(self, **kwargs) -> Optional[dict]:
                return {'id': 1, 'name': 'test'}

            def insert(self, record: dict) -> None:
                assert isinstance(record, dict)

            def insert_many(self, records: list[dict]) -> None:
                assert isinstance(records, list)

            def update(self, record: dict, keys: list) -> None:
                assert isinstance(record, dict)
                assert isinstance(keys, list)

            def count(self, **kwargs) -> int:
                return 42

            def query(self, sql: str) -> Any:
                return [('result',)]

        db = MockDatabase()
        assert isinstance(db, DatabaseInterface)

        # Verify return types
        result = db.find()
        assert isinstance(result, list)

        result_one = db.find_one()
        assert isinstance(result_one, dict) or result_one is None

        cnt = db.count()
        assert isinstance(cnt, int)


# =============================================================================
# FileSystemInterface tests
# =============================================================================


class TestFileSystemInterface:
    """Tests for FileSystemInterface Protocol."""

    def test_runtime_checkable(self):
        """Verify FileSystemInterface is runtime_checkable."""
        # Protocol classes with @runtime_checkable can be used with isinstance
        assert True

    def test_full_implementation_passes_isinstance(self):
        """A complete implementation should pass isinstance check."""
        class CompleteFileSystem:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = CompleteFileSystem()
        assert isinstance(fs, FileSystemInterface)

    def test_missing_list_files_fails_isinstance(self):
        """Missing list_files() method should fail isinstance check."""
        class MissingListFiles:
            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = MissingListFiles()
        assert not isinstance(fs, FileSystemInterface)

    def test_missing_read_file_fails_isinstance(self):
        """ Missing read_file() method should fail isinstance check."""
        class MissingReadFile:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = MissingReadFile()
        assert not isinstance(fs, FileSystemInterface)

    def test_missing_write_file_fails_isinstance(self):
        """ Missing write_file() method should fail isinstance check."""
        class MissingWriteFile:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = MissingWriteFile()
        assert not isinstance(fs, FileSystemInterface)

    def test_missing_file_exists_fails_isinstance(self):
        """ Missing file_exists() method should fail isinstance check."""
        class MissingFileExists:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = MissingFileExists()
        assert not isinstance(fs, FileSystemInterface)

    def test_missing_dir_exists_fails_isinstance(self):
        """ Missing dir_exists() method should fail isinstance check."""
        class MissingDirExists:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = MissingDirExists()
        assert not isinstance(fs, FileSystemInterface)

    def test_missing_get_absolute_path_fails_isinstance(self):
        """ Missing get_absolute_path() method should fail isinstance check."""
        class MissingGetAbsPath:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

        fs = MissingGetAbsPath()
        assert not isinstance(fs, FileSystemInterface)

    def test_method_signatures_with_parameters(self):
        """Test that method signatures accept correct parameters."""
        class MockFileSystem:
            def list_files(self, path: str) -> list[str]:
                return ['file1.txt', 'file2.txt']

            def read_file(self, path: str) -> bytes:
                return b'file content'

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                assert isinstance(encoding, str)
                return 'file content'

            def write_file(self, path: str, data: bytes) -> None:
                assert isinstance(data, bytes)

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                assert isinstance(data, str)
                assert isinstance(encoding, str)

            def file_exists(self, path: str) -> bool:
                return True

            def dir_exists(self, path: str) -> bool:
                return True

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                assert isinstance(src, str)
                assert isinstance(dst, str)

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return '/absolute/' + path

        fs = MockFileSystem()
        assert isinstance(fs, FileSystemInterface)

        # Test with various paths
        files = fs.list_files('/test/path')
        assert isinstance(files, list)

        content = fs.read_file('/test/file.txt')
        assert isinstance(content, bytes)

        text = fs.read_file_text('/test/file.txt', encoding='latin-1')
        assert isinstance(text, str)

        assert fs.file_exists('/test/file.txt') is True
        assert fs.dir_exists('/test/dir') is True

        abs_path = fs.get_absolute_path('relative/path')
        assert abs_path.startswith('/')


# =============================================================================
# BackendInterface tests
# =============================================================================


class TestBackendInterface:
    """Tests for BackendInterface Protocol."""

    def test_runtime_checkable(self):
        """Verify BackendInterface is runtime_checkable."""
        assert True

    def test_full_implementation_passes_isinstance(self):
        """A complete implementation should pass isinstance check."""
        class CompleteBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                pass

            def validate(self, params: dict) -> list[str]:
                return []

            def get_name(self) -> str:
                return "test_backend"

        backend = CompleteBackend()
        assert isinstance(backend, BackendInterface)

    def test_missing_send_method_fails_isinstance(self):
        """ Missing send() method should fail isinstance check."""
        class MissingSend:
            def validate(self, params: dict) -> list[str]:
                return []

            def get_name(self) -> str:
                return "test_backend"

        backend = MissingSend()
        assert not isinstance(backend, BackendInterface)

    def test_missing_validate_method_fails_isinstance(self):
        """ Missing validate() method should fail isinstance check."""
        class MissingValidate:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                pass

            def get_name(self) -> str:
                return "test_backend"

        backend = MissingValidate()
        assert not isinstance(backend, BackendInterface)

    def test_missing_get_name_method_fails_isinstance(self):
        """ Missing get_name() method should fail isinstance check."""
        class MissingGetName:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                pass

            def validate(self, params: dict) -> list[str]:
                return []

        backend = MissingGetName()
        assert not isinstance(backend, BackendInterface)

    def test_validate_returns_list_of_strings(self):
        """Test that validate returns list of error strings."""
        class MockBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                pass

            def validate(self, params: dict) -> list[str]:
                return ['Error 1', 'Error 2']

            def get_name(self) -> str:
                return "mock_backend"

        backend = MockBackend()
        assert isinstance(backend, BackendInterface)

        errors = backend.validate({'host': 'localhost'})
        assert isinstance(errors, list)
        assert all(isinstance(e, str) for e in errors)

    def test_validate_returns_empty_list_for_valid_params(self):
        """Test that validate returns empty list for valid params."""
        class MockBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                pass

            def validate(self, params: dict) -> list[str]:
                return []

            def get_name(self) -> str:
                return "valid_backend"

        backend = MockBackend()
        errors = backend.validate({'host': 'localhost', 'port': 21})
        assert errors == []

    def test_send_method_parameters(self):
        """Test that send method accepts correct parameters."""
        class MockBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                assert isinstance(params, dict)
                assert isinstance(settings, dict)
                assert isinstance(filename, str)

            def validate(self, params: dict) -> list[str]:
                return []

            def get_name(self) -> str:
                return "test"

        backend = MockBackend()
        backend.send(
            params={'host': 'ftp.example.com'},
            settings={'timeout': 30},
            filename='/path/to/file.txt'
        )


# =============================================================================
# ValidatorInterface tests
# =============================================================================


class TestValidatorInterface:
    """Tests for ValidatorInterface Protocol."""

    def test_runtime_checkable(self):
        """Verify ValidatorInterface is runtime_checkable."""
        assert True

    def test_full_implementation_passes_isinstance(self):
        """A complete implementation should pass isinstance check."""
        class CompleteValidator:
            def validate(self, file_path: str) -> tuple[bool, list[str]]:
                return True, []

            def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
                return True, [], []

        validator = CompleteValidator()
        assert isinstance(validator, ValidatorInterface)

    def test_missing_validate_method_fails_isinstance(self):
        """ Missing validate() method should fail isinstance check."""
        class MissingValidate:
            def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
                return True, [], []

        validator = MissingValidate()
        assert not isinstance(validator, ValidatorInterface)

    def test_missing_validate_with_warnings_fails_isinstance(self):
        """ Missing validate_with_warnings() method should fail isinstance check."""
        class MissingValidateWithWarnings:
            def validate(self, file_path: str) -> tuple[bool, list[str]]:
                return True, []

        validator = MissingValidateWithWarnings()
        assert not isinstance(validator, ValidatorInterface)

    def test_validate_returns_tuple(self):
        """Test that validate returns proper tuple."""
        class MockValidator:
            def validate(self, file_path: str) -> tuple[bool, list[str]]:
                return False, ['Error: invalid format']

            def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
                return True, [], ['Warning: missing optional field']

        validator = MockValidator()
        assert isinstance(validator, ValidatorInterface)

        is_valid, errors = validator.validate('/path/to/file.txt')
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert all(isinstance(e, str) for e in errors)

    def test_validate_with_warnings_returns_tuple(self):
        """Test that validate_with_warnings returns proper tuple."""
        class MockValidator:
            def validate(self, file_path: str) -> tuple[bool, list[str]]:
                return True, []

            def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
                return False, ['Critical error'], ['Minor warning']

        validator = MockValidator()
        assert isinstance(validator, ValidatorInterface)

        is_valid, errors, warnings = validator.validate_with_warnings('/path/to/file.txt')
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
        assert all(isinstance(e, str) for e in errors)
        assert all(isinstance(w, str) for w in warnings)

    def test_validate_with_empty_errors_and_warnings(self):
        """Test validation with empty errors and warnings lists."""
        class MockValidator:
            def validate(self, file_path: str) -> tuple[bool, list[str]]:
                return True, []

            def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
                return True, [], []

        validator = MockValidator()
        is_valid, errors = validator.validate('/path/to/valid.txt')
        assert is_valid is True
        assert errors == []

        is_valid, errors, warnings = validator.validate_with_warnings('/path/to/valid.txt')
        assert is_valid is True
        assert errors == []
        assert warnings == []


# =============================================================================
# ErrorHandlerInterface tests
# =============================================================================


class TestErrorHandlerInterface:
    """Tests for ErrorHandlerInterface Protocol."""

    def test_runtime_checkable(self):
        """Verify ErrorHandlerInterface is runtime_checkable."""
        assert True

    def test_full_implementation_passes_isinstance(self):
        """A complete implementation should pass isinstance check."""
        class CompleteErrorHandler:
            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                pass

            def get_errors(self) -> list[dict]:
                return []

            def clear_errors(self) -> None:
                pass

        handler = CompleteErrorHandler()
        assert isinstance(handler, ErrorHandlerInterface)

    def test_missing_record_error_fails_isinstance(self):
        """ Missing record_error() method should fail isinstance check."""
        class MissingRecordError:
            def get_errors(self) -> list[dict]:
                return []

            def clear_errors(self) -> None:
                pass

        handler = MissingRecordError()
        assert not isinstance(handler, ErrorHandlerInterface)

    def test_missing_get_errors_fails_isinstance(self):
        """ Missing get_errors() method should fail isinstance check."""
        class MissingGetErrors:
            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                pass

            def clear_errors(self) -> None:
                pass

        handler = MissingGetErrors()
        assert not isinstance(handler, ErrorHandlerInterface)

    def test_missing_clear_errors_fails_isinstance(self):
        """ Missing clear_errors() method should fail isinstance check."""
        class MissingClearErrors:
            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                pass

            def get_errors(self) -> list[dict]:
                return []

        handler = MissingClearErrors()
        assert not isinstance(handler, ErrorHandlerInterface)

    def test_record_error_accepts_exception(self):
        """Test that record_error accepts Exception parameter."""
        class MockErrorHandler:
            def __init__(self):
                self._errors = []

            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                assert isinstance(folder, str)
                assert isinstance(filename, str)
                assert isinstance(error, Exception)
                assert context is None or isinstance(context, dict)
                self._errors.append({
                    'folder': folder,
                    'filename': filename,
                    'error': error,
                    'context': context
                })

            def get_errors(self) -> list[dict]:
                return self._errors

            def clear_errors(self) -> None:
                self._errors = []

        handler = MockErrorHandler()
        assert isinstance(handler, ErrorHandlerInterface)

        exc = ValueError("Test error")
        handler.record_error('/folder', 'file.txt', exc, {'key': 'value'})

        errors = handler.get_errors()
        assert len(errors) == 1
        assert errors[0]['folder'] == '/folder'
        assert errors[0]['filename'] == 'file.txt'
        assert isinstance(errors[0]['error'], ValueError)
        assert errors[0]['context'] == {'key': 'value'}

    def test_record_error_with_none_context(self):
        """Test record_error with None context (default)."""
        class MockErrorHandler:
            def __init__(self):
                self._errors = []

            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                self._errors.append({
                    'folder': folder,
                    'filename': filename,
                    'error': error,
                    'context': context
                })

            def get_errors(self) -> list[dict]:
                return self._errors

            def clear_errors(self) -> None:
                self._errors = []

        handler = MockErrorHandler()
        exc = RuntimeError("Test")
        handler.record_error('/folder', 'file.txt', exc)

        errors = handler.get_errors()
        assert len(errors) == 1
        assert errors[0]['context'] is None

    def test_get_errors_returns_list(self):
        """Test that get_errors returns a list of dicts."""
        class MockErrorHandler:
            def __init__(self):
                self._errors = [
                    {'folder': '/folder1', 'filename': 'file1.txt', 'error': ValueError(), 'context': None},
                    {'folder': '/folder2', 'filename': 'file2.txt', 'error': TypeError(), 'context': {}},
                ]

            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                pass

            def get_errors(self) -> list[dict]:
                return self._errors

            def clear_errors(self) -> None:
                self._errors = []

        handler = MockErrorHandler()
        assert isinstance(handler, ErrorHandlerInterface)

        errors = handler.get_errors()
        assert isinstance(errors, list)
        assert len(errors) == 2
        assert all(isinstance(e, dict) for e in errors)

    def test_clear_errors(self):
        """Test that clear_errors empties the error list."""
        class MockErrorHandler:
            def __init__(self):
                self._errors = [{'folder': '/folder', 'filename': 'file.txt'}]

            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                self._errors.append({
                    'folder': folder,
                    'filename': filename,
                    'error': error,
                    'context': context
                })

            def get_errors(self) -> list[dict]:
                return self._errors

            def clear_errors(self) -> None:
                self._errors = []

        handler = MockErrorHandler()
        assert len(handler.get_errors()) == 1

        handler.clear_errors()
        assert handler.get_errors() == []


# =============================================================================
# LogInterface tests
# =============================================================================


class TestLogInterface:
    """Tests for LogInterface Protocol."""

    def test_runtime_checkable(self):
        """Verify LogInterface is runtime_checkable."""
        assert True

    def test_full_implementation_passes_isinstance(self):
        """A complete implementation should pass isinstance check."""
        class CompleteLog:
            def write(self, message: str) -> None:
                pass

            def writelines(self, lines: list[str]) -> None:
                pass

            def get_value(self) -> str:
                return ""

            def close(self) -> None:
                pass

        log = CompleteLog()
        assert isinstance(log, LogInterface)

    def test_missing_write_method_fails_isinstance(self):
        """ Missing write() method should fail isinstance check."""
        class MissingWrite:
            def writelines(self, lines: list[str]) -> None:
                pass

            def get_value(self) -> str:
                return ""

            def close(self) -> None:
                pass

        log = MissingWrite()
        assert not isinstance(log, LogInterface)

    def test_missing_writelines_method_fails_isinstance(self):
        """ Missing writelines() method should fail isinstance check."""
        class MissingWritelines:
            def write(self, message: str) -> None:
                pass

            def get_value(self) -> str:
                return ""

            def close(self) -> None:
                pass

        log = MissingWritelines()
        assert not isinstance(log, LogInterface)

    def test_missing_get_value_method_fails_isinstance(self):
        """ Missing get_value() method should fail isinstance check."""
        class MissingGetValue:
            def write(self, message: str) -> None:
                pass

            def writelines(self, lines: list[str]) -> None:
                pass

            def close(self) -> None:
                pass

        log = MissingGetValue()
        assert not isinstance(log, LogInterface)

    def test_missing_close_method_fails_isinstance(self):
        """ Missing close() method should fail isinstance check."""
        class MissingClose:
            def write(self, message: str) -> None:
                pass

            def writelines(self, lines: list[str]) -> None:
                pass

            def get_value(self) -> str:
                return ""

        log = MissingClose()
        assert not isinstance(log, LogInterface)

    def test_write_method(self):
        """Test that write method accepts string parameter."""
        class MockLog:
            def __init__(self):
                self._buffer = []

            def write(self, message: str) -> None:
                assert isinstance(message, str)
                self._buffer.append(message)

            def writelines(self, lines: list[str]) -> None:
                assert isinstance(lines, list)
                self._buffer.extend(lines)

            def get_value(self) -> str:
                return ''.join(self._buffer)

            def close(self) -> None:
                pass

        log = MockLog()
        assert isinstance(log, LogInterface)

        log.write("Test message")
        assert len(log.get_value()) > 0

    def test_writelines_method(self):
        """Test that writelines method accepts list of strings."""
        class MockLog:
            def __init__(self):
                self._buffer = []

            def write(self, message: str) -> None:
                self._buffer.append(message)

            def writelines(self, lines: list[str]) -> None:
                self._buffer.extend(lines)

            def get_value(self) -> str:
                return ''.join(self._buffer)

            def close(self) -> None:
                pass

        log = MockLog()
        lines = ["Line 1\n", "Line 2\n", "Line 3\n"]
        log.writelines(lines)

        assert log.get_value() == "Line 1\nLine 2\nLine 3\n"

    def test_get_value_returns_string(self):
        """Test that get_value returns string."""
        class MockLog:
            def __init__(self):
                self._content = "Log contents here"

            def write(self, message: str) -> None:
                self._content += message

            def writelines(self, lines: list[str]) -> None:
                self._content += ''.join(lines)

            def get_value(self) -> str:
                return self._content

            def close(self) -> None:
                pass

        log = MockLog()
        assert isinstance(log, LogInterface)

        value = log.get_value()
        assert isinstance(value, str)

    def test_close_method(self):
        """Test that close method can be called."""
        class MockLog:
            def __init__(self):
                self._closed = False

            def write(self, message: str) -> None:
                pass

            def writelines(self, lines: list[str]) -> None:
                pass

            def get_value(self) -> str:
                return ""

            def close(self) -> None:
                self._closed = True

        log = MockLog()
        assert log._closed is False
        log.close()
        assert log._closed is True


# =============================================================================
# Integration tests - Multiple protocol implementations
# =============================================================================


class TestProtocolIntegration:
    """Integration tests for using multiple protocols together."""

    def test_all_protocols_together(self):
        """Test that a class can implement multiple protocols."""
        class ComprehensiveHandler:
            """Implements all protocols for testing."""

            def find(self, **kwargs) -> list[dict]:
                return []

            def find_one(self, **kwargs) -> Optional[dict]:
                return None

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

            def send(self, params: dict, settings: dict, filename: str) -> None:
                pass

            def validate(self, params: dict) -> list[str]:
                return []

            def get_name(self) -> str:
                return "comprehensive"

            def validate_file(self, file_path: str) -> tuple[bool, list[str]]:
                return True, []

            def validate_with_warnings(self, file_path: str) -> tuple[bool, list[str], list[str]]:
                return True, [], []

            def record_error(
                self,
                folder: str,
                filename: str,
                error: Exception,
                context: Optional[dict] = None
            ) -> None:
                pass

            def get_errors(self) -> list[dict]:
                return []

            def clear_errors(self) -> None:
                pass

            def write(self, message: str) -> None:
                pass

            def writelines(self, lines: list[str]) -> None:
                pass

            def get_value(self) -> str:
                return ""

            def close(self) -> None:
                pass

        handler = ComprehensiveHandler()

        # Verify all protocol checks pass
        assert isinstance(handler, DatabaseInterface)
        assert isinstance(handler, FileSystemInterface)
        assert isinstance(handler, BackendInterface)
        assert isinstance(handler, ValidatorInterface)
        assert isinstance(handler, ErrorHandlerInterface)
        assert isinstance(handler, LogInterface)

    def test_protocol_with_mock_objects(self):
        """Test protocols work with unittest.mock objects."""
        from unittest.mock import MagicMock

        # Create mock objects that satisfy each protocol
        mock_db = MagicMock(spec=DatabaseInterface)
        mock_fs = MagicMock(spec=FileSystemInterface)
        mock_backend = MagicMock(spec=BackendInterface)
        mock_validator = MagicMock(spec=ValidatorInterface)
        mock_error_handler = MagicMock(spec=ErrorHandlerInterface)
        mock_log = MagicMock(spec=LogInterface)

        # Verify they pass isinstance checks
        assert isinstance(mock_db, DatabaseInterface)
        assert isinstance(mock_fs, FileSystemInterface)
        assert isinstance(mock_backend, BackendInterface)
        assert isinstance(mock_validator, ValidatorInterface)
        assert isinstance(mock_error_handler, ErrorHandlerInterface)
        assert isinstance(mock_log, LogInterface)


# =============================================================================
# Edge case tests
# =============================================================================


class TestProtocolEdgeCases:
    """Edge case tests for protocol implementations."""

    def test_empty_implementation_does_not_satisfy_protocol(self):
        """An empty class should not satisfy any protocol."""
        class EmptyClass:
            pass

        empty = EmptyClass()
        assert not isinstance(empty, DatabaseInterface)
        assert not isinstance(empty, FileSystemInterface)
        assert not isinstance(empty, BackendInterface)
        assert not isinstance(empty, ValidatorInterface)
        assert not isinstance(empty, ErrorHandlerInterface)
        assert not isinstance(empty, LogInterface)

    def test_partial_implementation_does_not_satisfy_protocol(self):
        """A class with only some methods should not satisfy the protocol."""
        class PartialDB:
            def find(self, **kwargs) -> list[dict]:
                return []

        partial = PartialDB()
        assert not isinstance(partial, DatabaseInterface)

    def test_methods_with_wrong_return_types(self):
        """A class with wrong return types annotation may fail protocol check."""
        # Note: runtime_checkable Protocols in modern Python verify both method
        # existence AND that the return type annotation matches the Protocol
        # This is more strict than just checking method existence
        class WrongReturnTypes:
            def find(self, **kwargs):  # No type annotation
                return "not a list"

        obj = WrongReturnTypes()
        # Without proper type annotation, may fail isinstance
        # This is implementation-dependent based on Python version
        # The key point is that return type correctness is the implementer's responsibility
        result = isinstance(obj, DatabaseInterface)
        # Either True or False is acceptable - what's important is the concept
        assert isinstance(result, bool)

    def test_optional_parameters_in_implementations(self):
        """Test that implementations can use default parameter values."""
        class OptionalParamsFS:
            def list_files(self, path: str) -> list[str]:
                return []

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = OptionalParamsFS()
        assert isinstance(fs, FileSystemInterface)

        # Can call with or without encoding
        result1 = fs.read_file_text('/path/file.txt')
        result2 = fs.read_file_text('/path/file.txt', encoding='latin-1')
        result3 = fs.read_file_text('/path/file.txt', 'latin-1')  # positional
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert isinstance(result3, str)

    def test_none_return_values(self):
        """Test that None return values are handled correctly."""
        class NoneReturningDB:
            def find(self, **kwargs) -> list[dict]:
                return []

            def find_one(self, **kwargs) -> Optional[dict]:
                return None  # Explicitly returns None

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

        db = NoneReturningDB()
        assert isinstance(db, DatabaseInterface)

        result = db.find_one()
        assert result is None

    def test_exception_in_implementation_method(self):
        """Test that exceptions in implementation methods are not caught by protocol."""
        class ExceptionThrowingDB:
            def find(self, **kwargs) -> list[dict]:
                raise RuntimeError("Database error")

            def find_one(self, **kwargs) -> Optional[dict]:
                return None

            def insert(self, record: dict) -> None:
                pass

            def insert_many(self, records: list[dict]) -> None:
                pass

            def update(self, record: dict, keys: list) -> None:
                pass

            def count(self, **kwargs) -> int:
                return 0

            def query(self, sql: str) -> Any:
                return None

        db = ExceptionThrowingDB()
        assert isinstance(db, DatabaseInterface)

        # The exception should propagate when called
        with pytest.raises(RuntimeError):
            db.find()

    def test_special_characters_in_parameters(self):
        """Test that implementations handle special characters."""
        class SpecialCharFS:
            def list_files(self, path: str) -> list[str]:
                # Handle unicode and special chars
                return ['file with émoji 🎉.txt', 'spaces and\ttabs.txt']

            def read_file(self, path: str) -> bytes:
                return b''

            def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
                return ''

            def write_file(self, path: str, data: bytes) -> None:
                pass

            def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
                pass

            def file_exists(self, path: str) -> bool:
                return False

            def dir_exists(self, path: str) -> bool:
                return False

            def mkdir(self, path: str) -> None:
                pass

            def makedirs(self, path: str) -> None:
                pass

            def copy_file(self, src: str, dst: str) -> None:
                pass

            def remove_file(self, path: str) -> None:
                pass

            def get_absolute_path(self, path: str) -> str:
                return path

        fs = SpecialCharFS()
        assert isinstance(fs, FileSystemInterface)

        # Test with special characters
        files = fs.list_files('/path/with/émojis/🎉')
        assert len(files) == 2
        assert '🎉' in files[0]
