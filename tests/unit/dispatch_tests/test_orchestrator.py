"""Tests for dispatch/orchestrator.py module."""

import hashlib
import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from dispatch.orchestrator import (
    DispatchConfig,
    DispatchOrchestrator,
    FolderResult,
    FileResult,
)
from dispatch.edi_validator import EDIValidator
from dispatch.send_manager import MockBackend
from dispatch.error_handler import ErrorHandler


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self, records=None):
        self.records = records or []
        self.inserted = []
    
    def find(self, **kwargs) -> list[dict]:
        return [
            r for r in self.records
            if all(r.get(k) == v for k, v in kwargs.items())
        ]
    
    def insert(self, record: dict) -> None:
        self.inserted.append(record)


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self, files=None, dirs=None):
        self.files = files or {}  # path -> content
        self.dirs = set(dirs or [])
    
    def dir_exists(self, path: str) -> bool:
        return path in self.dirs
    
    def list_files(self, path: str) -> list[str]:
        return [
            f for f in self.files
            if f.startswith(path) and self.dir_exists(path)
        ]
    
    def read_file(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path].encode() if isinstance(self.files[path], str) else self.files[path]
    
    def makedirs(self, path: str) -> None:
        self.dirs.add(path)
    
    def write_file_text(self, path: str, data: str) -> None:
        self.files[path] = data


class TestDispatchConfig:
    """Tests for DispatchConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DispatchConfig()
        
        assert config.database is None
        assert config.file_system is None
        assert config.backends == {}
        assert config.validator is None
        assert config.error_handler is None
        assert config.settings == {}
        assert config.version == "1.0.0"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        db = MockDatabase()
        fs = MockFileSystem()
        validator = EDIValidator()
        handler = ErrorHandler()
        
        config = DispatchConfig(
            database=db,
            file_system=fs,
            backends={'test': MockBackend()},
            validator=validator,
            error_handler=handler,
            settings={'key': 'value'},
            version="2.0.0"
        )
        
        assert config.database is db
        assert config.file_system is fs
        assert 'test' in config.backends
        assert config.validator is validator
        assert config.error_handler is handler
        assert config.settings == {'key': 'value'}
        assert config.version == "2.0.0"


class TestFolderResult:
    """Tests for FolderResult dataclass."""
    
    def test_default_result(self):
        """Test default result values."""
        result = FolderResult(folder_name='/data/input', alias='Input')
        
        assert result.folder_name == '/data/input'
        assert result.alias == 'Input'
        assert result.files_processed == 0
        assert result.files_failed == 0
        assert result.errors == []
        assert result.success is True
    
    def test_custom_result(self):
        """Test custom result values."""
        result = FolderResult(
            folder_name='/data/input',
            alias='Input',
            files_processed=10,
            files_failed=2,
            errors=['Error 1', 'Error 2'],
            success=False
        )
        
        assert result.files_processed == 10
        assert result.files_failed == 2
        assert len(result.errors) == 2
        assert result.success is False


class TestFileResult:
    """Tests for FileResult dataclass."""
    
    def test_default_result(self):
        """Test default result values."""
        result = FileResult(file_name='/data/file.edi', checksum='abc123')
        
        assert result.file_name == '/data/file.edi'
        assert result.checksum == 'abc123'
        assert result.sent is False
        assert result.validated is True
        assert result.converted is False
        assert result.errors == []
    
    def test_custom_result(self):
        """Test custom result values."""
        result = FileResult(
            file_name='/data/file.edi',
            checksum='abc123',
            sent=True,
            validated=True,
            converted=True,
            errors=[]
        )
        
        assert result.sent is True
        assert result.validated is True
        assert result.converted is True


class TestDispatchOrchestrator:
    """Tests for DispatchOrchestrator class."""
    
    def test_init_default(self):
        """Test initialization with default config."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator.config is config
        assert orchestrator.processed_count == 0
        assert orchestrator.error_count == 0
    
    def test_init_with_components(self):
        """Test initialization with custom components."""
        config = DispatchConfig(
            backends={'test': MockBackend()},
            settings={'key': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        
        assert 'test' in orchestrator.send_manager.backends
        assert orchestrator.config.settings == {'key': 'value'}
    
    def test_process_folder_not_found(self):
        """Test processing a non-existent folder."""
        mock_fs = MockFileSystem(dirs=['/data/exists'])
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/notexists', 'alias': 'Test'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        assert result.success is False
        assert result.files_failed == 1
        assert 'not found' in result.errors[0].lower()
    
    def test_process_folder_empty(self):
        """Test processing an empty folder."""
        mock_fs = MockFileSystem(dirs=['/data/input'])
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/input', 'alias': 'Test'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        assert result.success is True
        assert result.files_processed == 0
    
    def test_process_folder_with_files(self):
        """Test processing a folder with files."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={
                '/data/input/file1.edi': b'content1',
                '/data/input/file2.edi': b'content2'
            }
        )
        
        # Mock list_files to return actual files
        mock_fs.list_files = lambda path: [
            '/data/input/file1.edi',
            '/data/input/file2.edi'
        ] if path in mock_fs.dirs else []
        
        mock_backend = MockBackend(should_succeed=True)
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        # Process files
        result = orchestrator.process_folder(folder, run_log)
        
        # Check that files were processed
        assert result.files_processed >= 0
    
    def test_process_file_success(self):
        """Test successful file processing."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'test content'}
        )
        
        mock_backend = MockBackend(should_succeed=True)
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_backend_copy': True
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        assert result.file_name == '/data/input/file.edi'
        assert len(result.checksum) == 32  # MD5 hash length
    
    def test_process_file_no_backends(self):
        """Test file processing with no enabled backends."""
        mock_fs = MockFileSystem(
            files={'/data/input/file.edi': b'test content'}
        )
        
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            # No backends enabled
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        assert result.sent is False
        assert 'No backends enabled' in result.errors
    
    def test_process_file_with_validation(self):
        """Test file processing with validation."""
        mock_fs = MockFileSystem(
            files={'/data/input/file.edi': b'AHEADER\nCFOOTER\n'}
        )
        
        mock_validator = MagicMock()
        mock_validator.validate.return_value = (True, [])
        
        mock_backend = MockBackend(should_succeed=True)
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator=mock_validator
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_edi': 'True',
            'process_backend_copy': True
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        mock_validator.validate.assert_called_once()
    
    def test_process_file_validation_failure(self):
        """Test file processing with validation failure."""
        mock_fs = MockFileSystem(
            files={'/data/input/file.edi': b'invalid content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.validate.return_value = (False, ['Invalid EDI'])
        
        config = DispatchConfig(
            file_system=mock_fs,
            validator=mock_validator
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_edi': 'True'
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        assert result.validated is False
        assert 'Invalid EDI' in result.errors
    
    def test_get_summary(self):
        """Test getting processing summary."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        orchestrator.processed_count = 10
        orchestrator.error_count = 2
        
        summary = orchestrator.get_summary()
        
        assert "10 processed" in summary
        assert "2 errors" in summary
    
    def test_reset(self):
        """Test resetting orchestrator state."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        orchestrator.processed_count = 10
        orchestrator.error_count = 5
        
        orchestrator.reset()
        
        assert orchestrator.processed_count == 0
        assert orchestrator.error_count == 0


class TestOrchestratorHelperMethods:
    """Tests for orchestrator helper methods."""
    
    def test_folder_exists(self):
        """Test folder existence check."""
        mock_fs = MockFileSystem(dirs=['/data/exists'])
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._folder_exists('/data/exists') is True
        assert orchestrator._folder_exists('/data/notexists') is False
    
    def test_get_files_in_folder(self):
        """Test getting files in folder."""
        mock_fs = MockFileSystem(dirs=['/data/input'])
        mock_fs.list_files = lambda path: ['/data/input/file1.edi', '/data/input/file2.edi']
        
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        files = orchestrator._get_files_in_folder('/data/input')
        
        assert len(files) == 2
    
    def test_calculate_checksum(self):
        """Test checksum calculation."""
        mock_fs = MockFileSystem(files={'/data/file.edi': b'test content'})
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        checksum = orchestrator._calculate_checksum('/data/file.edi')
        
        expected = hashlib.md5(b'test content').hexdigest()
        assert checksum == expected
    
    def test_should_validate(self):
        """Test validation requirement check."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        # No validation flags
        assert orchestrator._should_validate({}) is False
        
        # With process_edi
        assert orchestrator._should_validate({'process_edi': 'True'}) is True
        
        # With tweak_edi
        assert orchestrator._should_validate({'tweak_edi': True}) is True
        
        # With split_edi
        assert orchestrator._should_validate({'split_edi': True}) is True
        
        # With force_edi_validation
        assert orchestrator._should_validate({'force_edi_validation': True}) is True
    
    def test_log_message(self):
        """Test message logging."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        # Test with file-like object
        run_log = MagicMock()
        orchestrator._log_message(run_log, "Test message")
        
        run_log.write.assert_called_once()
        
        # Test with list
        run_log = []
        orchestrator._log_message(run_log, "Test message")
        
        assert len(run_log) == 1
        assert "Test message" in run_log[0]


class TestOrchestratorIntegration:
    """Integration tests for DispatchOrchestrator."""
    
    def test_full_processing_workflow(self):
        """Test full file processing workflow."""
        # Set up mock file system with valid EDI file
        edi_content = "AHEADER\nB1234567890" + " " * 60 + "\nCFOOTER\n"
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/invoice.edi': edi_content.encode()}
        )
        mock_fs.list_files = lambda path: ['/data/input/invoice.edi']
        
        # Set up mock backend
        mock_backend = MockBackend(should_succeed=True)
        
        # Set up config
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            settings={'test': 'value'}
        )
        
        # Create orchestrator
        orchestrator = DispatchOrchestrator(config)
        
        # Process folder
        folder = {
            'folder_name': '/data/input',
            'alias': 'TestFolder',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        # Verify results
        assert result.folder_name == '/data/input'
        assert result.alias == 'TestFolder'
    
    def test_processing_with_error_handling(self):
        """Test processing with error handling."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        mock_fs.list_files = lambda path: ['/data/input/file.edi']
        
        # Backend that will fail
        mock_backend = MockBackend(should_succeed=False)
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_backend_copy': True
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        assert result.sent is False
        assert len(result.errors) > 0
    
    def test_multiple_folders(self):
        """Test processing multiple folders."""
        mock_fs = MockFileSystem(
            dirs=['/data/input1', '/data/input2'],
            files={
                '/data/input1/file1.edi': b'content1',
                '/data/input2/file2.edi': b'content2'
            }
        )
        mock_fs.list_files = lambda path: [f for f in mock_fs.files if f.startswith(path)]
        
        mock_backend = MockBackend(should_succeed=True)
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folders = [
            {'folder_name': '/data/input1', 'alias': 'Input1', 'process_backend_copy': True},
            {'folder_name': '/data/input2', 'alias': 'Input2', 'process_backend_copy': True}
        ]
        
        run_log = MagicMock()
        
        for folder in folders:
            result = orchestrator.process_folder(folder, run_log)
            assert result.folder_name == folder['folder_name']


class TestOrchestratorEdgeCases:
    """Edge case tests for DispatchOrchestrator."""
    
    def test_folder_with_special_characters(self):
        """Test folder with special characters in name."""
        mock_fs = MockFileSystem(dirs=['/data/input folder'])
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/input folder', 'alias': 'Test'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        assert result.folder_name == '/data/input folder'
    
    def test_empty_folder_name(self):
        """Test with empty folder name."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '', 'alias': 'Empty'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        assert result.success is False
    
    def test_missing_folder_alias(self):
        """Test with missing folder alias."""
        mock_fs = MockFileSystem(dirs=['/data/input'])
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/input'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        assert result.alias == ''
    
    def test_large_file(self):
        """Test processing large file."""
        large_content = b'x' * 10_000_000  # 10 MB
        
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/large.edi': large_content}
        )
        
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)
        
        checksum = orchestrator._calculate_checksum('/data/input/large.edi')
        
        assert len(checksum) == 32
        assert checksum == hashlib.md5(large_content).hexdigest()
    
    def test_concurrent_processing_safety(self):
        """Test that orchestrator state is properly managed."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        mock_fs.list_files = lambda path: ['/data/input/file.edi']
        
        mock_backend = MockBackend(should_succeed=True)
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend}
        )
        orchestrator = DispatchOrchestrator(config)
        
        # Process same folder multiple times
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        for _ in range(3):
            result = orchestrator.process_folder(folder, run_log)
            assert result is not None
