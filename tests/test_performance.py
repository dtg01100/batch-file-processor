import time
import pytest
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.benchmark
class TestStartupPerformance:
    """Benchmark tests for application startup."""

    def test_import_time_interface_main(self):
        """Benchmark import time for interface.main."""
        # Force reload if already imported to measure actual import cost
        if "interface.main" in sys.modules:
            del sys.modules["interface.main"]

        start_time = time.perf_counter()
        import interface.main

        end_time = time.perf_counter()

        duration = end_time - start_time
        print(f"\nImport interface.main: {duration:.4f}s")
        # Assert it's reasonably fast (e.g. < 2s) - mainly to catch massive regressions
        assert duration < 2.0

    def test_import_time_dispatch(self):
        """Benchmark import time for dispatch module."""
        if "dispatch" in sys.modules:
            del sys.modules["dispatch"]

        start_time = time.perf_counter()
        import legacy_dispatch as dispatch

        end_time = time.perf_counter()

        duration = end_time - start_time
        print(f"\nImport dispatch: {duration:.4f}s")
        assert duration < 1.0

    def test_import_time_qt_modules(self):
        """Benchmark import time for PyQt6 modules."""
        # Note: We can't easily unload C extensions like PyQt, so this mostly measures
        # the python side overhead if already loaded, or full load if not.

        start_time = time.perf_counter()
        from PyQt6.QtWidgets import QApplication
        from interface.ui.app import Application

        end_time = time.perf_counter()

        duration = end_time - start_time
        print(f"\nImport PyQt6 modules: {duration:.4f}s")
        assert duration < 2.0

    def test_cli_help_execution_time(self):
        """Benchmark execution time of --help command."""
        cmd = [sys.executable, str(project_root / "interface" / "main.py"), "--help"]

        start_time = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True)
        end_time = time.perf_counter()

        duration = end_time - start_time
        print(f"\nCLI --help execution: {duration:.4f}s")

        assert result.returncode == 0
        assert duration < 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
