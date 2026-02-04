"""
Tests to ensure that button clicks cannot crash the program.
These tests verify that all button interactions are resilient to crashes.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Import Qt components for UI testing
from PyQt6.QtCore import Qt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestButtonPanelResilience:
    """Test that ButtonPanel buttons don't crash the application."""

    def test_all_button_clicks_dont_crash(self, qtbot):
        """Test that clicking each button in ButtonPanel doesn't crash."""
        from interface.ui.widgets.button_panel import ButtonPanel
        from PyQt6.QtWidgets import QApplication
        
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create button panel
        panel = ButtonPanel()
        qtbot.addWidget(panel)
        
        # Connect each signal to a safe function to catch emissions
        def safe_emit(*args, **kwargs):
            pass  # Do nothing, just don't crash
        
        panel.add_folder_clicked.connect(safe_emit)
        panel.batch_add_clicked.connect(safe_emit)
        panel.set_defaults_clicked.connect(safe_emit)
        panel.process_clicked.connect(safe_emit)
        panel.edit_settings_clicked.connect(safe_emit)
        panel.maintenance_clicked.connect(safe_emit)
        panel.processed_files_clicked.connect(safe_emit)
        panel.enable_resend_clicked.connect(safe_emit)
        
        # Simulate clicks on all buttons - none should raise exceptions
        panel._add_folder_btn.click()
        panel._batch_add_btn.click()
        panel._set_defaults_btn.click()
        panel._process_btn.click()
        panel._settings_btn.click()
        panel._maintenance_btn.click()
        panel._processed_files_btn.click()
        panel._enable_resend_btn.click()
        
        # Clean up
        panel.deleteLater()


class TestEditFolderDialogButtonResilience:
    """Test that EditFolderDialog buttons don't crash the application."""

    def test_show_folder_path_button_doesnt_crash(self, qtbot):
        """Test that clicking 'Show Folder Path' button doesn't crash."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog
        from PyQt6.QtWidgets import QApplication
        
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create dialog with minimal data
        dialog = EditFolderDialog(
            folder_data={"folder_name": "/test/path", "alias": "Test Folder"},
            db_manager=Mock()
        )
        qtbot.addWidget(dialog)
        
        # Mock QMessageBox to prevent actual dialog from appearing
        with patch('interface.ui.dialogs.edit_folder_dialog.QMessageBox.information'):
            # Click the 'Show Folder Path' button - should not crash
            dialog._show_folder_path()
        
        # Test that the button click handler works
        dialog._alias_field.setText("New Alias")
        dialog._active_check.setChecked(True)
        
        # Clean up
        dialog.deleteLater()

    def test_dialog_buttons_dont_crash(self, qtbot):
        """Test that OK/Cancel buttons in dialog don't crash."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog
        from PyQt6.QtWidgets import QApplication
        
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create dialog
        dialog = EditFolderDialog(
            folder_data={"folder_name": "/test/path", "alias": "Test Folder"},
            db_manager=Mock()
        )
        qtbot.addWidget(dialog)
        
        # Mock validation and apply methods to control behavior
        with patch.object(dialog, 'validate', return_value=(True, "")), \
             patch.object(dialog, 'apply'):
            # Try to accept the dialog - should not crash
            dialog.accept()
        
        # Try to reject the dialog - should not crash
        dialog.reject()
        
        # Clean up
        dialog.deleteLater()


class TestMainWindowButtonResilience:
    """Test that MainWindow button connections don't crash."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db = Mock()
        db.oversight_and_defaults = Mock()
        db.folders_table = Mock()
        db.processed_files = Mock()
        db.session_database = Mock()
        return db

    @pytest.fixture
    def mock_main_window(self, mock_db_manager):
        """Create a mock main window with real button panel."""
        from interface.ui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
        
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create real main window with mocked db
        window = MainWindow(db_manager=mock_db_manager)
        return window

    def test_main_window_button_signal_connections_dont_crash(self, mock_main_window):
        """Test that connecting button panel signals to main window doesn't crash."""
        window = mock_main_window
        
        # Trigger all button panel signals - should not crash
        # These simulate what happens when buttons are clicked
        try:
            window._button_panel.process_clicked.emit()
            window._button_panel.add_folder_clicked.emit()
            window._button_panel.batch_add_clicked.emit()
            window._button_panel.set_defaults_clicked.emit()
            window._button_panel.edit_settings_clicked.emit()
            window._button_panel.maintenance_clicked.emit()
            window._button_panel.processed_files_clicked.emit()
            window._button_panel.enable_resend_clicked.emit()
        except Exception:
            # If any exception occurs, the test should fail
            raise


class TestApplicationControllerButtonResilience:
    """Test that ApplicationController button handlers don't crash."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db = Mock()
        # Mock oversight_and_defaults to return realistic values
        mock_oversight = Mock()
        mock_oversight.find_one.return_value = {"single_add_folder_prior": "/home/user", "batch_add_folder_prior": "/home/user"}
        db.oversight_and_defaults = mock_oversight
        db.folders_table = Mock()
        db.processed_files = Mock()
        db.session_database = {}
        return db

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window."""
        from PyQt6.QtWidgets import QMainWindow
        window = Mock(spec=QMainWindow)
        window._button_panel = Mock()
        window.refresh_folder_list = Mock()
        
        # Mock all signals
        window.process_directories_requested = Mock()
        window.add_folder_requested = Mock()
        window.batch_add_folders_requested = Mock()
        window.set_defaults_requested = Mock()
        window.edit_settings_requested = Mock()
        window.maintenance_requested = Mock()
        window.processed_files_requested = Mock()
        window.enable_resend_requested = Mock()
        window.edit_folder_requested = Mock()
        window.toggle_active_requested = Mock()
        window.delete_folder_requested = Mock()
        window.send_folder_requested = Mock()

        # Mock connect methods
        for attr in dir(window):
            if hasattr(getattr(window, attr), "connect"):
                getattr(window, attr).connect = Mock()

        return window

    @pytest.fixture
    def mock_app(self):
        """Create a mock application."""
        return Mock()

    @pytest.fixture  
    def controller_deps(self, mock_main_window, mock_db_manager, mock_app):
        """Create controller dependencies."""
        return {
            "main_window": mock_main_window,
            "db_manager": mock_db_manager,
            "app": mock_app,
            "database_path": "/tmp/test.db",
            "args": Mock(automatic=False),
            "version": "1.0.0",
        }

    def test_application_controller_init_doesnt_crash(self, mock_main_window):
        """Test that ApplicationController initialization doesn't crash."""
        from interface.application_controller import ApplicationController
        
        # Create minimal mocks for controller initialization
        mock_db_manager = Mock()
        # Mock oversight_and_defaults to return realistic values
        mock_oversight = Mock()
        mock_oversight.find_one.return_value = {"single_add_folder_prior": "/home/user", "batch_add_folder_prior": "/home/user"}
        mock_db_manager.oversight_and_defaults = mock_oversight
        mock_db_manager.folders_table = Mock()
        mock_db_manager.processed_files = Mock()
        mock_db_manager.session_database = {}
        
        controller_deps = {
            "main_window": mock_main_window,
            "db_manager": mock_db_manager,
            "app": Mock(),
            "database_path": "/tmp/test.db",
            "args": Mock(automatic=False),
            "version": "1.0.0",
        }
        
        # Mock operations to prevent actual processing
        with (
            patch("interface.application_controller.FolderOperations") as mock_folder_ops,
            patch("interface.application_controller.MaintenanceOperations"),
            patch("interface.application_controller.ProcessingOrchestrator"),
        ):
            # Configure folder operations mock
            mock_folder_ops.return_value.get_folder_count.return_value = 0
            
            # Create controller - this should not crash
            controller = ApplicationController(**controller_deps)
            
            # Verify that the controller was created successfully
            assert controller is not None
            assert hasattr(controller, '_main_window')
            assert hasattr(controller, '_db_manager')


class TestDialogBaseClassResilience:
    """Test that BaseDialog functionality doesn't crash."""

    def test_base_dialog_buttons_dont_crash(self, qtbot):
        """Test that BaseDialog OK/Cancel buttons don't crash."""
        from interface.ui.base_dialog import BaseDialog
        from PyQt6.QtWidgets import QApplication, QVBoxLayout, QLabel
        
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        class TestDialog(BaseDialog):
            def _setup_ui(self):
                self._body_layout = QVBoxLayout()
                self._body_layout.addWidget(QLabel("Test Dialog"))
                self._layout.addLayout(self._body_layout)
            
            def validate(self):
                return (True, "")
            
            def apply(self):
                pass
        
        dialog = TestDialog(title="Test Dialog")
        qtbot.addWidget(dialog)
        
        # Mock validation to ensure success
        with patch.object(dialog, 'validate', return_value=(True, "")), \
             patch.object(dialog, 'apply'):
            # Try to accept - should not crash
            dialog.accept()
        
        # Reset for another test
        dialog = TestDialog(title="Test Dialog 2")
        qtbot.addWidget(dialog)
        
        # Try to reject - should not crash
        dialog.reject()
        
        # Clean up
        dialog.deleteLater()


class TestRealUIButtonResilience:
    """Test button resilience with real UI components."""

    def test_real_button_panel_clicks_dont_crash(self, qtbot):
        """Test clicking real ButtonPanel buttons doesn't crash."""
        from interface.ui.widgets.button_panel import ButtonPanel
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # Ensure we have a QApplication instance
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
        
        panel = ButtonPanel()
        qtbot.addWidget(panel)
        
        # Connect all signals to safe methods to prevent crashes
        def safe_handler(*args, **kwargs):
            pass  # Do nothing, just don't crash
        
        # Connect all signals
        panel.process_clicked.connect(safe_handler)
        panel.add_folder_clicked.connect(safe_handler)
        panel.batch_add_clicked.connect(safe_handler)
        panel.set_defaults_clicked.connect(safe_handler)
        panel.edit_settings_clicked.connect(safe_handler)
        panel.maintenance_clicked.connect(safe_handler)
        panel.processed_files_clicked.connect(safe_handler)
        panel.enable_resend_clicked.connect(safe_handler)
        
        # Click each button - should not crash
        qtbot.mouseClick(panel._add_folder_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._batch_add_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._set_defaults_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._process_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._settings_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._maintenance_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._processed_files_btn, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(panel._enable_resend_btn, Qt.MouseButton.LeftButton)
        
        # Clean up
        panel.deleteLater()


class TestWidgetVisibility:
    """Test widget visibility functionality."""

    def test_button_panel_widgets_are_visible(self, qtbot):
        """Test that all buttons in ButtonPanel are visible."""
        from interface.ui.widgets.button_panel import ButtonPanel
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # Ensure we have a QApplication instance
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
        
        panel = ButtonPanel()
        qtbot.addWidget(panel)
        
        # Show the panel to make widgets visible
        panel.show()
        
        # Wait briefly for UI to render
        qtbot.wait(10)
        
        # Check that all buttons are visible
        assert panel._add_folder_btn.isVisible(), "Add Folder button should be visible"
        assert panel._batch_add_btn.isVisible(), "Batch Add button should be visible"
        assert panel._set_defaults_btn.isVisible(), "Set Defaults button should be visible"
        assert panel._process_btn.isVisible(), "Process button should be visible"
        assert panel._processed_files_btn.isVisible(), "Processed Files button should be visible"
        assert panel._maintenance_btn.isVisible(), "Maintenance button should be visible"
        assert panel._settings_btn.isVisible(), "Settings button should be visible"
        assert panel._enable_resend_btn.isVisible(), "Enable Resend button should be visible"
        
        # Check that separators are visible
        assert panel._separator1.isVisible(), "Separator 1 should be visible"
        assert panel._separator2.isVisible(), "Separator 2 should be visible"
        assert panel._separator3.isVisible(), "Separator 3 should be visible"
        assert panel._separator4.isVisible(), "Separator 4 should be visible"
        assert panel._separator5.isVisible(), "Separator 5 should be visible"
        assert panel._separator6.isVisible(), "Separator 6 should be visible"
        
        # Clean up
        panel.deleteLater()

    def test_edit_folder_dialog_widgets_are_visible(self, qtbot):
        """Test that key widgets in EditFolderDialog are visible."""
        from interface.ui.dialogs.edit_folder_dialog import EditFolderDialog
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # Ensure we have a QApplication instance
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
        
        # Create dialog with minimal data
        dialog = EditFolderDialog(
            folder_data={"folder_name": "/test/path", "alias": "Test Folder"},
            db_manager=Mock()
        )
        qtbot.addWidget(dialog)
        
        # Show the dialog to make widgets visible
        dialog.show()
        
        # Wait briefly for UI to render
        qtbot.wait(10)
        
        # Check that key widgets are visible
        assert dialog._tabs.isVisible(), "Tabs should be visible"
        assert dialog._general_tab.isVisible(), "General tab should be visible"
        assert dialog._alias_field.isVisible(), "Alias field should be visible"
        assert dialog._active_check.isVisible(), "Active checkbox should be visible"
        
        # Check that the 'Show Folder Path' button is visible
        # Find the button by iterating through the tab's children
        from PyQt6.QtWidgets import QPushButton
        buttons = dialog._general_tab.findChildren(QPushButton)
        show_path_button = None
        for btn in buttons:
            if btn.text() == "Show Folder Path":
                show_path_button = btn
                break
        
        assert show_path_button is not None, "Show Folder Path button should exist"
        assert show_path_button.isVisible(), "Show Folder Path button should be visible"
        
        # Clean up
        dialog.deleteLater()

    def test_widget_visibility_conditions(self, qtbot):
        """Test widget visibility under different conditions."""
        from interface.ui.widgets.button_panel import ButtonPanel
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # Ensure we have a QApplication instance
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
        
        panel = ButtonPanel()
        qtbot.addWidget(panel)
        
        # Initially, the panel might not be visible since it's not shown
        # But individual widgets inherit visibility from parent
        # Check that widgets are set up properly even if panel isn't shown yet
        assert hasattr(panel, '_add_folder_btn'), "Add Folder button should exist"
        assert hasattr(panel, '_process_btn'), "Process button should exist"
        
        # Show the panel
        panel.show()
        qtbot.wait(10)
        
        # Now they should definitely be visible
        assert panel._add_folder_btn.isVisible(), "Add Folder button should be visible when panel is shown"
        assert panel._process_btn.isVisible(), "Process button should be visible when panel is shown"
        
        # Hide the panel
        panel.hide()
        qtbot.wait(10)
        
        # Now they should not be visible
        assert not panel._add_folder_btn.isVisible(), "Add Folder button should not be visible when panel is hidden"
        assert not panel._process_btn.isVisible(), "Process button should not be visible when panel is hidden"
        
        # Clean up
        panel.deleteLater()


if __name__ == "__main__":
    pytest.main([__file__])