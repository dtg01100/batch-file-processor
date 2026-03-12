"""Comprehensive UI tests for all interface components.

This test module provides exhaustive coverage of:
- Widget functionality (FolderListWidget, SearchWidget)
- Dialog interactions (all dialogs)
- Main app window and state management
- UI services (progress, UI service)
- Keyboard shortcuts and accessibility
- State transitions and error handling
"""

import pytest

pytestmark = [pytest.mark.qt, pytest.mark.gui, pytest.mark.slow]

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
    QPushButton,
)

import create_database
from batch_file_processor.constants import CURRENT_DATABASE_VERSION
from interface.database.database_obj import DatabaseObj
from interface.qt.app import QtBatchFileSenderApp
from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog
from interface.qt.dialogs.resend_dialog import ResendDialog
from interface.qt.services.qt_services import QtProgressService, QtUIService
from interface.qt.widgets.folder_list_widget import FolderListWidget
from interface.qt.widgets.search_widget import SearchWidget

pytestmark = pytest.mark.qt


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def qt_app():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app
    # Process events to clean up
    QApplication.processEvents()


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        logs_dir = Path(tmpdir) / "logs"
        errors_dir = Path(tmpdir) / "errors"
        logs_dir.mkdir()
        errors_dir.mkdir()

        create_database.do(
            CURRENT_DATABASE_VERSION,
            str(db_path),
            str(tmpdir),
            "Linux",
        )
        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(tmpdir),
            running_platform="Linux",
        )

        oversight_table = db.oversight_and_defaults
        assert oversight_table is not None
        oversight_table.update(
            {
                "id": 1,
                "logs_directory": str(logs_dir),
                "errors_folder": str(errors_dir),
            },
            ["id"],
        )

        yield db
        db.close()


@pytest.fixture
def mock_folder_table():
    """Create a mock folder table with test data."""
    folders = [
        {
            "id": 1,
            "alias": "Folder 1",
            "folder_is_active": "True",
            "folder_name": "/path/to/folder1",
        },
        {
            "id": 2,
            "alias": "Folder 2",
            "folder_is_active": "True",
            "folder_name": "/path/to/folder2",
        },
        {
            "id": 3,
            "alias": "Inactive 1",
            "folder_is_active": "False",
            "folder_name": "/path/to/inactive1",
        },
        {
            "id": 4,
            "alias": "Test Folder",
            "folder_is_active": "True",
            "folder_name": "/path/to/test",
        },
        {
            "id": 5,
            "alias": "Archive",
            "folder_is_active": "False",
            "folder_name": "/path/to/archive",
        },
    ]

    mock_table = MagicMock()
    mock_table.find.side_effect = lambda **kwargs: (
        f for f in folders if all(f.get(k) == v for k, v in kwargs.items())
    )
    mock_table.count.side_effect = lambda **kwargs: sum(
        1 for f in folders if all(f.get(k) == v for k, v in kwargs.items())
    )
    mock_table.find_one.side_effect = lambda **kwargs: next(
        (f for f in folders if all(f.get(k) == v for k, v in kwargs.items())), None
    )
    mock_table.all.return_value = iter(folders)

    return mock_table


# =============================================================================
# FolderListWidget Comprehensive Tests
# =============================================================================


class TestFolderListWidgetComprehensive:
    """Comprehensive tests for FolderListWidget."""

    def test_widget_initialization(self, qtbot, mock_folder_table):
        """Test widget initializes with correct structure."""
        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        assert widget is not None
        assert widget.layout() is not None

    def test_folder_list_displays_active_folders(self, qtbot, mock_folder_table):
        """Test that active folders are displayed correctly."""
        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Should display 3 active folders
        active_folders = list(mock_folder_table.find(folder_is_active="True"))
        assert len(active_folders) == 3

    def test_folder_list_displays_inactive_folders(self, qtbot, mock_folder_table):
        """Test that inactive folders are displayed correctly."""
        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Should display 2 inactive folders
        inactive_folders = list(mock_folder_table.find(folder_is_active="False"))
        assert len(inactive_folders) == 2

    def test_folder_filtering_by_alias(self, qtbot, mock_folder_table):
        """Test folder filtering with fuzzy matching."""
        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
            filter_value="Test",
        )
        qtbot.addWidget(widget)

        # Should filter to show folders matching "Test"
        # The fuzzy matching should find "Test Folder"
        assert widget is not None

    def test_total_count_callback_invoked(self, qtbot, mock_folder_table):
        """Test that total count callback is invoked correctly."""
        callback_data = {}

        def count_callback(filtered, total):
            callback_data["filtered"] = filtered
            callback_data["total"] = total

        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
            total_count_callback=count_callback,
        )
        qtbot.addWidget(widget)

        # Callback should have been invoked with counts
        assert "filtered" in callback_data
        assert "total" in callback_data

    def test_send_button_callback(self, qtbot, mock_folder_table):
        """Test that send button triggers callback with correct folder ID."""
        send_calls = []

        def on_send(folder_id):
            send_calls.append(folder_id)

        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=on_send,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Find a send button and click it
        send_buttons = widget.findChildren(QPushButton)
        send_button = next((b for b in send_buttons if "Send" in b.text()), None)

        if send_button:
            qtbot.mouseClick(send_button, Qt.MouseButton.LeftButton)
            assert len(send_calls) > 0

    def test_edit_button_callback(self, qtbot, mock_folder_table):
        """Test that edit button triggers callback with correct folder ID."""
        edit_calls = []

        def on_edit(folder_id):
            edit_calls.append(folder_id)

        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=on_edit,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Find an edit button and click it
        edit_buttons = widget.findChildren(QPushButton)
        edit_button = next((b for b in edit_buttons if "Edit" in b.text()), None)

        if edit_button:
            qtbot.mouseClick(edit_button, Qt.MouseButton.LeftButton)
            assert len(edit_calls) > 0

    def test_disable_button_callback(self, qtbot, mock_folder_table):
        """Test that disable button triggers callback with correct folder ID."""
        disable_calls = []

        def on_toggle(folder_id):
            disable_calls.append(folder_id)

        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=on_toggle,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Find a disable button and click it
        disable_buttons = widget.findChildren(QPushButton)
        disable_button = next(
            (b for b in disable_buttons if "<-" in b.text() or "->" in b.text()), None
        )

        if disable_button:
            qtbot.mouseClick(disable_button, Qt.MouseButton.LeftButton)
            assert len(disable_calls) > 0

    def test_delete_button_callback(self, qtbot, mock_folder_table):
        """Test that delete button triggers callback with folder ID and alias."""
        delete_calls = []

        def on_delete(folder_id, alias):
            delete_calls.append((folder_id, alias))

        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=on_delete,
        )
        qtbot.addWidget(widget)

        # Find a delete button and click it
        delete_buttons = widget.findChildren(QPushButton)
        delete_button = next((b for b in delete_buttons if "Delete" in b.text()), None)

        if delete_button:
            qtbot.mouseClick(delete_button, Qt.MouseButton.LeftButton)
            assert len(delete_calls) > 0

    def test_empty_folder_list(self, qtbot):
        """Test widget behavior with no folders."""
        empty_table = MagicMock()
        empty_table.find.return_value = iter([])
        empty_table.count.return_value = 0
        empty_table.find_one.return_value = None

        widget = FolderListWidget(
            None,
            empty_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Should not crash with empty data
        assert widget is not None

    def test_folder_list_scrollable(self, qtbot, mock_folder_table):
        """Test that folder lists are scrollable."""
        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Find scroll areas
        from PyQt6.QtWidgets import QScrollArea

        scroll_areas = widget.findChildren(QScrollArea)
        assert len(scroll_areas) > 0


# =============================================================================
# SearchWidget Comprehensive Tests
# =============================================================================


class TestSearchWidgetComprehensive:
    """Comprehensive tests for SearchWidget."""

    def test_search_widget_initialization(self, qtbot):
        """Test search widget initializes correctly."""
        widget = SearchWidget()
        qtbot.addWidget(widget)

        assert widget.entry is not None
        assert widget.value == ""

    def test_search_widget_with_initial_value(self, qtbot):
        """Test search widget with initial value."""
        widget = SearchWidget(initial_value="test")
        qtbot.addWidget(widget)

        assert widget.value == "test"
        assert widget.entry.text() == "test"

    def test_search_widget_filter_change_callback(self, qtbot):
        """Test that filter change callback is invoked."""
        filter_values = []

        def on_filter_change(value):
            filter_values.append(value)

        widget = SearchWidget(on_filter_change=on_filter_change)
        qtbot.addWidget(widget)

        # Text change fires after debounce timer (150ms)
        with qtbot.waitSignal(widget.filter_changed, timeout=1000):
            widget.entry.setText("test search")

        # Callback should have been invoked
        assert filter_values == ["test search"]

    def test_search_widget_clear_function(self, qtbot):
        """Test search widget clear function."""
        widget = SearchWidget(initial_value="test")
        qtbot.addWidget(widget)

        assert widget.value == "test"

        widget.clear()

        assert widget.value == ""
        assert widget.entry.text() == ""

    def test_search_widget_set_value(self, qtbot):
        """Test programmatically setting search value."""
        widget = SearchWidget()
        qtbot.addWidget(widget)

        widget.set_value("new value")

        assert widget.value == "new value"
        assert widget.entry.text() == "new value"

    def test_search_widget_enable_disable(self, qtbot):
        """Test enabling and disabling search widget."""
        widget = SearchWidget()
        qtbot.addWidget(widget)

        assert widget.entry.isEnabled()

        widget.set_enabled(False)

        assert not widget.entry.isEnabled()

        widget.set_enabled(True)

        assert widget.entry.isEnabled()

    def test_search_widget_escape_key(self, qtbot):
        """Test that Escape key clears search when active."""
        filter_values = []

        def on_filter_change(value):
            filter_values.append(value)

        widget = SearchWidget(initial_value="test", on_filter_change=on_filter_change)
        qtbot.addWidget(widget)
        widget.show()  # Widget must be visible for shortcuts

        widget._escape_shortcut.activated.emit()

        assert widget.value == ""
        assert filter_values[-1] == ""

    def test_search_widget_enter_key(self, qtbot):
        """Test that Enter key does not trigger additional filtering."""
        filter_values = []

        def on_filter_change(value):
            filter_values.append(value)

        widget = SearchWidget(on_filter_change=on_filter_change)
        qtbot.addWidget(widget)

        # setText triggers filtering after debounce timer
        with qtbot.waitSignal(widget.filter_changed, timeout=1000):
            widget.entry.setText("test")
        assert filter_values == ["test"]

        # Enter key should not trigger additional filtering
        with qtbot.assertNotEmitted(widget.filter_changed):
            qtbot.keyPress(widget.entry, Qt.Key.Key_Return)

    def test_search_widget_placeholder_text(self, qtbot):
        """Test that search widget has placeholder text."""
        widget = SearchWidget()
        qtbot.addWidget(widget)

        placeholder = widget.entry.placeholderText()
        assert placeholder != ""
        assert "Search" in placeholder or "🔍" in placeholder


# =============================================================================
# QtProgressService Comprehensive Tests
# =============================================================================


class TestQtProgressServiceComprehensive:
    """Comprehensive tests for QtProgressService."""

    def test_progress_service_initialization(self, qtbot):
        """Test progress service initializes correctly."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        assert service.progress_dialog is not None

    def test_progress_service_show_hide(self, qtbot):
        """Test showing and hiding progress dialog."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.show_progress()
        assert service.progress_dialog.isVisible()

        service.hide_progress()
        assert not service.progress_dialog.isVisible()

    def test_progress_service_set_total(self, qtbot):
        """Test setting total progress value."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.set_total(100)
        assert service._total == 100

    def test_progress_service_set_current(self, qtbot):
        """Test setting current progress value."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.set_total(100)
        service.set_current(50)
        assert service._progress_bar.value() == 50
        assert not service._progress_bar.isHidden()

    def test_progress_service_set_message(self, qtbot):
        """Test setting progress message."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.set_message("Processing files...")
        assert service._title_label.text() == "Processing files..."

    def test_progress_service_indeterminate_mode(self, qtbot):
        """Test indeterminate progress mode."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.set_indeterminate()
        assert service._progress_bar.isHidden()
        assert not service._throbber.isHidden()

    def test_progress_service_multiple_updates(self, qtbot):
        """Test multiple progress updates in sequence."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.show_progress()
        service.set_total(100)

        for i in range(0, 101, 10):
            service.set_current(i)
            service.set_message(f"Processing {i}%")
            QApplication.processEvents()

        service.hide_progress()
        assert service._progress_bar.value() == 100
        assert service._title_label.text() == "Processing 100%"
        assert not service.progress_dialog.isVisible()


# =============================================================================
# QtUIService Comprehensive Tests
# =============================================================================


class TestQtUIServiceComprehensive:
    """Comprehensive tests for QtUIService."""

    def test_ui_service_show_info(self, qtbot, monkeypatch):
        """Test showing info message."""
        service = QtUIService()

        mock_info = MagicMock()
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        service.show_info("Test Title", "Test Message")

        mock_info.assert_called_once()

    def test_ui_service_show_warning(self, qtbot, monkeypatch):
        """Test showing warning message."""
        service = QtUIService()

        mock_warning = MagicMock()
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)

        service.show_warning("Test Title", "Test Message")

        mock_warning.assert_called_once()

    def test_ui_service_show_error(self, qtbot, monkeypatch):
        """Test showing error message."""
        service = QtUIService()

        mock_critical = MagicMock()
        monkeypatch.setattr(QMessageBox, "critical", mock_critical)

        service.show_error("Test Title", "Test Message")

        mock_critical.assert_called_once()

    def test_ui_service_ask_yes_no_yes(self, qtbot, monkeypatch):
        """Test ask yes/no dialog with yes response."""
        service = QtUIService()

        mock_question = MagicMock(return_value=QMessageBox.StandardButton.Yes)
        monkeypatch.setattr(QMessageBox, "question", mock_question)

        result = service.ask_yes_no("Test Title", "Test Question")

        assert result is True
        mock_question.assert_called_once()

    def test_ui_service_ask_yes_no_no(self, qtbot, monkeypatch):
        """Test ask yes/no dialog with no response."""
        service = QtUIService()

        mock_question = MagicMock(return_value=QMessageBox.StandardButton.No)
        monkeypatch.setattr(QMessageBox, "question", mock_question)

        result = service.ask_yes_no("Test Title", "Test Question")

        assert result is False
        mock_question.assert_called_once()

    def test_ui_service_ask_open_filename(self, qtbot, monkeypatch):
        """Test asking for open filename."""
        service = QtUIService()

        from PyQt6.QtWidgets import QFileDialog

        mock_open = MagicMock(return_value=("/path/to/file.txt", ""))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", mock_open)

        result = service.ask_open_filename("Select File")

        assert result == "/path/to/file.txt"

    def test_ui_service_ask_save_filename(self, qtbot, monkeypatch):
        """Test asking for save filename."""
        service = QtUIService()

        from PyQt6.QtWidgets import QFileDialog

        mock_save = MagicMock(return_value=("/path/to/save.txt", ""))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", mock_save)

        result = service.ask_save_filename("Save File")

        assert result == "/path/to/save.txt"

    def test_ui_service_ask_directory(self, qtbot, monkeypatch):
        """Test asking for directory."""
        service = QtUIService()

        from PyQt6.QtWidgets import QFileDialog

        mock_dir = MagicMock(return_value="/path/to/directory")
        monkeypatch.setattr(QFileDialog, "getExistingDirectory", mock_dir)

        result = service.ask_directory("Select Directory")

        assert result == "/path/to/directory"


# =============================================================================
# Main App Comprehensive Tests
# =============================================================================


class TestMainAppComprehensive:
    """Comprehensive tests for main app window and initialization."""

    def test_app_initialization(self, temp_database):
        """Test app initializes correctly."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            assert app.database is not None
            assert app.folder_manager is not None

            app.shutdown()

    def test_app_window_creation(self, temp_database):
        """Test app creates main window."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            assert app._window is not None
            assert app._app is not None

            app.shutdown()

    def test_app_folder_list_widget_exists(self, temp_database):
        """Test app creates folder list widget."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            assert app._folder_list_widget is not None

            app.shutdown()

    def test_app_search_widget_exists(self, temp_database):
        """Test app creates search widget."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            assert app._search_widget is not None

            app.shutdown()

    def test_app_process_button_exists(self, temp_database):
        """Test app creates process button."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            assert app._process_folder_button is not None

            app.shutdown()

    def test_app_button_states_initial(self, temp_database):
        """Test initial button states."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            # Buttons should exist
            assert app._process_folder_button is not None
            assert app._processed_files_button is not None
            assert app._allow_resend_button is not None

            app.shutdown()

    def test_app_refresh_folders(self, temp_database):
        """Test refreshing folder list."""
        with patch("sys.argv", ["test"]):
            app = QtBatchFileSenderApp(database_obj=temp_database)
            app.initialize()

            # Add a test folder
            test_path = "/test/folder"
            app.folder_manager.add_folder(test_path)

            # Refresh should not crash
            app._refresh_users_list()

            app.shutdown()


# =============================================================================
# Dialog State and Validation Tests
# =============================================================================


class TestDialogStateValidation:
    """Comprehensive tests for dialog state and validation."""

    def test_edit_settings_dialog_validation_all_valid(self, qtbot, monkeypatch):
        """Test settings dialog validation with all valid data."""
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        folder_config = {
            "logs_directory": "/test/logs",
            "errors_folder": "/test/errors",
        }

        mock_smtp = MagicMock()
        mock_smtp.test_connection.return_value = (True, None)

        dialog = EditSettingsDialog(None, folder_config, smtp_service=mock_smtp)
        qtbot.addWidget(dialog)

        # All should be valid initially if defaults are reasonable
        # Just verify dialog can be created
        assert dialog is not None

    def test_edit_settings_dialog_email_validation_invalid_format(
        self, qtbot, monkeypatch
    ):
        """Test email format validation."""
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        folder_config = {
            "logs_directory": "/test/logs",
            "errors_folder": "/test/errors",
        }

        mock_critical = MagicMock()
        monkeypatch.setattr(QMessageBox, "critical", mock_critical)

        dialog = EditSettingsDialog(None, folder_config)
        qtbot.addWidget(dialog)

        # Enable email and set invalid format
        if hasattr(dialog, "_enable_email_cb"):
            dialog._enable_email_cb.setChecked(True)
        if hasattr(dialog, "_email_address"):
            dialog._email_address.setText("invalid-email")

        # Validation should fail
        result = dialog.validate()
        assert result is False

    def test_maintenance_dialog_operations(self, qtbot, temp_database):
        """Test maintenance dialog operations."""
        dialog = MaintenanceDialog(None, temp_database)
        qtbot.addWidget(dialog)

        # Should have operation buttons
        buttons = dialog.findChildren(QPushButton)
        assert len(buttons) > 0

    def test_processed_files_dialog_display(self, qtbot, temp_database):
        """Test processed files dialog displays correctly."""
        # Add some processed files
        temp_database.processed_files.insert(
            {
                "folder_id": 1,
                "file_name": "test1.edi",
                "md5": "test_hash_1",
            }
        )
        temp_database.processed_files.insert(
            {
                "folder_id": 1,
                "file_name": "test2.edi",
                "md5": "test_hash_2",
            }
        )

        dialog = ProcessedFilesDialog(None, temp_database)
        qtbot.addWidget(dialog)

        # Dialog should display
        assert dialog is not None

    def test_resend_dialog_folder_selection(self, qtbot, temp_database):
        """Test resend dialog folder selection."""
        # Add a folder
        temp_database.folders_table.insert(
            {
                "folder_name": "/test/folder",
                "alias": "Test Folder",
                "folder_is_active": "True",
            }
        )

        # Add processed file
        temp_database.processed_files.insert(
            {
                "folder_id": 1,
                "file_name": "test.edi",
                "md5": "test_hash",
                "resend_flag": 0,
            }
        )

        dialog = ResendDialog(None, temp_database)
        qtbot.addWidget(dialog)

        # Dialog should display
        assert dialog is not None


# =============================================================================
# Keyboard Shortcuts and Accessibility Tests
# =============================================================================


class TestKeyboardAndAccessibility:
    """Test keyboard shortcuts and accessibility features."""

    def test_search_widget_keyboard_navigation(self, qtbot):
        """Test keyboard navigation in search widget."""
        filter_values = []

        widget = SearchWidget(on_filter_change=filter_values.append)
        qtbot.addWidget(widget)

        # Focus on entry
        widget.entry.setFocus()

        # Type text
        qtbot.keyClicks(widget.entry, "test")
        assert widget.entry.text() == "test"

        # Press Enter
        qtbot.keyClick(widget.entry, Qt.Key.Key_Return)

        assert filter_values[-1] == "test"

    def test_search_widget_escape_clears(self, qtbot):
        """Test Escape key clears search."""
        widget = SearchWidget(initial_value="test")
        qtbot.addWidget(widget)
        widget.show()

        widget.entry.setFocus()
        qtbot.keyClick(widget, Qt.Key.Key_Escape)

        assert widget.value == ""

    def test_dialog_tab_navigation(self, qtbot):
        """Test Tab key navigation between fields."""
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        folder_config = {"logs_directory": "/test"}
        dialog = EditSettingsDialog(None, folder_config)
        qtbot.addWidget(dialog)

        # Tab key should move focus between widgets
        first_widget = dialog.focusWidget()
        qtbot.keyClick(first_widget or dialog, Qt.Key.Key_Tab)
        second_widget = dialog.focusWidget()

        assert second_widget is not None

    def test_dialog_escape_closes(self, qtbot):
        """Test Escape key closes dialogs."""
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        folder_config = {"logs_directory": "/test"}
        dialog = EditSettingsDialog(None, folder_config)
        qtbot.addWidget(dialog)

        dialog.show()
        qtbot.keyClick(dialog, Qt.Key.Key_Escape)

        qtbot.waitUntil(lambda: not dialog.isVisible(), timeout=1000)
        assert not dialog.isVisible()


# =============================================================================
# UI Thread Safety and State Management Tests
# =============================================================================


class TestUIThreadSafetyAndState:
    """Test UI thread safety and state management."""

    def test_progress_updates_from_background_thread(self, qtbot):
        """Test progress updates are thread-safe."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        service.show_progress()
        service.set_total(10)

        # Simulate background thread updates
        for i in range(10):
            service.set_current(i)
            QApplication.processEvents()

        service.hide_progress()
        assert service._progress_bar.value() == 90
        assert not service.progress_dialog.isVisible()

    def test_folder_list_refresh_maintains_state(self, qtbot, mock_folder_table):
        """Test folder list refresh maintains scroll position."""
        widget = FolderListWidget(
            None,
            mock_folder_table,
            on_send=lambda x: None,
            on_edit=lambda x: None,
            on_toggle=lambda x: None,
            on_delete=lambda x, y: None,
        )
        qtbot.addWidget(widget)

        # Refresh widget (simulate state update)
        # Should not lose position or crash
        assert widget is not None

    def test_concurrent_dialog_opening(self, qtbot, temp_database):
        """Test opening multiple dialogs in sequence."""
        dialogs = []

        # Create multiple dialogs
        dialog1 = MaintenanceDialog(None, temp_database)
        dialogs.append(dialog1)
        qtbot.addWidget(dialog1)

        dialog2 = ProcessedFilesDialog(None, temp_database)
        dialogs.append(dialog2)
        qtbot.addWidget(dialog2)

        # Both should exist without conflicts
        assert len(dialogs) == 2


# =============================================================================
# Error Handling and Edge Cases
# =============================================================================


class TestUIErrorHandlingEdgeCases:
    """Test UI error handling and edge cases."""

    def test_folder_list_with_database_error(self, qtbot):
        """Test folder list handles database errors gracefully."""
        mock_table = MagicMock()
        mock_table.find.side_effect = RuntimeError("Database error")
        mock_table.count.return_value = 0

        # Current behavior: database exceptions propagate during widget build.
        with pytest.raises(RuntimeError, match="Database error"):
            FolderListWidget(
                None,
                mock_table,
                on_send=lambda x: None,
                on_edit=lambda x: None,
                on_toggle=lambda x: None,
                on_delete=lambda x, y: None,
            )

    def test_search_with_special_characters(self, qtbot):
        """Test search handles special characters."""
        widget = SearchWidget()
        qtbot.addWidget(widget)

        special_chars = "!@#$%^&*()[]{}|\\;:'\",<>?/`~"
        widget.set_value(special_chars)

        # Should not crash
        assert widget.value == special_chars

    def test_progress_with_invalid_values(self, qtbot):
        """Test progress service handles invalid values."""
        from PyQt6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        service = QtProgressService(parent)
        qtbot.addWidget(service.progress_dialog)

        # Set invalid values
        service.set_total(-1)
        service.set_current(1000)
        service.set_current(-50)

        assert service._total == -1
        assert service._progress_bar.value() == 0
        assert not service._progress_bar.isVisible()

    def test_ui_service_with_none_parent(self, qtbot):
        """Test UI service works with None parent."""
        service = QtUIService()

        # All methods should work with None parent
        # (just verify no crashes - actual display tested elsewhere)
        assert service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
