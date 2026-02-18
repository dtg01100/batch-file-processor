"""Tests for DispatchOrchestrator pipeline integration."""

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


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self, files=None, dirs=None):
        self.files = files or {}
        self.dirs = set(dirs or [])
    
    def dir_exists(self, path: str) -> bool:
        return path in self.dirs
    
    def list_files(self, path: str) -> list[str]:
        return [f for f in self.files if f.startswith(path) and self.dir_exists(path)]
    
    def read_file(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path].encode() if isinstance(self.files[path], str) else self.files[path]
    
    def makedirs(self, path: str) -> None:
        self.dirs.add(path)


class TestDispatchConfigPipelineFields:
    """Tests for DispatchConfig pipeline fields."""
    
    def test_default_pipeline_fields(self):
        """Test default values for pipeline fields."""
        config = DispatchConfig()
        
        assert config.upc_service is None
        assert config.progress_reporter is None
        assert config.validator_step is None
        assert config.splitter_step is None
        assert config.converter_step is None
        assert config.tweaker_step is None
        assert config.file_processor is None
        assert config.upc_dict == {}
        assert config.use_pipeline is False
    
    def test_set_pipeline_fields_in_constructor(self):
        """Test setting pipeline fields in constructor."""
        mock_validator = MagicMock()
        mock_splitter = MagicMock()
        mock_converter = MagicMock()
        mock_tweaker = MagicMock()
        mock_file_processor = MagicMock()
        mock_upc_service = MagicMock()
        mock_progress_reporter = MagicMock()
        
        config = DispatchConfig(
            validator_step=mock_validator,
            splitter_step=mock_splitter,
            converter_step=mock_converter,
            tweaker_step=mock_tweaker,
            file_processor=mock_file_processor,
            upc_service=mock_upc_service,
            progress_reporter=mock_progress_reporter,
            upc_dict={'123': 'product'},
            use_pipeline=True
        )
        
        assert config.validator_step is mock_validator
        assert config.splitter_step is mock_splitter
        assert config.converter_step is mock_converter
        assert config.tweaker_step is mock_tweaker
        assert config.file_processor is mock_file_processor
        assert config.upc_service is mock_upc_service
        assert config.progress_reporter is mock_progress_reporter
        assert config.upc_dict == {'123': 'product'}
        assert config.use_pipeline is True


class TestGetUPCDictionary:
    """Tests for _get_upc_dictionary method."""
    
    def test_with_cached_dictionary(self):
        """Test returning cached UPC dictionary."""
        cached_dict = {'123': 'product1', '456': 'product2'}
        config = DispatchConfig(upc_dict=cached_dict)
        orchestrator = DispatchOrchestrator(config)
        
        result = orchestrator._get_upc_dictionary({})
        
        assert result == cached_dict
    
    def test_fetch_new_dictionary_via_service(self):
        """Test fetching new dictionary via UPC service."""
        mock_upc_service = MagicMock()
        mock_upc_service.get_dictionary.return_value = {'789': 'product3'}
        
        config = DispatchConfig(upc_service=mock_upc_service)
        orchestrator = DispatchOrchestrator(config)
        
        result = orchestrator._get_upc_dictionary({})
        
        assert result == {'789': 'product3'}
        assert config.upc_dict == {'789': 'product3'}
        mock_upc_service.get_dictionary.assert_called_once()
    
    def test_service_exception_returns_empty_dict(self):
        """Test that service exception returns empty dict."""
        mock_upc_service = MagicMock()
        mock_upc_service.get_dictionary.side_effect = Exception("Service unavailable")
        
        config = DispatchConfig(upc_service=mock_upc_service)
        orchestrator = DispatchOrchestrator(config)
        
        result = orchestrator._get_upc_dictionary({})
        
        assert result == {}


class TestInitializePipelineSteps:
    """Tests for _initialize_pipeline_steps method."""
    
    def test_initialization_when_pipeline_enabled(self):
        """Test initialization when steps are provided."""
        mock_file_processor = MagicMock()
        mock_file_processor.initialize = MagicMock()
        
        config = DispatchConfig(
            use_pipeline=True,
            file_processor=mock_file_processor
        )
        orchestrator = DispatchOrchestrator(config)
        
        orchestrator._initialize_pipeline_steps()
        
        mock_file_processor.initialize.assert_called_once()
    
    def test_initialization_when_pipeline_disabled(self):
        """Test that no initialization happens when pipeline disabled."""
        mock_file_processor = MagicMock()
        
        config = DispatchConfig(
            use_pipeline=False,
            file_processor=mock_file_processor
        )
        orchestrator = DispatchOrchestrator(config)
        
        orchestrator._initialize_pipeline_steps()
        
        mock_file_processor.initialize.assert_not_called()
    
    def test_lazy_initialization_no_steps(self):
        """Test lazy initialization when no steps provided."""
        config = DispatchConfig(use_pipeline=True)
        orchestrator = DispatchOrchestrator(config)
        
        orchestrator._initialize_pipeline_steps()


class TestIsPipelineReady:
    """Tests for _is_pipeline_ready method."""
    
    def test_pipeline_ready_with_validator_step(self):
        """Test pipeline ready with validator step."""
        mock_validator = MagicMock()
        config = DispatchConfig(validator_step=mock_validator)
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._is_pipeline_ready() is True
    
    def test_pipeline_ready_with_splitter_step(self):
        """Test pipeline ready with splitter step."""
        mock_splitter = MagicMock()
        config = DispatchConfig(splitter_step=mock_splitter)
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._is_pipeline_ready() is True
    
    def test_pipeline_ready_with_converter_step(self):
        """Test pipeline ready with converter step."""
        mock_converter = MagicMock()
        config = DispatchConfig(converter_step=mock_converter)
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._is_pipeline_ready() is True
    
    def test_pipeline_ready_with_tweaker_step(self):
        """Test pipeline ready with tweaker step."""
        mock_tweaker = MagicMock()
        config = DispatchConfig(tweaker_step=mock_tweaker)
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._is_pipeline_ready() is True
    
    def test_pipeline_ready_with_file_processor(self):
        """Test pipeline ready with file processor."""
        mock_file_processor = MagicMock()
        config = DispatchConfig(file_processor=mock_file_processor)
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._is_pipeline_ready() is True
    
    def test_pipeline_not_ready(self):
        """Test pipeline not ready when no steps configured."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)
        
        assert orchestrator._is_pipeline_ready() is False


class TestProcessFolderWithPipeline:
    """Tests for process_folder_with_pipeline method."""
    
    def test_process_folder_pipeline_enabled(self):
        """Test processing with pipeline enabled."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file1.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, '/data/input/file1.edi')
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator_step=mock_validator,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        result = orchestrator.process_folder_with_pipeline(folder, run_log)
        
        assert result.folder_name == '/data/input'
        assert result.alias == 'Test'
    
    def test_pipeline_steps_called_correctly(self):
        """Test that pipeline steps are called correctly."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, '/data/input/file.edi')
        
        mock_converter = MagicMock()
        mock_converter.execute.return_value = '/data/input/file_converted.edi'
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator_step=mock_validator,
            converter_step=mock_converter,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_edi': 'True',
            'convert_edi': True,
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        result = orchestrator.process_folder_with_pipeline(folder, run_log)
        
        mock_validator.execute.assert_called()
        mock_converter.execute.assert_called()
    
    def test_pipeline_folder_not_found(self):
        """Test pipeline processing with non-existent folder."""
        mock_fs = MockFileSystem(dirs=[])
        
        config = DispatchConfig(
            file_system=mock_fs,
            use_pipeline=True
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/notexists', 'alias': 'Test'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder_with_pipeline(folder, run_log)
        
        assert result.success is False
        assert result.files_failed == 1
        assert 'not found' in result.errors[0].lower()
    
    def test_pipeline_empty_folder(self):
        """Test pipeline processing with empty folder."""
        mock_fs = MockFileSystem(dirs=['/data/input'])
        
        config = DispatchConfig(
            file_system=mock_fs,
            use_pipeline=True
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/input', 'alias': 'Test'}
        run_log = MagicMock()
        
        result = orchestrator.process_folder_with_pipeline(folder, run_log)
        
        assert result.success is True
        assert result.files_processed == 0


class TestProcessFileWithPipeline:
    """Tests for _process_file_with_pipeline method."""
    
    def test_full_pipeline_processing_flow(self):
        """Test full pipeline processing flow."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, '/data/input/file.edi')
        
        mock_converter = MagicMock()
        mock_converter.execute.return_value = None
        
        mock_tweaker = MagicMock()
        mock_tweaker.execute.return_value = None
        
        mock_file_processor = MagicMock()
        mock_file_processor.process.return_value = None
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator_step=mock_validator,
            converter_step=mock_converter,
            tweaker_step=mock_tweaker,
            file_processor=mock_file_processor,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_edi': 'True',
            'process_backend_copy': True
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {})
        
        assert result.file_name == '/data/input/file.edi'
        assert result.checksum is not None
    
    def test_pipeline_validation_failure(self):
        """Test pipeline with validation failure."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (False, ['Validation error'])
        
        config = DispatchConfig(
            file_system=mock_fs,
            validator_step=mock_validator,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_edi': 'True'
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {})
        
        assert result.validated is False
        assert 'Validation error' in result.errors
    
    def test_pipeline_splitter_integration(self):
        """Test pipeline with splitter step."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_splitter = MagicMock()
        mock_splitter.execute.return_value = ['/data/input/split1.edi', '/data/input/split2.edi']
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            splitter_step=mock_splitter,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'split_edi': True,
            'process_backend_copy': True
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {})
        
        mock_splitter.execute.assert_called_once()
    
    def test_pipeline_converter_integration(self):
        """Test pipeline with converter step."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, '/data/input/file.edi')
        
        mock_converter = MagicMock()
        mock_converter.execute.return_value = '/data/input/converted.edi'
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator_step=mock_validator,
            converter_step=mock_converter,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'convert_edi': True,
            'process_backend_copy': True
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {})
        
        mock_converter.execute.assert_called_once()
        assert result.converted is True
    
    def test_pipeline_tweaker_integration(self):
        """Test pipeline with tweaker step."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, '/data/input/file.edi')
        
        mock_tweaker = MagicMock()
        mock_tweaker.execute.return_value = '/data/input/tweaked.edi'
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator_step=mock_validator,
            tweaker_step=mock_tweaker,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'tweak_edi': True,
            'process_backend_copy': True
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {'123': 'product'})
        
        mock_tweaker.execute.assert_called_once()
    
    def test_pipeline_sending_to_backends(self):
        """Test pipeline sending files to backends."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_backend_copy': True
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {})
        
        assert result.sent is True
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.side_effect = Exception("Validator error")
        
        config = DispatchConfig(
            file_system=mock_fs,
            validator_step=mock_validator,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_edi': 'True'
        }
        
        result = orchestrator._process_file_with_pipeline('/data/input/file.edi', folder, {})
        
        assert 'Validator error' in result.errors


class TestSendPipelineFile:
    """Tests for _send_pipeline_file method."""
    
    def test_send_pipeline_file_success(self):
        """Test successful sending of pipeline file."""
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            backends={'copy': mock_backend},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'process_backend_copy': True}
        
        result = orchestrator._send_pipeline_file('/data/input/file.edi', folder)
        
        assert result is True
    
    def test_send_pipeline_file_no_backends(self):
        """Test sending with no enabled backends."""
        config = DispatchConfig(
            backends={},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {}
        
        result = orchestrator._send_pipeline_file('/data/input/file.edi', folder)
        
        assert result is False
    
    def test_send_pipeline_file_partial_failure(self):
        """Test sending with partial backend failure."""
        mock_backend1 = MagicMock()
        mock_backend1.send.return_value = True
        
        mock_backend2 = MagicMock()
        mock_backend2.send.return_value = False
        
        config = DispatchConfig(
            backends={'copy1': mock_backend1, 'copy2': mock_backend2},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'process_backend_copy1': True, 'process_backend_copy2': True}
        
        result = orchestrator._send_pipeline_file('/data/input/file.edi', folder)
        
        assert result is False


class TestProcessFolderPipelineRouting:
    """Tests for routing in process_folder method."""
    
    def test_process_folder_routes_to_pipeline(self):
        """Test that process_folder routes to pipeline when enabled."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, '/data/input/file.edi')
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator_step=mock_validator,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        with patch.object(orchestrator, 'process_folder_with_pipeline') as mock_pipeline:
            mock_pipeline.return_value = FolderResult(
                folder_name='/data/input',
                alias='Test',
                files_processed=1
            )
            result = orchestrator.process_folder(folder, run_log)
            
            mock_pipeline.assert_called_once()
    
    def test_process_folder_routes_to_legacy(self):
        """Test that process_folder routes to legacy when pipeline not enabled."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            use_pipeline=False,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        with patch.object(orchestrator, '_process_folder_legacy') as mock_legacy:
            mock_legacy.return_value = FolderResult(
                folder_name='/data/input',
                alias='Test',
                files_processed=1
            )
            result = orchestrator.process_folder(folder, run_log)
            
            mock_legacy.assert_called_once()
    
    def test_legacy_processing_when_pipeline_not_ready(self):
        """Test legacy processing when pipeline not ready despite use_pipeline flag."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        with patch.object(orchestrator, '_process_folder_legacy') as mock_legacy:
            mock_legacy.return_value = FolderResult(
                folder_name='/data/input',
                alias='Test',
                files_processed=1
            )
            result = orchestrator.process_folder(folder, run_log)
            
            mock_legacy.assert_called_once()


class TestProcessFilePipelineRouting:
    """Tests for routing in process_file method."""
    
    def test_process_file_routes_to_pipeline(self):
        """Test that process_file routes to pipeline when enabled."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_validator = MagicMock()
        
        config = DispatchConfig(
            file_system=mock_fs,
            validator_step=mock_validator,
            use_pipeline=True,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/input'}
        
        with patch.object(orchestrator, '_process_file_with_pipeline') as mock_pipeline:
            mock_pipeline.return_value = FileResult(
                file_name='/data/input/file.edi',
                checksum='abc123'
            )
            result = orchestrator.process_file('/data/input/file.edi', folder)
            
            mock_pipeline.assert_called_once()
    
    def test_process_file_routes_to_legacy(self):
        """Test that process_file routes to legacy when pipeline not enabled."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        config = DispatchConfig(
            file_system=mock_fs,
            use_pipeline=False,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {'folder_name': '/data/input'}
        
        with patch.object(orchestrator, '_process_file_legacy') as mock_legacy:
            mock_legacy.return_value = FileResult(
                file_name='/data/input/file.edi',
                checksum='abc123'
            )
            result = orchestrator.process_file('/data/input/file.edi', folder)
            
            mock_legacy.assert_called_once()


class TestBackwardCompatibility:
    """Tests for backward compatibility with legacy processing."""
    
    def test_legacy_processing_still_works(self):
        """Test that legacy processing still works when pipeline not enabled."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            use_pipeline=False,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_backend_copy': True
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        assert result.file_name == '/data/input/file.edi'
        assert result.checksum is not None
    
    def test_legacy_processing_with_validation(self):
        """Test legacy processing with validation."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'valid content'}
        )
        
        mock_validator = MagicMock()
        mock_validator.validate.return_value = (True, [])
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            validator=mock_validator,
            use_pipeline=False,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'process_edi': 'True',
            'process_backend_copy': True
        }
        
        result = orchestrator.process_file('/data/input/file.edi', folder)
        
        mock_validator.validate.assert_called_once()
    
    def test_legacy_folder_processing(self):
        """Test legacy folder processing."""
        mock_fs = MockFileSystem(
            dirs=['/data/input'],
            files={'/data/input/file.edi': b'content'}
        )
        
        mock_backend = MagicMock()
        mock_backend.send.return_value = True
        
        config = DispatchConfig(
            file_system=mock_fs,
            backends={'copy': mock_backend},
            use_pipeline=False,
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder = {
            'folder_name': '/data/input',
            'alias': 'Test',
            'process_backend_copy': True
        }
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder, run_log)
        
        assert result.folder_name == '/data/input'
        assert result.alias == 'Test'
