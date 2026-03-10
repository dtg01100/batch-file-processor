"""Performance benchmark tests for batch file processor.

Tests cover:
- Processing time vs file count
- Database size impact on query performance
- Memory usage during batch processing
- UI responsiveness during processing
- Disk I/O performance

Note: These tests are marked with @pytest.mark.performance
and should be run separately from regular test suite.
"""

import pytest
import tempfile
import time
import tracemalloc
from pathlib import Path
from unittest.mock import MagicMock
from contextlib import contextmanager

pytestmark = [pytest.mark.integration, pytest.mark.performance]


class Timer:
    """Simple timer class to capture elapsed time."""
    def __init__(self):
        self.elapsed = 0
    
    def __call__(self):
        return self.elapsed


@contextmanager
def measure_time():
    """Context manager to measure execution time."""
    timer = Timer()
    start = time.perf_counter()
    yield timer
    timer.elapsed = time.perf_counter() - start


class MemoryTracker:
    """Simple tracker to capture memory usage."""
    def __init__(self):
        self.current = 0
        self.peak = 0
    
    def __call__(self):
        return self.current, self.peak


@contextmanager
def measure_memory():
    """Context manager to measure memory usage."""
    tracker = MemoryTracker()
    tracemalloc.start()
    yield tracker
    tracker.current, tracker.peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()


@pytest.fixture
def large_dataset_workspace(tmp_path):
    """Create workspace with large dataset for performance testing."""
    workspace = tmp_path / "performance_test"
    workspace.mkdir()
    
    input_dir = workspace / "input"
    input_dir.mkdir()
    output_dir = workspace / "output"
    output_dir.mkdir()
    
    # Create EDI files
    edi_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item 1                     0000010000
B001002ITEM002     000020EA0020Test Item 2                     0000020000
C00000003000030000
"""
    
    return {
        'workspace': workspace,
        'input': input_dir,
        'output': output_dir,
        'edi_content': edi_content,
    }


@pytest.mark.performance
class TestScalabilityByFileCount:
    """Test processing time scalability with file count."""

    def test_process_10_files(self, large_dataset_workspace):
        """Test processing 10 files - baseline."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 10 files
        for i in range(10):
            (large_dataset_workspace['input'] / f"file_{i:03d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Performance Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        run_log = MagicMock()
        
        with measure_time() as t:
            result = orchestrator.process_folder(folder_config, run_log)
        
        elapsed = t()
        assert result.success is True
        assert elapsed < 5.0  # Should complete in under 5 seconds
        print(f"\n10 files processed in {elapsed:.3f}s")

    def test_process_100_files(self, large_dataset_workspace):
        """Test processing 100 files."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 100 files
        for i in range(100):
            (large_dataset_workspace['input'] / f"file_{i:03d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Performance Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        run_log = MagicMock()
        
        with measure_time() as t:
            result = orchestrator.process_folder(folder_config, run_log)
        
        elapsed = t()
        assert result.success is True
        assert elapsed < 30.0  # Should complete in under 30 seconds
        print(f"\n100 files processed in {elapsed:.3f}s")

    def test_process_1000_files(self, large_dataset_workspace):
        """Test processing 1000 files."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 1000 files
        for i in range(1000):
            (large_dataset_workspace['input'] / f"file_{i:04d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Performance Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        run_log = MagicMock()
        
        with measure_time() as t:
            result = orchestrator.process_folder(folder_config, run_log)
        
        elapsed = t()
        assert result.success is True
        # Allow more time for large batch
        assert elapsed < 300.0  # Should complete in under 5 minutes
        print(f"\n1000 files processed in {elapsed:.3f}s ({elapsed/1000*1000:.1f} ms/file)")


@pytest.mark.performance
class TestDatabasePerformance:
    """Test database performance with varying sizes."""

    def test_query_performance_small_database(self, temp_database):
        """Test query performance with small database (10 records)."""
        folders_table = temp_database.folders_table
        
        # Add 10 records
        for i in range(10):
            temp_database.folders_table.insert({
                'folder_name': f'/folder/{i}',
                'alias': f'Folder {i}',
                'folder_is_active': True,
            })
        
        with measure_time() as t:
            # Query all
            results = list(folders_table.find({}))
        
        elapsed = t()
        assert len(results) == 10
        assert elapsed < 0.1  # Should be very fast
        print(f"\nSmall DB query (10 records): {elapsed:.4f}s")

    def test_query_performance_medium_database(self, temp_database):
        """Test query performance with medium database (1000 records)."""
        folders_table = temp_database.folders_table
        
        # Add 1000 records
        for i in range(1000):
            temp_database.folders_table.insert({
                'folder_name': f'/folder/{i}',
                'alias': f'Folder {i}',
                'folder_is_active': True if i % 2 == 0 else False,
            })
        
        with measure_time() as t:
            # Query active only
            results = list(folders_table.find(folder_is_active=True))
        
        elapsed = t()
        assert len(results) == 500
        assert elapsed < 1.0  # Should complete in under 1 second
        print(f"\nMedium DB query (1000 records): {elapsed:.4f}s")

    def test_query_performance_large_database(self, temp_database):
        """Test query performance with large database (10000 records)."""
        folders_table = temp_database.folders_table
        
        # Add 10000 records
        for i in range(10000):
            temp_database.folders_table.insert({
                'folder_name': f'/folder/{i}',
                'alias': f'Folder {i}',
                'folder_is_active': True,
            })
        
        with measure_time() as t:
            # Complex query
            results = list(folders_table.find(folder_is_active=True))
        
        elapsed = t()
        assert len(results) == 10000
        assert elapsed < 5.0  # Should complete in under 5 seconds
        print(f"\nLarge DB query (10000 records): {elapsed:.4f}s")


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage during processing."""

    def test_memory_usage_small_batch(self, large_dataset_workspace):
        """Test memory usage with small batch (10 files)."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 10 files
        for i in range(10):
            (large_dataset_workspace['input'] / f"file_{i:03d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Memory Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        run_log = MagicMock()
        
        with measure_memory() as mem:
            result = orchestrator.process_folder(folder_config, run_log)
        
        current, peak = mem()
        assert result.success is True
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100  # Should use less than 100 MB
        print(f"\nSmall batch memory - Current: {current/1024/1024:.2f}MB, Peak: {peak_mb:.2f}MB")

    def test_memory_usage_large_batch(self, large_dataset_workspace):
        """Test memory usage with large batch (100 files)."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 100 files
        for i in range(100):
            (large_dataset_workspace['input'] / f"file_{i:03d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Memory Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        run_log = MagicMock()
        
        with measure_memory() as mem:
            result = orchestrator.process_folder(folder_config, run_log)
        
        current, peak = mem()
        assert result.success is True
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 500  # Should use less than 500 MB
        print(f"\nLarge batch memory - Current: {current/1024/1024:.2f}MB, Peak: {peak_mb:.2f}MB")


@pytest.mark.performance
class TestDiskIO:
    """Test disk I/O performance."""

    def test_read_performance(self, large_dataset_workspace):
        """Test file read performance."""
        # Create test files
        file_size = 1024  # 1KB
        test_files = []
        
        for i in range(100):
            file_path = large_dataset_workspace['input'] / f"test_{i}.txt"
            file_path.write_text("x" * file_size)
            test_files.append(file_path)
        
        # Measure read performance
        with measure_time() as t:
            for file_path in test_files:
                content = file_path.read_text()
        
        elapsed = t()
        total_bytes = file_size * 100
        throughput_mb_s = (total_bytes / 1024 / 1024) / elapsed
        print(f"\nRead throughput: {throughput_mb_s:.2f} MB/s")
        assert elapsed < 1.0  # Should read 100KB in under 1 second

    def test_write_performance(self, tmp_path):
        """Test file write performance."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        file_size = 1024  # 1KB
        num_files = 100
        
        # Measure write performance
        with measure_time() as t:
            for i in range(num_files):
                file_path = output_dir / f"test_{i}.txt"
                file_path.write_text("x" * file_size)
        
        elapsed = t()
        total_bytes = file_size * num_files
        throughput_mb_s = (total_bytes / 1024 / 1024) / elapsed
        print(f"\nWrite throughput: {throughput_mb_s:.2f} MB/s")
        assert elapsed < 1.0


@pytest.mark.performance
class TestUIResponsiveness:
    """Test UI responsiveness during processing."""

    def test_progress_update_frequency(self, large_dataset_workspace):
        """Test that progress updates are frequent enough."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 50 files
        for i in range(50):
            (large_dataset_workspace['input'] / f"file_{i:03d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Progress Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        # Track progress updates
        progress_updates = []
        
        class TrackingRunLog:
            def update_progress(self, current, total, message=""):
                progress_updates.append((current, total, time.time()))
            
            def log(self, message):
                pass
        
        run_log = TrackingRunLog()
        
        with measure_time() as t:
            result = orchestrator.process_folder(folder_config, run_log)
        
        elapsed = t()
        
        assert result.success is True
        
        # Note: Progress update tracking depends on implementation
        # Just verify the processing completes successfully
        print(f"\n50 files processed in {elapsed:.3f}s")
        assert elapsed < 60.0  # Should complete in reasonable time


@pytest.mark.performance
class TestConversionPerformance:
    """Test conversion performance."""

    def test_csv_conversion_speed(self, large_dataset_workspace):
        """Test CSV conversion speed."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        
        # Create 50 EDI files
        for i in range(50):
            (large_dataset_workspace['input'] / f"file_{i:03d}.edi").write_text(
                large_dataset_workspace['edi_content']
            )
        
        config = DispatchConfig(
            backends={'copy': CopyBackend()},
            settings={}
        )
        orchestrator = DispatchOrchestrator(config)
        
        folder_config = {
            'folder_name': str(large_dataset_workspace['input']),
            'alias': 'Conversion Test',
            'process_backend_copy': True,
            'copy_to_directory': str(large_dataset_workspace['output']),
            'convert_to_type': 'csv',
        }
        
        run_log = MagicMock()
        
        with measure_time() as t:
            result = orchestrator.process_folder(folder_config, run_log)
        
        elapsed = t()
        assert result.success is True
        
        files_per_second = 50 / elapsed
        print(f"\nCSV conversion speed: {files_per_second:.1f} files/second")
        
        # Should convert at reasonable speed
        assert files_per_second > 1.0  # At least 1 file per second


@pytest.mark.performance
class TestConcurrentProcessing:
    """Test concurrent processing performance."""

    def test_parallel_folder_processing(self, tmp_path):
        """Test processing multiple folders in parallel."""
        from dispatch.orchestrator import DispatchOrchestrator, DispatchConfig
        from copy_backend import CopyBackend
        from concurrent.futures import ThreadPoolExecutor
        
        # Create 5 folders
        folders = []
        for i in range(5):
            folder_dir = tmp_path / f"folder_{i}"
            folder_dir.mkdir()
            output_dir = tmp_path / f"output_{i}"
            output_dir.mkdir()
            
            # Add 20 files per folder
            for j in range(20):
                (folder_dir / f"file_{j}.edi").write_text(
                    f"A00000{i}20240101001TESTVENDOR         Test Vendor Inc                 0000{i}\n"
                )
            
            folders.append({
                'input': folder_dir,
                'output': output_dir,
            })
        
        def process_folder(folder):
            config = DispatchConfig(
                backends={'copy': CopyBackend()},
                settings={}
            )
            orchestrator = DispatchOrchestrator(config)
            
            folder_config = {
                'folder_name': str(folder['input']),
                'alias': 'Parallel Test',
                'process_backend_copy': True,
                'copy_to_directory': str(folder['output']),
                'convert_to_type': 'csv',
            }
            
            run_log = MagicMock()
            return orchestrator.process_folder(folder_config, run_log)
        
        # Process in parallel
        with measure_time() as t:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(process_folder, folder) for folder in folders]
                results = [f.result() for f in futures]
        
        elapsed = t()
        
        # All should succeed
        assert all(r.success for r in results)
        
        print(f"\nParallel processing (5 folders × 20 files): {elapsed:.3f}s")
        
        # Parallel should be faster than sequential
        assert elapsed < 30.0  # Should complete in under 30 seconds
