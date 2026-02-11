"""Tests for dispatch/send_manager.py module."""

import pytest
from unittest.mock import MagicMock, patch

from dispatch.send_manager import SendManager, MockBackend


class TestSendManager:
    """Tests for SendManager class."""
    
    def test_init_empty(self):
        """Test initialization with no backends."""
        manager = SendManager()
        
        assert manager.backends == {}
        assert manager.results == {}
    
    def test_init_with_backends(self):
        """Test initialization with custom backends."""
        mock_backend = MockBackend()
        backends = {'test': mock_backend}
        
        manager = SendManager(backends=backends)
        
        assert manager.backends == backends
    
    def test_get_enabled_backends_all_disabled(self):
        """Test getting enabled backends when all are disabled."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': False,
            'process_backend_ftp': False,
            'process_backend_email': False
        }
        
        enabled = manager.get_enabled_backends(params)
        
        assert enabled == set()
    
    def test_get_enabled_backends_single(self):
        """Test getting enabled backends with single backend enabled."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': True,
            'process_backend_ftp': False,
            'process_backend_email': False
        }
        
        enabled = manager.get_enabled_backends(params)
        
        assert enabled == {'copy'}
    
    def test_get_enabled_backends_multiple(self):
        """Test getting enabled backends with multiple enabled."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': True,
            'process_backend_ftp': True,
            'process_backend_email': False
        }
        
        enabled = manager.get_enabled_backends(params)
        
        assert enabled == {'copy', 'ftp'}
    
    def test_get_enabled_backends_all_enabled(self):
        """Test getting enabled backends with all enabled."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': True,
            'process_backend_ftp': True,
            'process_backend_email': True
        }
        
        enabled = manager.get_enabled_backends(params)
        
        assert enabled == {'copy', 'ftp', 'email'}
    
    def test_send_all_with_mock_backends(self):
        """Test sending to all enabled backends with mocks."""
        mock_copy = MockBackend(should_succeed=True)
        mock_ftp = MockBackend(should_succeed=True)
        
        manager = SendManager(backends={'copy': mock_copy, 'ftp': mock_ftp})
        
        params = {'process_backend_copy': True}
        settings = {}
        
        results = manager.send_all({'copy'}, '/test/file.edi', params, settings)
        
        assert results['copy'] is True
        assert len(mock_copy.send_calls) == 1
    
    def test_send_all_with_failure(self):
        """Test sending with one backend failing."""
        mock_copy = MockBackend(should_succeed=False)
        
        manager = SendManager(backends={'copy': mock_copy})
        
        params = {}
        settings = {}
        
        with pytest.raises(Exception):
            manager.send_all({'copy'}, '/test/file.edi', params, settings)
    
    def test_send_all_multiple_backends(self):
        """Test sending to multiple backends."""
        mock_copy = MockBackend(should_succeed=True)
        mock_ftp = MockBackend(should_succeed=True)
        mock_email = MockBackend(should_succeed=True)
        
        manager = SendManager(backends={
            'copy': mock_copy,
            'ftp': mock_ftp,
            'email': mock_email
        })
        
        params = {}
        settings = {}
        
        results = manager.send_all(
            {'copy', 'ftp', 'email'},
            '/test/file.edi',
            params,
            settings
        )
        
        assert all(results.values())
        assert len(mock_copy.send_calls) == 1
        assert len(mock_ftp.send_calls) == 1
        assert len(mock_email.send_calls) == 1
    
    def test_send_to_unknown_backend(self):
        """Test sending to unknown backend raises error."""
        manager = SendManager(use_default_backends=False)
        
        with pytest.raises(ValueError, match="Unknown backend"):
            manager.send_all({'unknown'}, '/test/file.edi', {}, {})
    
    def test_validate_backend_config_valid(self):
        """Test validation with valid configuration."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': True,
            'copy_to_directory': '/backup',
            'process_backend_ftp': False,
            'process_backend_email': False
        }
        
        errors = manager.validate_backend_config(params)
        
        assert errors == []
    
    def test_validate_backend_config_missing_setting(self):
        """Test validation with missing required setting."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': True,
            # Missing copy_to_directory
            'process_backend_ftp': False,
            'process_backend_email': False
        }
        
        errors = manager.validate_backend_config(params)
        
        assert len(errors) == 1
        assert 'copy_to_directory' in errors[0]
    
    def test_validate_backend_config_multiple_missing(self):
        """Test validation with multiple missing settings."""
        manager = SendManager()
        
        params = {
            'process_backend_copy': True,
            'process_backend_ftp': True,
            'process_backend_email': True
            # All destination settings missing
        }
        
        errors = manager.validate_backend_config(params)
        
        assert len(errors) == 3
    
    def test_get_results(self):
        """Test getting results after send."""
        mock_backend = MockBackend(should_succeed=True)
        manager = SendManager(backends={'test': mock_backend})
        
        manager.send_all({'test'}, '/test/file.edi', {}, {})
        
        results = manager.get_results()
        
        assert 'test' in results
        assert results['test'] is True
    
    def test_clear_results(self):
        """Test clearing results."""
        mock_backend = MockBackend(should_succeed=True)
        manager = SendManager(backends={'test': mock_backend})
        
        manager.send_all({'test'}, '/test/file.edi', {}, {})
        manager.clear_results()
        
        assert manager.results == {}


class TestMockBackend:
    """Tests for MockBackend class."""
    
    def test_send_success(self):
        """Test successful send."""
        backend = MockBackend(should_succeed=True)
        
        backend.send({'param': 'value'}, {'setting': 'value'}, '/test/file.edi')
        
        assert len(backend.send_calls) == 1
        params, settings, filename = backend.send_calls[0]
        assert params == {'param': 'value'}
        assert settings == {'setting': 'value'}
        assert filename == '/test/file.edi'
    
    def test_send_failure(self):
        """Test failed send."""
        backend = MockBackend(should_succeed=False)
        
        with pytest.raises(Exception, match="Mock backend failure"):
            backend.send({}, {}, '/test/file.edi')
    
    def test_validate_success(self):
        """Test successful validation."""
        backend = MockBackend(should_succeed=True)
        
        errors = backend.validate({})
        
        assert errors == []
    
    def test_validate_failure(self):
        """Test failed validation."""
        backend = MockBackend(should_succeed=False)
        
        errors = backend.validate({})
        
        assert len(errors) == 1
        assert "validation error" in errors[0]
    
    def test_get_name(self):
        """Test getting backend name."""
        backend = MockBackend()
        
        assert backend.get_name() == "Mock Backend"
    
    def test_reset(self):
        """Test resetting recorded calls."""
        backend = MockBackend(should_succeed=True)
        backend.send({}, {}, '/test/file.edi')
        backend.validate({})
        
        backend.reset()
        
        assert backend.send_calls == []
        assert backend.validate_calls == []


class TestSendManagerModuleBackends:
    """Tests for SendManager with module-based backends."""
    
    @patch('dispatch.send_manager.importlib.import_module')
    def test_send_via_module_copy(self, mock_import):
        """Test sending via copy_backend module."""
        mock_module = MagicMock()
        mock_import.return_value = mock_module
        
        manager = SendManager(use_default_backends=True)
        
        params = {
            'process_backend_copy': True,
            'copy_to_directory': '/backup'
        }
        settings = {}
        
        # This should use the module-based backend
        manager._send_via_module('copy', '/test/file.edi', params, settings)
        
        mock_import.assert_called_with('copy_backend')
        mock_module.do.assert_called_once()
    
    @patch('dispatch.send_manager.importlib.import_module')
    def test_send_via_module_ftp(self, mock_import):
        """Test sending via ftp_backend module."""
        mock_module = MagicMock()
        mock_import.return_value = mock_module
        
        manager = SendManager(use_default_backends=True)
        
        params = {
            'process_backend_ftp': True,
            'ftp_server': 'ftp.example.com'
        }
        settings = {}
        
        manager._send_via_module('ftp', '/test/file.edi', params, settings)
        
        mock_import.assert_called_with('ftp_backend')
        mock_module.do.assert_called_once()
    
    @patch('dispatch.send_manager.importlib.import_module')
    def test_send_via_module_email(self, mock_import):
        """Test sending via email_backend module."""
        mock_module = MagicMock()
        mock_import.return_value = mock_module
        
        manager = SendManager(use_default_backends=True)
        
        params = {
            'process_backend_email': True,
            'email_to': 'user@example.com'
        }
        settings = {}
        
        manager._send_via_module('email', '/test/file.edi', params, settings)
        
        mock_import.assert_called_with('email_backend')
        mock_module.do.assert_called_once()
    
    def test_send_via_module_disabled_backend(self):
        """Test sending via module when backend is disabled."""
        manager = SendManager(use_default_backends=True)
        
        params = {
            'process_backend_copy': False,
            'copy_to_directory': '/backup'
        }
        
        result = manager._send_via_module('copy', '/test/file.edi', params, {})
        
        assert result is False
    
    def test_send_via_unknown_module(self):
        """Test sending via unknown module raises error."""
        manager = SendManager(use_default_backends=True)
        
        with pytest.raises(ValueError, match="Unknown backend"):
            manager._send_via_module('unknown', '/test/file.edi', {}, {})


class TestSendManagerIntegration:
    """Integration tests for SendManager."""
    
    def test_full_send_workflow(self):
        """Test full send workflow with mock backends."""
        # Create mock backends
        copy_backend = MockBackend(should_succeed=True)
        ftp_backend = MockBackend(should_succeed=True)
        
        manager = SendManager(backends={
            'copy': copy_backend,
            'ftp': ftp_backend
        })
        
        # Configure parameters
        params = {
            'process_backend_copy': True,
            'process_backend_ftp': True,
            'copy_to_directory': '/backup',
            'ftp_server': 'ftp.example.com'
        }
        settings = {
            'some_setting': 'value'
        }
        
        # Get enabled backends
        enabled = manager.get_enabled_backends(params)
        
        # Validate configuration
        errors = manager.validate_backend_config(params)
        
        # Send to all enabled backends
        results = manager.send_all(enabled, '/test/file.edi', params, settings)
        
        assert enabled == {'copy', 'ftp'}
        assert errors == []
        assert all(results.values())
    
    def test_partial_failure_workflow(self):
        """Test workflow with partial backend failure."""
        copy_backend = MockBackend(should_succeed=True)
        ftp_backend = MockBackend(should_succeed=False)
        
        manager = SendManager(backends={
            'copy': copy_backend,
            'ftp': ftp_backend
        })
        
        params = {
            'process_backend_copy': True,
            'process_backend_ftp': True
        }
        
        # First backend should succeed
        results = manager.send_all({'copy'}, '/test/file.edi', params, {})
        assert results['copy'] is True
        
        # Second backend should fail
        with pytest.raises(Exception):
            manager.send_all({'ftp'}, '/test/file.edi', params, {})
