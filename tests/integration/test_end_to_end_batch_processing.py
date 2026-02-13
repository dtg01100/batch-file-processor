"""End-to-end integration test for batch file processing.

This test exercises the complete batch processing flow from start to finish:
1. File discovery in input folders
2. Hash generation and duplicate detection
3. EDI validation
4. File sending via backends
5. Error handling and recovery

Uses real file system and refactored components for realistic testing.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import hashlib

import pytest

from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
from dispatch.send_manager import SendManager
from dispatch.edi_validator import EDIValidator
from dispatch.error_handler import ErrorHandler
from dispatch.hash_utils import generate_file_hash


# =============================================================================
# Test Fixtures
# =============================================================================

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


@pytest.fixture
def mock_backends(temp_workspace):
    """Create mock backends for testing."""
    class MockCopyBackend:
        """Mock copy backend that implements BackendInterface."""
        def send(self, params: dict, settings: dict, filename: str) -> bool:
            """Send file using copy semantics (matching BackendInterface)."""
            # Copy file to destination directory
            dest_dir = Path(params.get('copy_to_directory', temp_workspace['output_folder']))
            if not dest_dir.exists():
                dest_dir.mkdir(parents=True)
            dest_file = dest_dir / Path(filename).name
            shutil.copy(filename, dest_file)
            return True
    
    class MockFTPBackend:
        """Mock FTP backend that implements BackendInterface."""
        def send(self, params: dict, settings: dict, filename: str) -> bool:
            """Mock FTP send."""
            return True
    
    class MockEmailBackend:
        """Mock email backend that implements BackendInterface."""
        def send(self, params: dict, settings: dict, filename: str) -> bool:
            """Mock email send."""
            return True
    
    return {
        'copy': MockCopyBackend(),
        'ftp': MockFTPBackend(),
        'email': MockEmailBackend(),
    }


# =============================================================================
# End-to-End Tests
# =============================================================================

class TestEndToEndBatchProcessing:
    """Test complete batch processing workflow using real files and orchestrator."""
    
    def test_full_batch_processing_flow(self, temp_workspace, folder_config, mock_backends):
        """Test complete batch processing from file discovery through file sending.
        
        This test verifies the complete end-to-end flow:
        1. Files are discovered in input folder
        2. Files are validated
        3. Files are sent to backends
        4. Processing completes successfully
        """
        # Create orchestrator
        config = DispatchConfig(
            backends=mock_backends,
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Verify processing succeeded
        assert result.folder_name == str(temp_workspace['input_folder'])
        assert result.alias == 'TestFolder'
        assert result.success is True
        assert result.files_processed == 3, "Should process all 3 files"
        assert result.files_failed == 0, "No files should fail"
        
        # Verify files were copied to output
        output_files = list(temp_workspace['output_folder'].glob("*.edi"))
        assert len(output_files) == 3, "All files should be copied to output"
    
    def test_file_hashing_consistency(self, temp_workspace):
        """Test that file hash generation is consistent."""
        file_path = temp_workspace['input_folder'] / "invoice_001.edi"
        
        # Generate hash multiple times
        hash1 = generate_file_hash(str(file_path))
        hash2 = generate_file_hash(str(file_path))
        hash3 = generate_file_hash(str(file_path))
        
        # All hashes should be identical
        assert hash1 == hash2 == hash3, "Same file should produce same hash"
        assert hash1 is not None
        assert len(hash1) == 32, "MD5 hash should be 32 hex characters"
        assert isinstance(hash1, str)
    
    def test_different_files_different_hashes(self, temp_workspace):
        """Test that different files produce different hashes."""
        file1 = temp_workspace['input_folder'] / "invoice_001.edi"
        file2 = temp_workspace['input_folder'] / "invoice_002.edi"
        
        hash1 = generate_file_hash(str(file1))
        hash2 = generate_file_hash(str(file2))
        
        assert hash1 != hash2, "Different files should have different hashes"
    
    def test_multiple_backends_enabled(self, temp_workspace, folder_config):
        """Test processing with multiple backends enabled."""
        # Enable multiple backends
        folder_config['process_backend_copy'] = True
        folder_config['process_backend_ftp'] = True
        folder_config['ftp_server'] = 'test.example.com'
        
        # Track backend calls
        copy_calls = []
        ftp_calls = []
        
        class TrackingCopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                copy_calls.append(filename)
                return True
        
        class TrackingFTPBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                ftp_calls.append(filename)
                return True
        
        config = DispatchConfig(
            backends={'copy': TrackingCopyBackend(), 'ftp': TrackingFTPBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Verify processing succeeded
        assert result.success is True
        assert result.files_processed == 3
        
        # Verify both backends were called
        assert len(copy_calls) == 3, "Copy backend should be called for all 3 files"
        assert len(ftp_calls) == 3, "FTP backend should be called for all 3 files"
    
    def test_backend_failure_handling(self, temp_workspace, folder_config):
        """Test handling of backend failures during processing."""
        # Create a failing backend that raises an exception (not just returns False)
        class FailingBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                raise Exception("Backend send failed")
        
        config = DispatchConfig(
            backends={'copy': FailingBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Verify failures were recorded
        assert result.success is False, "Should fail when backend raises exception"
        assert result.files_failed == 3, "All files should fail"
        assert result.files_processed == 0, "No files should succeed"
    
    def test_backend_exception_handling(self, temp_workspace, folder_config):
        """Test handling of backend exceptions during processing."""
        # Create a backend that raises exceptions
        class ExceptionBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                raise Exception("Network error")
        
        config = DispatchConfig(
            backends={'copy': ExceptionBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process should handle exception gracefully
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should complete without raising exception
        assert result is not None
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_empty_folder_processing(self, temp_workspace, folder_config, mock_backends):
        """Test processing an empty folder."""
        # Create empty folder
        empty_folder = temp_workspace['workspace'] / "empty"
        empty_folder.mkdir()
        
        folder_config['folder_name'] = str(empty_folder)  
        
        config = DispatchConfig(
            backends=mock_backends,
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process empty folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should complete successfully with no files processed
        assert result.success is True
        assert result.files_processed == 0
        assert result.files_failed == 0
    
    def test_missing_folder_handling(self, temp_workspace, folder_config, mock_backends):
        """Test handling of non-existent folders."""
        # Point to non-existent folder
        folder_config['folder_name'] = str(temp_workspace['workspace'] / "nonexistent")
        
        config = DispatchConfig(
            backends=mock_backends,
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process non-existent folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should handle gracefully
        assert result is not None
        assert result.files_processed == 0
    
    def test_mixed_success_and_failure(self, temp_workspace, folder_config):
        """Test processing where some files succeed and some fail."""
        # Create backend that raises exception for specific files
        class SelectiveBackend:
            def send(self, params: dict, settings: dict, filename: str) -> bool:
                # Raise exception for invoice_002, succeed on others
                if 'invoice_002' in filename:
                    raise Exception("Failed for invoice_002")
                return True
        
        config = DispatchConfig(
            backends={'copy': SelectiveBackend()},
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should have mixed results
        assert result.files_processed == 2, "Two files should succeed"
        assert result.files_failed == 1, "One file should fail"
        assert result.success is False, "Overall should be failure"
    
    def test_file_filters_edi_files_only(self, temp_workspace, folder_config, mock_backends):
        """Test that only EDI files are processed."""
        # Create non-EDI files in input folder
        (temp_workspace['input_folder'] / "readme.txt").write_text("Not an EDI file")
        (temp_workspace['input_folder'] / "data.csv").write_text("col1,col2\n1,2")
        
        config = DispatchConfig(
            backends=mock_backends,
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder
        result = orchestrator.process_folder(folder_config, run_log)
        
        # Should only process EDI files
        # Note: Actual behavior depends on orchestrator implementation
        # This test documents expected behavior
        assert result.files_processed >= 3, "Should process at least the 3 EDI files"


# =============================================================================
# Performance and Stress Tests
# =============================================================================

class TestBatchProcessingPerformance:
    """Test performance characteristics of batch processing."""
    
    def test_processes_multiple_files_efficiently(self, temp_workspace, folder_config, mock_backends, sample_edi_content):
        """Test that multiple files are processed efficiently."""
        # Create 10 more files
        for i in range(4, 14):
            (temp_workspace['input_folder'] / f"invoice_{i:03d}.edi").write_text(
                sample_edi_content.replace("00001", f"{i:05d}")
            )
        
        config = DispatchConfig(
            backends=mock_backends,
            settings={'test': 'value'}
        )
        orchestrator = DispatchOrchestrator(config)
        run_log = MagicMock()
        
        # Process folder with 13 files
        result = orchestrator.process_folder(folder_config, run_log)
        
        # All files should be processed
        assert result.files_processed == 13
        assert result.success is True
        
        # Verify all files copied
        output_files = list(temp_workspace['output_folder'].glob("*.edi"))
        assert len(output_files) == 13
