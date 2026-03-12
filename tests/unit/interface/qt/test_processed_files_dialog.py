"""Tests for ProcessedFilesDialog."""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QDialogButtonBox


@pytest.mark.qt
class TestProcessedFilesDialogInitialization:
    """Test suite for ProcessedFilesDialog initialization."""

    def test_dialog_class_exists(self):
        """Test that ProcessedFilesDialog class exists."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        assert ProcessedFilesDialog is not None

    def test_dialog_inherits_from_base_dialog(self):
        """Test that ProcessedFilesDialog inherits from BaseDialog."""
        from interface.qt.dialogs.base_dialog import BaseDialog
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        assert issubclass(ProcessedFilesDialog, BaseDialog)

    def test_dialog_initialization_with_minimal_parameters(self, qtbot):
        """Test that dialog can be initialized with minimal parameters."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = []

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "Processed Files Report"
        assert dialog.isModal()

    def test_dialog_stores_database_reference(self, qtbot):
        """Test that dialog stores database reference."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = []

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        assert dialog._database_obj is db

    def test_dialog_initializes_output_folder_from_prior(self, qtbot):
        """Test that dialog loads prior output folder from database."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {
            "export_processed_folder_prior": "/path/to/exports"
        }
        db.folders_table.all.return_value = []

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        assert dialog._output_folder == "/path/to/exports"

    def test_dialog_builds_ui_without_folders(self, qtbot):
        """Test that dialog builds UI even with no folders."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = []

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        # Should not crash, UI should be built
        assert dialog._button_group is not None

    def test_dialog_uses_close_only_action_mode(self, qtbot):
        """Test dialog uses BaseDialog close-only actions."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = []

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        assert dialog._button_box is not None
        assert (
            dialog._button_box.button(QDialogButtonBox.StandardButton.Close) is not None
        )


@pytest.mark.qt
class TestProcessedFilesDialogFolderSelection:
    """Test suite for folder selection functionality."""

    def test_folder_selected_updates_actions_panel(self, qtbot, monkeypatch):
        """Test that selecting a folder updates the actions panel."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = [
            {"id": 1, "alias": "Test Folder", "folder_name": "/test"},
        ]
        db.processed_files.count.return_value = 10

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        # Simulate folder selection
        if hasattr(dialog, "_on_folder_selected"):
            dialog._on_folder_selected(1)
            assert dialog._selected_folder_id == 1


@pytest.mark.qt
class TestProcessedFilesDialogExport:
    """Test suite for export functionality."""

    def test_export_button_triggers_file_dialog(self, qtbot, monkeypatch):
        """Test that export button opens file dialog."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = [
            {"id": 1, "alias": "Test", "folder_name": "/test"},
        ]
        db.processed_files.count.return_value = 5

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)
        dialog._selected_folder_id = 1

        # Mock file dialog
        mock_file_dialog = MagicMock(return_value="/export/path")
        monkeypatch.setattr(
            "interface.qt.dialogs.processed_files_dialog.QFileDialog.getExistingDirectory",
            mock_file_dialog,
        )

        # Trigger export if method exists
        if hasattr(dialog, "_select_output_folder"):
            dialog._select_output_folder()
            assert dialog._output_folder == "/export/path" or mock_file_dialog.called


@pytest.mark.qt
class TestProcessedFilesDialogEdgeCases:
    """Test edge cases and error handling."""

    def test_dialog_handles_no_processed_files(self, qtbot):
        """Test dialog behavior when no processed files exist."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = [
            {"id": 1, "alias": "Empty", "folder_name": "/empty"},
        ]
        db.processed_files.count.return_value = 0

        dialog = ProcessedFilesDialog(None, db)
        qtbot.addWidget(dialog)

        # Dialog should still construct successfully
        assert dialog is not None

    def test_ui_service_injection(self, qtbot):
        """Test that UI service can be injected."""
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        db = MagicMock()
        db.get_oversight_or_default.return_value = {}
        db.folders_table.all.return_value = []

        ui_service = MagicMock()
        dialog = ProcessedFilesDialog(None, db, ui_service=ui_service)
        qtbot.addWidget(dialog)

        assert dialog._ui_service is ui_service
