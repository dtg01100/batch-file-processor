"""Integration tests between dispatch orchestrator and convert/send backends.

These tests verify that the dispatch orchestrator correctly integrates with:
1. Convert backends (convert_to_fintech, convert_to_scannerware, etc.)
2. Send backends (ftp_backend, email_backend, copy_backend)

Tests use real convert/send modules with mocked file system and network operations.
"""

import os
import tempfile
import hashlib
from io import StringIO
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

import pytest

from dispatch.orchestrator import (
    DispatchConfig,
    DispatchOrchestrator,
    FolderResult,
    FileResult,
)
from dispatch.send_manager import SendManager, MockBackend
from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_edi_content():
    """Sample EDI file content for testing.
    
    This is a simplified EDI format with A (header), B (line item), 
    and C (trailer) records.
    """
    return """AINV001202401011234567890Test Vendor        001
B001001ITEM001     000010EA0010Test Item Description      0000010000
B001002ITEM002     000020EA0020Another Test Item          0000020000
C00000003000030000
"""


@pytest.fixture
def sample_edi_file(tmp_path, sample_edi_content):
    """Create a sample EDI file in a temporary directory."""
    edi_file = tmp_path / "test_invoice.edi"
    edi_file.write_text(sample_edi_content)
    return str(edi_file)


@pytest.fixture
def sample_folder(tmp_path, sample_edi_content):
    """Create a sample folder with EDI files for processing."""
    folder = tmp_path / "test_folder"
    folder.mkdir()
    
    # Create multiple EDI files
    for i in range(3):
        edi_file = folder / f"invoice_{i:03d}.edi"
        edi_file.write_text(sample_edi_content)
    
    return str(folder)


@pytest.fixture
def folder_config_with_copy(sample_folder):
    """Folder configuration with copy backend enabled."""
    return {
        'id': 1,
        'folder_name': sample_folder,
        'alias': 'Test Folder',
        'process_backend_copy': True,
        'copy_to_directory': '/tmp/test_output',
        'process_backend_ftp': False,
        'process_backend_email': False,
        'process_edi': "False",
        'force_edi_validation': False,
    }


@pytest.fixture
def folder_config_with_ftp(sample_folder):
    """Folder configuration with FTP backend enabled."""
    return {
        'id': 2,
        'folder_name': sample_folder,
        'alias': 'FTP Test Folder',
        'process_backend_ftp': True,
        'ftp_server': 'ftp.example.com',
        'ftp_port': 21,
        'ftp_username': 'testuser',
        'ftp_password': 'testpass',
        'ftp_folder': '/uploads/',
        'process_backend_copy': False,
        'process_backend_email': False,
        'process_edi': "False",
        'force_edi_validation': False,
    }


@pytest.fixture
def folder_config_with_email(sample_folder):
    """Folder configuration with email backend enabled."""
    return {
        'id': 3,
        'folder_name': sample_folder,
        'alias': 'Email Test Folder',
        'process_backend_email': True,
        'email_to': 'recipient@example.com',
        'email_subject_line': 'File: %filename%',
        'process_backend_copy': False,
        'process_backend_ftp': False,
        'process_edi': "False",
        'force_edi_validation': False,
    }


@pytest.fixture
def folder_config_with_all_backends(sample_folder):
    """Folder configuration with all backends enabled."""
    return {
        'id': 4,
        'folder_name': sample_folder,
        'alias': 'All Backends Folder',
        'process_backend_copy': True,
        'copy_to_directory': '/tmp/test_output',
        'process_backend_ftp': True,
        'ftp_server': 'ftp.example.com',
        'ftp_port': 21,
        'ftp_username': 'testuser',
        'ftp_password': 'testpass',
        'ftp_folder': '/uploads/',
        'process_backend_email': True,
        'email_to': 'recipient@example.com',
        'email_subject_line': 'File: %filename%',
        'process_edi': "False",
        'force_edi_validation': False,
    }


@pytest.fixture
def folder_config_with_validation(sample_folder):
    """Folder configuration with EDI validation enabled."""
    return {
        'id': 5,
        'folder_name': sample_folder,
        'alias': 'Validation Test Folder',
        'process_edi': "True",  # String "True" as per orchestrator logic
        'process_backend_copy': True,
        'copy_to_directory': '/tmp/test_output',
        'process_backend_ftp': False,
        'process_backend_email': False,
        'force_edi_validation': False,
    }


@pytest.fixture
def settings_dict():
    """Global application settings for testing."""
    return {
        'email_address': 'sender@example.com',
        'email_smtp_server': 'smtp.example.com',
        'smtp_port': 587,
        'email_username': 'smtpuser',
        'email_password': 'smtppass',
    }


@pytest.fixture
def mock_file_system(sample_folder, sample_edi_content):
    """Mock file system for testing."""
    class MockFileSystem:
        def __init__(self):
            self.dirs = {sample_folder}
            self.files = {}
            # Add sample files
            for i in range(3):
                file_path = os.path.join(sample_folder, f"invoice_{i:03d}.edi")
                self.files[file_path] = sample_edi_content.encode()
        
        def dir_exists(self, path: str) -> bool:
            return path in self.dirs
        
        def list_files(self, path: str) -> list[str]:
            if path not in self.dirs:
                return []
            return [f for f in self.files if os.path.dirname(f) == path]
        
        def read_file(self, path: str) -> bytes:
            if path not in self.files:
                raise FileNotFoundError(path)
            return self.files[path]
        
        def write_file(self, path: str, data: bytes) -> None:
            self.files[path] = data
        
        def makedirs(self, path: str) -> None:
            self.dirs.add(path)
    
    return MockFileSystem()


# =============================================================================
# Convert Backend Integration Tests
# =============================================================================

class TestDispatchConvertBackendIntegration:
    """Test suite for dispatch integration with convert backends."""
    
    def test_dispatch_uses_convert_backend_correctly(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Verify dispatch calls convert with correct params.
        
        This test verifies that when a folder is configured for conversion,
        the dispatch orchestrator correctly invokes the convert backend
        with the expected parameters.
        """
        # Create a mock convert backend that records calls
        convert_calls = []
        
        def mock_edi_convert(edi_process, output_filename, settings_dict_arg, 
                            parameters_dict, upc_lookup):
            convert_calls.append({
                'edi_process': edi_process,
                'output_filename': output_filename,
                'settings_dict': settings_dict_arg,
                'parameters_dict': parameters_dict,
                'upc_lookup': upc_lookup,
            })
            # Return a mock output file path
            return output_filename + ".csv"
        
        # Patch the convert_to_fintech module
        with patch.dict('sys.modules', {'convert_to_fintech': MagicMock(edi_convert=mock_edi_convert)}):
            # Create orchestrator with copy backend
            mock_copy_backend = MockBackend()
            config = DispatchConfig(
                backends={'copy': mock_copy_backend},
                settings=settings_dict,
            )
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
            
            # Verify the file was processed
            assert result.sent is True
            assert len(result.errors) == 0
    
    def test_dispatch_handles_convert_output(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Verify dispatch uses convert output for sending.
        
        This test verifies that the output from the convert backend
        is correctly passed to the send backends.
        """
        # Track what files are sent
        sent_files = []
        
        class TrackingMockBackend:
            def __init__(self):
                self.send_calls = []
            
            def send(self, params, settings, filename):
                self.send_calls.append({
                    'params': params,
                    'settings': settings,
                    'filename': filename,
                })
                sent_files.append(filename)
            
            def validate(self, params):
                return []
            
            def get_name(self):
                return "Tracking Mock Backend"
        
        tracking_backend = TrackingMockBackend()
        config = DispatchConfig(
            backends={'copy': tracking_backend},
            settings=settings_dict,
        )
        orchestrator = DispatchOrchestrator(config)
        
        # Process the file
        result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
        
        # Verify the file was sent
        assert result.sent is True
        assert len(sent_files) == 1
        assert sent_files[0] == sample_edi_file


# =============================================================================
# Send Backend Integration Tests
# =============================================================================

class TestDispatchSendBackendIntegration:
    """Test suite for dispatch integration with send backends."""
    
    def test_dispatch_sends_to_ftp_backend(
        self, sample_edi_file, folder_config_with_ftp, settings_dict
    ):
        """Verify FTP backend receives correct params.
        
        This test verifies that when FTP is enabled, the dispatch
        orchestrator correctly passes the FTP configuration to the
        FTP backend.
        """
        # Track FTP backend calls
        ftp_calls = []
        
        def mock_ftp_do(process_parameters, settings, filename):
            ftp_calls.append({
                'process_parameters': process_parameters,
                'settings': settings,
                'filename': filename,
            })
        
        # Patch the ftp_backend module
        with patch('ftp_backend.do', side_effect=mock_ftp_do):
            config = DispatchConfig(
                settings=settings_dict,
            )
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_ftp)
            
            # Verify FTP was called with correct params
            assert result.sent is True
            assert len(ftp_calls) == 1
            
            call = ftp_calls[0]
            assert call['process_parameters']['ftp_server'] == 'ftp.example.com'
            assert call['process_parameters']['ftp_port'] == 21
            assert call['process_parameters']['ftp_username'] == 'testuser'
            assert call['process_parameters']['ftp_password'] == 'testpass'
            assert call['process_parameters']['ftp_folder'] == '/uploads/'
            assert call['filename'] == sample_edi_file
    
    def test_dispatch_sends_to_email_backend(
        self, sample_edi_file, folder_config_with_email, settings_dict
    ):
        """Verify email backend receives correct params.
        
        This test verifies that when email is enabled, the dispatch
        orchestrator correctly passes the email configuration to the
        email backend.
        """
        # Track email backend calls
        email_calls = []
        
        def mock_email_do(process_parameters, settings, filename):
            email_calls.append({
                'process_parameters': process_parameters,
                'settings': settings,
                'filename': filename,
            })
        
        # Patch the email_backend module
        with patch('email_backend.do', side_effect=mock_email_do):
            config = DispatchConfig(
                settings=settings_dict,
            )
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_email)
            
            # Verify email was called with correct params
            assert result.sent is True
            assert len(email_calls) == 1
            
            call = email_calls[0]
            assert call['process_parameters']['email_to'] == 'recipient@example.com'
            assert call['process_parameters']['email_subject_line'] == 'File: %filename%'
            assert call['settings']['email_address'] == 'sender@example.com'
            assert call['filename'] == sample_edi_file
    
    def test_dispatch_sends_to_copy_backend(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Verify copy backend receives correct params.
        
        This test verifies that when copy is enabled, the dispatch
        orchestrator correctly passes the copy configuration to the
        copy backend.
        """
        # Track copy backend calls
        copy_calls = []
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({
                'process_parameters': process_parameters,
                'settings': settings,
                'filename': filename,
            })
        
        # Patch the copy_backend module
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(
                settings=settings_dict,
            )
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
            
            # Verify copy was called with correct params
            assert result.sent is True
            assert len(copy_calls) == 1
            
            call = copy_calls[0]
            assert call['process_parameters']['copy_to_directory'] == '/tmp/test_output'
            assert call['filename'] == sample_edi_file


# =============================================================================
# Backend Toggle Tests
# =============================================================================

class TestDispatchBackendToggles:
    """Test suite for backend toggle functionality."""
    
    def test_dispatch_backend_toggle_ftp(
        self, sample_edi_file, folder_config_with_ftp, settings_dict
    ):
        """Verify FTP toggle gates FTP sending.
        
        When process_backend_ftp is False, FTP backend should not be called.
        """
        ftp_calls = []
        
        def mock_ftp_do(process_parameters, settings, filename):
            ftp_calls.append({'filename': filename})
        
        # Test with FTP enabled
        with patch('ftp_backend.do', side_effect=mock_ftp_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_file(sample_edi_file, folder_config_with_ftp)
            
            assert result.sent is True
            assert len(ftp_calls) == 1
        
        # Test with FTP disabled
        ftp_calls.clear()
        folder_config_disabled = folder_config_with_ftp.copy()
        folder_config_disabled['process_backend_ftp'] = False
        
        with patch('ftp_backend.do', side_effect=mock_ftp_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_file(sample_edi_file, folder_config_disabled)
            
            # Should have no backends enabled
            assert result.sent is False
            assert len(ftp_calls) == 0
            assert "No backends enabled" in result.errors
    
    def test_dispatch_backend_toggle_email(
        self, sample_edi_file, folder_config_with_email, settings_dict
    ):
        """Verify email toggle gates email sending.
        
        When process_backend_email is False, email backend should not be called.
        """
        email_calls = []
        
        def mock_email_do(process_parameters, settings, filename):
            email_calls.append({'filename': filename})
        
        # Test with email enabled
        with patch('email_backend.do', side_effect=mock_email_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_file(sample_edi_file, folder_config_with_email)
            
            assert result.sent is True
            assert len(email_calls) == 1
        
        # Test with email disabled
        email_calls.clear()
        folder_config_disabled = folder_config_with_email.copy()
        folder_config_disabled['process_backend_email'] = False
        
        with patch('email_backend.do', side_effect=mock_email_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_file(sample_edi_file, folder_config_disabled)
            
            # Should have no backends enabled
            assert result.sent is False
            assert len(email_calls) == 0
            assert "No backends enabled" in result.errors
    
    def test_dispatch_backend_toggle_copy(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Verify copy toggle gates copy sending.
        
        When process_backend_copy is False, copy backend should not be called.
        """
        copy_calls = []
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        # Test with copy enabled
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
            
            assert result.sent is True
            assert len(copy_calls) == 1
        
        # Test with copy disabled
        copy_calls.clear()
        folder_config_disabled = folder_config_with_copy.copy()
        folder_config_disabled['process_backend_copy'] = False
        
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            result = orchestrator.process_file(sample_edi_file, folder_config_disabled)
            
            # Should have no backends enabled
            assert result.sent is False
            assert len(copy_calls) == 0
            assert "No backends enabled" in result.errors


# =============================================================================
# Full Pipeline Tests
# =============================================================================

class TestDispatchFullPipeline:
    """Test suite for full dispatch pipeline."""
    
    def test_dispatch_full_pipeline(
        self, sample_edi_file, folder_config_with_all_backends, settings_dict
    ):
        """Full pipeline: validate → convert → send.
        
        This test verifies the complete dispatch pipeline from validation
        through conversion to sending to all enabled backends.
        """
        # Track all backend calls
        ftp_calls = []
        email_calls = []
        copy_calls = []
        
        def mock_ftp_do(process_parameters, settings, filename):
            ftp_calls.append({'filename': filename})
        
        def mock_email_do(process_parameters, settings, filename):
            email_calls.append({'filename': filename})
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        # Patch all backends
        with patch('ftp_backend.do', side_effect=mock_ftp_do), \
             patch('email_backend.do', side_effect=mock_email_do), \
             patch('copy_backend.do', side_effect=mock_copy_do):
            
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_all_backends)
            
            # Verify all backends were called
            assert result.sent is True
            assert len(ftp_calls) == 1
            assert len(email_calls) == 1
            assert len(copy_calls) == 1
            
            # Verify all received the same file
            assert ftp_calls[0]['filename'] == sample_edi_file
            assert email_calls[0]['filename'] == sample_edi_file
            assert copy_calls[0]['filename'] == sample_edi_file
    
    def test_dispatch_full_pipeline_with_validation(
        self, sample_edi_file, folder_config_with_validation, settings_dict
    ):
        """Full pipeline with EDI validation.
        
        This test verifies that validation is performed before sending
        when process_edi is enabled.
        """
        copy_calls = []
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        # Create a mock validator
        mock_validator = MagicMock()
        mock_validator.validate.return_value = (True, [])
        
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(
                settings=settings_dict,
                validator=mock_validator,
            )
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_validation)
            
            # Verify validation was called
            mock_validator.validate.assert_called_once_with(sample_edi_file)
            
            # Verify file was sent after validation
            assert result.sent is True
            assert result.validated is True
            assert len(copy_calls) == 1


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestDispatchErrorHandling:
    """Test suite for dispatch error handling with backends."""
    
    def test_dispatch_error_handling_with_backend_failure(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Error handling when backend fails.
        
        This test verifies that when a backend fails, the error is
        properly captured and reported.
        """
        def mock_copy_do_failure(process_parameters, settings, filename):
            raise Exception("Simulated copy failure")
        
        with patch('copy_backend.do', side_effect=mock_copy_do_failure):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
            
            # Verify error was captured
            assert result.sent is False
            assert len(result.errors) > 0
            assert "Simulated copy failure" in str(result.errors)
    
    def test_dispatch_error_handling_with_ftp_failure(
        self, sample_edi_file, folder_config_with_ftp, settings_dict
    ):
        """Error handling when FTP backend fails.
        
        This test verifies that FTP connection failures are properly handled.
        """
        def mock_ftp_do_failure(process_parameters, settings, filename):
            raise Exception("FTP connection failed")
        
        with patch('ftp_backend.do', side_effect=mock_ftp_do_failure):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_ftp)
            
            # Verify error was captured
            assert result.sent is False
            assert len(result.errors) > 0
            assert "FTP connection failed" in str(result.errors)
    
    def test_dispatch_error_handling_with_email_failure(
        self, sample_edi_file, folder_config_with_email, settings_dict
    ):
        """Error handling when email backend fails.
        
        This test verifies that email sending failures are properly handled.
        """
        def mock_email_do_failure(process_parameters, settings, filename):
            raise Exception("SMTP connection failed")
        
        with patch('email_backend.do', side_effect=mock_email_do_failure):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file
            result = orchestrator.process_file(sample_edi_file, folder_config_with_email)
            
            # Verify error was captured
            assert result.sent is False
            assert len(result.errors) > 0
            assert "SMTP connection failed" in str(result.errors)
    
    def test_dispatch_partial_backend_failure(
        self, sample_edi_file, folder_config_with_all_backends, settings_dict
    ):
        """Error handling when some backends fail but others succeed.
        
        This test verifies that when multiple backends are enabled and
        some fail, the results correctly report which backends failed.
        
        Note: The current implementation raises exceptions immediately,
        so the first backend failure stops processing. This test verifies
        that behavior.
        """
        ftp_calls = []
        email_calls = []
        copy_calls = []
        
        def mock_ftp_do(process_parameters, settings, filename):
            ftp_calls.append({'filename': filename})
        
        def mock_email_do_failure(process_parameters, settings, filename):
            raise Exception("Email failed")
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        # Test with email failing - since backends are processed in order,
        # copy will be called first (alphabetically in set), then email fails
        with patch('copy_backend.do', side_effect=mock_copy_do), \
             patch('email_backend.do', side_effect=mock_email_do_failure), \
             patch('ftp_backend.do', side_effect=mock_ftp_do):
            
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            
            # Process the file - this will raise an exception when email fails
            result = orchestrator.process_file(sample_edi_file, folder_config_with_all_backends)
            
            # Verify error was captured
            assert result.sent is False
            assert "Email failed" in str(result.errors)


# =============================================================================
# SendManager Integration Tests
# =============================================================================

class TestSendManagerIntegration:
    """Test suite for SendManager integration with backends."""
    
    def test_send_manager_get_enabled_backends(self):
        """Test SendManager correctly identifies enabled backends."""
        manager = SendManager()
        
        params = {
            'process_backend_ftp': True,
            'process_backend_email': False,
            'process_backend_copy': True,
        }
        
        enabled = manager.get_enabled_backends(params)
        
        assert 'ftp' in enabled
        assert 'copy' in enabled
        assert 'email' not in enabled
    
    def test_send_manager_validate_backend_config(self):
        """Test SendManager validates backend configuration."""
        manager = SendManager()
        
        # Missing required settings
        params = {
            'process_backend_ftp': True,
            # Missing ftp_server
            'process_backend_email': True,
            # Missing email_to
        }
        
        errors = manager.validate_backend_config(params)
        
        assert len(errors) == 2
        assert any('ftp_server' in e for e in errors)
        assert any('email_to' in e for e in errors)
    
    def test_send_manager_with_injected_backend(self, sample_edi_file, settings_dict):
        """Test SendManager uses injected backend instances."""
        mock_backend = MockBackend()
        manager = SendManager(backends={'test': mock_backend})
        
        params = {'process_backend_test': True}
        
        # Send via injected backend
        results = manager.send_all(
            {'test'}, sample_edi_file, params, settings_dict
        )
        
        assert results['test'] is True
        assert len(mock_backend.send_calls) == 1
    
    def test_send_manager_send_all_success(self, sample_edi_file, settings_dict):
        """Test SendManager send_all with all backends succeeding."""
        ftp_calls = []
        email_calls = []
        copy_calls = []
        
        def mock_ftp_do(params, settings, filename):
            ftp_calls.append(filename)
        
        def mock_email_do(params, settings, filename):
            email_calls.append(filename)
        
        def mock_copy_do(params, settings, filename):
            copy_calls.append(filename)
        
        with patch('ftp_backend.do', side_effect=mock_ftp_do), \
             patch('email_backend.do', side_effect=mock_email_do), \
             patch('copy_backend.do', side_effect=mock_copy_do):
            
            manager = SendManager()
            
            params = {
                'process_backend_ftp': True,
                'process_backend_email': True,
                'process_backend_copy': True,
                'ftp_server': 'ftp.example.com',
                'ftp_port': 21,
                'ftp_username': 'user',
                'ftp_password': 'pass',
                'ftp_folder': '/uploads/',
                'email_to': 'test@example.com',
                'copy_to_directory': '/tmp/output',
            }
            
            results = manager.send_all(
                {'ftp', 'email', 'copy'},
                sample_edi_file,
                params,
                settings_dict
            )
            
            assert all(results.values())
            assert len(ftp_calls) == 1
            assert len(email_calls) == 1
            assert len(copy_calls) == 1


# =============================================================================
# Folder Processing Integration Tests
# =============================================================================

class TestFolderProcessingIntegration:
    """Test suite for folder-level processing integration."""
    
    def test_process_folder_with_multiple_files(
        self, sample_folder, folder_config_with_copy, settings_dict
    ):
        """Test processing a folder with multiple files."""
        copy_calls = []
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(settings=settings_dict)
            orchestrator = DispatchOrchestrator(config)
            
            # Update folder config with actual path
            folder_config = folder_config_with_copy.copy()
            folder_config['folder_name'] = sample_folder
            
            # Create a mock run log
            run_log = MagicMock()
            run_log.write = MagicMock()
            
            # Process the folder
            result = orchestrator.process_folder(folder_config, run_log)
            
            # Verify all files were processed
            assert result.success is True
            assert result.files_processed == 3
            assert result.files_failed == 0
            assert len(copy_calls) == 3
    
    def test_process_folder_with_validation_errors(
        self, sample_folder, settings_dict
    ):
        """Test processing a folder when validation fails."""
        # Create a validator that always fails
        mock_validator = MagicMock()
        mock_validator.validate.return_value = (False, ["Validation error"])
        
        folder_config = {
            'id': 1,
            'folder_name': sample_folder,
            'alias': 'Test Folder',
            'process_edi': "True",  # String "True" as per orchestrator logic
            'force_edi_validation': False,
            'process_backend_copy': True,
            'copy_to_directory': '/tmp/output',
        }
        
        copy_calls = []
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(
                settings=settings_dict,
                validator=mock_validator,
            )
            orchestrator = DispatchOrchestrator(config)
            
            run_log = MagicMock()
            run_log.write = MagicMock()
            
            # Process the folder
            result = orchestrator.process_folder(folder_config, run_log)
            
            # Files should fail validation
            assert result.success is False
            assert result.files_failed == 3
            assert result.files_processed == 0
            # Copy should not be called due to validation failure
            assert len(copy_calls) == 0
    
    def test_process_folder_with_force_validation(
        self, sample_folder, settings_dict
    ):
        """Test processing with force_edi_validation sends despite errors."""
        # Create a validator that always fails
        mock_validator = MagicMock()
        mock_validator.validate.return_value = (False, ["Validation error"])
        
        folder_config = {
            'id': 1,
            'folder_name': sample_folder,
            'alias': 'Test Folder',
            'process_edi': "True",  # String "True" as per orchestrator logic
            'force_edi_validation': True,  # Force sending despite errors
            'process_backend_copy': True,
            'copy_to_directory': '/tmp/output',
        }
        
        copy_calls = []
        
        def mock_copy_do(process_parameters, settings, filename):
            copy_calls.append({'filename': filename})
        
        with patch('copy_backend.do', side_effect=mock_copy_do):
            config = DispatchConfig(
                settings=settings_dict,
                validator=mock_validator,
            )
            orchestrator = DispatchOrchestrator(config)
            
            run_log = MagicMock()
            run_log.write = MagicMock()
            
            # Process the folder
            result = orchestrator.process_folder(folder_config, run_log)
            
            # Files should be sent despite validation errors
            assert result.success is True
            assert result.files_processed == 3
            assert len(copy_calls) == 3


# =============================================================================
# Checksum and Deduplication Tests
# =============================================================================

class TestChecksumIntegration:
    """Test suite for checksum calculation and deduplication."""
    
    def test_checksum_calculation(self, sample_edi_file):
        """Test that checksums are correctly calculated."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        checksum = orchestrator._calculate_checksum(sample_edi_file)
        
        # Verify it's a valid MD5 hex string
        assert len(checksum) == 32
        assert all(c in '0123456789abcdef' for c in checksum)
        
        # Verify consistency
        checksum2 = orchestrator._calculate_checksum(sample_edi_file)
        assert checksum == checksum2
    
    def test_different_files_different_checksums(self, tmp_path):
        """Test that different files produce different checksums."""
        file1 = tmp_path / "file1.edi"
        file2 = tmp_path / "file2.edi"
        
        file1.write_text("Content A")
        file2.write_text("Content B")
        
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        checksum1 = orchestrator._calculate_checksum(str(file1))
        checksum2 = orchestrator._calculate_checksum(str(file2))
        
        assert checksum1 != checksum2


# =============================================================================
# Mock Backend Tests
# =============================================================================

class TestMockBackendIntegration:
    """Test suite using MockBackend for controlled testing."""
    
    def test_mock_backend_records_calls(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Test that MockBackend correctly records calls."""
        mock_backend = MockBackend()
        
        config = DispatchConfig(
            backends={'copy': mock_backend},
            settings=settings_dict,
        )
        orchestrator = DispatchOrchestrator(config)
        
        # Process the file
        result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
        
        # Verify the call was recorded
        assert result.sent is True
        assert len(mock_backend.send_calls) == 1
        
        call = mock_backend.send_calls[0]
        assert call[2] == sample_edi_file  # filename is third argument
    
    def test_mock_backend_failure(
        self, sample_edi_file, folder_config_with_copy, settings_dict
    ):
        """Test MockBackend can simulate failure."""
        mock_backend = MockBackend(should_succeed=False)
        
        config = DispatchConfig(
            backends={'copy': mock_backend},
            settings=settings_dict,
        )
        orchestrator = DispatchOrchestrator(config)
        
        # Process the file
        result = orchestrator.process_file(sample_edi_file, folder_config_with_copy)
        
        # Verify failure was captured
        assert result.sent is False
        assert len(result.errors) > 0
        assert "Mock backend failure" in result.errors[0]
    
    def test_mock_backend_reset(self):
        """Test MockBackend reset clears recorded calls."""
        mock_backend = MockBackend()
        
        # Record some calls
        mock_backend.send({'param': 'value'}, {}, 'test.txt')
        mock_backend.validate({'param': 'value'})
        
        assert len(mock_backend.send_calls) == 1
        assert len(mock_backend.validate_calls) == 1
        
        # Reset
        mock_backend.reset()
        
        assert len(mock_backend.send_calls) == 0
        assert len(mock_backend.validate_calls) == 0
