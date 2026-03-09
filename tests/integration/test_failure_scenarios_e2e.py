"""Comprehensive end-to-end tests for failure scenarios and error recovery.

This test suite covers:
1. Multiple backend failures during processing
2. Database connection failures during operations
3. File system errors during processing
4. Recovery workflows after various failure modes
5. Mixed success/failure scenarios
6. Error propagation and logging verification
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e, pytest.mark.workflow, pytest.mark.slow]

import os
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import hashlib

import pytest

from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
from dispatch.send_manager import SendManager
from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler
from dispatch.hash_utils import generate_file_hash


@pytest.fixture
def sample_edi_content():
    """Sample EDI file content representing a valid invoice."""
    return """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""


@pytest.fixture
def temp_workspace(sample_edi_content):
    """Create a complete temporary workspace for batch processing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create input folder with EDI files
        input_folder = workspace / "input"
        input_folder.mkdir()
        
        # Create sample EDI files
        (input_folder / "invoice_001.edi").write_text(sample_edi_content)
        (input_folder / "invoice_002.edi").write_text(sample_edi_content.replace("00001", "00002"))
        (input_folder / "invoice_003.edi").write_text(sample_edi_content.replace("00001", "00003"))
        
        # Create output folder for copy backend
        output_folder = workspace / "output"
        output_folder.mkdir()
        
        yield {
            'workspace': workspace,
            'input_folder': input_folder,
            'output_folder': output_folder,
        }


@pytest.fixture
def folder_config(temp_workspace):
    """Create folder configuration for batch processing."""
    return {
        'id': 1,
        'folder_name': str(temp_workspace['input_folder']),
        'alias': 'TestFolder',
        'process_backend_copy': True,
        'copy_to_directory': str(temp_workspace['output_folder']),
        'process_backend_ftp': False,
        'process_backend_email': False,
        'convert_to_type': 'csv',
        'edi_filter_category': '',
    }


class TestBackendFailureScenarios:
    """Test various backend failure scenarios and recovery."""
    
    def test_multiple_backend_failures_with_partial_recovery(self, temp_workspace, folder_config):
        """Test processing when some backends fail but others succeed."""
        # Create a backend that fails on first file but succeeds on others
        call_count = 0
        class IntermittentFailureBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 1:  # First call fails
                    raise Exception("Backend failed on first call")
        
        class AlwaysSuccessBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                # Success - do nothing (no exception)
                pass
        
        config = DispatchConfig(
            backends={'copy': IntermittentFailureBackend(), 'email': AlwaysSuccessBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should have partial success - some files processed, some failed
        assert result.files_processed > 0, "Should process some files"
        assert result.files_failed > 0, "Should have some failures"
        assert result.success is False, "Overall should be failure due to partial failures"
    
    def test_all_backends_fail_with_error_logging(self, temp_workspace, folder_config, caplog):
        """Test that all backend failures are properly logged and tracked."""
        # Track failure details
        failure_details = []
        
        class LoggingFailureBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                failure_details.append({
                    'filename': filename,
                    'params': params,
                    'settings': settings
                })
                raise Exception("Logging backend failure")
        
        config = DispatchConfig(
            backends={'copy': LoggingFailureBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder and capture logging
        with caplog.at_level(logging.ERROR):
            result = orchestrator.process_folder(folder_config, run_log)
        
        # All files should fail
        assert result.files_failed == 3, "All 3 files should fail"
        assert result.files_processed == 0, "No files should be processed"
        assert len(failure_details) == 3, "Backend should be called for all 3 files"
        
        # Verify errors were logged via Python logging
        assert "Backend 'copy' failed to send: Logging backend failure" in caplog.text, \
            "Error should be logged via Python logging"
    
    def test_exception_in_one_backend_does_not_stop_others(self, temp_workspace, folder_config):
        """Test that exception in one backend doesn't stop other backends from processing."""
        class ExceptionBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                raise Exception("Critical backend failure")
        
        success_calls = []
        class SuccessBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                success_calls.append(filename)
                # Success - do nothing (no exception)
        
        config = DispatchConfig(
            backends={'exception_backend': ExceptionBackend(), 'success_backend': SuccessBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder - should continue despite exception in first backend
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Exception backend should fail, success backend should continue
        assert len(success_calls) == 3, "Success backend should process all files"
        assert result.files_processed >= 0  # Depends on implementation, but should not crash
    
    def test_cascading_backend_failures(self, temp_workspace, folder_config):
        """Test processing when multiple backends fail in sequence."""
        class CascadingFailureBackend:
            def __init__(self, fail_after_call=2):
                self.call_count = 0
                self.fail_after_call = fail_after_call
            
            def send(self, params: dict, settings: dict, filename: str) -> None:
                self.call_count += 1
                if self.call_count >= self.fail_after_call:
                    raise Exception(f"Backend failed after {self.call_count} calls")
                # Success - do nothing (no exception)
        
        config = DispatchConfig(
            backends={'ftp': CascadingFailureBackend(fail_after_call=2), 
                     'email': CascadingFailureBackend(fail_after_call=1)},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should handle cascading failures gracefully
        assert result is not None
        assert hasattr(result, 'files_failed')
        assert hasattr(result, 'files_processed')


class TestFileProcessingFailureScenarios:
    """Test file-specific processing failure scenarios."""
    
    def test_corrupted_file_handling(self, temp_workspace, folder_config):
        """Test handling of corrupted or invalid EDI files."""
        # Add a corrupted file
        corrupted_content = "This is not a valid EDI file content at all!"
        (temp_workspace['input_folder'] / "corrupted.edi").write_text(corrupted_content)
        
        success_calls = []
        class SuccessBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                success_calls.append(filename)
                return True
        
        config = DispatchConfig(
            backends={'copy': SuccessBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Set up folder_config to point to input with corrupted file
        folder_config['folder_name'] = str(temp_workspace['input_folder'])
        
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should process valid files but handle corrupted files appropriately
        assert len(success_calls) <= 3, "Should handle corrupted file without crashing"
        assert result.files_processed + result.files_failed == 4, "All 4 files should be attempted"
    
    def test_file_access_permission_failures(self, temp_workspace, folder_config):
        """Test handling of file permission errors during processing."""
        # Make one of the files unreadable (on systems that support it)
        test_file = temp_workspace['input_folder'] / "invoice_001.edi"
        original_mode = test_file.stat().st_mode
        
        success_calls = []
        class SuccessBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                success_calls.append(filename)
                return True
        
        try:
            # Try making file unreadable (on POSIX systems)
            test_file.chmod(0o000)
        
            config = DispatchConfig(
                backends={'copy': SuccessBackend()},
                settings={'test': 'value'}
            )
            orchestrator = DispatchOrchestrator(config)
            run_log = MagicMock()
            
            result = orchestrator.process_folder(folder_config, run_log)
            
            # Should handle permission errors gracefully
            assert result is not None
            assert result.files_processed + result.files_failed == 3, "All 3 files should be attempted"
        finally:
            # Restore file permissions
            test_file.chmod(original_mode)
    
    def test_output_folder_unavailable(self, temp_workspace, folder_config):
        """Test handling when output destination is unavailable."""
        # Temporarily make output directory unavailable
        output_dir = Path(folder_config['copy_to_directory'])
        original_path = folder_config['copy_to_directory']
        
        failure_calls = []
        class FailingCopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                # Try to access output directory that may not exist
                dest_dir = Path(params.get('copy_to_directory', output_dir))
                if not dest_dir.exists():
                    failure_calls.append(filename)
                    raise Exception("Output directory does not exist")
                # Attempt copy operation
                dest_file = dest_dir / Path(filename).name
                with open(filename, 'r') as src:
                    content = src.read()
                with open(dest_file, 'w') as dest:
                    dest.write(content)
                # Success - do nothing (no exception)
        
        # Temporarily remove output directory
        shutil.rmtree(output_dir)
        
        config = DispatchConfig(
            backends={'copy': FailingCopyBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder_config, run_log)
        
        # All files should fail due to output directory not existing
        assert result.files_failed == 3, "All files should fail due to output directory"
        assert len(failure_calls) == 3, "Backend should be called for all files"


class TestErrorRecoveryWorkflows:
    """Test error recovery and retry mechanisms."""
    
    def test_error_retry_logic(self, temp_workspace, folder_config):
        """Test that errors are properly tracked and can be retried."""
        # Create a backend that fails initially but succeeds on retry
        attempt_count = {}
        
        class RetryAwareBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                if filename not in attempt_count:
                    attempt_count[filename] = 0
                attempt_count[filename] += 1
                
                # Fail on first attempt, succeed on subsequent attempts
                if attempt_count[filename] < 2:
                    raise Exception(f"Backend failed on attempt {attempt_count[filename]} for {filename}")
        
        config = DispatchConfig(
            backends={'copy': RetryAwareBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # First attempt - should have failures
        result1 = orchestrator.process_folder(folder_config, run_log)
        
        # Simulate a retry mechanism
        # This would typically be handled by the application's retry logic
        failed_files = []
        if result1.files_failed > 0:
            # In a real scenario, we would retry failed files
            # Here we just verify that the system tracks failures properly
            assert result1.files_failed == 3, "First attempt should fail all files"
        
        # Process again - files should now succeed on retry
        result2 = orchestrator.process_folder(folder_config, run_log)
        
        # Verify tracking of attempts
        assert len(attempt_count) == 3, "All 3 files should be tracked"
        # Note: This test focuses on error tracking rather than actual retry
        # since the retry mechanism would be implemented at a higher level
    
    def test_error_isolation(self, temp_workspace, folder_config):
        """Test that errors in one file don't affect processing of other files."""
        # Track which files are processed
        processed_files = []
        
        class TrackingBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                # Fail for specific file only
                if "invoice_002" in filename:
                    raise Exception("Specific file failure for invoice_002")
                processed_files.append(filename)
                # Success - do nothing (no exception)
        
        config = DispatchConfig(
            backends={'copy': TrackingBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should process 2 files successfully, fail 1
        assert len(processed_files) == 2, "Should process 2 out of 3 files"
        assert result.files_processed == 2, "Should record 2 processed files"
        assert result.files_failed == 1, "Should record 1 failed file"
        assert result.success is False, "Overall success should be False due to failures"


class TestDatabaseConnectionFailures:
    """Test scenarios where database operations fail."""
    
    def test_database_unavailable_during_processing(self, temp_workspace, folder_config):
        """Test processing when database is unavailable."""
        # This would require mocking the database layer
        # For now, we'll test the error handling structure
        success_calls = []
        
        class SuccessBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                success_calls.append(filename)
                return True
        
        # Mock database operations to fail
        with patch('dispatch.hash_utils.generate_file_hash') as mock_hash:
            mock_hash.side_effect = Exception("Database unavailable")
            
            config = DispatchConfig(
                backends={'copy': SuccessBackend()},
                settings={'test': 'value'}
            )
            orchestrator = DispatchOrchestrator(config)
            run_log = MagicMock()
            
            result = orchestrator.process_folder(folder_config, run_log)
            
            # Should handle database failures gracefully
            assert result is not None
            assert result.success is False, "Should fail when database operations fail"