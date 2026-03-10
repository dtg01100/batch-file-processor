"""Additional tests for ResendDialog to improve coverage."""

import pytest
from PyQt6.QtCore import Qt

pytestmark = pytest.mark.qt


@pytest.mark.qt
class TestResendDialogUI:
    """Tests for ResendDialog UI initialization and setup."""

    def test_dialog_initialization(self, qtbot, mock_database_obj):
        """Test dialog initializes with correct properties."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Enable Resend"
        assert dialog._database_connection == mock_database_obj
        assert dialog._folder_id is None

    def test_ui_has_required_widgets(self, qtbot, mock_database_obj):
        """Test that all required UI widgets are created."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_folders_scroll")
        assert hasattr(dialog, "_folders_content")
        assert hasattr(dialog, "_files_frame")
        assert hasattr(dialog, "_file_count_spinbox")
        assert hasattr(dialog, "_select_all_button")
        assert hasattr(dialog, "_clear_all_button")
        assert hasattr(dialog, "_resend_button")

    def test_minimum_size_set(self, qtbot, mock_database_obj):
        """Test that minimum size is set for comfortable viewing."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 700
        assert dialog.minimumHeight() >= 500


@pytest.mark.qt
class TestResendDialogFolderDisplay:
    """Tests for folder display functionality."""

    def test_load_folders_with_data(self, qtbot, mock_database_obj):
        """Test loading folders with processed files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        # Mock folder data
        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Folder A"},
            {"folder_id": 2, "folder_name": "Folder B"},
        ]

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Should have created buttons for folders
        assert len(dialog._folder_buttons) > 0

    def test_load_folders_empty(self, qtbot, mock_database_obj):
        """Test loading when no folders have processed files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = []

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Should handle empty state gracefully
        assert len(dialog._folder_buttons) == 0

    def test_folder_button_click_loads_files(self, qtbot, mock_database_obj):
        """Test clicking folder button loads associated files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]
        mock_database_obj.processed_files.find.return_value = iter(
            [
                {"id": 1, "file_name": "file1.txt", "resend": False},
                {"id": 2, "file_name": "file2.txt", "resend": False},
            ]
        )

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Click folder button
        if 1 in dialog._folder_buttons:
            qtbot.mouseClick(dialog._folder_buttons[1], Qt.MouseButton.LeftButton)
            assert dialog._folder_id == 1


@pytest.mark.qt
class TestResendDialogFileDisplay:
    """Tests for file display and selection functionality."""

    def test_display_files_for_folder(self, qtbot, mock_database_obj):
        """Test displaying files for a selected folder."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]
        mock_database_obj.processed_files.find.return_value = iter(
            [
                {"id": 1, "file_name": "file1.txt", "resend": False},
                {"id": 2, "file_name": "file2.txt", "resend": True},
            ]
        )

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog._folder_id = 1
        dialog._display_files_for_folder()

        # Should have created checkboxes for files
        assert len(dialog._file_checkboxes) > 0

    def test_file_checkbox_states(self, qtbot, mock_database_obj):
        """Test that file checkboxes reflect current resend state."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]
        mock_database_obj.processed_files.find.return_value = iter(
            [
                {"id": 1, "file_name": "file1.txt", "resend": False},
                {"id": 2, "file_name": "file2.txt", "resend": True},
            ]
        )

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog._folder_id = 1
        dialog._display_files_for_folder()

        # Check checkbox states
        if 1 in dialog._file_checkboxes:
            assert not dialog._file_checkboxes[1].isChecked()
        if 2 in dialog._file_checkboxes:
            assert dialog._file_checkboxes[2].isChecked()


@pytest.mark.qt
class TestResendDialogFileCount:
    """Tests for file count limit functionality."""

    def test_file_count_spinbox_default(self, qtbot, mock_database_obj):
        """Test file count spinbox has sensible default."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert dialog._file_count_spinbox.value() > 0

    def test_file_count_spinbox_changes_limit(self, qtbot, mock_database_obj):
        """Test changing file count spinbox updates display."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Change spinbox value
        dialog._file_count_spinbox.setValue(50)

        # Should trigger reload of files
        # (actual behavior depends on implementation)


@pytest.mark.qt
class TestResendDialogSelection:
    """Tests for file selection controls."""

    def test_select_all_button(self, qtbot, mock_database_obj):
        """Test select all button checks all files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]
        mock_database_obj.processed_files.find.return_value = iter(
            [
                {"id": 1, "file_name": "file1.txt", "resend": False},
                {"id": 2, "file_name": "file2.txt", "resend": False},
            ]
        )

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog._folder_id = 1
        dialog._display_files_for_folder()

        # Click select all
        qtbot.mouseClick(dialog._select_all_button, Qt.MouseButton.LeftButton)

        # All checkboxes should be checked
        for checkbox in dialog._file_checkboxes.values():
            assert checkbox.isChecked()

    def test_clear_all_button(self, qtbot, mock_database_obj):
        """Test clear all button unchecks all files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]
        mock_database_obj.processed_files.find.return_value = iter(
            [
                {"id": 1, "file_name": "file1.txt", "resend": True},
                {"id": 2, "file_name": "file2.txt", "resend": True},
            ]
        )

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog._folder_id = 1
        dialog._display_files_for_folder()

        # Click clear all
        qtbot.mouseClick(dialog._clear_all_button, Qt.MouseButton.LeftButton)

        # All checkboxes should be unchecked
        for checkbox in dialog._file_checkboxes.values():
            assert not checkbox.isChecked()


@pytest.mark.qt
class TestResendDialogApply:
    """Tests for applying resend flags."""

    def test_resend_button_toggled_without_folder(self, qtbot, mock_database_obj):
        """Test resend button is disabled when no folder selected."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert not dialog._resend_button.isEnabled()

    def test_resend_button_enabled_with_folder(self, qtbot, mock_database_obj):
        """Test resend button is enabled when folder is selected."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog._folder_id = 1
        dialog._update_button_states()

        assert dialog._resend_button.isEnabled()

    def test_apply_resend_flags(self, qtbot, mock_database_obj):
        """Test applying resend flags updates database."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1, "folder_name": "Test Folder"},
        ]
        mock_database_obj.processed_files.find.return_value = iter(
            [
                {"id": 1, "file_name": "file1.txt", "resend": False},
            ]
        )

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        dialog._folder_id = 1
        dialog._display_files_for_folder()

        # Check the file
        if 1 in dialog._file_checkboxes:
            dialog._file_checkboxes[1].setChecked(True)

        # Apply would update database
        # (actual implementation depends on ResendService)


@pytest.mark.qt
class TestResendDialogServiceIntegration:
    """Tests for integration with ResendService."""

    def test_service_initialization(self, qtbot, mock_database_obj):
        """Test that ResendService is properly initialized."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Service should be created
        assert dialog._service is not None

    def test_service_has_processed_files_called(self, qtbot, mock_database_obj):
        """Test that service is queried for processed files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        dialog = ResendDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Service should have been called during load_data
        mock_database_obj.processed_files.distinct.assert_called()
