"""
Comprehensive unit tests for the dispatch coordinator module.

These tests cover the DispatchCoordinator class, ProcessingContext,
and all related functionality with extensive mocking of external dependencies.
"""

import os
import sys
import queue
import threading
import tempfile
import datetime
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, mock_open, call

import pytest

# Import the module under test
from dispatch.coordinator import (
    DispatchCoordinator,
    ProcessingContext,
    process,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_database_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    conn.query = MagicMock()
    return conn


@pytest.fixture
def mock_folders_database():
    """Create a mock folders database."""
    db = MagicMock()
    db.find = MagicMock(return_value=[])
    db.count = MagicMock(return_value=0)
    return db


@pytest.fixture
def mock_processed_files():
    """Create a mock processed files database."""
    db = MagicMock()
    db.find = MagicMock(return_value=[])
    db.count = MagicMock(return_value=0)
    db.insert_many = MagicMock()
    db.find_one = MagicMock(return_value=None)
    db.update = MagicMock()
    return db


@pytest.fixture
def mock_run_log():
    """Create a mock run log."""
    log = MagicMock()
    log.write = MagicMock()
    log.writelines = MagicMock()
    return log


@pytest.fixture
def mock_emails_table():
    """Create a mock emails table."""
    table = MagicMock()
    table.insert = MagicMock()
    return table


@pytest.fixture
def mock_root():
    """Create a mock root UI element."""
    root = MagicMock()
    root.update = MagicMock()
    return root


@pytest.fixture
def mock_args():
    """Create mock command line arguments."""
    args = MagicMock()
    args.automatic = True
    return args


@pytest.fixture
def mock_settings():
    """Create mock application settings."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "test_host",
        "odbc_driver": "test_driver",
    }


@pytest.fixture
def mock_errors_folder(temp_dir):
    """Create mock errors folder configuration."""
    return {"errors_folder": os.path.join(temp_dir, "errors")}


@pytest.fixture
def sample_folder_config():
    """Provide sample folder configuration."""
    return {
        "id": 1,
        "old_id": 1,
        "alias": "Test Folder",
        "folder_name": "/test/folder",
        "process_edi": "False",
        "tweak_edi": False,
        "split_edi": False,
        "force_edi_validation": False,
        "split_edi_include_credits": 1,
        "split_edi_include_invoices": 1,
        "convert_to_format": "CSV",
        "rename_file": "",
        "process_backend_copy": False,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "copy_to_directory": "",
        "ftp_server": "",
        "ftp_folder": "",
        "email_to": "",
    }


@pytest.fixture
def sample_folder_config_with_edi():
    """Provide sample folder configuration with EDI processing enabled."""
    return {
        "id": 1,
        "old_id": 1,
        "alias": "Test Folder EDI",
        "folder_name": "/test/folder",
        "process_edi": "True",
        "tweak_edi": True,
        "split_edi": True,
        "force_edi_validation": True,
        "split_edi_include_credits": 1,
        "split_edi_include_invoices": 1,
        "convert_to_format": "CSV",
        "rename_file": "output_%datetime%",
        "process_backend_copy": True,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "copy_to_directory": "/output",
        "ftp_server": "",
        "ftp_folder": "",
        "email_to": "",
    }


@pytest.fixture
def coordinator(
    mock_database_connection,
    mock_folders_database,
    mock_run_log,
    mock_emails_table,
    temp_dir,
    mock_root,
    mock_args,
    mock_settings,
    mock_errors_folder,
    mock_processed_files,
):
    """Create a DispatchCoordinator instance with mocked dependencies."""
    reporting = {"enable_reporting": "False"}

    with patch("dispatch.coordinator.DBManager") as mock_db_manager, \
         patch("dispatch.coordinator.ErrorHandler") as mock_error_handler, \
         patch("dispatch.coordinator.SendManager") as mock_send_manager, \
         patch("dispatch.coordinator.EDIValidator") as mock_edi_validator:

        mock_db_manager_instance = MagicMock()
        mock_db_manager.return_value = mock_db_manager_instance
        mock_db_manager_instance.get_active_folders.return_value = []
        mock_db_manager_instance.get_active_folder_count.return_value = 0
        mock_db_manager_instance.get_processed_files.return_value = []

        coordinator = DispatchCoordinator(
            database_connection=mock_database_connection,
            folders_database=mock_folders_database,
            run_log=mock_run_log,
            emails_table=mock_emails_table,
            run_log_directory=temp_dir,
            reporting=reporting,
            processed_files=mock_processed_files,
            root=mock_root,
            args=mock_args,
            version="1.0.0",
            errors_folder=mock_errors_folder,
            settings=mock_settings,
            simple_output=None,
        )
        return coordinator


# =============================================================================
# ProcessingContext Tests
# =============================================================================

class TestProcessingContext:
    """Tests for the ProcessingContext class."""

    def test_initialization(self):
        """Test ProcessingContext initializes with correct default values."""
        context = ProcessingContext()

        assert context.hash_counter == 0
        assert context.file_count == 0
        assert context.parameters_dict_list == []
        assert isinstance(context.hash_thread_return_queue, queue.Queue)
        assert isinstance(context.edi_validator_errors, StringIO)
        assert context.global_edi_validator_error_status is False
        assert context.upc_dict == {}

    def test_reset(self):
        """Test ProcessingContext reset clears counters and queues."""
        context = ProcessingContext()

        # Modify values
        context.hash_counter = 10
        context.file_count = 5
        context.global_edi_validator_error_status = True
        context.upc_dict = {"key": "value"}
        context.hash_thread_return_queue.put("test")
        context.edi_validator_errors.write("error")

        # Reset
        context.reset()

        assert context.hash_counter == 0
        assert context.file_count == 0
        assert isinstance(context.hash_thread_return_queue, queue.Queue)
        assert isinstance(context.edi_validator_errors, StringIO)
        assert context.global_edi_validator_error_status is False

    def test_reset_preserves_upc_dict(self):
        """Test that reset does not clear upc_dict."""
        context = ProcessingContext()
        context.upc_dict = {"test": "value"}

        context.reset()

        # upc_dict should be preserved after reset
        assert context.upc_dict == {"test": "value"}


# =============================================================================
# DispatchCoordinator Initialization Tests
# =============================================================================

class TestDispatchCoordinatorInitialization:
    """Tests for DispatchCoordinator initialization."""

    def test_init_with_defaults(self, coordinator):
        """Test DispatchCoordinator initializes with correct default values."""
        assert coordinator.database_connection is not None
        assert coordinator.folders_database is not None
        assert coordinator.run_log is not None
        assert coordinator.emails_table is not None
        assert coordinator.run_log_directory is not None
        assert coordinator.reporting is not None
        assert coordinator.processed_files is not None
        assert coordinator.root is not None
        assert coordinator.args is not None
        assert coordinator.version == "1.0.0"
        assert coordinator.errors_folder is not None
        assert coordinator.settings is not None
        assert coordinator.simple_output is None

    def test_init_creates_context(self, coordinator):
        """Test DispatchCoordinator creates ProcessingContext."""
        assert isinstance(coordinator.context, ProcessingContext)

    def test_init_creates_components(self, coordinator):
        """Test DispatchCoordinator initializes internal components."""
        assert coordinator.db_manager is not None
        assert coordinator.error_handler is not None
        assert coordinator.send_manager is not None
        assert coordinator.edi_validator is not None

    def test_init_creates_overlay_updater(self, coordinator):
        """Test DispatchCoordinator creates overlay update function."""
        assert callable(coordinator.update_overlay)

    def test_init_with_simple_output(
        self,
        mock_database_connection,
        mock_folders_database,
        mock_run_log,
        mock_emails_table,
        temp_dir,
        mock_root,
        mock_args,
        mock_settings,
        mock_errors_folder,
        mock_processed_files,
    ):
        """Test DispatchCoordinator initializes with simple_output."""
        reporting = {"enable_reporting": "False"}
        simple_output = MagicMock()

        with patch("dispatch.coordinator.DBManager"), \
             patch("dispatch.coordinator.ErrorHandler"), \
             patch("dispatch.coordinator.SendManager"), \
             patch("dispatch.coordinator.EDIValidator"):

            coordinator = DispatchCoordinator(
                database_connection=mock_database_connection,
                folders_database=mock_folders_database,
                run_log=mock_run_log,
                emails_table=mock_emails_table,
                run_log_directory=temp_dir,
                reporting=reporting,
                processed_files=mock_processed_files,
                root=mock_root,
                args=mock_args,
                version="1.0.0",
                errors_folder=mock_errors_folder,
                settings=mock_settings,
                simple_output=simple_output,
            )

            assert coordinator.simple_output is simple_output


# =============================================================================
# DispatchCoordinator Overlay Update Tests
# =============================================================================

class TestDispatchCoordinatorOverlayUpdate:
    """Tests for the overlay update functionality."""

    def test_update_overlay_automatic_mode(self, coordinator, mock_root):
        """Test overlay update in automatic mode."""
        coordinator.args.automatic = True

        coordinator.update_overlay("Processing", 1, 5, 2, 10, "Footer text")

        mock_root.update.assert_called_once()

    def test_update_overlay_manual_mode(self, coordinator, mock_root):
        """Test overlay update in manual mode calls doingstuffoverlay."""
        coordinator.args.automatic = False

        with patch("dispatch.coordinator.doingstuffoverlay") as mock_overlay:
            coordinator.update_overlay("Processing", 1, 5, 2, 10, "Footer text")

            mock_overlay.update_overlay.assert_called_once()
            call_args = mock_overlay.update_overlay.call_args
            assert call_args.kwargs["parent"] == mock_root
            assert "Processing" in call_args.kwargs["overlay_text"]
            assert call_args.kwargs["footer"] == "Footer text"

    def test_update_overlay_with_simple_output(self, coordinator, mock_root):
        """Test overlay update with simple_output configured."""
        coordinator.args.automatic = True
        simple_output = MagicMock()
        coordinator.simple_output = simple_output

        coordinator.update_overlay("Processing", 1, 5, 2, 10, "Footer text")

        simple_output.configure.assert_called_once()
        mock_root.update.assert_called_once()


# =============================================================================
# DispatchCoordinator Load UPC Data Tests
# =============================================================================

class TestDispatchCoordinatorLoadUpcData:
    """Tests for _load_upc_data method."""

    def test_load_upc_data_success(self, coordinator, mock_settings):
        """Test successful UPC data loading."""
        mock_query_result = [
            ("12345", "CAT1", "UPC1", "UPC2", "UPC3", "UPC4"),
            ("67890", "CAT2", "UPC5", "UPC6", "UPC7", "UPC8"),
        ]

        with patch("dispatch.coordinator.query_runner") as mock_query_runner:
            mock_query_instance = MagicMock()
            mock_query_runner.return_value = mock_query_instance
            mock_query_instance.run_arbitrary_query.return_value = mock_query_result

            coordinator._load_upc_data()

            assert coordinator.context.upc_dict == {
                12345: ["CAT1", "UPC1", "UPC2", "UPC3", "UPC4"],
                67890: ["CAT2", "UPC5", "UPC6", "UPC7", "UPC8"],
            }

    def test_load_upc_data_empty_result(self, coordinator):
        """Test UPC data loading with empty result."""
        with patch("dispatch.coordinator.query_runner") as mock_query_runner:
            mock_query_instance = MagicMock()
            mock_query_runner.return_value = mock_query_instance
            mock_query_instance.run_arbitrary_query.return_value = []

            coordinator._load_upc_data()

            assert coordinator.context.upc_dict == {}


# =============================================================================
# DispatchCoordinator Create Hash Thread Tests
# =============================================================================

class TestDispatchCoordinatorCreateHashThread:
    """Tests for _create_hash_thread method."""

    def test_create_hash_thread_returns_thread(self, coordinator):
        """Test _create_hash_thread returns a Thread object."""
        temp_processed_files = []
        coordinator.context.parameters_dict_list = []

        thread = coordinator._create_hash_thread(temp_processed_files)

        assert isinstance(thread, threading.Thread)

    def test_hash_thread_target_with_old_id(self, coordinator):
        """Test hash thread handles old_id in parameters."""
        coordinator.context.parameters_dict_list = [
            {"folder_name": "/test/folder1", "old_id": 1},
        ]

        temp_processed_files = []

        with patch("dispatch.coordinator.FileDiscoverer") as mock_discoverer, \
             patch("dispatch.coordinator.HashGenerator") as mock_hash_gen, \
             patch("dispatch.coordinator.FileFilter") as mock_file_filter:

            mock_discoverer.discover_files.return_value = ["/test/folder1/file1.txt"]
            mock_hash_gen.generate_file_hash.return_value = "hash123"
            mock_file_filter.generate_match_lists.return_value = ([], [], set())
            mock_file_filter.should_send_file.return_value = True

            thread = coordinator._create_hash_thread(temp_processed_files)

            # Run the thread target directly
            with patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor") as mock_executor:
                mock_executor_instance = MagicMock()
                mock_executor.return_value.__enter__.return_value = mock_executor_instance
                mock_executor_instance.map.return_value = ["hash123"]

                thread._target()

            # Verify queue has result
            result = coordinator.context.hash_thread_return_queue.get(timeout=1)
            assert result["folder_name"] == "/test/folder1"

    def test_hash_thread_target_with_id_fallback(self, coordinator):
        """Test hash thread falls back to id when old_id not present."""
        coordinator.context.parameters_dict_list = [
            {"folder_name": "/test/folder1", "id": 2},
        ]

        temp_processed_files = [
            {"folder_id": 2, "file_name": "file1.txt", "file_checksum": "hash1", "resend_flag": False}
        ]

        with patch("dispatch.coordinator.FileDiscoverer") as mock_discoverer, \
             patch("dispatch.coordinator.HashGenerator") as mock_hash_gen, \
             patch("dispatch.coordinator.FileFilter") as mock_file_filter:

            mock_discoverer.discover_files.return_value = ["/test/folder1/file1.txt"]
            mock_hash_gen.generate_file_hash.return_value = "hash1"
            mock_file_filter.generate_match_lists.return_value = (
                [("file1.txt", "hash1")],
                [("hash1", "file1.txt")],
                set()
            )
            mock_file_filter.should_send_file.return_value = True

            thread = coordinator._create_hash_thread(temp_processed_files)

            with patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor") as mock_executor:
                mock_executor_instance = MagicMock()
                mock_executor.return_value.__enter__.return_value = mock_executor_instance
                mock_executor_instance.map.return_value = ["hash1"]

                thread._target()

            result = coordinator.context.hash_thread_return_queue.get(timeout=1)
            assert result["folder_name"] == "/test/folder1"


# =============================================================================
# DispatchCoordinator Process Tests
# =============================================================================

class TestDispatchCoordinatorProcess:
    """Tests for the main process() method."""

    def test_process_no_folders(self, coordinator):
        """Test process with no active folders."""
        with patch.object(coordinator.db_manager, "get_active_folders", return_value=[]), \
             patch.object(coordinator.db_manager, "get_active_folder_count", return_value=0), \
             patch.object(coordinator.db_manager, "get_processed_files", return_value=[]), \
             patch.object(coordinator, "_load_upc_data") as mock_load_upc, \
             patch.object(coordinator, "_create_hash_thread") as mock_create_thread:

            mock_thread = MagicMock()
            mock_create_thread.return_value = mock_thread

            has_errors, run_summary = coordinator.process()

            assert has_errors is False
            assert "0 processed, 0 errors" in run_summary
            mock_load_upc.assert_called_once()
            mock_thread.start.assert_called_once()

    def test_process_with_missing_folder(self, coordinator, mock_run_log):
        """Test process handles missing folder."""
        folders = [
            {"folder_name": "/nonexistent/folder", "alias": "Missing", "id": 1}
        ]

        with patch.object(coordinator.db_manager, "get_active_folders", return_value=folders), \
             patch.object(coordinator.db_manager, "get_active_folder_count", return_value=1), \
             patch.object(coordinator.db_manager, "get_processed_files", return_value=[]), \
             patch.object(coordinator, "_load_upc_data"), \
             patch.object(coordinator, "_create_hash_thread") as mock_create_thread, \
             patch("dispatch.coordinator.os.path.isdir", return_value=False):

            mock_thread = MagicMock()
            mock_create_thread.return_value = mock_thread

            has_errors, run_summary = coordinator.process()

            assert has_errors is True
            assert "0 processed, 1 errors" in run_summary
            mock_run_log.write.assert_called()

    def test_process_folder_mismatch_raises_error(self, coordinator):
        """Test process raises error when folder names don't match."""
        folders = [
            {"folder_name": "/test/folder1", "alias": "Test1", "id": 1}
        ]

        with patch.object(coordinator.db_manager, "get_active_folders", return_value=folders), \
             patch.object(coordinator.db_manager, "get_active_folder_count", return_value=1), \
             patch.object(coordinator.db_manager, "get_processed_files", return_value=[]), \
             patch.object(coordinator, "_load_upc_data"), \
             patch.object(coordinator, "_create_hash_thread") as mock_create_thread, \
             patch("dispatch.coordinator.os.path.isdir", return_value=True):

            mock_thread = MagicMock()
            mock_create_thread.return_value = mock_thread

            # Put mismatched folder name in queue
            coordinator.context.hash_thread_return_queue.put({
                "folder_name": "/different/folder",
                "files": [],
                "filtered_files": [],
            })

            with pytest.raises(ValueError) as exc_info:
                coordinator.process()

            assert "desync between current folder" in str(exc_info.value)

    def test_process_with_edi_validation_errors(self, coordinator):
        """Test process handles EDI validation errors."""
        folders = [
            {"folder_name": "/test/folder1", "alias": "Test1", "id": 1}
        ]

        coordinator.context.global_edi_validator_error_status = True
        coordinator.context.edi_validator_errors.write("Some EDI errors")

        with patch.object(coordinator.db_manager, "get_active_folders", return_value=folders), \
             patch.object(coordinator.db_manager, "get_active_folder_count", return_value=1), \
             patch.object(coordinator.db_manager, "get_processed_files", return_value=[]), \
             patch.object(coordinator, "_load_upc_data"), \
             patch.object(coordinator, "_create_hash_thread") as mock_create_thread, \
             patch.object(coordinator, "_process_folder", return_value=False), \
             patch("dispatch.coordinator.os.path.isdir", return_value=True), \
             patch.object(coordinator, "_write_validation_report", return_value="/path/to/report.txt"):

            mock_thread = MagicMock()
            mock_create_thread.return_value = mock_thread

            coordinator.context.hash_thread_return_queue.put({
                "folder_name": "/test/folder1",
                "files": [],
                "filtered_files": [],
            })

            has_errors, run_summary = coordinator.process()

            assert "has EDI validator errors" in run_summary

    def test_process_successful_folder_processing(self, coordinator):
        """Test process with successful folder processing."""
        folders = [
            {"folder_name": "/test/folder1", "alias": "Test1", "id": 1}
        ]

        with patch.object(coordinator.db_manager, "get_active_folders", return_value=folders), \
             patch.object(coordinator.db_manager, "get_active_folder_count", return_value=1), \
             patch.object(coordinator.db_manager, "get_processed_files", return_value=[]), \
             patch.object(coordinator, "_load_upc_data"), \
             patch.object(coordinator, "_create_hash_thread") as mock_create_thread, \
             patch.object(coordinator, "_process_folder", return_value=False), \
             patch("dispatch.coordinator.os.path.isdir", return_value=True):

            mock_thread = MagicMock()
            mock_create_thread.return_value = mock_thread

            coordinator.context.hash_thread_return_queue.put({
                "folder_name": "/test/folder1",
                "files": ["/test/folder1/file1.txt"],
                "filtered_files": [(0, "file1.txt", "hash123")],
            })

            has_errors, run_summary = coordinator.process()

            assert has_errors is False
            assert "1 processed, 0 errors" in run_summary


# =============================================================================
# DispatchCoordinator Process Folder Tests
# =============================================================================

class TestDispatchCoordinatorProcessFolder:
    """Tests for _process_folder method."""

    def test_process_folder_no_files(self, coordinator, mock_run_log):
        """Test _process_folder with no files."""
        parameters_dict = {"folder_name": "/test/folder", "id": 1}
        files = []
        filtered_files = []

        result = coordinator._process_folder(parameters_dict, files, filtered_files, 1, 1)

        assert result is False
        mock_run_log.write.assert_any_call("Checking for new files\r\n".encode())
        mock_run_log.write.assert_any_call("No files in directory\r\n\r\n".encode())

    def test_process_folder_no_new_files(self, coordinator, mock_run_log):
        """Test _process_folder with files but no new ones to process."""
        parameters_dict = {"folder_name": "/test/folder", "id": 1}
        files = ["/test/folder/file1.txt"]
        filtered_files = []

        result = coordinator._process_folder(parameters_dict, files, filtered_files, 1, 1)

        assert result is False
        mock_run_log.write.assert_any_call("No new files in directory\r\n\r\n".encode())

    def test_process_folder_with_files(self, coordinator, mock_run_log):
        """Test _process_folder processes files successfully."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "id": 1,
            "alias": "Test",
        }
        files = ["/test/folder/file1.txt"]
        filtered_files = [(0, "file1.txt", "hash123")]

        with patch.object(coordinator, "_process_single_file") as mock_process_single:
            mock_process_single.return_value = (
                False,  # errors
                "/test/folder/file1.txt",  # original_filename
                "hash123",  # file_checksum
                ["log entry"],  # return_log
                [],  # return_error_log
            )

            with patch.object(coordinator.db_manager, "insert_processed_files") as mock_insert, \
                 patch.object(coordinator.db_manager.tracker, "mark_as_processed") as mock_mark, \
                 patch.object(coordinator.db_manager.tracker, "is_resend", return_value=False), \
                 patch.object(coordinator.db_manager, "cleanup_old_records"), \
                 patch.object(coordinator.db_manager, "update_folder_records"):

                mock_mark.return_value = {"file_name": "file1.txt", "folder_id": 1}

                with patch("dispatch.coordinator.concurrent.futures.ThreadPoolExecutor") as mock_executor:
                    mock_executor_instance = MagicMock()
                    mock_executor.return_value.__enter__.return_value = mock_executor_instance
                    mock_executor_instance.map.return_value = [
                        (False, "/test/folder/file1.txt", "hash123", ["log entry"], [])
                    ]

                    result = coordinator._process_folder(parameters_dict, files, filtered_files, 1, 1)

        assert result is False

    def test_process_folder_with_errors(self, coordinator):
        """Test _process_folder handles file processing errors."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "id": 1,
            "alias": "Test",
        }
        files = ["/test/folder/file1.txt"]
        filtered_files = [(0, "file1.txt", "hash123")]

        with patch("dispatch.coordinator.concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_executor_instance = MagicMock()
            mock_executor.return_value.__enter__.return_value = mock_executor_instance
            mock_executor_instance.map.return_value = [
                (True, "/test/folder/file1.txt", "hash123", ["log entry"], ["error entry"])
            ]

            with patch.object(coordinator, "_write_folder_errors_report"):
                result = coordinator._process_folder(parameters_dict, files, filtered_files, 1, 1)

        assert result is True

    def test_process_folder_with_reporting_enabled(self, coordinator):
        """Test _process_folder with reporting enabled."""
        coordinator.reporting["enable_reporting"] = "True"
        parameters_dict = {
            "folder_name": "/test/folder",
            "id": 1,
            "alias": "Test",
        }
        files = ["/test/folder/file1.txt"]
        filtered_files = [(0, "file1.txt", "hash123")]

        with patch("dispatch.coordinator.concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_executor_instance = MagicMock()
            mock_executor.return_value.__enter__.return_value = mock_executor_instance
            mock_executor_instance.map.return_value = [
                (True, "/test/folder/file1.txt", "hash123", ["log entry"], ["error entry"])
            ]

            with patch.object(coordinator, "_write_folder_errors_report"):
                result = coordinator._process_folder(parameters_dict, files, filtered_files, 1, 1)

                assert coordinator.emails_table.insert.called


# =============================================================================
# DispatchCoordinator Process Single File Tests
# =============================================================================

class TestDispatchCoordinatorProcessSingleFile:
    """Tests for _process_single_file method."""

    def test_process_single_file_success(self, coordinator):
        """Test _process_single_file with successful processing."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "process_edi": "False",
            "tweak_edi": False,
            "split_edi": False,
            "force_edi_validation": False,
        }
        filtered_files = [(0, "file1.txt", "hash123")]
        folder_errors_log = StringIO()

        with patch.object(coordinator, "_process_edi") as mock_process_edi, \
             patch.object(coordinator, "_send_file", return_value=False) as mock_send_file:

            mock_process_edi.return_value = [("/test/folder/file1.txt", "", "")]

            result = coordinator._process_single_file(0, parameters_dict, filtered_files, folder_errors_log)

            errors, original_filename, file_checksum, process_log, error_log = result

            assert errors is False
            assert original_filename == "/test/folder/file1.txt"
            assert file_checksum == "hash123"

    def test_process_single_file_with_edi_validation(self, coordinator):
        """Test _process_single_file with EDI validation."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "process_edi": "True",
            "tweak_edi": False,
            "split_edi": False,
            "force_edi_validation": True,
        }
        filtered_files = [(0, "file1.edi", "hash123")]
        folder_errors_log = StringIO()

        mock_validation_result = MagicMock()
        mock_validation_result.has_errors = False
        mock_validation_result.has_minor_errors = False
        mock_validation_result.error_message = ""

        with patch.object(coordinator.edi_validator, "validate_file", return_value=mock_validation_result), \
             patch.object(coordinator, "_process_edi") as mock_process_edi, \
             patch.object(coordinator, "_send_file", return_value=False):

            mock_process_edi.return_value = [("/test/folder/file1.edi", "", "")]

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = os.path.join(tmpdir, "file1.edi")
                with open(test_file, "w") as f:
                    f.write("EDI content")

                # Update parameters to use temp file
                parameters_dict["folder_name"] = tmpdir

                result = coordinator._process_single_file(0, parameters_dict, [(0, "file1.edi", "hash123")], folder_errors_log)

            errors, _, _, _, _ = result
            assert errors is False

    def test_process_single_file_edi_validation_with_minor_errors(self, coordinator):
        """Test _process_single_file captures minor EDI validation errors."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "process_edi": "False",
            "tweak_edi": False,
            "split_edi": False,
            "force_edi_validation": True,
        }
        filtered_files = [(0, "file1.edi", "hash123")]
        folder_errors_log = StringIO()

        mock_validation_result = MagicMock()
        mock_validation_result.has_errors = False
        mock_validation_result.has_minor_errors = True
        mock_validation_result.error_message = "Minor EDI issues"

        with patch.object(coordinator.edi_validator, "validate_file", return_value=mock_validation_result), \
             patch.object(coordinator, "_process_edi") as mock_process_edi, \
             patch.object(coordinator, "_send_file", return_value=False):

            mock_process_edi.return_value = [("/test/folder/file1.edi", "", "")]

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = os.path.join(tmpdir, "file1.edi")
                with open(test_file, "w") as f:
                    f.write("EDI content")

                parameters_dict["folder_name"] = tmpdir

                result = coordinator._process_single_file(0, parameters_dict, [(0, "file1.edi", "hash123")], folder_errors_log)

            assert coordinator.context.global_edi_validator_error_status is True

    def test_process_single_file_with_send_error(self, coordinator):
        """Test _process_single_file handles send errors."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "process_edi": "False",
            "tweak_edi": False,
            "split_edi": False,
            "force_edi_validation": False,
        }
        filtered_files = [(0, "file1.txt", "hash123")]
        folder_errors_log = StringIO()

        with patch.object(coordinator, "_process_edi") as mock_process_edi, \
             patch.object(coordinator, "_send_file", return_value=True) as mock_send_file:

            mock_process_edi.return_value = [("/test/folder/file1.txt", "", "")]

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = os.path.join(tmpdir, "file1.txt")
                with open(test_file, "w") as f:
                    f.write("content")

                parameters_dict["folder_name"] = tmpdir

                result = coordinator._process_single_file(0, parameters_dict, [(0, "file1.txt", "hash123")], folder_errors_log)

            errors, _, _, _, _ = result
            assert errors is True


# =============================================================================
# DispatchCoordinator Process EDI Tests
# =============================================================================

class TestDispatchCoordinatorProcessEdi:
    """Tests for _process_edi method."""

    def test_process_edi_no_split(self, coordinator):
        """Test _process_edi without splitting."""
        parameters_dict = {"split_edi": False}
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            result = coordinator._process_edi(
                "/test/file.edi",
                parameters_dict,
                True,
                scratch_folder,
                process_files_log,
                process_files_error_log
            )

        assert result == [("/test/file.edi", "", "")]

    def test_process_edi_with_split(self, coordinator):
        """Test _process_edi with splitting enabled."""
        parameters_dict = {"split_edi": True}
        process_files_log = []
        process_files_error_log = []

        with patch("dispatch.coordinator.EDISplitter") as mock_splitter:
            mock_splitter.split_edi.return_value = [
                ("/scratch/file1.edi", "", "_1"),
                ("/scratch/file2.edi", "", "_2"),
            ]

            with tempfile.TemporaryDirectory() as scratch_folder:
                result = coordinator._process_edi(
                    "/test/file.edi",
                    parameters_dict,
                    True,
                    scratch_folder,
                    process_files_log,
                    process_files_error_log
                )

            assert len(result) == 2
            assert "Splitting edi file" in process_files_log[0]

    def test_process_edi_split_failure(self, coordinator):
        """Test _process_edi handles split failure."""
        parameters_dict = {"split_edi": True}
        process_files_log = []
        process_files_error_log = []

        with patch("dispatch.coordinator.EDISplitter") as mock_splitter:
            mock_splitter.split_edi.side_effect = Exception("Split error")

            with tempfile.TemporaryDirectory() as scratch_folder:
                result = coordinator._process_edi(
                    "/test/file.edi",
                    parameters_dict,
                    True,
                    scratch_folder,
                    process_files_log,
                    process_files_error_log
                )

            # Should fall back to original file
            assert result == [("/test/file.edi", "", "")]

    def test_process_edi_single_result_with_split(self, coordinator):
        """Test _process_edi reports when split produces only one file."""
        parameters_dict = {"split_edi": True}
        process_files_log = []
        process_files_error_log = []

        with patch("dispatch.coordinator.EDISplitter") as mock_splitter:
            mock_splitter.split_edi.return_value = [("/scratch/file.edi", "", "")]

            with tempfile.TemporaryDirectory() as scratch_folder:
                result = coordinator._process_edi(
                    "/test/file.edi",
                    parameters_dict,
                    True,
                    scratch_folder,
                    process_files_log,
                    process_files_error_log
                )

            assert "Cannot split edi file" in process_files_log


# =============================================================================
# DispatchCoordinator Send File Tests
# =============================================================================

class TestDispatchCoordinatorSendFile:
    """Tests for _send_file method."""

    def test_send_file_success(self, coordinator):
        """Test _send_file with successful send."""
        parameters_dict = {
            "process_edi": "True",
            "tweak_edi": False,
            "convert_to_format": "CSV",
            "process_backend_copy": False,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "rename_file": "",
        }
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            test_file = os.path.join(scratch_folder, "test.edi")
            with open(test_file, "w") as f:
                f.write("EDI content")

            with patch("dispatch.coordinator.EDIConverter") as mock_converter, \
                 patch.object(coordinator.send_manager, "send_file") as mock_send:

                mock_converter.convert_edi.return_value = test_file
                mock_send.return_value = [MagicMock(success=True)]

                result = coordinator._send_file(
                    test_file,
                    parameters_dict,
                    "",
                    "",
                    process_files_log,
                    process_files_error_log,
                    test_file,
                    True,
                    scratch_folder,
                )

            assert result is False

    def test_send_file_with_backend_error(self, coordinator):
        """Test _send_file handles backend errors."""
        parameters_dict = {
            "process_edi": "False",
            "tweak_edi": False,
            "process_backend_copy": True,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "copy_to_directory": "/output",
            "rename_file": "",
        }
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            test_file = os.path.join(scratch_folder, "test.txt")
            with open(test_file, "w") as f:
                f.write("content")

            with patch.object(coordinator.send_manager, "send_file") as mock_send:
                mock_result = MagicMock()
                mock_result.success = False
                mock_result.error_message = "Backend error"
                mock_result.backend_name = "Copy Backend"
                mock_send.return_value = [mock_result]

                result = coordinator._send_file(
                    test_file,
                    parameters_dict,
                    "",
                    "",
                    process_files_log,
                    process_files_error_log,
                    test_file,
                    True,
                    scratch_folder,
                )

            assert result is True

    def test_send_file_with_conversion_error(self, coordinator):
        """Test _send_file handles conversion errors."""
        parameters_dict = {
            "process_edi": "True",
            "tweak_edi": False,
            "convert_to_format": "CSV",
            "process_backend_copy": False,
            "rename_file": "",
        }
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            test_file = os.path.join(scratch_folder, "test.edi")
            with open(test_file, "w") as f:
                f.write("EDI content")

            with patch("dispatch.coordinator.EDIConverter") as mock_converter:
                mock_converter.convert_edi.side_effect = Exception("Conversion failed")

                result = coordinator._send_file(
                    test_file,
                    parameters_dict,
                    "",
                    "",
                    process_files_log,
                    process_files_error_log,
                    test_file,
                    True,
                    scratch_folder,
                )

            assert result is True

    def test_send_file_skip_credit_invoice_split(self, coordinator):
        """Test _send_file skips files based on split settings."""
        parameters_dict = {
            "process_edi": "False",
            "tweak_edi": False,
            "split_edi": True,
            "split_edi_include_credits": 0,
            "split_edi_include_invoices": 1,
            "process_backend_copy": False,
            "rename_file": "",
        }
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            test_file = os.path.join(scratch_folder, "test.edi")
            with open(test_file, "w") as f:
                f.write("EDI content")

            with patch("dispatch.coordinator.utils.detect_invoice_is_credit", return_value=True), \
                 patch.object(coordinator.send_manager, "send_file") as mock_send:

                mock_send.return_value = []

                result = coordinator._send_file(
                    test_file,
                    parameters_dict,
                    "",
                    "_credit",
                    process_files_log,
                    process_files_error_log,
                    test_file,
                    True,
                    scratch_folder,
                )

            # Should skip credit file
            assert mock_send.call_count == 0


# =============================================================================
# DispatchCoordinator Write Reports Tests
# =============================================================================

class TestDispatchCoordinatorWriteReports:
    """Tests for report writing methods."""

    def test_write_validation_report(self, coordinator, temp_dir):
        """Test _write_validation_report creates report file."""
        coordinator.context.edi_validator_errors.write("Validation errors")

        with patch("dispatch.coordinator.datetime") as mock_datetime:
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = coordinator._write_validation_report()

            assert os.path.exists(result)
            with open(result, "r") as f:
                content = f.read()
                assert "Validation errors" in content

    def test_write_folder_errors_report(self, coordinator, temp_dir):
        """Test _write_folder_errors_report creates error report."""
        parameters_dict = {
            "alias": "Test Folder",
            "folder_name": "/test/folder",
        }

        with patch("dispatch.coordinator.datetime") as mock_datetime:
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = coordinator._write_folder_errors_report(parameters_dict, "Error details")

            assert os.path.exists(result)
            with open(result, "r") as f:
                content = f.read()
                assert "Program Version = 1.0.0" in content
                assert "Error details" in content

    def test_write_folder_errors_report_creates_directories(self, coordinator, temp_dir):
        """Test _write_folder_errors_report creates necessary directories."""
        parameters_dict = {
            "alias": "Test Folder",
            "folder_name": "/test/folder",
        }

        errors_subdir = os.path.join(temp_dir, "errors_subdir")
        coordinator.errors_folder["errors_folder"] = errors_subdir

        with patch("dispatch.coordinator.datetime") as mock_datetime:
            mock_datetime.datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = coordinator._write_folder_errors_report(parameters_dict, "Error details")

            assert os.path.exists(errors_subdir)


# =============================================================================
# Backward Compatibility Process Function Tests
# =============================================================================

class TestBackwardCompatibilityProcess:
    """Tests for the backward-compatible process function."""

    def test_process_creates_coordinator_and_runs(self):
        """Test that process() creates DispatchCoordinator and calls process()."""
        mock_database_connection = MagicMock()
        mock_folders_database = MagicMock()
        mock_run_log = MagicMock()
        mock_emails_table = MagicMock()
        mock_processed_files = MagicMock()
        mock_root = MagicMock()
        mock_args = MagicMock()
        mock_settings = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            errors_folder = {"errors_folder": os.path.join(temp_dir, "errors")}
            reporting = {"enable_reporting": "False"}

            with patch("dispatch.coordinator.DispatchCoordinator") as mock_coordinator_class:
                mock_coordinator = MagicMock()
                mock_coordinator_class.return_value = mock_coordinator
                mock_coordinator.process.return_value = (False, "0 processed, 0 errors")

                result = process(
                    mock_database_connection,
                    mock_folders_database,
                    mock_run_log,
                    mock_emails_table,
                    temp_dir,
                    reporting,
                    mock_processed_files,
                    mock_root,
                    mock_args,
                    "1.0.0",
                    errors_folder,
                    mock_settings,
                    None,
                )

                mock_coordinator_class.assert_called_once()
                mock_coordinator.process.assert_called_once()
                assert result == (False, "0 processed, 0 errors")


# =============================================================================
# Integration and Edge Case Tests
# =============================================================================

class TestDispatchCoordinatorEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_process_single_file_file_not_found(self, coordinator):
        """Test _process_single_file handles missing file gracefully."""
        parameters_dict = {
            "folder_name": "/nonexistent",
            "process_edi": "False",
            "tweak_edi": False,
            "split_edi": False,
            "force_edi_validation": False,
        }
        filtered_files = [(0, "missing.txt", "hash123")]
        folder_errors_log = StringIO()

        # Should handle gracefully even if file doesn't exist
        with patch.object(coordinator, "_process_edi") as mock_process_edi:
            mock_process_edi.return_value = [("/nonexistent/missing.txt", "", "")]

            result = coordinator._process_single_file(0, parameters_dict, filtered_files, folder_errors_log)

            # Should complete without crashing
            assert result is not None

    def test_context_queue_operations(self, coordinator):
        """Test ProcessingContext queue operations."""
        # Test putting and getting from queue
        coordinator.context.hash_thread_return_queue.put({"test": "data"})
        result = coordinator.context.hash_thread_return_queue.get(timeout=1)
        assert result == {"test": "data"}

    def test_context_queue_empty(self, coordinator):
        """Test ProcessingContext queue empty behavior."""
        assert coordinator.context.hash_thread_return_queue.empty() is True
        coordinator.context.hash_thread_return_queue.put("item")
        assert coordinator.context.hash_thread_return_queue.empty() is False

    def test_edi_validator_errors_accumulation(self, coordinator):
        """Test EDI validator errors accumulate in context."""
        coordinator.context.edi_validator_errors.write("Error 1\n")
        coordinator.context.edi_validator_errors.write("Error 2\n")

        errors = coordinator.context.edi_validator_errors.getvalue()
        assert "Error 1" in errors
        assert "Error 2" in errors


# =============================================================================
# Thread Safety Tests
# =============================================================================

class TestDispatchCoordinatorThreadSafety:
    """Tests for thread safety and concurrent operations."""

    def test_hash_thread_concurrent_access(self, coordinator):
        """Test hash thread handles concurrent access properly."""
        coordinator.context.parameters_dict_list = [
            {"folder_name": f"/test/folder{i}", "old_id": i}
            for i in range(3)
        ]

        temp_processed_files = []

        with patch("dispatch.coordinator.FileDiscoverer") as mock_discoverer, \
             patch("dispatch.coordinator.HashGenerator") as mock_hash_gen, \
             patch("dispatch.coordinator.FileFilter") as mock_file_filter:

            mock_discoverer.discover_files.side_effect = [
                [f"/test/folder{i}/file.txt"]
                for i in range(3)
            ]
            mock_hash_gen.generate_file_hash.return_value = "hash"
            mock_file_filter.generate_match_lists.return_value = ([], [], set())
            mock_file_filter.should_send_file.return_value = True

            thread = coordinator._create_hash_thread(temp_processed_files)

            with patch("dispatch.coordinator.concurrent.futures.ProcessPoolExecutor") as mock_executor:
                mock_executor_instance = MagicMock()
                mock_executor.return_value.__enter__.return_value = mock_executor_instance
                mock_executor_instance.map.side_effect = [
                    ["hash"] for _ in range(3)
                ]

                thread._target()

            # Should have 3 results in queue
            results = []
            while not coordinator.context.hash_thread_return_queue.empty():
                results.append(coordinator.context.hash_thread_return_queue.get())

            assert len(results) == 3


# =============================================================================
# File Naming and Path Handling Tests
# =============================================================================

class TestDispatchCoordinatorFileNaming:
    """Tests for file naming and path handling."""

    def test_process_edi_renaming(self, coordinator):
        """Test EDI processing with file renaming."""
        parameters_dict = {
            "split_edi": False,
            "rename_file": "output_%datetime%",
        }
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            result = coordinator._process_edi(
                "/test/file.edi",
                parameters_dict,
                True,
                scratch_folder,
                process_files_log,
                process_files_error_log
            )

        # File naming happens in _send_file, not _process_edi
        assert result == [("/test/file.edi", "", "")]


# =============================================================================
# Configuration Variations Tests
# =============================================================================

class TestDispatchCoordinatorConfigurationVariations:
    """Tests for different configuration combinations."""

    def test_process_single_file_all_edi_options_enabled(self, coordinator):
        """Test _process_single_file with all EDI options enabled."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "process_edi": "True",
            "tweak_edi": True,
            "split_edi": True,
            "force_edi_validation": True,
            "split_edi_include_credits": 1,
            "split_edi_include_invoices": 1,
            "convert_to_format": "CSV",
            "rename_file": "output",
            "process_backend_copy": True,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "copy_to_directory": "/output",
        }
        filtered_files = [(0, "file.edi", "hash123")]
        folder_errors_log = StringIO()

        mock_validation_result = MagicMock()
        mock_validation_result.has_errors = False
        mock_validation_result.has_minor_errors = False

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "file.edi")
            with open(test_file, "w") as f:
                f.write("EDI content")

            parameters_dict["folder_name"] = tmpdir

            with patch.object(coordinator.edi_validator, "validate_file", return_value=mock_validation_result), \
                 patch.object(coordinator, "_process_edi") as mock_process_edi, \
                 patch.object(coordinator, "_send_file", return_value=False):

                mock_process_edi.return_value = [
                    (os.path.join(tmpdir, "split1.edi"), "", "_1"),
                    (os.path.join(tmpdir, "split2.edi"), "", "_2"),
                ]

                result = coordinator._process_single_file(0, parameters_dict, [(0, "file.edi", "hash123")], folder_errors_log)

            errors, _, _, _, _ = result
            assert errors is False

    def test_process_single_file_no_backends_enabled(self, coordinator):
        """Test _process_single_file with no backends enabled."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "process_edi": "False",
            "tweak_edi": False,
            "split_edi": False,
            "force_edi_validation": False,
            "process_backend_copy": False,
            "process_backend_ftp": False,
            "process_backend_email": False,
            "rename_file": "",
        }
        filtered_files = [(0, "file.txt", "hash123")]
        folder_errors_log = StringIO()

        with patch.object(coordinator, "_process_edi") as mock_process_edi, \
             patch.object(coordinator, "_send_file", return_value=False):

            mock_process_edi.return_value = [("/test/folder/file.txt", "", "")]

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = os.path.join(tmpdir, "file.txt")
                with open(test_file, "w") as f:
                    f.write("content")

                parameters_dict["folder_name"] = tmpdir

                result = coordinator._process_single_file(0, parameters_dict, [(0, "file.txt", "hash123")], folder_errors_log)

            errors, _, _, _, _ = result
            assert errors is False


# =============================================================================
# Error Recovery Tests
# =============================================================================

class TestDispatchCoordinatorErrorRecovery:
    """Tests for error recovery and resilience."""

    def test_process_folder_partial_failure(self, coordinator):
        """Test _process_folder handles partial file processing failures."""
        parameters_dict = {
            "folder_name": "/test/folder",
            "id": 1,
            "alias": "Test",
        }
        files = ["/test/folder/file1.txt", "/test/folder/file2.txt"]
        filtered_files = [
            (0, "file1.txt", "hash1"),
            (1, "file2.txt", "hash2"),
        ]

        with patch("dispatch.coordinator.concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_executor_instance = MagicMock()
            mock_executor.return_value.__enter__.return_value = mock_executor_instance
            # First file succeeds, second fails
            mock_executor_instance.map.return_value = [
                (False, "/test/folder/file1.txt", "hash1", ["log1"], []),
                (True, "/test/folder/file2.txt", "hash2", ["log2"], ["error"]),
            ]

            with patch.object(coordinator, "_write_folder_errors_report"):
                result = coordinator._process_folder(parameters_dict, files, filtered_files, 1, 1)

        assert result is True

    def test_send_file_handles_missing_file(self, coordinator):
        """Test _send_file handles missing file gracefully."""
        parameters_dict = {
            "process_edi": "False",
            "tweak_edi": False,
            "process_backend_copy": False,
            "rename_file": "",
        }
        process_files_log = []
        process_files_error_log = []

        with tempfile.TemporaryDirectory() as scratch_folder:
            missing_file = "/nonexistent/file.txt"

            result = coordinator._send_file(
                missing_file,
                parameters_dict,
                "",
                "",
                process_files_log,
                process_files_error_log,
                missing_file,
                True,
                scratch_folder,
            )

            # Should complete without crashing even if file doesn't exist
            assert result is False  # No backends configured, so no errors


# =============================================================================
# Complex Workflow Tests
# =============================================================================

class TestDispatchCoordinatorComplexWorkflows:
    """Tests for complex multi-step workflows."""

    def test_full_workflow_simulation(self, coordinator, temp_dir):
        """Test a complete workflow simulation with all components."""
        # Setup folders
        folders = [
            {
                "folder_name": temp_dir,
                "alias": "Test Workflow",
                "id": 1,
                "old_id": 1,
                "process_edi": "True",
                "tweak_edi": True,
                "split_edi": False,
                "force_edi_validation": False,
                "split_edi_include_credits": 1,
                "split_edi_include_invoices": 1,
                "convert_to_format": "CSV",
                "rename_file": "output",
                "process_backend_copy": True,
                "process_backend_ftp": False,
                "process_backend_email": False,
                "copy_to_directory": os.path.join(temp_dir, "output"),
            }
        ]

        # Create test file
        test_file = os.path.join(temp_dir, "test.edi")
        with open(test_file, "w") as f:
            f.write("UNA:+.? 'UNB+UNOC:3+SENDER+RECEIVER+210101:1200+1'")

        os.makedirs(os.path.join(temp_dir, "output"), exist_ok=True)

        with patch.object(coordinator.db_manager, "get_active_folders", return_value=folders), \
             patch.object(coordinator.db_manager, "get_active_folder_count", return_value=1), \
             patch.object(coordinator.db_manager, "get_processed_files", return_value=[]), \
             patch.object(coordinator, "_load_upc_data"), \
             patch.object(coordinator, "_create_hash_thread") as mock_create_thread, \
             patch("dispatch.coordinator.os.path.isdir", return_value=True):

            mock_thread = MagicMock()
            mock_create_thread.return_value = mock_thread

            # Setup queue with hash results
            coordinator.context.hash_thread_return_queue.put({
                "folder_name": temp_dir,
                "files": [test_file],
                "filtered_files": [(0, "test.edi", "hash123")],
            })

            # Mock EDI validation
            mock_validation_result = MagicMock()
            mock_validation_result.has_errors = False
            mock_validation_result.has_minor_errors = False

            with patch.object(coordinator.edi_validator, "validate_file", return_value=mock_validation_result), \
                 patch("dispatch.coordinator.EDIConverter") as mock_converter, \
                 patch("dispatch.coordinator.EDITweaker") as mock_tweaker, \
                 patch.object(coordinator.send_manager, "send_file") as mock_send, \
                 patch.object(coordinator.db_manager.tracker, "mark_as_processed") as mock_mark, \
                 patch.object(coordinator.db_manager.tracker, "is_resend", return_value=False):

                mock_converter.convert_edi.return_value = test_file
                mock_tweaker.tweak_edi.return_value = test_file
                mock_send.return_value = [MagicMock(success=True)]
                mock_mark.return_value = {"file_name": "test.edi", "folder_id": 1}

                with patch("dispatch.coordinator.concurrent.futures.ThreadPoolExecutor") as mock_executor:
                    mock_executor_instance = MagicMock()
                    mock_executor.return_value.__enter__.return_value = mock_executor_instance
                    mock_executor_instance.map.return_value = [
                        (False, test_file, "hash123", ["log entry"], [])
                    ]

                    has_errors, run_summary = coordinator.process()

                assert has_errors is False
                assert "1 processed, 0 errors" in run_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
