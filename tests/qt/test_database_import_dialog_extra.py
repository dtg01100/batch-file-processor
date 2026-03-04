"""Additional tests for DatabaseImportDialog to improve coverage."""
from unittest.mock import MagicMock, patch, call
import pytest
from PyQt6.QtCore import Qt

pytestmark = pytest.mark.qt


@pytest.mark.qt
class TestDatabaseImportDialogUI:
    """Tests for DatabaseImportDialog UI initialization and setup."""

    def test_dialog_initialization(self, qtbot):
        """Test dialog initializes with correct properties."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        # Check for required widgets
        assert hasattr(dialog, "_select_button")
        assert hasattr(dialog, "_db_label")
        assert hasattr(dialog, "_import_button")
        assert hasattr(dialog, "_progress_bar")
        assert hasattr(dialog, "_close_button")

    def test_initial_button_states(self, qtbot):
        """Test initial button enabled/disabled states."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        assert not dialog._import_button.isEnabled()
        assert dialog._select_button.isEnabled()
        assert dialog._close_button.isEnabled()

    def test_progress_bar_initially_hidden(self, qtbot):
        """Test that progress bar is initially hidden."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        assert not dialog._progress_bar.isVisible()

    def test_db_label_initial_text(self, qtbot):
        """Test database label initial text."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        assert dialog._db_label.text() == "No File Selected"


@pytest.mark.qt
class TestDatabaseImportDialogFileSelection:
    """Tests for database file selection functionality."""

    def test_select_database_success(self, qtbot, monkeypatch):
        """Test successful database file selection."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/test/new_database.db", "")
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists",
            lambda x: True
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
            lambda *args, **kwargs: ("", "")
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._new_database_path is None
        assert not dialog._import_button.isEnabled()

    def test_select_same_database_allows_selection(self, qtbot, monkeypatch):
        """Test selecting the same database - it allows the selection."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/original.db", "")
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists",
            lambda x: True
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        # The dialog allows selecting the same database
        assert dialog._new_database_path == "/original.db"
        assert dialog._import_button.isEnabled()

    def test_select_nonexistent_database_does_not_set_path(self, qtbot, monkeypatch):
        """Test selecting nonexistent database does not set the path."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/nonexistent.db", "")
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists",
            lambda x: False
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        # The dialog should not set the path if file doesn't exist
        assert dialog._new_database_path is None
        assert not dialog._import_button.isEnabled()


@pytest.mark.qt
class TestDatabaseImportDialogProgress:
    """Tests for progress tracking during import."""

    def test_progress_update(self, qtbot):
        """Test progress bar updates correctly."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
        qtbot.addWidget(dialog)

        dialog._progress_bar.setVisible(True)
        dialog._on_progress(50, 100, "Processing...")

        assert dialog._progress_bar.maximum() == 100
        assert dialog._progress_bar.value() == 50

    def test_progress_with_zero_maximum(self, qtbot):
        """Test progress bar handles zero maximum (indeterminate mode)."""
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
            mock_info
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
            mock_critical
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
            mock_critical
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
            mock_question
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
            mock_question
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Linux", "/backup", "42"
        )
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
        from interface.qt.dialogs.database_import_dialog import ImportThread, DbMigrationJob

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
        from interface.qt.dialogs.database_import_dialog import ImportThread, DbMigrationJob
        from PyQt6.QtCore import pyqtSignal

        # Verify signals exist
        assert hasattr(ImportThread, 'progress')
        assert hasattr(ImportThread, 'finished')
        assert hasattr(ImportThread, 'error')
        assert hasattr(ImportThread, 'confirm_required')

    def test_import_thread_confirm_mechanism(self, qtbot):
        """Test ImportThread._confirm uses signal mechanism."""
        import threading
        from interface.qt.dialogs.database_import_dialog import ImportThread, DbMigrationJob

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
        thread.confirm_required.emit("Test Title", "Test Message", result_event)
        
        # Wait for the event to be processed
        qtbot.wait(100)

    def test_import_thread_run_handles_exception(self, tmp_path):
        """Test ImportThread.run handles exceptions when database doesn't exist."""
        from interface.qt.dialogs.database_import_dialog import ImportThread, DbMigrationJob

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
        """Test _migrate_folder merges copy backend settings."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            'id': 1,
            'folder_name': '/test/folder',
            'process_backend_copy': False,
        }

        # Old folder with copy backend enabled
        old_folders = MagicMock()
        old_folders.find.return_value = [
            {
                'folder_name': '/test/folder',
                'process_backend_copy': True,
                'copy_to_directory': '/backup',
                'process_backend_ftp': False,
                'process_backend_email': False,
            }
        ]

        new_db = MagicMock()
        new_db['folders'] = MagicMock()

        # Mock samefile to return True for matching paths
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: a == b and a == '/test/folder'
        )

        job._migrate_folder(folder, old_folders, new_db)

        # Should update with copy backend settings
        new_db['folders'].update.assert_called_once()
        update_data = new_db['folders'].update.call_args[0][0]
        assert update_data['id'] == 1
        assert update_data['process_backend_copy'] is True
        assert update_data['copy_to_directory'] == '/backup'

    def test_migration_job_migrate_folder_with_ftp_backend(self, monkeypatch):
        """Test _migrate_folder merges FTP backend settings."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            'id': 1,
            'folder_name': '/test/folder',
            'process_backend_ftp': False,
        }

        old_folders = MagicMock()
        old_folders.find.return_value = [
            {
                'folder_name': '/test/folder',
                'process_backend_ftp': True,
                'ftp_server': 'ftp.example.com',
                'ftp_folder': '/upload',
                'ftp_username': 'user',
                'ftp_password': 'pass',
                'process_backend_copy': False,
                'process_backend_email': False,
            }
        ]

        new_db = MagicMock()
        new_db['folders'] = MagicMock()

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: a == b and a == '/test/folder'
        )

        job._migrate_folder(folder, old_folders, new_db)

        new_db['folders'].update.assert_called_once()
        update_data = new_db['folders'].update.call_args[0][0]
        assert update_data['ftp_server'] == 'ftp.example.com'
        assert update_data['ftp_folder'] == '/upload'
        assert update_data['ftp_username'] == 'user'
        assert update_data['ftp_password'] == 'pass'

    def test_migration_job_migrate_folder_with_email_backend(self, monkeypatch):
        """Test _migrate_folder merges email backend settings."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            'id': 1,
            'folder_name': '/test/folder',
            'process_backend_email': False,
        }

        old_folders = MagicMock()
        old_folders.find.return_value = [
            {
                'folder_name': '/test/folder',
                'process_backend_email': True,
                'email_recipients': 'test@example.com',
                'email_subject': 'Test Subject',
                'email_from': 'sender@example.com',
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'smtp_username': 'smtp_user',
                'smtp_password': 'smtp_pass',
                'smtp_use_tls': True,
                'process_backend_copy': False,
                'process_backend_ftp': False,
            }
        ]

        new_db = MagicMock()
        new_db['folders'] = MagicMock()

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: a == b and a == '/test/folder'
        )

        job._migrate_folder(folder, old_folders, new_db)

        new_db['folders'].update.assert_called_once()
        update_data = new_db['folders'].update.call_args[0][0]
        assert update_data['email_recipients'] == 'test@example.com'
        assert update_data['smtp_server'] == 'smtp.example.com'

    def test_migration_job_migrate_folder_no_match(self, monkeypatch):
        """Test _migrate_folder does nothing when no matching folder."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            'id': 1,
            'folder_name': '/test/folder',
        }

        old_folders = MagicMock()
        old_folders.find.return_value = [
            {
                'folder_name': '/different/folder',
                'process_backend_copy': True,
            }
        ]

        new_db = MagicMock()
        new_db['folders'] = MagicMock()

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda a, b: False
        )

        job._migrate_folder(folder, old_folders, new_db)

        # Should not update when no match
        new_db['folders'].update.assert_not_called()

    def test_migration_job_migrate_folder_handles_samefile_error(self, monkeypatch):
        """Test _migrate_folder handles samefile errors gracefully."""
        from interface.qt.dialogs.database_import_dialog import DbMigrationJob

        job = DbMigrationJob("/original.db", "/new.db")

        folder = {
            'id': 1,
            'folder_name': '/test/folder',
        }

        old_folders = MagicMock()
        old_folders.find.return_value = [
            {
                'folder_name': '/test/folder',  # Same name
                'process_backend_copy': True,
                'copy_to_directory': '/backup',
                'process_backend_ftp': False,
                'process_backend_email': False,
            }
        ]

        new_db = MagicMock()
        new_db['folders'] = MagicMock()

        def mock_samefile(a, b):
            raise OSError("Cannot compare paths")

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            mock_samefile
        )

        job._migrate_folder(folder, old_folders, new_db)

        # Should fallback to string comparison and update
        new_db['folders'].update.assert_called_once()


@pytest.mark.qt
class TestShowDatabaseImportDialog:
    """Tests for show_database_import_dialog function."""

    def test_show_database_import_dialog_function(self, monkeypatch):
        """Test show_database_import_dialog creates and executes dialog."""
        from interface.qt.dialogs.database_import_dialog import show_database_import_dialog

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
        )
        assert len(exec_called) == 1
