"""Tests for ResendDialog."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QLineEdit, QTableWidget


@pytest.mark.qt
class TestResendDialogInitialization:
    """Test suite for ResendDialog initialization."""

    def test_dialog_class_exists(self):
        """Test that ResendDialog class exists."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        assert ResendDialog is not None

    def test_dialog_inherits_from_base_dialog(self):
        """Test that ResendDialog inherits from BaseDialog."""
        from interface.qt.dialogs.base_dialog import BaseDialog
        from interface.qt.dialogs.resend_dialog import ResendDialog

        assert issubclass(ResendDialog, BaseDialog)

    def test_dialog_initialization_with_minimal_parameters(self, qtbot, monkeypatch):
        """Test that dialog can be initialized with minimal parameters."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            assert dialog is not None
            assert dialog.windowTitle() == "Enable Resend"

    def test_dialog_stores_database_connection(self, qtbot):
        """Test that dialog stores database connection."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            assert dialog._database_connection is db_conn

    def test_dialog_initializes_service(self, qtbot):
        """Test that dialog initializes ResendService."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ) as mock_service_class:
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            mock_service_class.assert_called_once_with(db_conn)

    def test_dialog_builds_ui_without_folders(self, qtbot):
        """Test that dialog builds UI with table and search input."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            # Verify the flat table UI was built
            assert isinstance(dialog._table, QTableWidget)
            assert isinstance(dialog._search_input, QLineEdit)
            assert hasattr(dialog, "_search_field_selector")
            assert dialog._should_show is True


@pytest.mark.qt
class TestResendDialogFileManagement:
    """Test suite for file management in the flat table."""

    def test_checkboxes_created_for_files(self, qtbot):
        """Test that table rows are created for processed files."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = [
            {
                "id": 10,
                "folder_id": 1,
                "folder_alias": "Test",
                "file_name": "file1.txt",
                "resend_flag": False,
                "sent_date_time": "2025-01-01T10:00:00",
            },
            {
                "id": 11,
                "folder_id": 1,
                "folder_alias": "Test",
                "file_name": "file2.txt",
                "resend_flag": True,
                "sent_date_time": "2025-01-02T10:00:00",
            },
        ]

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            # _all_files should be populated from service
            assert len(dialog._all_files) == 2
            # Table should have one row per file
            assert dialog._table.rowCount() == 2

    def test_save_updates_resend_flags(self, qtbot):
        """Test that selecting files and marking for resend calls the service."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = [
            {
                "id": 10,
                "folder_id": 1,
                "folder_alias": "Test",
                "file_name": "file1.txt",
                "resend_flag": False,
                "sent_date_time": "2025-01-01T10:00:00",
            },
        ]

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            # Select a file via _on_file_selected
            dialog._on_file_selected(10, selected=True)
            assert 10 in dialog._selected_files

            # Mark selected for resend
            with patch.object(dialog, "show_info"):
                dialog._mark_selected_for_resend()

            mock_service.set_resend_flags_batch.assert_called_once_with(
                [10], resend_flag=True
            )


@pytest.mark.qt
class TestResendDialogEdgeCases:
    """Test edge cases and error handling."""

    def test_dialog_handles_service_error(self, qtbot):
        """Test dialog behavior when service fails."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        with (
            patch(
                "interface.qt.dialogs.resend_dialog.ResendService",
                side_effect=Exception("Database error"),
            ),
            patch("PyQt5.QtWidgets.QMessageBox.critical") as mock_critical,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            assert dialog._should_show is False
            assert dialog._service is None
            mock_critical.assert_called_once()
            _, title, message = mock_critical.call_args[0]
            assert title == "Database Error"
            assert "Database error" in message

    def test_load_more_button_reenabled_when_more_pages_exist(self, qtbot, monkeypatch):
        """Load More should re-enable after a successful page load when more data exists."""
        from interface.qt.dialogs.resend_dialog import ResendDialog

        db_conn = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True

        first_page = [
            {
                "id": 1,
                "folder_id": 1,
                "folder_alias": "F",
                "file_name": "f1",
                "resend_flag": False,
                "sent_date_time": "2025-01-01T10:00:00",
            },
            {
                "id": 2,
                "folder_id": 1,
                "folder_alias": "F",
                "file_name": "f2",
                "resend_flag": False,
                "sent_date_time": "2025-01-02T10:00:00",
            },
        ]
        second_page = [
            {
                "id": 3,
                "folder_id": 1,
                "folder_alias": "F",
                "file_name": "f3",
                "resend_flag": False,
                "sent_date_time": "2025-01-03T10:00:00",
            },
            {
                "id": 4,
                "folder_id": 1,
                "folder_alias": "F",
                "file_name": "f4",
                "resend_flag": False,
                "sent_date_time": "2025-01-04T10:00:00",
            },
        ]

        mock_service.get_all_files_for_resend.side_effect = [
            first_page,
            second_page,
            [],
        ]

        monkeypatch.setattr(ResendDialog, "PAGE_SIZE", 2)

        with patch(
            "interface.qt.dialogs.resend_dialog.ResendService",
            return_value=mock_service,
        ):
            dialog = ResendDialog(None, db_conn)
            qtbot.addWidget(dialog)

            assert dialog._load_more_button.isEnabled() is True
            dialog._load_more_button.click()

            assert len(dialog._all_files) == 4
            assert dialog._load_more_button.isEnabled() is True

            dialog._load_more_button.click()
            assert len(dialog._all_files) == 4
            assert dialog._load_more_button.isEnabled() is False
