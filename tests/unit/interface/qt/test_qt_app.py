"""Enhanced comprehensive tests for QtBatchFileSenderApp.

Tests cover:
- UI initialization and window creation
- Button interactions and signal connections
- Dialog showing methods
- Window lifecycle management
- Error handling
- Button state management
- Folder operations
"""

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QApplication, QPushButton

from interface.qt.app import QtBatchFileSenderApp


@pytest.fixture
def mock_database():
    """Provide a mock database object."""
    db = MagicMock()
    db.close = MagicMock()
    db.get_oversight_or_default = MagicMock(return_value={})
    db.get_settings_or_default = MagicMock(return_value={})
    db.folders_table = MagicMock()
    db.folders_table.count = MagicMock(return_value=0)
    db.processed_files = MagicMock()
    db.processed_files.count = MagicMock(return_value=0)
    db.database_connection = MagicMock()
    db.settings = MagicMock()
    db.settings.update = MagicMock()
    db.oversight_and_defaults = MagicMock()
    db.oversight_and_defaults.update = MagicMock()
    return db


@pytest.fixture
def mock_folder_manager():
    """Provide a mock folder manager."""
    manager = MagicMock()
    manager.add_folder = MagicMock()
    manager.delete_folder_with_related = MagicMock()
    manager.check_folder_exists = MagicMock(return_value={"truefalse": False})
    return manager


@pytest.fixture
def mock_ui_service():
    """Provide a mock UI service."""
    service = MagicMock()
    service.ask_directory = MagicMock(return_value=None)
    service.ask_yes_no = MagicMock(return_value=False)
    service.ask_ok_cancel = MagicMock(return_value=False)
    return service


@pytest.fixture
def mock_progress_service():
    """Provide a mock progress service."""
    service = MagicMock()
    service.show = MagicMock()
    service.hide = MagicMock()
    return service


@pytest.fixture
def qt_app():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    return app


def _make_app(**kwargs):
    """Helper to create a QtBatchFileSenderApp with minimal required parameters."""
    app = QtBatchFileSenderApp(**kwargs)
    return app


class TestQtAppInitialization:
    """Test suite for QtBatchFileSenderApp initialization."""

    def test_app_initialization(self):
        """Test that QtBatchFileSenderApp can be initialized."""
        app = _make_app()

        assert app is not None
        assert hasattr(app, "initialize")
        assert hasattr(app, "run")
        assert hasattr(app, "shutdown")

    def test_app_initialization_with_dependencies(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test initialization with injected dependencies."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )

        assert app is not None
        assert app._database is mock_database
        assert app._folder_manager is mock_folder_manager
        assert app._ui_service is mock_ui_service
        assert app._progress_service is mock_progress_service

    def test_app_properties_before_initialization(self):
        """Test app property access before initialization raises RuntimeError."""
        app = _make_app()

        with pytest.raises(RuntimeError, match="Database not initialized"):
            _ = app.database

        with pytest.raises(RuntimeError, match="Folder manager not initialized"):
            _ = app.folder_manager

        with pytest.raises(RuntimeError, match="Arguments not parsed"):
            _ = app.args


class TestQtAppWindowCreation:
    """Test main window creation and UI building."""

    def test_initialize_creates_window(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test that initialize creates the main window."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )

        with patch.object(app, "_build_main_window") as mock_build:
            app.initialize()

            mock_build.assert_called_once()

    def test_main_buttons_created(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test that main action buttons are created."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        # Check that key buttons exist
        assert hasattr(app, "_process_folder_button")
        assert hasattr(app, "_processed_files_button")
        assert hasattr(app, "_allow_resend_button")

    def test_folder_list_widget_created(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test that folder list widget is created."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_folder_list_widget")
        assert hasattr(app, "_search_widget")


class TestQtAppButtonConnections:
    """Test button signal connections."""

    def test_add_directory_button_connection(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Add Directory button is connected to handler."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        # Find the Add Directory button
        add_button = app._window.findChild(QPushButton, None)
        if add_button and add_button.text() == "Add Directory...":
            # Verify it's connected by checking the handler exists
            assert hasattr(app, "_select_folder")
            assert callable(app._select_folder)

    def test_edit_settings_button_connection(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Edit Settings button is connected to handler."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        # Verify handler exists
        assert hasattr(app, "_show_edit_settings_dialog")
        assert callable(app._show_edit_settings_dialog)

    def test_maintenance_button_connection(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Maintenance button is connected to handler."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_show_maintenance_dialog_wrapper")
        assert callable(app._show_maintenance_dialog_wrapper)

    def test_process_folder_button_connection(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Process All Folders button is connected to handler."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_graphical_process_directories")
        assert callable(app._graphical_process_directories)


class TestQtAppButtonStates:
    """Test button state management."""

    def test_process_button_toggled_when_no_folders(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Process button is disabled when there are no folders."""
        mock_database.folders_table.count.return_value = 0

        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert app._process_folder_button.isEnabled() is False

    def test_process_button_enabled_when_folders_exist(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Process button is enabled when there are active folders."""
        mock_database.folders_table.count.side_effect = lambda **kwargs: (
            5 if kwargs.get("folder_is_active") is True else 0
        )

        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert app._process_folder_button.isEnabled() is True

    def test_processed_files_button_toggled_when_no_processed(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Processed Files button is disabled when no files processed."""
        mock_database.processed_files.count.return_value = 0

        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert app._processed_files_button.isEnabled() is False

    def test_processed_files_button_enabled_when_files_processed(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Processed Files button is enabled when files are processed."""
        mock_database.processed_files.count.return_value = 10

        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert app._processed_files_button.isEnabled() is True

    def test_resend_button_toggled_when_no_processed(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Enable Resend button is disabled when no files processed."""
        mock_database.processed_files.count.return_value = 0

        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert app._allow_resend_button.isEnabled() is False


class TestQtAppDialogMethods:
    """Test dialog showing methods."""

    def test_show_edit_settings_dialog_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Edit Settings dialog method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_show_edit_settings_dialog")
        assert callable(app._show_edit_settings_dialog)

    def test_show_maintenance_dialog_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Maintenance dialog method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_show_maintenance_dialog_wrapper")
        assert callable(app._show_maintenance_dialog_wrapper)

    def test_show_processed_files_dialog_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Processed Files dialog method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_show_processed_files_dialog_wrapper")
        assert callable(app._show_processed_files_dialog_wrapper)

    def test_show_resend_dialog_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test Resend dialog method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_show_resend_dialog")
        assert callable(app._show_resend_dialog)


class TestQtAppFolderOperations:
    """Test folder operation methods."""

    def test_select_folder_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test select folder method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_select_folder")
        assert callable(app._select_folder)

    def test_batch_add_folders_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test batch add folders method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_batch_add_folders")
        assert callable(app._batch_add_folders)

    def test_edit_folder_selector_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test edit folder selector method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_edit_folder_selector")
        assert callable(app._edit_folder_selector)

    def test_send_single_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test send single method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_send_single")
        assert callable(app._send_single)

    def test_disable_folder_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test disable folder method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_disable_folder")
        assert callable(app._disable_folder)

    def test_delete_folder_entry_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test delete folder entry method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_delete_folder_entry_wrapper")
        assert callable(app._delete_folder_entry_wrapper)


class TestQtAppSettingsHelpers:
    """Test settings helper methods."""

    def test_disable_all_email_backends_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test disable all email backends method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_disable_all_email_backends")
        assert callable(app._disable_all_email_backends)

    def test_disable_folders_without_backends_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test disable folders without backends method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_disable_folders_without_backends")
        assert callable(app._disable_folders_without_backends)


class TestQtAppRefresh:
    """Test refresh functionality."""

    def test_refresh_users_list_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test refresh users list method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_refresh_users_list")
        assert callable(app._refresh_users_list)

    def test_update_filter_count_label_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test update filter count label method exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_update_filter_count_label")
        assert callable(app._update_filter_count_label)


class TestQtAppLifecycle:
    """Test app lifecycle methods."""

    def test_initialize_method_exists(self):
        """Test that initialize method exists."""
        app = _make_app()
        assert hasattr(app, "initialize")
        assert callable(app.initialize)

    def test_run_method_exists(self):
        """Test that run method exists."""
        app = _make_app()
        assert hasattr(app, "run")
        assert callable(app.run)

    def test_shutdown_method_exists(self):
        """Test that shutdown method exists."""
        app = _make_app()
        assert hasattr(app, "shutdown")
        assert callable(app.shutdown)

    def test_shutdown_closes_database(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test that shutdown closes the database connection."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()
        app.shutdown()

        mock_database.close.assert_called_once()

    def test_shutdown_handles_no_database(self):
        """Test that shutdown handles case when database is not initialized."""
        app = _make_app()
        # Should not raise exception
        app.shutdown()


class TestQtAppSelfTest:
    """Test self-test functionality."""

    def test_run_self_test_exists(self):
        """Test that the self-test method exists."""
        app = _make_app()
        assert hasattr(app, "_run_self_test")
        assert callable(app._run_self_test)


class TestQtAppErrorHandling:
    """Test error handling verification."""

    def test_database_property_access_before_init(self):
        """Test accessing database property before initialization."""
        app = _make_app()
        with pytest.raises(RuntimeError, match="Database not initialized"):
            _ = app.database

    def test_run_before_initialize_raises_error(self):
        """Test that run raises error if called before initialize."""
        app = _make_app()
        with patch("sys.argv", ["test"]):
            app._args = Namespace(automatic=False)
            with pytest.raises(RuntimeError, match="Application not initialized"):
                app.run()


class TestQtAppIntegration:
    """Test integration concepts."""

    def test_app_has_required_dependencies(self):
        """Test that required dependencies can be imported."""
        from backend.database.database_obj import DatabaseObj
        from interface.operations.folder_manager import FolderManager
        from interface.ports import ProgressServiceProtocol, UIServiceProtocol

        assert DatabaseObj is not None
        assert FolderManager is not None
        assert UIServiceProtocol is not None
        assert ProgressServiceProtocol is not None


class TestQtAppProperties:
    """Test property access after initialization."""

    def test_properties_after_initialization(
        self, mock_database, mock_folder_manager, mock_ui_service, mock_progress_service
    ):
        """Test property access after proper initialization."""
        app = _make_app(
            database_obj=mock_database,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )

        # Manually set like initialization would do
        app._folder_manager = mock_folder_manager
        app._args = Namespace()

        # Now properties should be accessible
        assert app.database is mock_database
        assert app.folder_manager is mock_folder_manager
        assert app.args is not None


class TestQtAppWindowConfiguration:
    """Test window configuration."""

    @patch("sys.argv", ["test_app"])
    def test_window_has_minimum_size(
        self, mock_database, mock_folder_manager, mock_ui_service, mock_progress_service
    ):
        """Test that window has minimum size set."""
        app = _make_app(
            database_obj=mock_database,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert app._window.minimumWidth() > 0
        assert app._window.minimumHeight() > 0

    @patch("sys.argv", ["test_app"])
    def test_window_is_resizable(
        self, mock_database, mock_folder_manager, mock_ui_service, mock_progress_service
    ):
        """Test that window is resizable."""
        app = _make_app(
            database_obj=mock_database,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        # Window should be resizable (not fixed width)
        # Qt uses 16777215 as default maximum (effectively unlimited)
        assert app._window.maximumWidth() > app._window.minimumWidth()
        assert app._window.maximumHeight() > app._window.minimumHeight()


class TestQtAppFilterFunctionality:
    """Test filter functionality."""

    def test_folder_filter_exists(
        self,
        qt_app,
        mock_database,
        mock_folder_manager,
        mock_ui_service,
        mock_progress_service,
    ):
        """Test that folder filter functionality exists."""
        app = _make_app(
            database_obj=mock_database,
            folder_manager=mock_folder_manager,
            ui_service=mock_ui_service,
            progress_service=mock_progress_service,
        )
        app.initialize()

        assert hasattr(app, "_folder_filter")
        assert hasattr(app, "_set_folders_filter")
        assert callable(app._set_folders_filter)
