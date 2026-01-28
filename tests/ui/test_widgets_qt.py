"""
Tests for UI Widgets using actual PyQt6 widgets
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.qt
class TestButtonPanelQt:
    """Test ButtonPanel with actual Qt widgets."""

    def test_create_button_panel(self, qtbot):
        """Test ButtonPanel can be created."""
        from interface.ui.widgets.button_panel import ButtonPanel

        panel = ButtonPanel()
        qtbot.addWidget(panel)

        assert panel is not None
        assert panel.isVisible() == False  # Not shown yet

    def test_button_panel_has_buttons(self, qtbot):
        """Test ButtonPanel creates all buttons."""
        from interface.ui.widgets.button_panel import ButtonPanel

        panel = ButtonPanel()
        qtbot.addWidget(panel)

        # Check buttons exist
        assert hasattr(panel, "_add_folder_btn")
        assert hasattr(panel, "_batch_add_btn")
        assert hasattr(panel, "_settings_btn")
        assert hasattr(panel, "_process_btn")
        assert hasattr(panel, "_maintenance_btn")
        assert hasattr(panel, "_processed_files_btn")
        assert hasattr(panel, "_exit_btn")

    def test_button_panel_signals_emit(self, qtbot):
        """Test ButtonPanel signals can be connected and emit."""
        from interface.ui.widgets.button_panel import ButtonPanel

        panel = ButtonPanel()
        qtbot.addWidget(panel)

        # Test process signal
        with qtbot.waitSignal(panel.process_clicked, timeout=1000):
            panel._process_btn.click()

    def test_set_button_enabled(self, qtbot):
        """Test set_button_enabled changes button state."""
        from interface.ui.widgets.button_panel import ButtonPanel

        panel = ButtonPanel()
        qtbot.addWidget(panel)

        # Initially enabled
        assert panel._process_btn.isEnabled()

        # Disable
        panel.set_button_enabled("process", False)
        assert not panel._process_btn.isEnabled()

        # Enable again
        panel.set_button_enabled("process", True)
        assert panel._process_btn.isEnabled()

    def test_set_process_enabled(self, qtbot):
        """Test set_process_enabled controls process button."""
        from interface.ui.widgets.button_panel import ButtonPanel

        panel = ButtonPanel()
        qtbot.addWidget(panel)

        # No folders, no active
        panel.set_process_enabled(enabled=False, has_active_folders=False)
        assert not panel._process_btn.isEnabled()

        # Has folders and active
        panel.set_process_enabled(enabled=True, has_active_folders=True)
        assert panel._process_btn.isEnabled()


@pytest.mark.qt
class TestFolderListWidgetQt:
    """Test FolderListWidget with actual Qt widgets."""

    def test_create_folder_list(self, qtbot, mock_db_manager):
        """Test FolderListWidget can be created."""
        from interface.ui.widgets.folder_list import FolderListWidget

        widget = FolderListWidget(db_manager=mock_db_manager)
        qtbot.addWidget(widget)

        assert widget is not None

    def test_folder_list_has_components(self, qtbot, mock_db_manager):
        """Test FolderListWidget creates all UI components."""
        from interface.ui.widgets.folder_list import FolderListWidget

        widget = FolderListWidget(db_manager=mock_db_manager)
        qtbot.addWidget(widget)

        # Check components exist
        assert hasattr(widget, "_filter_field")
        assert hasattr(widget, "_active_list")
        assert hasattr(widget, "_inactive_list")
        assert hasattr(widget, "_count_label")

    def test_folder_list_refresh(self, qtbot, mock_db_manager, sample_folders):
        """Test refresh updates folder display."""
        from interface.ui.widgets.folder_list import FolderListWidget

        mock_db_manager.folders_table.find.return_value = sample_folders

        widget = FolderListWidget(db_manager=mock_db_manager)
        qtbot.addWidget(widget)

        widget.refresh()

        # Should have items in lists
        assert widget._active_list.count() > 0 or widget._inactive_list.count() > 0

    def test_folder_list_set_filter(self, qtbot, mock_db_manager, sample_folders):
        """Test set_filter updates filter field."""
        from interface.ui.widgets.folder_list import FolderListWidget

        mock_db_manager.folders_table.find.return_value = sample_folders

        widget = FolderListWidget(db_manager=mock_db_manager)
        qtbot.addWidget(widget)

        widget.set_filter("test")

        assert widget._filter_field.text() == "test"

    def test_folder_list_signals_exist(self, qtbot, mock_db_manager):
        """Test FolderListWidget has all required signals."""
        from interface.ui.widgets.folder_list import FolderListWidget

        widget = FolderListWidget(db_manager=mock_db_manager)
        qtbot.addWidget(widget)

        # Check signals exist
        assert hasattr(widget, "folder_edit_requested")
        assert hasattr(widget, "folder_toggle_active")
        assert hasattr(widget, "folder_delete_requested")
        assert hasattr(widget, "folder_send_requested")


@pytest.mark.qt
class TestMainWindowQt:
    """Test MainWindow with actual Qt widgets."""

    def test_create_main_window(self, qtbot, mock_db_manager, qapp):
        """Test MainWindow can be created."""
        from interface.ui.main_window import MainWindow

        window = MainWindow(db_manager=mock_db_manager, app=qapp)
        qtbot.addWidget(window)

        assert window is not None
        assert window.windowTitle() == "Batch File Processor"

    def test_main_window_has_components(self, qtbot, mock_db_manager, qapp):
        """Test MainWindow creates all UI components."""
        from interface.ui.main_window import MainWindow

        window = MainWindow(db_manager=mock_db_manager, app=qapp)
        qtbot.addWidget(window)

        # Check components exist
        assert hasattr(window, "_button_panel")
        assert hasattr(window, "_folder_list")
        assert hasattr(window, "_folder_splitter")

    def test_main_window_signals_exist(self, qtbot, mock_db_manager, qapp):
        """Test MainWindow has all required signals."""
        from interface.ui.main_window import MainWindow

        window = MainWindow(db_manager=mock_db_manager, app=qapp)
        qtbot.addWidget(window)

        # Check signals exist
        assert hasattr(window, "process_directories_requested")
        assert hasattr(window, "add_folder_requested")
        assert hasattr(window, "batch_add_folders_requested")
        assert hasattr(window, "edit_settings_requested")
        assert hasattr(window, "maintenance_requested")
        assert hasattr(window, "processed_files_requested")
        assert hasattr(window, "exit_requested")
        assert hasattr(window, "edit_folder_requested")
        assert hasattr(window, "toggle_active_requested")
        assert hasattr(window, "delete_folder_requested")
        assert hasattr(window, "send_folder_requested")

    def test_main_window_refresh_folder_list(self, qtbot, mock_db_manager, qapp):
        """Test refresh_folder_list method works."""
        from interface.ui.main_window import MainWindow

        window = MainWindow(db_manager=mock_db_manager, app=qapp)
        qtbot.addWidget(window)

        # Should not raise exception
        window.refresh_folder_list()


# Non-Qt tests for logic without requiring Qt
class TestFolderListWidgetLogic:
    """Test FolderListWidget filtering logic without Qt."""

    def test_load_folders_separates_active_inactive(
        self, mock_db_manager, sample_folders
    ):
        """Test _load_folders separates active and inactive folders."""
        from interface.ui.widgets.folder_list import FolderListWidget
        from unittest.mock import Mock

        mock_db_manager.folders_table.find.return_value = sample_folders

        # Create partial mock to test the method
        widget = Mock(spec=FolderListWidget)
        widget._db_manager = mock_db_manager

        # Call the actual method
        all_folders, active, inactive = FolderListWidget._load_folders(widget)

        assert len(all_folders) == 3
        assert len(active) == 2  # Folders 1 and 3 are active
        assert len(inactive) == 1  # Folder 2 is inactive
        assert active[0]["alias"] == "Test Folder 1"
        assert inactive[0]["alias"] == "Test Folder 2"
