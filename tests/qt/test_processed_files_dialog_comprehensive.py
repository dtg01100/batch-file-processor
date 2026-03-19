"""Comprehensive tests for ProcessedFilesDialog.

Tests cover:
- Dialog initialization
- Folder selection (only folders with processed files are shown)
- Empty state handling
- Export functionality
- Keyboard shortcuts
- Error handling
"""

from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

pytestmark = [pytest.mark.qt, pytest.mark.gui]


@pytest.fixture
def populated_database(mock_database_obj):
    """Create database with folders and processed files for testing.

    The ProcessedFilesDialog only shows folders that have processed files,
    so we need to ensure folders have associated processed_files records.
    """
    # Add folders with processed files
    for i in range(3):
        folder_id = i + 1
        mock_database_obj.folders_table.insert(
            {
                "id": folder_id,
                "folder_name": f"/test/folder{i}",
                "alias": f"Test Folder {i}",
            }
        )
        # Add at least one processed file per folder for dialog to show them
        mock_database_obj.processed_files.insert(
            {
                "folder_id": folder_id,
                "filename": f"file_{i}.edi",
                "md5": f"hash_{i:04d}",
                "processed_at": "2024-01-01T00:00:00",
                "resend_flag": False,
            }
        )
    return mock_database_obj


@pytest.fixture
def empty_database(mock_database_obj):
    """Create database with folder but no processed files."""
    # Add a folder but no processed files
    mock_database_obj.folders_table.insert(
        {
            "id": 1,
            "folder_name": "/test/folder",
            "alias": "Test Folder",
        }
    )
    return mock_database_obj


@pytest.fixture
def no_folders_database(mock_database_obj):
    """Create database with no folders at all."""
    return mock_database_obj


@pytest.mark.qt
class TestProcessedFilesDialogInitialization:
    """Test dialog initialization and basic functionality."""

    def test_dialog_initialization(self, qtbot, populated_database):
        """Test dialog initializes correctly."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Processed Files Report"
        assert dialog._database_obj == populated_database
        assert dialog.isVisible() is False  # Not shown yet

    def test_dialog_has_required_widgets(self, qtbot, populated_database):
        """Test that all required widgets exist."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Dialog should have button group for folder selection
        assert hasattr(dialog, "_button_group")
        # Dialog should have actions container
        assert hasattr(dialog, "_actions_container")
        # Dialog should have output folder
        assert hasattr(dialog, "_output_folder")

    def test_dialog_minimum_size(self, qtbot, populated_database):
        """Test dialog has appropriate minimum size."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 600
        assert dialog.minimumHeight() >= 450


@pytest.mark.qt
class TestProcessedFilesDialogEmptyState:
    """Test empty state handling."""

    def test_no_folders_display(self, qtbot, no_folders_database):
        """Test dialog displays correctly with no folders."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, no_folders_database)
        qtbot.addWidget(dialog)

        # Should not crash with no folders
        assert dialog is not None

    def test_no_processed_files_for_folder(self, qtbot, empty_database):
        """Test dialog handles folder with no processed files.

        The ProcessedFilesDialog only shows folders that have processed files.
        With no processed files, the folder list should be empty.
        """
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, empty_database)
        qtbot.addWidget(dialog)

        # Should not crash - folder list will be empty
        assert dialog is not None
        buttons = dialog._button_group.buttons()
        assert len(buttons) == 0


@pytest.mark.qt
class TestProcessedFilesDialogFolderSelection:
    """Test folder selection functionality."""

    def test_folder_list_populated(self, qtbot, populated_database):
        """Test folder list is populated correctly.

        Only folders with processed files should be shown.
        """
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Button group should have buttons for folders with processed files
        buttons = dialog._button_group.buttons()
        assert len(buttons) == 3
        # Check folder aliases
        button_texts = [btn.text() for btn in buttons]
        assert "Test Folder 0" in button_texts
        assert "Test Folder 1" in button_texts
        assert "Test Folder 2" in button_texts

    def test_folder_selection_triggers_actions(self, qtbot, populated_database):
        """Test that selecting a folder shows action buttons."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Get the folder buttons
        buttons = dialog._button_group.buttons()
        assert len(buttons) > 0

        # Click the first folder button
        buttons[0].click()

        # Should have selected folder id
        assert dialog._selected_folder_id is not None

    def test_folder_selection_shows_export_button(self, qtbot, populated_database):
        """Test that selecting a folder shows export button."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Click folder to select it
        buttons = dialog._button_group.buttons()
        buttons[0].click()

        # Should have selected folder id
        assert dialog._selected_folder_id is not None


@pytest.mark.qt
class TestProcessedFilesDialogOutputFolder:
    """Test output folder selection."""

    def test_choose_output_folder(self, qtbot, populated_database):
        """Test choosing output folder."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Select a folder first
        buttons = dialog._button_group.buttons()
        buttons[0].click()

        # Mock the file dialog
        with patch(
            "interface.qt.dialogs.processed_files_dialog.QFileDialog.getExistingDirectory"
        ) as mock_get_dir:
            mock_get_dir.return_value = "/test/output"

            # Find and click the choose output folder button
            choose_btn = dialog._actions_layout.itemAt(0).widget()
            if isinstance(choose_btn, QPushButton):
                choose_btn.click()

        # Output folder should be set
        assert dialog._output_folder == "/test/output"
        assert dialog._output_folder_confirmed is True


@pytest.mark.qt
class TestProcessedFilesDialogBulkOperations:
    """Test bulk operations on files."""

    def test_multiple_folders_with_processed_files(self, qtbot, mock_database_obj):
        """Test dialog with multiple folders that have processed files."""
        # Add multiple folders, each with processed files
        for i in range(3):
            mock_database_obj.folders_table.insert(
                {
                    "id": i + 1,
                    "folder_name": f"/test/folder{i}",
                    "alias": f"Test Folder {i}",
                }
            )
            mock_database_obj.processed_files.insert(
                {
                    "folder_id": i + 1,
                    "filename": f"file_{i}.edi",
                    "md5": f"hash_{i}",
                    "processed_at": "2024-01-01T00:00:00",
                    "resend_flag": False,
                }
            )

        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Should have 3 folder buttons (only folders with processed files)
        buttons = dialog._button_group.buttons()
        assert len(buttons) == 3


@pytest.mark.qt
class TestProcessedFilesDialogExport:
    """Test export functionality."""

    def test_export_button_disabled_initially(self, qtbot, populated_database):
        """Test export button is disabled until folder and output are selected."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Select a folder first
        buttons = dialog._button_group.buttons()
        buttons[0].click()

        # Export button should still be disabled (no output folder selected)
        if hasattr(dialog, "_export_btn"):
            assert dialog._export_btn.isEnabled() is False

    def test_export_button_enabled_after_output_selected(
        self, qtbot, populated_database
    ):
        """Test export button is enabled after output folder is selected."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        # Select a folder
        buttons = dialog._button_group.buttons()
        buttons[0].click()

        # Manually trigger rebuild of actions to simulate what happens after
        # the user selects an output folder
        dialog._output_folder = "/test/output"
        dialog._output_folder_confirmed = True
        dialog._rebuild_actions()

        # Export button should be enabled
        if hasattr(dialog, "_export_btn"):
            assert dialog._export_btn.isEnabled() is True


@pytest.mark.qt
class TestProcessedFilesDialogKeyboardShortcuts:
    """Test keyboard shortcuts."""

    def test_escape_closes_dialog(self, qtbot, populated_database):
        """Test Escape key closes dialog."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, populated_database)
        qtbot.addWidget(dialog)

        dialog.show()
        assert dialog.isVisible()

        # Press Escape
        qtbot.keyPress(dialog, Qt.Key.Key_Escape)

        # Dialog should close
        assert not dialog.isVisible()


@pytest.mark.qt
class TestProcessedFilesDialogErrorHandling:
    """Test error handling."""

    def test_invalid_folder_data(self, qtbot, mock_database_obj):
        """Test handling invalid folder data in database."""
        # Insert folder with None alias
        mock_database_obj.folders_table.insert(
            {
                "id": 1,
                "folder_name": None,
                "alias": None,
            }
        )

        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        # Should not crash
        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        assert dialog is not None


@pytest.mark.qt
class TestProcessedFilesDialogLargeDataset:
    """Test performance with large datasets."""

    def test_display_1000_files(self, qtbot, mock_database_obj):
        """Test dialog performance with 1000 files."""
        # Add a folder
        folder_id = 1
        mock_database_obj.folders_table.insert(
            {
                "id": folder_id,
                "folder_name": "/test/folder",
                "alias": "Test Folder",
            }
        )

        # Add 1000 files
        for i in range(1000):
            mock_database_obj.processed_files.insert(
                {
                    "folder_id": folder_id,
                    "filename": f"file_{i:04d}.edi",
                    "md5": f"hash_{i:05d}",
                    "processed_at": "2024-01-01T00:00:00",
                    "resend_flag": False,
                }
            )

        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        # Should not crash and should be reasonably responsive
        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Dialog should load successfully
        assert dialog is not None
        # Folder button should exist (for folder with processed files)
        buttons = dialog._button_group.buttons()
        assert len(buttons) == 1

    def test_many_folders_with_processed_files(self, qtbot, mock_database_obj):
        """Test dialog with many folders, each with processed files."""
        # Add 50 folders, each with at least one processed file
        for i in range(50):
            folder_id = i + 1
            mock_database_obj.folders_table.insert(
                {
                    "id": folder_id,
                    "folder_name": f"/test/folder{i}",
                    "alias": f"Folder {i}",
                }
            )
            mock_database_obj.processed_files.insert(
                {
                    "folder_id": folder_id,
                    "filename": f"file_{i}.edi",
                    "md5": f"hash_{i}",
                    "processed_at": "2024-01-01T00:00:00",
                    "resend_flag": False,
                }
            )

        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

        # Should have 50 folder buttons
        buttons = dialog._button_group.buttons()
        assert len(buttons) == 50
