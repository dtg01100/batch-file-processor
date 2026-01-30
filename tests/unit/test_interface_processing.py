"""
Comprehensive unit tests for the interface operations processing module.

These tests cover the ProcessingOrchestrator and automatic_process_directories
with extensive mocking of external dependencies.
"""

import datetime
import os
import sys
import tempfile
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, mock_open, call

import pytest

# Import the module under test
from interface.operations.processing import (
    ProcessingOrchestrator,
    ProcessingResult,
    DispatchResult,
    automatic_process_directories,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db = MagicMock()
    db.settings = MagicMock()
    db.oversight_and_defaults = MagicMock()
    db.emails_table = MagicMock()
    db.emails_table_batch = MagicMock()
    db.sent_emails_removal_queue = MagicMock()
    db.processed_files = MagicMock()
    db.folders_table = MagicMock()
    db.database_connection = MagicMock()
    db.close = MagicMock()
    
    # Default return values
    db.settings.find_one.return_value = {
        "id": 1,
        "enable_interval_backups": True,
        "backup_counter": 5,
        "backup_counter_maximum": 10,
    }
    db.oversight_and_defaults.find_one.return_value = {
        "id": 1,
        "logs_directory": "/test/logs",
        "errors_folder": "/test/errors",
        "enable_reporting": "True",
        "report_printing_fallback": "False",
    }
    db.emails_table.count.return_value = 0
    db.emails_table.all.return_value = []
    db.emails_table_batch.count.return_value = 0
    
    return db


@pytest.fixture
def sample_args():
    """Provide sample command-line arguments."""
    args = MagicMock()
    args.automatic = False
    args.test = False
    return args


@pytest.fixture
def sample_dispatch_result():
    """Provide sample dispatch result."""
    return DispatchResult(error=False, summary="Processing completed successfully")


@pytest.fixture
def orchestrator(mock_db_manager, sample_args):
    """Create a ProcessingOrchestrator instance with mocked dependencies."""
    return ProcessingOrchestrator(
        db_manager=mock_db_manager,
        database_path="/test/database.sqlite",
        args=sample_args,
        version="1.0.0",
    )


# =============================================================================
# ProcessingResult and DispatchResult Tests
# =============================================================================

class TestDataClasses:
    """Tests for ProcessingResult and DispatchResult dataclasses."""

    def test_processing_result_defaults(self):
        """Test ProcessingResult with default values."""
        result = ProcessingResult(success=True)
        
        assert result.success is True
        assert result.backup_path is None
        assert result.log_path is None
        assert result.error is None

    def test_processing_result_full(self):
        """Test ProcessingResult with all values."""
        result = ProcessingResult(
            success=True,
            backup_path="/backup/db.sqlite",
            log_path="/logs/run.txt",
            error=None,
        )
        
        assert result.success is True
        assert result.backup_path == "/backup/db.sqlite"
        assert result.log_path == "/logs/run.txt"
        assert result.error is None

    def test_dispatch_result_creation(self):
        """Test DispatchResult creation."""
        result = DispatchResult(error=True, summary="Error occurred")
        
        assert result.error is True
        assert result.summary == "Error occurred"


# =============================================================================
# ProcessingOrchestrator Initialization Tests
# =============================================================================

class TestProcessingOrchestratorInitialization:
    """Tests for ProcessingOrchestrator initialization."""

    def test_initialization(self, mock_db_manager, sample_args):
        """Test ProcessingOrchestrator initializes correctly."""
        orchestrator = ProcessingOrchestrator(
            db_manager=mock_db_manager,
            database_path="/test/database.sqlite",
            args=sample_args,
            version="1.0.0",
        )
        
        assert orchestrator.db_manager is mock_db_manager
        assert orchestrator.database_path == "/test/database.sqlite"
        assert orchestrator.args is sample_args
        assert orchestrator.version == "1.0.0"
        assert orchestrator.errors_directory is None
        assert orchestrator.logs_directory is None

    def test_class_constants(self):
        """Test ProcessingOrchestrator class constants."""
        assert ProcessingOrchestrator.FALLBACK_ERROR_LOG == "C:\\Users\\Public\\batch_error_log.txt"
        assert ProcessingOrchestrator.MAX_EMAIL_BATCH_SIZE == 9000000
        assert ProcessingOrchestrator.MAX_EMAILS_PER_BATCH == 15


# =============================================================================
# process_all Tests
# =============================================================================

class TestProcessAll:
    """Tests for the process_all method."""

    @patch("interface.operations.processing.os.getcwd")
    @patch("interface.operations.processing.os.chdir")
    def test_process_all_success(
        self, mock_chdir, mock_getcwd, orchestrator, mock_db_manager
    ):
        """Test successful process_all execution."""
        mock_getcwd.return_value = "/original/dir"
        
        with patch.object(orchestrator, '_run_backup') as mock_backup, \
             patch.object(orchestrator, '_setup_logging') as mock_setup_log, \
             patch.object(orchestrator, '_run_dispatch') as mock_dispatch, \
             patch.object(orchestrator, '_send_email_report') as mock_send_email:
            
            mock_backup.return_value = None
            mock_setup_log.return_value = "/test/logs/run.txt"
            mock_dispatch.return_value = DispatchResult(error=False, summary="Success")
            
            result = orchestrator.process_all(auto_mode=False)
        
        assert result.success is True
        assert result.log_path == "/test/logs/run.txt"
        assert result.error is None
        mock_chdir.assert_called_with("/original/dir")

    @patch("interface.operations.processing.os.getcwd")
    @patch("interface.operations.processing.os.chdir")
    def test_process_all_with_backup(
        self, mock_chdir, mock_getcwd, orchestrator, mock_db_manager
    ):
        """Test process_all when backup is created."""
        mock_getcwd.return_value = "/original/dir"
        
        with patch.object(orchestrator, '_run_backup') as mock_backup, \
             patch.object(orchestrator, '_setup_logging') as mock_setup_log, \
             patch.object(orchestrator, '_run_dispatch') as mock_dispatch, \
             patch.object(orchestrator, '_send_email_report') as mock_send_email:
            
            mock_backup.return_value = "/backup/db_backup.sqlite"
            mock_setup_log.return_value = "/test/logs/run.txt"
            mock_dispatch.return_value = DispatchResult(error=False, summary="Success")
            
            result = orchestrator.process_all(auto_mode=False)
        
        assert result.backup_path == "/backup/db_backup.sqlite"

    @patch("interface.operations.processing.os.getcwd")
    @patch("interface.operations.processing.os.chdir")
    def test_process_all_logging_failure(
        self, mock_chdir, mock_getcwd, orchestrator, mock_db_manager
    ):
        """Test process_all when logging setup fails."""
        mock_getcwd.return_value = "/original/dir"
        
        with patch.object(orchestrator, '_run_backup') as mock_backup, \
             patch.object(orchestrator, '_setup_logging') as mock_setup_log:
            
            mock_backup.return_value = None
            mock_setup_log.return_value = None  # Logging failed
            
            result = orchestrator.process_all(auto_mode=False)
        
        assert result.success is False
        assert "Failed to setup logging directory" in result.error

    @patch("interface.operations.processing.os.getcwd")
    @patch("interface.operations.processing.os.chdir")
    def test_process_all_exception_handling(
        self, mock_chdir, mock_getcwd, orchestrator, mock_db_manager
    ):
        """Test process_all handles exceptions."""
        mock_getcwd.return_value = "/original/dir"
        
        with patch.object(orchestrator, '_run_backup') as mock_backup, \
             patch.object(orchestrator, '_setup_logging') as mock_setup_log, \
             patch.object(orchestrator, '_handle_error') as mock_handle_error:
            
            mock_backup.side_effect = Exception("Backup failed")
            
            result = orchestrator.process_all(auto_mode=False)
        
        assert result.success is False
        assert "Processing failed" in result.error
        assert "Backup failed" in result.error
        mock_handle_error.assert_called_once()


# =============================================================================
# _run_backup Tests
# =============================================================================

class TestRunBackup:
    """Tests for the _run_backup method."""

    @patch("interface.operations.processing.backup_increment.do_backup")
    def test_backup_triggered_when_counter_reaches_max(
        self, mock_do_backup, orchestrator, mock_db_manager
    ):
        """Test backup is triggered when counter reaches maximum."""
        mock_db_manager.settings.find_one.return_value = {
            "id": 1,
            "enable_interval_backups": True,
            "backup_counter": 10,
            "backup_counter_maximum": 10,
        }
        mock_do_backup.return_value = None
        
        result = orchestrator._run_backup()
        
        mock_do_backup.assert_called_once_with("/test/database.sqlite")
        # Counter should be reset to 0 and then incremented to 1
        mock_db_manager.settings.update.assert_called_once()
        update_call = mock_db_manager.settings.update.call_args[0]
        assert update_call[0]["backup_counter"] == 1

    @patch("interface.operations.processing.backup_increment.do_backup")
    def test_no_backup_when_counter_below_max(
        self, mock_do_backup, orchestrator, mock_db_manager
    ):
        """Test no backup when counter below maximum."""
        mock_db_manager.settings.find_one.return_value = {
            "id": 1,
            "enable_interval_backups": True,
            "backup_counter": 5,
            "backup_counter_maximum": 10,
        }
        
        result = orchestrator._run_backup()
        
        mock_do_backup.assert_not_called()
        mock_db_manager.settings.update.assert_called_once()

    @patch("interface.operations.processing.backup_increment.do_backup")
    def test_no_backup_when_disabled(
        self, mock_do_backup, orchestrator, mock_db_manager
    ):
        """Test no backup when interval backups disabled."""
        mock_db_manager.settings.find_one.return_value = {
            "id": 1,
            "enable_interval_backups": False,
            "backup_counter": 10,
            "backup_counter_maximum": 10,
        }
        
        result = orchestrator._run_backup()
        
        mock_do_backup.assert_not_called()


# =============================================================================
# _setup_logging Tests
# =============================================================================

class TestSetupLogging:
    """Tests for the _setup_logging method."""

    @patch("interface.operations.processing.os.path.isdir")
    @patch("interface.operations.processing.os.mkdir")
    @patch("interface.operations.processing.time.ctime")
    def test_setup_logging_success(
        self, mock_ctime, mock_mkdir, mock_isdir, orchestrator, mock_db_manager
    ):
        """Test successful logging setup."""
        mock_isdir.return_value = True
        mock_ctime.return_value = "Wed Jan 15 10:30:00 2024"
        
        result = orchestrator._setup_logging()
        
        assert result is not None
        assert "Run Log" in result
        assert ".txt" in result

    @patch("interface.operations.processing.os.path.isdir")
    @patch("interface.operations.processing.os.mkdir")
    def test_setup_logging_creates_directory(
        self, mock_mkdir, mock_isdir, orchestrator, mock_db_manager
    ):
        """Test logging setup creates directory if needed."""
        mock_isdir.return_value = False
        
        with patch("interface.operations.processing.time.ctime", return_value="Wed Jan 15 10:30:00 2024"):
            result = orchestrator._setup_logging()
        
        mock_mkdir.assert_called_once_with("/test/logs")

    @patch("interface.operations.processing.os.path.isdir")
    def test_setup_logging_directory_not_writable_gui_mode(
        self, mock_isdir, orchestrator, mock_db_manager
    ):
        """Test logging setup when directory not writable in GUI mode."""
        mock_isdir.return_value = True
        orchestrator.args.automatic = False
        
        with patch.object(orchestrator, '_check_logs_directory', return_value=False):
            result = orchestrator._setup_logging()
        
        assert result is None

    @patch("interface.operations.processing.os.path.isdir")
    def test_setup_logging_directory_not_writable_auto_mode(
        self, mock_isdir, orchestrator, mock_db_manager
    ):
        """Test logging setup when directory not writable in auto mode."""
        mock_isdir.return_value = True
        orchestrator.args.automatic = True
        
        with patch.object(orchestrator, '_check_logs_directory', return_value=False), \
             patch("builtins.open", mock_open()) as mock_file, \
             patch("interface.operations.processing.print"):
            
            result = orchestrator._setup_logging()
        
        assert result is None
        mock_file.assert_called()


# =============================================================================
# _check_logs_directory Tests
# =============================================================================

class TestCheckLogsDirectory:
    """Tests for the _check_logs_directory method."""

    @patch("builtins.open", mock_open())
    @patch("interface.operations.processing.os.remove")
    def test_check_logs_directory_writable(self, mock_remove, orchestrator):
        """Test check returns True when directory is writable."""
        result = orchestrator._check_logs_directory("/test/logs")
        
        assert result is True
        mock_remove.assert_called_once()

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_check_logs_directory_not_writable(self, mock_open, orchestrator):
        """Test check returns False when directory not writable."""
        result = orchestrator._check_logs_directory("/test/logs")
        
        assert result is False


# =============================================================================
# _run_dispatch Tests
# =============================================================================

class TestRunDispatch:
    """Tests for the _run_dispatch method."""

    @patch("interface.operations.processing.open", mock_open())
    @patch("interface.operations.processing.utils.do_clear_old_files")
    @patch("interface.operations.processing.dispatch.process")
    def test_run_dispatch_success(
        self, mock_dispatch_process, mock_clear, orchestrator, mock_db_manager
    ):
        """Test successful dispatch execution."""
        mock_dispatch_process.return_value = (False, "Success summary")
        
        result = orchestrator._run_dispatch("/test/logs/run.txt")
        
        assert isinstance(result, DispatchResult)
        assert result.error is False
        assert result.summary == "Success summary"
        mock_clear.assert_called_once()
        mock_dispatch_process.assert_called_once()

    @patch("interface.operations.processing.open", mock_open())
    @patch("interface.operations.processing.utils.do_clear_old_files")
    @patch("interface.operations.processing.dispatch.process")
    def test_run_dispatch_with_error(
        self, mock_dispatch_process, mock_clear, orchestrator, mock_db_manager
    ):
        """Test dispatch with error result."""
        mock_dispatch_process.return_value = (True, "Error occurred")
        
        result = orchestrator._run_dispatch("/test/logs/run.txt")
        
        assert result.error is True
        assert result.summary == "Error occurred"

    @patch("interface.operations.processing.open", mock_open())
    @patch("interface.operations.processing.utils.do_clear_old_files")
    @patch("interface.operations.processing.dispatch.process")
    @patch("interface.operations.processing.traceback.print_exc")
    @patch("interface.operations.processing.print")
    def test_run_dispatch_exception(
        self, mock_print, mock_traceback, mock_dispatch_process, mock_clear, orchestrator, mock_db_manager
    ):
        """Test dispatch exception handling."""
        mock_dispatch_process.side_effect = Exception("Dispatch failed")
        
        result = orchestrator._run_dispatch("/test/logs/run.txt")
        
        assert result.error is True
        assert "Dispatch failed" in result.summary
        mock_traceback.assert_called_once()

    @patch("interface.operations.processing.open", mock_open())
    @patch("interface.operations.processing.utils.do_clear_old_files")
    @patch("interface.operations.processing.dispatch.process")
    def test_run_dispatch_adds_to_email_queue(
        self, mock_dispatch_process, mock_clear, orchestrator, mock_db_manager
    ):
        """Test dispatch adds run log to email queue when reporting enabled."""
        mock_db_manager.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "logs_directory": "/test/logs",
            "enable_reporting": "True",
        }
        mock_dispatch_process.return_value = (False, "Success")
        
        result = orchestrator._run_dispatch("/test/logs/run.txt")
        
        mock_db_manager.emails_table.insert.assert_called_once()


# =============================================================================
# _send_email_report Tests
# =============================================================================

class TestSendEmailReport:
    """Tests for the _send_email_report method."""

    @patch("interface.operations.processing.os.path.isfile")
    @patch("interface.operations.processing.os.path.getsize")
    @patch("interface.operations.processing.os.path.abspath")
    @patch("interface.operations.processing.batch_log_sender.do")
    def test_send_email_report_success(
        self, mock_batch_sender, mock_abspath, mock_getsize, mock_isfile,
        orchestrator, mock_db_manager
    ):
        """Test successful email report sending."""
        mock_isfile.return_value = True
        mock_getsize.return_value = 1000
        mock_abspath.return_value = "/test/logs/test_log.txt"
        mock_db_manager.emails_table.all.return_value = [
            {"log": "/test/logs/test_log.txt", "folder_alias": "Test"}
        ]
        mock_batch_sender.return_value = None
        
        dispatch_result = DispatchResult(error=False, summary="Success")
        
        result = orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        assert result is True

    @patch("interface.operations.processing.os.path.isfile")
    @patch("interface.operations.processing.os.path.getsize")
    @patch("interface.operations.processing.os.path.abspath")
    @patch("interface.operations.processing.batch_log_sender.do")
    @patch("interface.operations.processing.zipfile.ZipFile")
    def test_send_email_report_with_large_file_zipping(
        self, mock_zipfile, mock_batch_sender, mock_abspath, mock_getsize, mock_isfile,
        orchestrator, mock_db_manager
    ):
        """Test email report zips large files."""
        mock_isfile.return_value = True
        mock_getsize.return_value = 10000000  # 10MB > 9MB limit
        mock_abspath.return_value = "/test/logs/large_log.txt"
        mock_db_manager.emails_table.all.return_value = [
            {"log": "/test/logs/large_log.txt", "folder_alias": "LargeTest"}
        ]
        
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__ = MagicMock(return_value=mock_zip)
        mock_zipfile.return_value.__exit__ = MagicMock(return_value=False)
        
        dispatch_result = DispatchResult(error=False, summary="Success")
        
        result = orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        mock_zipfile.assert_called_once()

    def test_send_email_report_reporting_disabled(self, orchestrator, mock_db_manager):
        """Test email report when reporting is disabled."""
        mock_db_manager.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "enable_reporting": "False",
        }
        
        dispatch_result = DispatchResult(error=False, summary="Success")
        
        result = orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        assert result is True

    @patch("interface.operations.processing.os.path.isfile")
    def test_send_email_report_skipped_files(
        self, mock_isfile, orchestrator, mock_db_manager
    ):
        """Test email report handles missing files."""
        mock_isfile.return_value = False
        mock_db_manager.emails_table.all.return_value = [
            {"log": "/test/logs/missing.txt", "folder_alias": "Missing"}
        ]
        
        dispatch_result = DispatchResult(error=False, summary="Success")
        
        with patch("interface.operations.processing.batch_log_sender.do"):
            result = orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        assert result is True
        mock_db_manager.sent_emails_removal_queue.insert.assert_called_once()

    @patch("interface.operations.processing.os.path.isfile")
    @patch("interface.operations.processing.os.path.getsize")
    @patch("interface.operations.processing.os.path.abspath")
    def test_send_email_report_exception(
        self, mock_abspath, mock_getsize, mock_isfile,
        orchestrator, mock_db_manager
    ):
        """Test email report exception handling."""
        mock_isfile.return_value = True
        mock_getsize.return_value = 1000
        mock_abspath.return_value = "/test/logs/test_log.txt"
        mock_db_manager.emails_table.all.return_value = [
            {"log": "/test/logs/test_log.txt", "folder_alias": "Test"}
        ]
        
        with patch.object(orchestrator, '_handle_email_error') as mock_handle_error:
            with patch("interface.operations.processing.batch_log_sender.do", side_effect=Exception("Email failed")):
                dispatch_result = DispatchResult(error=False, summary="Success")
                
                result = orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        assert result is False


# =============================================================================
# _handle_email_error Tests
# =============================================================================

class TestHandleEmailError:
    """Tests for the _handle_email_error method."""

    @patch("builtins.open", mock_open())
    def test_handle_email_error_with_printing_fallback(self, orchestrator, mock_db_manager):
        """Test email error handling with printing fallback enabled."""
        mock_db_manager.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "report_printing_fallback": "True",
        }
        
        with patch("interface.operations.processing.print_run_log.do") as mock_print_run:
            orchestrator._handle_email_error(Exception("Email failed"), "/test/logs/run.txt", mock_db_manager.oversight_and_defaults.find_one.return_value)
        
        mock_print_run.assert_called_once()

    @patch("builtins.open", mock_open())
    def test_handle_email_error_without_printing_fallback(self, orchestrator, mock_db_manager):
        """Test email error handling without printing fallback."""
        mock_db_manager.oversight_and_defaults.find_one.return_value = {
            "id": 1,
            "report_printing_fallback": "False",
        }
        
        with patch("interface.operations.processing.print_run_log.do") as mock_print_run:
            orchestrator._handle_email_error(Exception("Email failed"), "/test/logs/run.txt", mock_db_manager.oversight_and_defaults.find_one.return_value)
        
        mock_print_run.assert_not_called()


# =============================================================================
# _handle_error Tests
# =============================================================================

class TestHandleError:
    """Tests for the _handle_error method."""

    @patch("builtins.open", mock_open())
    @patch("interface.operations.processing.print")
    def test_handle_error_writes_to_log(self, mock_print, orchestrator):
        """Test error handling writes to critical error log."""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            orchestrator._handle_error(Exception("Test error"))
        
        mock_print.assert_called_with("Test error")
        mock_file.assert_called_once_with("critical_error.log", "a", encoding="utf-8")

    @patch("interface.operations.processing.print")
    def test_handle_error_fallback_to_public_directory(self, mock_print, orchestrator):
        """Test error handling falls back to public directory."""
        # First open fails, second succeeds
        mock_file = MagicMock()
        mock_file_handle = MagicMock()
        
        def side_effect(*args, **kwargs):
            if args[0] == "critical_error.log":
                raise IOError("Cannot write")
            return mock_file_handle
        
        with patch("builtins.open", side_effect=side_effect):
            orchestrator._handle_error(Exception("Test error"))


# =============================================================================
# automatic_process_directories Tests
# =============================================================================

class TestAutomaticProcessDirectories:
    """Tests for the automatic_process_directories function."""

    @patch("interface.operations.processing.print")
    def test_no_active_folders(self, mock_print, mock_db_manager, sample_args):
        """Test automatic processing with no active folders."""
        mock_db_manager.folders_table.count.return_value = 0
        
        with pytest.raises(SystemExit):
            automatic_process_directories(mock_db_manager, sample_args, "1.0.0")
        
        mock_print.assert_called_with("Error, No Active Folders")
        mock_db_manager.close.assert_called_once()

    @patch("interface.operations.processing.print")
    def test_successful_processing(self, mock_print, mock_db_manager, sample_args):
        """Test successful automatic processing."""
        mock_db_manager.folders_table.count.return_value = 1
        mock_db_manager._database_path = "/test/database.sqlite"
        
        with patch.object(ProcessingOrchestrator, "process_all") as mock_process:
            mock_process.return_value = ProcessingResult(
                success=True,
                backup_path=None,
                log_path="/test/logs/run.txt",
                error=None,
            )
            
            with pytest.raises(SystemExit):
                automatic_process_directories(mock_db_manager, sample_args, "1.0.0")
        
        mock_print.assert_any_call("batch processing configured directories")
        mock_print.assert_any_call("batch processing complete")
        mock_db_manager.close.assert_called_once()

    @patch("interface.operations.processing.print")
    def test_processing_failure(self, mock_print, mock_db_manager, sample_args):
        """Test automatic processing failure."""
        mock_db_manager.folders_table.count.return_value = 1
        mock_db_manager._database_path = "/test/database.sqlite"
        
        with patch.object(ProcessingOrchestrator, "process_all") as mock_process:
            mock_process.return_value = ProcessingResult(
                success=False,
                error="Processing failed",
            )
            
            with pytest.raises(SystemExit):
                automatic_process_directories(mock_db_manager, sample_args, "1.0.0")
        
        mock_print.assert_any_call("Processing failed: Processing failed")
        mock_db_manager.close.assert_called_once()

    @patch("builtins.open", mock_open())
    @patch("interface.operations.processing.print")
    def test_processing_exception(self, mock_print, mock_db_manager, sample_args):
        """Test automatic processing with exception."""
        mock_db_manager.folders_table.count.return_value = 1
        mock_db_manager._database_path = "/test/database.sqlite"
        
        with patch.object(ProcessingOrchestrator, "process_all", side_effect=Exception("Critical error")):
            with pytest.raises(SystemExit):
                automatic_process_directories(mock_db_manager, sample_args, "1.0.0")
        
        mock_print.assert_any_call("Critical error")
        mock_db_manager.close.assert_called_once()


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_backup_counter_overflow(self, orchestrator, mock_db_manager):
        """Test backup counter overflow handling."""
        mock_db_manager.settings.find_one.return_value = {
            "id": 1,
            "enable_interval_backups": True,
            "backup_counter": 999999,
            "backup_counter_maximum": 10,
        }
        
        with patch("interface.operations.processing.backup_increment.do_backup") as mock_backup:
            orchestrator._run_backup()
        
        mock_backup.assert_called_once()

    @patch("interface.operations.processing.os.path.isfile")
    def test_batch_size_exceeded(self, mock_isfile, orchestrator, mock_db_manager):
        """Test email batching when size exceeded."""
        mock_isfile.return_value = True
        
        # Create multiple emails that exceed batch size
        emails = []
        for i in range(20):
            emails.append({"log": f"/test/logs/log_{i}.txt", "folder_alias": f"Test{i}"})
        
        mock_db_manager.emails_table.all.return_value = emails
        mock_db_manager.emails_table.count.return_value = 20
        
        with patch("interface.operations.processing.os.path.getsize", return_value=1000000):  # 1MB each
            with patch("interface.operations.processing.os.path.abspath", return_value="/test/logs/test.txt"):
                with patch("interface.operations.processing.batch_log_sender.do") as mock_sender:
                    dispatch_result = DispatchResult(error=False, summary="Success")
                    orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        # Should have sent multiple batches
        assert mock_sender.call_count >= 1

    def test_empty_email_queue(self, orchestrator, mock_db_manager):
        """Test email report with empty queue."""
        mock_db_manager.emails_table.all.return_value = []
        mock_db_manager.emails_table.count.return_value = 0
        
        dispatch_result = DispatchResult(error=False, summary="Success")
        
        with patch("interface.operations.processing.batch_log_sender.do") as mock_sender:
            result = orchestrator._send_email_report(dispatch_result, "/test/logs/run.txt")
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
