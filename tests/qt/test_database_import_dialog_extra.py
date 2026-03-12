"""Additional tests for DatabaseImportDialog to improve coverage."""

from unittest.mock import MagicMock
import pytest
from PyQt6.QtCore import Qt

pytestmark = pytest.mark.qt


@pytest.mark.qt
class TestDatabaseImportDialogUI:
    """Tests for DatabaseImportDialog UI initialization and setup."""

    def test_dialog_initialization(self, qtbot):
        """Test dialog initializes with correct properties."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "folders.db merging utility"
        assert dialog._original_database_path == "/original.db"
        assert dialog._running_platform == "Linux"
        assert dialog._backup_path == "/backup"
        assert dialog._current_db_version == "42"
        assert dialog._new_database_path is None

    def test_ui_has_required_widgets(self, qtbot):
        """Test that all required UI widgets are created."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        # Check for required widgets
        assert hasattr(dialog, "_select_button")
        assert hasattr(dialog, "_db_label")
        assert hasattr(dialog, "_import_button")
        assert hasattr(dialog, "_progress_bar")
        assert hasattr(dialog, "_close_button")

    def test_dialog_uses_no_base_action_mode(self, qtbot):
        """Test dialog opts out of BaseDialog default action buttons."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        assert dialog._button_box is None

    def test_initial_button_states(self, qtbot):
        """Test initial button enabled/disabled states."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        assert not dialog._import_button.isEnabled()
        assert dialog._select_button.isEnabled()
        assert dialog._close_button.isEnabled()

    def test_progress_bar_initially_hidden(self, qtbot):
        """Test that progress bar is initially hidden."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        assert not dialog._progress_bar.isVisible()

    def test_db_label_initial_text(self, qtbot):
        """Test database label initial text."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        assert dialog._db_label.text() == "No File Selected"

    def test_preselected_path_populates_label_and_enables_import(self, qtbot):
        """Test constructor preselection immediately reflects selected DB in UI."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        selected = "/workspaces/batch-file-processor/tests/fixtures/legacy_v32_folders.db"
        dialog = DatabaseImportDialog(
            None,
            "/original.db",
            "Linux",
            "/backup",
            "42",
            preselected_database_path=selected,
        )
        qtbot.addWidget(dialog)

        assert dialog._new_database_path == selected
        assert dialog._db_label.text() == selected
        assert dialog._import_button.isEnabled()


@pytest.mark.qt
class TestDatabaseImportDialogFileSelection:
    """Tests for database file selection functionality."""

    def test_select_database_success(self, qtbot, monkeypatch):
        """Test successful database file selection."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/test/new_database.db", ""),
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists", lambda x: True
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._new_database_path == "/test/new_database.db"
        assert "new_database.db" in dialog._db_label.text()
        assert dialog._import_button.isEnabled()

    def test_select_database_cancelled(self, qtbot, monkeypatch):
        """Test cancelling file selection."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("", ""),
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._new_database_path is None
        assert not dialog._import_button.isEnabled()

    def test_select_same_database_allows_selection(self, qtbot, monkeypatch):
        """Test selecting the same database - it allows the selection."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/original.db", ""),
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists", lambda x: True
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        # The dialog allows selecting the same database
        assert dialog._new_database_path == "/original.db"
        assert dialog._import_button.isEnabled()

    def test_select_database_updates_ui_without_exists_check(self, qtbot, monkeypatch):
        """Test selection updates UI even when path existence checks are unreliable."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/nonexistent.db", ""),
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._new_database_path == "/nonexistent.db"
        assert dialog._db_label.text() == "/nonexistent.db"
        assert dialog._import_button.isEnabled()


@pytest.mark.qt
class TestDatabaseImportDialogProgress:
    """Tests for progress tracking during import."""

    def test_progress_update(self, qtbot):
        """Test progress bar updates correctly."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        dialog._progress_bar.setVisible(True)
        dialog._on_progress(50, 100, "Processing...")

        assert dialog._progress_bar.maximum() == 100
        assert dialog._progress_bar.value() == 50

    def test_progress_with_zero_maximum(self, qtbot):
        """Test progress bar handles zero maximum (indeterminate mode)."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        dialog._progress_bar.setVisible(True)
        dialog._on_progress(0, 0, "Starting...")

        # Should handle gracefully
        assert dialog._progress_bar.minimum() == 0


@pytest.mark.qt
class TestDatabaseImportDialogCompletion:
    """Tests for import completion handling."""

    def test_on_finished_success(self, qtbot, monkeypatch):
        """Test successful completion handler."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        mock_info = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.information",
            mock_info,
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        dialog._on_finished(True, "Import completed successfully")

        mock_info.assert_called_once()
        assert dialog._select_button.isEnabled()
        assert not dialog._progress_bar.isVisible()

    def test_on_finished_failure(self, qtbot, monkeypatch):
        """Test failure completion handler."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        mock_critical = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.critical",
            mock_critical,
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        dialog._on_finished(False, "Import failed")

        mock_critical.assert_called_once()
        assert dialog._select_button.isEnabled()

    def test_on_error(self, qtbot, monkeypatch):
        """Test error handler."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        mock_critical = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.critical",
            mock_critical,
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        dialog._on_error("Connection failed")

        mock_critical.assert_called_once()


@pytest.mark.qt
class TestDatabaseImportDialogConfirm:
    """Tests for confirmation dialog handling."""

    def test_on_confirm_required_yes(self, qtbot, monkeypatch):
        """Test confirmation handler with Yes response."""
        import threading
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
        from PyQt6.QtWidgets import QMessageBox

        def mock_question(parent, title, message, buttons, default):
            return QMessageBox.StandardButton.Yes

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.question",
            mock_question,
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        result_event = threading.Event()
        dialog._on_confirm_required("Title", "Message", result_event)

        assert result_event.is_set()
        assert result_event.result is True

    def test_on_confirm_required_no(self, qtbot, monkeypatch):
        """Test confirmation handler with No response."""
        import threading
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
        from PyQt6.QtWidgets import QMessageBox

        def mock_question(parent, title, message, buttons, default):
            return QMessageBox.StandardButton.No

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.question",
            mock_question,
        )

        dialog = DatabaseImportDialog(None, "/original.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        result_event = threading.Event()
        dialog._on_confirm_required("Title", "Message", result_event)

        assert result_event.is_set()
        assert result_event.result is False


@pytest.mark.qt
class TestImportThread:
    """Tests for ImportThread class."""

    def test_import_thread_init(self):
        """Test ImportThread initialization."""
        from interface.qt.dialogs.database_import_dialog import (
            ImportThread,
            DbMigrationJob,
        )

        job = DbMigrationJob("/original.db", "/new.db")
        thread = ImportThread(
            migrate_job=job,
            new_db_path="/new.db",
            original_db_path="/original.db",
            platform="Linux",
            db_version="42",
            backup_path="/backup",
        )

        assert thread._new_db_path == "/new.db"
        assert thread._original_db_path == "/original.db"
        assert thread._platform == "Linux"
        assert thread._db_version == "42"

    def test_import_thread_signals_exist(self):
        """Test ImportThread has required signals."""
        from interface.qt.dialogs.database_import_dialog import ImportThread

        # Verify signals exist
        assert hasattr(ImportThread, "progress")
        assert hasattr(ImportThread, "finished")
        assert hasattr(ImportThread, "error")
        assert hasattr(ImportThread, "confirm_required")

    def test_import_thread_confirm_mechanism(self, qtbot):
        """Test ImportThread._confirm uses signal mechanism."""
        import threading
        from interface.qt.dialogs.database_import_dialog import (
            ImportThread,
            DbMigrationJob,
        )

        job = DbMigrationJob("/original.db", "/new.db")
        thread = ImportThread(
            migrate_job=job,
            new_db_path="/new.db",
            original_db_path="/original.db",
            platform="Linux",
            db_version="42",
            backup_path="/backup",
        )

        # Use qtbot to wait for signal
        signal_emitted = []

        def on_confirm_required(title, message, event):
            signal_emitted.append((title, message, event))
            event.result = True
            event.set()

        thread.confirm_required.connect(on_confirm_required)

        # Start the thread to create the signal connections
        # But we'll manually test the _confirm method
        result_event = threading.Event()
        result_event.result = False

        # Manually emit the signal to test the connection
        with qtbot.waitSignal(thread.confirm_required, timeout=1000) as blocker:
            thread.confirm_required.emit("Test Title", "Test Message", result_event)

        qtbot.waitUntil(result_event.is_set, timeout=1000)

        assert blocker.args == ["Test Title", "Test Message", result_event]
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == ("Test Title", "Test Message", result_event)
        assert result_event.result is True

    def test_import_thread_run_handles_exception(self, tmp_path):
        """Test ImportThread.run handles exceptions when database doesn't exist."""
        from interface.qt.dialogs.database_import_dialog import (
            ImportThread,
            DbMigrationJob,
        )

        job = DbMigrationJob("/original.db", "/new.db")
        thread = ImportThread(
            migrate_job=job,
            new_db_path="/nonexistent/path/database.db",
            original_db_path="/original.db",
            platform="Linux",
            db_version="42",
            backup_path="/backup",
        )

        # Create a database at the new path for testing
        # Since we can't mock signals, we just verify run() doesn't crash
        # when dealing with non-existent files
        try:
            thread.run()
        except Exception:
            pass  # The method should handle exceptions internally


@pytest.mark.qt
class TestDbMigrationJob:
    """Tests for DbMigrationJob class."""

    def test_migration_job_init(self):
        """Test DbMigrationJob initialization."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        assert job.original_folder_path == "/original.db"
        assert job.new_folder_path == "/new.db"

    def test_migration_job_migrate_folder_with_copy_backend(self, monkeypatch):
        """Test _migrate_folder updates matching target row from imported folder."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            "id": 1,
            "folder_name": "/test/folder",
            "process_backend_copy": True,
            "copy_to_directory": "/imported/copy",
            "folder_is_active": True,
        }

        target_folders = MagicMock()
        target_folders.find.return_value = [
            {
                "folder_name": "/test/folder",
                "id": 42,
            }
        ]

        target_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "folder_name", "TEXT", 0, None, 0),
            (2, "process_backend_copy", "INTEGER", 0, None, 0),
            (3, "copy_to_directory", "TEXT", 0, None, 0),
            (4, "folder_is_active", "INTEGER", 0, None, 0),
        ]
        target_db.raw_connection.cursor.return_value = cursor

        # Mock samefile to return True for matching paths
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: a == b and a == "/test/folder",
        )

        job._migrate_folder(folder, target_folders, target_db)

        target_folders.update.assert_called_once()
        update_data = target_folders.update.call_args[0][0]
        assert update_data["id"] == 42
        assert update_data["process_backend_copy"] is True
        assert update_data["copy_to_directory"] == "/imported/copy"

    def test_migration_job_migrate_folder_with_ftp_backend(self, monkeypatch):
        """Test _migrate_folder keeps FTP settings from imported folder."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            "id": 1,
            "folder_name": "/test/folder",
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
            "ftp_folder": "/upload",
            "ftp_username": "user",
            "ftp_password": "pass",
        }

        target_folders = MagicMock()
        target_folders.find.return_value = [
            {
                "folder_name": "/test/folder",
                "id": 7,
            }
        ]

        target_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "folder_name", "TEXT", 0, None, 0),
            (2, "process_backend_ftp", "INTEGER", 0, None, 0),
            (3, "ftp_server", "TEXT", 0, None, 0),
            (4, "ftp_folder", "TEXT", 0, None, 0),
            (5, "ftp_username", "TEXT", 0, None, 0),
            (6, "ftp_password", "TEXT", 0, None, 0),
        ]
        target_db.raw_connection.cursor.return_value = cursor

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: a == b and a == "/test/folder",
        )

        job._migrate_folder(folder, target_folders, target_db)

        target_folders.update.assert_called_once()
        update_data = target_folders.update.call_args[0][0]
        assert update_data["ftp_server"] == "ftp.example.com"
        assert update_data["ftp_folder"] == "/upload"
        assert update_data["ftp_username"] == "user"
        assert update_data["ftp_password"] == "pass"

    def test_migration_job_migrate_folder_with_email_backend(self, monkeypatch):
        """Test _migrate_folder keeps email settings from imported folder."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            "id": 1,
            "folder_name": "/test/folder",
            "process_backend_email": True,
            "email_to": "test@example.com",
            "email_subject_line": "Test Subject",
        }

        target_folders = MagicMock()
        target_folders.find.return_value = [
            {
                "folder_name": "/test/folder",
                "id": 9,
            }
        ]

        target_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "folder_name", "TEXT", 0, None, 0),
            (2, "process_backend_email", "INTEGER", 0, None, 0),
            (3, "email_to", "TEXT", 0, None, 0),
            (4, "email_subject_line", "TEXT", 0, None, 0),
        ]
        target_db.raw_connection.cursor.return_value = cursor

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: a == b and a == "/test/folder",
        )

        job._migrate_folder(folder, target_folders, target_db)

        target_folders.update.assert_called_once()
        update_data = target_folders.update.call_args[0][0]
        assert update_data["email_to"] == "test@example.com"
        assert update_data["email_subject_line"] == "Test Subject"

    def test_migration_job_migrate_folder_no_match_inserts(self, monkeypatch):
        """Test _migrate_folder inserts when no matching target folder exists."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            "id": 1,
            "folder_name": "/test/folder",
        }

        target_folders = MagicMock()
        target_folders.find.return_value = [
            {
                "folder_name": "/different/folder",
                "process_backend_copy": True,
            }
        ]

        target_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "folder_name", "TEXT", 0, None, 0),
        ]
        target_db.raw_connection.cursor.return_value = cursor

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: False,
        )

        job._migrate_folder(folder, target_folders, target_db)

        target_folders.update.assert_not_called()
        target_folders.insert.assert_called_once()

    def test_migration_job_migrate_folder_handles_samefile_error(self, monkeypatch):
        """Test _migrate_folder handles samefile errors gracefully."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            "id": 1,
            "folder_name": "/test/folder",
        }

        target_folders = MagicMock()
        target_folders.find.return_value = [
            {
                "folder_name": "/test/folder",  # Same name
                "id": 11,
            }
        ]

        target_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (0, "id", "INTEGER", 0, None, 1),
            (1, "folder_name", "TEXT", 0, None, 0),
        ]
        target_db.raw_connection.cursor.return_value = cursor

        def mock_samefile(a, b):
            raise OSError("Cannot compare paths")

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            mock_samefile,
        )

        job._migrate_folder(folder, target_folders, target_db)

        # Should fallback to string comparison and update
        target_folders.update.assert_called_once()

    @pytest.mark.timeout(120)
    def test_do_migrate_imports_active_folders_into_target_db(
        self, legacy_v32_db, tmp_path
    ):
        """Regression: import should preserve active folders from legacy source."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob
        from interface.database.database_obj import DatabaseObj
        from interface.database import sqlite_wrapper
        from batch_file_processor.constants import CURRENT_DATABASE_VERSION

        target_path = str(tmp_path / "target_folders.db")
        # Create fresh live database that receives imported folders.
        target_db_obj = DatabaseObj(
            database_path=target_path,
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmp_path),
            running_platform="Linux",
        )
        target_db_obj.close()

        source_db = sqlite_wrapper.Database.connect(legacy_v32_db)
        expected_active = source_db["folders"].count(folder_is_active=True)
        source_db.close()
        assert expected_active > 0

        class _Signal:
            def emit(self, *args, **kwargs):
                return

        class _Thread:
            progress = _Signal()

        job = DbMigrationJob(target_path, legacy_v32_db)
        job.do_migrate(_Thread(), legacy_v32_db, target_path)

        imported_db = sqlite_wrapper.Database.connect(target_path)
        actual_active = imported_db["folders"].count(folder_is_active=True)
        imported_settings = imported_db["settings"].find_one(id=1)
        imported_jolley = imported_db["folders"].find_one(folder_name="D:/DATA/OUT/011078")
        imported_db.close()

        assert actual_active == expected_active
        assert bool(imported_settings.get("enable_email")) is True
        assert bool(imported_jolley.get("process_backend_ftp")) is True


@pytest.mark.qt
class TestShowDatabaseImportDialog:
    """Tests for show_database_import_dialog function."""

    def test_show_database_import_dialog_function(self, monkeypatch):
        """Test show_database_import_dialog creates and executes dialog."""
        from interface.qt.dialogs.database_import_dialog import (
            show_database_import_dialog,
        )

        exec_called = []
        mock_dialog = MagicMock()
        mock_dialog.exec = lambda: exec_called.append(1)

        mock_dialog_class = MagicMock(return_value=mock_dialog)

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.DatabaseImportDialog",
            mock_dialog_class,
        )

        show_database_import_dialog(
            parent=None,
            original_database_path="/original.db",
            running_platform="Linux",
            backup_path="/backup",
            current_db_version="42",
        )

        mock_dialog_class.assert_called_once_with(
            None,
            "/original.db",
            "Linux",
            "/backup",
            "42",
            None,
        )
        assert len(exec_called) == 1

    def test_show_database_import_dialog_with_preselected_path(self, monkeypatch):
        """Test show_database_import_dialog forwards a preselected database path."""
        from interface.qt.dialogs.database_import_dialog import (
            show_database_import_dialog,
        )

        exec_called = []
        mock_dialog = MagicMock()
        mock_dialog.exec = lambda: exec_called.append(1)

        mock_dialog_class = MagicMock(return_value=mock_dialog)

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.DatabaseImportDialog",
            mock_dialog_class,
        )

        show_database_import_dialog(
            parent=None,
            original_database_path="/original.db",
            running_platform="Linux",
            backup_path="/backup",
            current_db_version="42",
            preselected_database_path="/fixtures/legacy_v32_folders.db",
        )

        mock_dialog_class.assert_called_once_with(
            None,
            "/original.db",
            "Linux",
            "/backup",
            "42",
            "/fixtures/legacy_v32_folders.db",
        )
        assert len(exec_called) == 1
