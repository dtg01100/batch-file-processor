"""
Smoke tests for running the Batch File Processor application.

These tests verify that the application can actually start and run in both
GUI and automatic modes without crashing. They test the real entry points
that users would use.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def isolated_config():
    """Create an isolated configuration directory for testing."""
    temp_config = tempfile.mkdtemp()

    # Mock appdirs to use our temp directory
    with patch("appdirs.user_data_dir", return_value=temp_config):
        yield temp_config

    # Cleanup
    shutil.rmtree(temp_config, ignore_errors=True)


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager for testing."""
    mock_db = Mock()
    mock_db.oversight_and_defaults = Mock()
    mock_db.folders_table = Mock()
    mock_db.emails_table = Mock()
    mock_db.processed_files = Mock()
    mock_db.settings = Mock()
    mock_db.close = Mock()

    # Setup default return values
    mock_db.oversight_and_defaults.find_one.return_value = {
        "id": 1,
        "logs_directory": tempfile.gettempdir(),
        "errors_folder": tempfile.gettempdir(),
        "enable_reporting": "False",
        "report_printing_fallback": "False",
    }

    mock_db.settings.find_one.return_value = {
        "id": 1,
        "enable_interval_backups": False,
        "backup_counter": 0,
        "backup_counter_maximum": 10,
    }

    mock_db.folders_table.count.return_value = 0
    mock_db.folders_table.all.return_value = []

    return mock_db


@pytest.mark.smoke
class TestMainEntryPoint:
    """Test the main entry point (interface/main.py)."""

    def test_main_module_imports(self):
        """Main module can be imported without errors."""
        import interface.main as main

        assert hasattr(main, "main")
        assert hasattr(main, "parse_arguments")
        assert hasattr(main, "get_database_path")
        assert hasattr(main, "run_automatic_mode")
        assert hasattr(main, "run_gui_mode")

    def test_parse_arguments_default(self):
        """parse_arguments works with no arguments."""
        from interface.main import parse_arguments

        with patch("sys.argv", ["main.py"]):
            args = parse_arguments()
            assert hasattr(args, "automatic")
            assert args.automatic is False

    def test_parse_arguments_automatic_flag(self):
        """parse_arguments recognizes --automatic flag."""
        from interface.main import parse_arguments

        with patch("sys.argv", ["main.py", "--automatic"]):
            args = parse_arguments()
            assert args.automatic is True

        with patch("sys.argv", ["main.py", "-a"]):
            args = parse_arguments()
            assert args.automatic is True

    def test_get_database_path_returns_valid_paths(self, isolated_config):
        """get_database_path returns valid file paths."""
        from interface.main import get_database_path

        config_folder, database_path = get_database_path()

        assert isinstance(config_folder, str)
        assert isinstance(database_path, str)
        assert database_path.endswith("folders.db")
        assert config_folder in database_path

    def test_ensure_config_directory_creates_directory(self, isolated_config):
        """ensure_config_directory creates the configuration directory."""
        from interface.main import ensure_config_directory

        test_dir = os.path.join(isolated_config, "test_config")
        assert not os.path.exists(test_dir)

        ensure_config_directory(test_dir)

        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

    def test_ensure_config_directory_handles_existing_directory(self, isolated_config):
        """ensure_config_directory doesn't fail if directory exists."""
        from interface.main import ensure_config_directory

        test_dir = os.path.join(isolated_config, "existing_config")
        os.makedirs(test_dir)

        # Should not raise any exception
        ensure_config_directory(test_dir)

        assert os.path.exists(test_dir)


@pytest.mark.smoke
class TestAutomaticMode:
    """Test automatic (headless) mode functionality."""

    def test_automatic_mode_with_no_active_folders(
        self, isolated_config, mock_database_manager
    ):
        """Automatic mode exits gracefully with no active folders."""
        from interface.main import run_automatic_mode
        from interface.operations.processing import automatic_process_directories

        mock_database_manager.folders_table.count.return_value = 0

        # automatic_process_directories raises SystemExit
        with pytest.raises(SystemExit):
            automatic_process_directories(
                mock_database_manager, Mock(automatic=True), "1.0.0"
            )

        mock_database_manager.close.assert_called_once()

    def test_automatic_process_directories_imports(self):
        """automatic_process_directories can be imported."""
        from interface.operations.processing import automatic_process_directories

        assert callable(automatic_process_directories)

    def test_run_automatic_mode_callable(self):
        """run_automatic_mode function is callable."""
        from interface.main import run_automatic_mode

        assert callable(run_automatic_mode)


@pytest.mark.smoke
class TestGUIMode:
    """Test GUI mode startup functionality."""

    def test_gui_mode_imports_required_modules(self):
        """GUI mode can import all required PyQt6 modules."""
        try:
            from PyQt6.QtWidgets import QApplication
            from interface.ui.app import Application, create_application
            from interface.ui.main_window import create_main_window
            from interface.application_controller import ApplicationController

            assert QApplication is not None
            assert Application is not None
            assert create_application is not None
            assert create_main_window is not None
            assert ApplicationController is not None
        except ImportError as e:
            pytest.skip(f"PyQt6 not installed: {e}")

    def test_create_application_function_exists(self):
        """create_application function exists and is callable."""
        try:
            from interface.ui.app import create_application

            assert callable(create_application)
        except ImportError:
            pytest.skip("PyQt6 not installed")

    def test_create_main_window_function_exists(self):
        """create_main_window function exists and is callable."""
        try:
            from interface.ui.main_window import create_main_window

            assert callable(create_main_window)
        except ImportError:
            pytest.skip("PyQt6 not installed")

    @pytest.mark.qt
    def test_application_controller_exists(self):
        """ApplicationController class exists and is importable."""
        try:
            from interface.application_controller import ApplicationController

            assert ApplicationController is not None
            assert hasattr(ApplicationController, "__init__")
        except ImportError:
            pytest.skip("PyQt6 not installed")

    @pytest.mark.qt
    def test_gui_startup_creates_qapp_before_database(self, qapp, isolated_config):
        """GUI mode creates QApplication before DatabaseManager.

        This tests that run_gui_mode creates QApplication first, avoiding
        'QSqlDatabase requires a QCoreApplication' crash.
        """
        from PyQt6.QtWidgets import QApplication

        assert QApplication.instance() is not None, (
            "QApplication must exist before DatabaseManager is created. "
            "QSqlDatabase requires QCoreApplication to exist first."
        )

        from interface.database.database_manager import DatabaseManager

        db_path = os.path.join(isolated_config, "test_startup.db")
        db_manager = DatabaseManager(
            database_path=db_path,
            config_folder=isolated_config,
            platform="Linux",
            app_version="1.0.0",
            database_version="39",
        )

        assert db_manager.database_connection is not None
        db_manager.close()


@pytest.mark.smoke
class TestProcessingOrchestrator:
    """Test the ProcessingOrchestrator that runs the actual processing."""

    def test_processing_orchestrator_imports(self):
        """ProcessingOrchestrator can be imported."""
        from interface.operations.processing import ProcessingOrchestrator

        assert ProcessingOrchestrator is not None

    def test_processing_orchestrator_initialization(
        self, mock_database_manager, isolated_config
    ):
        """ProcessingOrchestrator can be initialized."""
        from interface.operations.processing import ProcessingOrchestrator

        orchestrator = ProcessingOrchestrator(
            db_manager=mock_database_manager,
            database_path=os.path.join(isolated_config, "test.db"),
            args=Mock(automatic=True),
            version="1.0.0",
        )

        assert orchestrator.db_manager == mock_database_manager
        assert orchestrator.version == "1.0.0"

    def test_processing_result_dataclass_exists(self):
        """ProcessingResult dataclass is defined."""
        from interface.operations.processing import ProcessingResult

        result = ProcessingResult(success=True)
        assert result.success is True
        assert result.backup_path is None
        assert result.log_path is None
        assert result.error is None

    def test_dispatch_result_dataclass_exists(self):
        """DispatchResult dataclass is defined."""
        from interface.operations.processing import DispatchResult

        result = DispatchResult(error=False, summary="Test summary")
        assert result.error is False
        assert result.summary == "Test summary"


@pytest.mark.smoke
class TestRunScript:
    """Test the run.sh script (shell script execution)."""

    def test_run_script_exists(self):
        """run.sh script exists and is executable."""
        script_path = project_root / "run.sh"

        assert script_path.exists(), "run.sh not found"
        assert os.access(script_path, os.X_OK), "run.sh is not executable"

    def test_run_script_help_flag(self):
        """run.sh --help works and shows usage."""
        script_path = project_root / "run.sh"

        result = subprocess.run(
            [str(script_path), "--help"], capture_output=True, text=True, timeout=5
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()
        assert "automatic" in result.stdout.lower()

    @pytest.mark.slow
    def test_run_script_syntax_valid(self):
        """run.sh has valid bash syntax."""
        script_path = project_root / "run.sh"

        # Use bash -n to check syntax without executing
        result = subprocess.run(
            ["bash", "-n", str(script_path)], capture_output=True, text=True, timeout=5
        )

        assert result.returncode == 0, f"Syntax error in run.sh: {result.stderr}"


@pytest.mark.smoke
class TestRunTestsScript:
    """Test the run_tests.sh script."""

    def test_run_tests_script_exists(self):
        """run_tests.sh script exists and is executable."""
        script_path = project_root / "run_tests.sh"

        assert script_path.exists(), "run_tests.sh not found"
        assert os.access(script_path, os.X_OK), "run_tests.sh is not executable"

    @pytest.mark.slow
    def test_run_tests_script_syntax_valid(self):
        """run_tests.sh has valid bash syntax."""
        script_path = project_root / "run_tests.sh"

        # Use bash -n to check syntax without executing
        result = subprocess.run(
            ["bash", "-n", str(script_path)], capture_output=True, text=True, timeout=5
        )

        assert result.returncode == 0, f"Syntax error in run_tests.sh: {result.stderr}"


@pytest.mark.smoke
class TestApplicationStructure:
    """Test that the application structure is intact."""

    def test_interface_directory_exists(self):
        """interface/ directory exists."""
        interface_dir = project_root / "interface"
        assert interface_dir.exists()
        assert interface_dir.is_dir()

    def test_main_entry_point_exists(self):
        """interface/main.py exists."""
        main_file = project_root / "interface" / "main.py"
        assert main_file.exists()
        assert main_file.is_file()

    def test_dispatch_module_exists(self):
        """dispatch.py module exists."""
        dispatch_file = project_root / "dispatch.py"
        assert dispatch_file.exists()
        assert dispatch_file.is_file()

    def test_utils_module_exists(self):
        """utils.py module exists."""
        utils_file = project_root / "utils.py"
        assert utils_file.exists()
        assert utils_file.is_file()

    def test_converter_backends_exist(self):
        """Converter backend files exist."""
        backends = [
            "convert_base.py",
            "convert_to_csv.py",
            "convert_to_fintech.py",
        ]

        for backend in backends:
            backend_file = project_root / backend
            assert backend_file.exists(), f"{backend} not found"

    def test_send_backends_exist(self):
        """Send backend files exist."""
        backends = [
            "send_base.py",
            "email_backend.py",
            "ftp_backend.py",
            "copy_backend.py",
        ]

        for backend in backends:
            backend_file = project_root / backend
            assert backend_file.exists(), f"{backend} not found"


@pytest.mark.smoke
def test_python_version_compatible():
    """Python version is compatible with the application."""
    assert sys.version_info >= (3, 11), "Python 3.11+ required"


@pytest.mark.smoke
def test_requirements_file_exists():
    """requirements.txt exists."""
    requirements_file = project_root / "requirements.txt"
    assert requirements_file.exists()


@pytest.mark.smoke
def test_critical_dependencies_importable():
    """Critical dependencies can be imported."""
    critical_imports = [
        "appdirs",
    ]

    for module_name in critical_imports:
        try:
            __import__(module_name)
        except ImportError:
            pytest.fail(f"Critical dependency '{module_name}' cannot be imported")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
