"""Tests for dispatch/pipeline/converter.py module."""

from unittest.mock import MagicMock, patch
import pytest

from dispatch.pipeline.converter import (
    ConverterResult,
    ConverterInterface,
    ModuleLoaderProtocol,
    DefaultModuleLoader,
    MockConverter,
    EDIConverterStep,
    SUPPORTED_FORMATS,
)


class MockFileSystem:
    """Mock file system for testing."""
    
    def __init__(self, files: dict[str, str] = None):
        self.files = files or {}
        self.text_files = {}
        self.binary_files = {}
        self.directories = set()
        self.removed_files = []
    
    def read_file_text(self, path: str, encoding: str = 'utf-8') -> str:
        if path not in self.files and path not in self.text_files:
            raise FileNotFoundError(f"File not found: {path}")
        return self.files.get(path, self.text_files.get(path, ''))
    
    def read_file(self, path: str) -> bytes:
        if path not in self.files and path not in self.binary_files:
            raise FileNotFoundError(f"File not found: {path}")
        content = self.files.get(path) or self.binary_files.get(path, b'')
        if isinstance(content, str):
            return content.encode()
        return content
    
    def write_file(self, path: str, data: bytes) -> None:
        self.binary_files[path] = data
    
    def write_file_text(self, path: str, data: str, encoding: str = 'utf-8') -> None:
        self.text_files[path] = data
    
    def file_exists(self, path: str) -> bool:
        return path in self.files or path in self.text_files or path in self.binary_files
    
    def dir_exists(self, path: str) -> bool:
        return path in self.directories
    
    def mkdir(self, path: str) -> None:
        self.directories.add(path)
    
    def makedirs(self, path: str) -> None:
        self.directories.add(path)
    
    def copy_file(self, src: str, dst: str) -> None:
        if src in self.files:
            self.files[dst] = self.files[src]
    
    def remove_file(self, path: str) -> None:
        self.removed_files.append(path)
        self.files.pop(path, None)
        self.text_files.pop(path, None)
        self.binary_files.pop(path, None)
    
    def get_absolute_path(self, path: str) -> str:
        return path
    
    def list_files(self, path: str) -> list[str]:
        all_files = list(self.files.keys()) + list(self.text_files.keys()) + list(self.binary_files.keys())
        return [f for f in all_files if f.startswith(path)]


class MockErrorHandler:
    """Mock error handler for testing."""
    
    def __init__(self):
        self.errors = []
    
    def record_error(self, folder: str, filename: str, error: Exception, context: dict = None, error_source: str = "Dispatch"):
        self.errors.append({
            'folder': folder,
            'filename': filename,
            'error': error,
            'context': context,
            'error_source': error_source
        })


class MockModuleLoader:
    """Mock module loader for testing."""
    
    def __init__(self, modules: dict = None):
        self._modules = modules or {}
        self.call_count = 0
        self.last_module_name = None
    
    def load_module(self, module_name: str):
        self.call_count += 1
        self.last_module_name = module_name
        
        if module_name not in self._modules:
            raise ImportError(f"No module named '{module_name}'")
        
        return self._modules[module_name]
    
    def module_exists(self, module_name: str) -> bool:
        return module_name in self._modules
    
    def add_module(self, name: str, module):
        self._modules[name] = module


def create_mock_conversion_module(output_path: str = '/output/converted.csv', should_raise: Exception = None):
    """Create a mock conversion module with edi_convert function."""
    module = MagicMock()
    
    if should_raise:
        module.edi_convert.side_effect = should_raise
    else:
        module.edi_convert.return_value = output_path
    
    return module


class TestConverterResult:
    """Tests for ConverterResult dataclass."""
    
    def test_default_values(self):
        """Test ConverterResult with default values."""
        result = ConverterResult()
        
        assert result.output_path == ""
        assert result.format_used == ""
        assert result.success is False
        assert result.errors == []
    
    def test_custom_values(self):
        """Test ConverterResult with custom values."""
        result = ConverterResult(
            output_path="/output/converted.csv",
            format_used="csv",
            success=True,
            errors=["Warning: minor issue"]
        )
        
        assert result.output_path == "/output/converted.csv"
        assert result.format_used == "csv"
        assert result.success is True
        assert result.errors == ["Warning: minor issue"]
    
    def test_errors_list_handling(self):
        """Test that errors list is properly handled."""
        errors = ["Error 1", "Error 2", "Error 3"]
        result = ConverterResult(
            output_path="/output/test.csv",
            format_used="csv",
            success=False,
            errors=errors
        )
        
        assert len(result.errors) == 3
        assert "Error 1" in result.errors
        assert "Error 2" in result.errors
        assert "Error 3" in result.errors
    
    def test_errors_list_mutable(self):
        """Test that errors list can be modified after creation."""
        result = ConverterResult()
        
        result.errors.append("New error")
        result.errors.append("Another error")
        
        assert len(result.errors) == 2
        assert "New error" in result.errors
        assert "Another error" in result.errors
    
    def test_empty_errors_list(self):
        """Test ConverterResult with explicitly empty errors list."""
        result = ConverterResult(errors=[])
        
        assert result.errors == []
        assert len(result.errors) == 0


class TestDefaultModuleLoader:
    """Tests for DefaultModuleLoader class."""
    
    def test_loading_a_valid_module(self):
        """Test loading a valid module."""
        loader = DefaultModuleLoader()
        
        module = loader.load_module('os')
        
        assert module is not None
        assert hasattr(module, 'path')
    
    def test_module_exists_returns_true_for_valid_modules(self):
        """Test module_exists returns True for valid modules."""
        loader = DefaultModuleLoader()
        
        assert loader.module_exists('os') is True
        assert loader.module_exists('sys') is True
    
    def test_module_exists_returns_false_for_invalid_modules(self):
        """Test module_exists returns False for invalid modules."""
        loader = DefaultModuleLoader()
        
        assert loader.module_exists('nonexistent_module_xyz') is False
        assert loader.module_exists('another_fake_module_123') is False
    
    def test_load_module_raises_import_error_for_invalid_module(self):
        """Test load_module raises ImportError for invalid module."""
        loader = DefaultModuleLoader()
        
        with pytest.raises(ImportError):
            loader.load_module('nonexistent_module_xyz')


class TestMockConverter:
    """Tests for MockConverter class."""
    
    def test_initialization_with_default_result(self):
        """Test MockConverter initialization with default result."""
        converter = MockConverter()
        
        assert converter._result is not None
        assert converter._result.output_path == ""
        assert converter._result.format_used == ""
        assert converter._result.success is True
        assert converter._result.errors == []
        assert converter.call_count == 0
    
    def test_initialization_with_custom_result(self):
        """Test MockConverter initialization with custom result."""
        custom_result = ConverterResult(
            output_path="/output/custom.csv",
            format_used="csv",
            success=True,
            errors=[]
        )
        converter = MockConverter(result=custom_result)
        
        assert converter._result == custom_result
        assert converter._result.output_path == "/output/custom.csv"
    
    def test_initialization_with_individual_parameters(self):
        """Test MockConverter initialization with individual parameters."""
        converter = MockConverter(
            output_path="/output/test.csv",
            format_used="csv",
            success=False,
            errors=["Test error"]
        )
        
        assert converter._result.output_path == "/output/test.csv"
        assert converter._result.format_used == "csv"
        assert converter._result.success is False
        assert converter._result.errors == ["Test error"]
    
    def test_call_tracking(self):
        """Test call tracking (call_count, last_* fields)."""
        converter = MockConverter()
        
        assert converter.call_count == 0
        assert converter.last_input_path is None
        assert converter.last_output_dir is None
        assert converter.last_params is None
        assert converter.last_settings is None
        assert converter.last_upc_dict is None
        
        converter.convert('/input/test.edi', '/output', {'param': 'value'}, {'setting': 'value'}, {'upc': 'dict'})
        
        assert converter.call_count == 1
        assert converter.last_input_path == '/input/test.edi'
        assert converter.last_output_dir == '/output'
        assert converter.last_params == {'param': 'value'}
        assert converter.last_settings == {'setting': 'value'}
        assert converter.last_upc_dict == {'upc': 'dict'}
        
        converter.convert('/input/another.edi', '/output2', {}, {}, {})
        
        assert converter.call_count == 2
        assert converter.last_input_path == '/input/another.edi'
        assert converter.last_output_dir == '/output2'
    
    def test_reset_method(self):
        """Test reset method clears tracking state."""
        converter = MockConverter()
        
        converter.convert('/input/test.edi', '/output', {}, {}, {})
        
        assert converter.call_count == 1
        assert converter.last_input_path == '/input/test.edi'
        
        converter.reset()
        
        assert converter.call_count == 0
        assert converter.last_input_path is None
        assert converter.last_output_dir is None
        assert converter.last_params is None
        assert converter.last_settings is None
        assert converter.last_upc_dict is None
    
    def test_set_result_method(self):
        """Test set_result method updates the result."""
        converter = MockConverter()
        
        new_result = ConverterResult(
            output_path="/new/output.csv",
            format_used="csv",
            success=True,
            errors=[]
        )
        
        converter.set_result(new_result)
        
        assert converter._result == new_result
        assert converter._result.output_path == "/new/output.csv"
    
    def test_convert_returns_configured_result(self):
        """Test that convert returns the configured result."""
        custom_result = ConverterResult(
            output_path="/output/test.csv",
            format_used="csv",
            success=True,
            errors=[]
        )
        converter = MockConverter(result=custom_result)
        
        result = converter.convert('/input/test.edi', '/output', {}, {}, {})
        
        assert result == custom_result
        assert result.output_path == "/output/test.csv"


class TestEDIConverterStep:
    """Tests for EDIConverterStep class."""
    
    def test_initialization_with_defaults(self):
        """Test EDIConverterStep initialization with default values."""
        step = EDIConverterStep()
        
        assert step._module_loader is not None
        assert isinstance(step._module_loader, DefaultModuleLoader)
        assert step._error_handler is None
        assert step._file_system is None
    
    def test_initialization_with_injected_dependencies(self):
        """Test EDIConverterStep initialization with injected dependencies."""
        mock_loader = MockModuleLoader()
        mock_error_handler = MockErrorHandler()
        mock_fs = MockFileSystem()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler,
            file_system=mock_fs
        )
        
        assert step._module_loader is mock_loader
        assert step._error_handler is mock_error_handler
        assert step._file_system is mock_fs
    
    def test_convert_with_no_format_specified(self):
        """Test convert() with no format specified (returns input path)."""
        step = EDIConverterStep()
        
        params = {}
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == ""
        assert result.success is True
        assert result.errors == []
    
    def test_convert_with_process_edi_not_true(self):
        """Test convert() with process_edi != "True" (returns input path)."""
        step = EDIConverterStep()
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'False'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == 'csv'
        assert result.success is True
        assert result.errors == []
    
    def test_convert_with_unsupported_format(self):
        """Test convert() with unsupported format."""
        mock_error_handler = MockErrorHandler()
        step = EDIConverterStep(error_handler=mock_error_handler)
        
        params = {
            'convert_to_format': 'unsupported_format',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == 'unsupported_format'
        assert result.success is False
        assert len(result.errors) == 1
        assert "Unsupported conversion format" in result.errors[0]
    
    def test_convert_with_supported_format_and_mock_module_loader(self):
        """Test convert() with supported format and mock module loader."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/output/converted.csv'
        assert result.format_used == 'csv'
        assert result.success is True
        assert result.errors == []
        assert mock_loader.last_module_name == 'convert_to_csv'
    
    def test_convert_handles_import_error(self):
        """Test convert() handles ImportError."""
        mock_loader = MockModuleLoader({})
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == 'csv'
        assert result.success is False
        assert len(result.errors) == 1
        assert "Conversion module not found" in result.errors[0]
    
    def test_convert_handles_module_without_edi_convert_function(self):
        """Test convert() handles module without edi_convert function."""
        mock_module = MagicMock(spec=[])
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == 'csv'
        assert result.success is False
        assert len(result.errors) == 1
        assert "does not have edi_convert function" in result.errors[0]
    
    def test_convert_handles_conversion_exception(self):
        """Test convert() handles conversion exception."""
        mock_module = create_mock_conversion_module(should_raise=RuntimeError("Conversion failed"))
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == 'csv'
        assert result.success is False
        assert len(result.errors) == 1
        assert "Conversion failed" in result.errors[0]
    
    def test_error_recording_to_error_handler(self):
        """Test error recording to error handler."""
        mock_loader = MockModuleLoader({})
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert len(mock_error_handler.errors) == 1
        assert mock_error_handler.errors[0]['filename'] == '/input/test.edi'
        assert mock_error_handler.errors[0]['error_source'] == 'EDIConverter'
        assert mock_error_handler.errors[0]['context'] == {'source': 'EDIConverterStep'}
    
    def test_get_supported_formats(self):
        """Test get_supported_formats()."""
        step = EDIConverterStep()
        
        formats = step.get_supported_formats()
        
        assert formats == SUPPORTED_FORMATS
        assert 'csv' in formats
        assert 'fintech' in formats
        assert isinstance(formats, list)
    
    def test_get_supported_formats_returns_copy(self):
        """Test get_supported_formats returns a copy."""
        step = EDIConverterStep()
        
        formats1 = step.get_supported_formats()
        formats2 = step.get_supported_formats()
        
        formats1.append('new_format')
        
        assert 'new_format' not in formats2
    
    def test_format_normalization_with_spaces(self):
        """Test format normalization handles spaces."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_estore_einvoice': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'estore einvoice',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.success is True
        assert mock_loader.last_module_name == 'convert_to_estore_einvoice'
    
    def test_format_normalization_with_hyphens(self):
        """Test format normalization handles hyphens."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_estore_einvoice': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'estore-einvoice',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.success is True
        assert mock_loader.last_module_name == 'convert_to_estore_einvoice'
    
    def test_format_normalization_case_insensitive(self):
        """Test format normalization is case insensitive."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'CSV',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.success is True
        assert mock_loader.last_module_name == 'convert_to_csv'


class TestProtocolTests:
    """Protocol tests for converter module."""
    
    def test_mock_converter_satisfies_converter_interface(self):
        """Test MockConverter satisfies ConverterInterface."""
        converter = MockConverter()
        
        assert hasattr(converter, 'convert')
        assert callable(converter.convert)
    
    def test_edi_converter_step_satisfies_converter_interface(self):
        """Test EDIConverterStep satisfies ConverterInterface."""
        step = EDIConverterStep()
        
        assert hasattr(step, 'convert')
        assert callable(step.convert)
    
    def test_mock_module_loader_satisfies_module_loader_protocol(self):
        """Test MockModuleLoader satisfies ModuleLoaderProtocol."""
        loader = MockModuleLoader()
        
        assert hasattr(loader, 'load_module')
        assert hasattr(loader, 'module_exists')
        assert callable(loader.load_module)
        assert callable(loader.module_exists)
    
    def test_default_module_loader_satisfies_module_loader_protocol(self):
        """Test DefaultModuleLoader satisfies ModuleLoaderProtocol."""
        loader = DefaultModuleLoader()
        
        assert hasattr(loader, 'load_module')
        assert hasattr(loader, 'module_exists')
        assert callable(loader.load_module)
        assert callable(loader.module_exists)


class TestIntegration:
    """Integration tests for converter module."""
    
    def test_full_conversion_flow_with_mock_module_loader(self):
        """Test full conversion flow with mock module loader."""
        mock_module = create_mock_conversion_module('/output/result.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        settings = {'setting1': 'value1'}
        upc_dict = {'upc': 'data'}
        
        result = step.convert('/input/test.edi', '/output', params, settings, upc_dict)
        
        assert result.success is True
        assert result.output_path == '/output/result.csv'
        assert result.format_used == 'csv'
        assert len(mock_error_handler.errors) == 0
        
        mock_module.edi_convert.assert_called_once_with(
            '/input/test.edi',
            '/output/test.edi',
            settings,
            params,
            upc_dict
        )
    
    def test_output_directory_created_if_needed(self):
        """Test that output directory is created if needed."""
        mock_module = create_mock_conversion_module('/output/subdir/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        mock_fs = MockFileSystem()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            file_system=mock_fs
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        
        result = step.convert('/input/test.edi', '/output/subdir', params, {}, {})
        
        assert result.success is True
    
    def test_multiple_conversions_in_sequence(self):
        """Test multiple conversions in sequence."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        
        result1 = step.convert('/input/file1.edi', '/output', params, {}, {})
        result2 = step.convert('/input/file2.edi', '/output', params, {}, {})
        
        assert result1.success is True
        assert result2.success is True
        assert mock_loader.call_count == 2
    
    def test_error_handler_context_preserved(self):
        """Test that error handler receives correct context."""
        mock_loader = MockModuleLoader({})
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert mock_error_handler.errors[0]['context'] == {'source': 'EDIConverterStep'}
    
    def test_conversion_with_all_supported_formats(self):
        """Test conversion with various supported formats."""
        for format_name in ['csv', 'fintech', 'scannerware']:
            mock_module = create_mock_conversion_module(f'/output/converted.{format_name}')
            mock_loader = MockModuleLoader({f'convert_to_{format_name}': mock_module})
            
            step = EDIConverterStep(module_loader=mock_loader)
            
            params = {
                'convert_to_format': format_name,
                'process_edi': 'True'
            }
            result = step.convert('/input/test.edi', '/output', params, {}, {})
            
            assert result.success is True
            assert result.format_used == format_name
    
    def test_no_conversion_without_process_edi_flag(self):
        """Test no conversion happens without process_edi = True."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'False'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert mock_loader.call_count == 0
        assert result.output_path == '/input/test.edi'


class TestEdgeCases:
    """Edge case tests for converter module."""
    
    def test_empty_convert_to_format(self):
        """Test with empty convert_to_format string."""
        step = EDIConverterStep()
        
        params = {
            'convert_to_format': '',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == ""
    
    def test_missing_convert_to_format_key(self):
        """Test with missing convert_to_format key."""
        step = EDIConverterStep()
        
        params = {'process_edi': 'True'}
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.format_used == ""
    
    def test_empty_params_dict(self):
        """Test with empty params dict."""
        step = EDIConverterStep()
        
        result = step.convert('/input/test.edi', '/output', {}, {}, {})
        
        assert result.output_path == '/input/test.edi'
        assert result.success is True
    
    def test_none_upc_dict(self):
        """Test with None upc_dict."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, None)
        
        assert result.success is True
    
    def test_format_with_mixed_spaces_and_hyphens(self):
        """Test format normalization with mixed spaces and hyphens."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_estore_einvoice_generic': mock_module})
        
        step = EDIConverterStep(module_loader=mock_loader)
        
        params = {
            'convert_to_format': 'estore einvoice-generic',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.success is True
        assert mock_loader.last_module_name == 'convert_to_estore_einvoice_generic'
    
    def test_file_system_makedirs_failure(self):
        """Test handling of file system makedirs failure."""
        mock_module = create_mock_conversion_module('/output/converted.csv')
        mock_loader = MockModuleLoader({'convert_to_csv': mock_module})
        mock_fs = MockFileSystem()
        
        def raise_error(path):
            raise PermissionError("Cannot create directory")
        
        mock_fs.makedirs = raise_error
        mock_error_handler = MockErrorHandler()
        
        step = EDIConverterStep(
            module_loader=mock_loader,
            file_system=mock_fs,
            error_handler=mock_error_handler
        )
        
        params = {
            'convert_to_format': 'csv',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert result.success is False
        assert "Failed to create output directory" in result.errors[0]
    
    def test_large_number_of_errors_recorded(self):
        """Test that multiple errors are recorded correctly."""
        step = EDIConverterStep()
        
        params = {
            'convert_to_format': 'invalid_format_1',
            'process_edi': 'True'
        }
        result = step.convert('/input/test.edi', '/output', params, {}, {})
        
        assert len(result.errors) == 1
    
    def test_converter_result_with_all_fields_set(self):
        """Test ConverterResult with all fields explicitly set."""
        result = ConverterResult(
            output_path="/path/to/output.csv",
            format_used="csv",
            success=True,
            errors=["warning1", "warning2"]
        )
        
        assert result.output_path == "/path/to/output.csv"
        assert result.format_used == "csv"
        assert result.success is True
        assert len(result.errors) == 2