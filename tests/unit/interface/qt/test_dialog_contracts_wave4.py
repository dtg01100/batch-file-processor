"""Wave 4 dialog contract tests.

These tests harden cross-dialog behavioral contracts that should remain stable
even as internal dialog implementations evolve.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialogButtonBox

from interface.qt.dialogs.base_dialog import BaseDialog
from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog
from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog
from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog
from interface.qt.dialogs.resend_dialog import ResendDialog
from interface.validation.folder_settings_validator import ValidationResult
from tests.fakes import FakeDatabaseObj, FakeMaintenanceFunctions

pytestmark = pytest.mark.qt


class TestBaseDialogActionModes:
    def test_ok_cancel_mode_has_ok_and_cancel(self, qtbot):
        dialog = BaseDialog(action_mode="ok_cancel")
        qtbot.addWidget(dialog)

        assert dialog._button_box is not None
        assert dialog._button_box.button(QDialogButtonBox.StandardButton.Ok) is not None
        assert (
            dialog._button_box.button(QDialogButtonBox.StandardButton.Cancel)
            is not None
        )

    def test_close_only_mode_has_close_only(self, qtbot):
        dialog = BaseDialog(action_mode="close_only")
        qtbot.addWidget(dialog)

        assert dialog._button_box is not None
        assert (
            dialog._button_box.button(QDialogButtonBox.StandardButton.Close) is not None
        )
        assert dialog._button_box.button(QDialogButtonBox.StandardButton.Ok) is None
        assert dialog._button_box.button(QDialogButtonBox.StandardButton.Cancel) is None

    def test_none_mode_has_no_button_box(self, qtbot):
        dialog = BaseDialog(action_mode="none")
        qtbot.addWidget(dialog)
        assert dialog._button_box is None


class TestNonApplyDialogRejectContracts:
    def test_processed_files_close_button_rejects(self, qtbot):
        db = FakeDatabaseObj()
        with patch.object(ProcessedFilesDialog, "_get_folder_tuples", return_value=[]):
            dialog = ProcessedFilesDialog(None, db)
            qtbot.addWidget(dialog)

        close_btn = dialog._button_box.button(QDialogButtonBox.StandardButton.Close)
        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            qtbot.mouseClick(close_btn, Qt.MouseButton.LeftButton)

    def test_resend_close_button_rejects(self, qtbot, monkeypatch):
        service = MagicMock()
        service.has_processed_files.return_value = True
        service.get_all_files_for_resend.return_value = []
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService", lambda *_args: service
        )
        dialog = ResendDialog(None, FakeDatabaseObj())
        qtbot.addWidget(dialog)
        dialog.show()

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            qtbot.keyPress(dialog, Qt.Key.Key_Escape)

    def test_database_import_close_button_rejects(self, qtbot):
        dialog = DatabaseImportDialog(None, "/old.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            qtbot.mouseClick(dialog._close_button, Qt.MouseButton.LeftButton)

    def test_maintenance_escape_rejects(self, qtbot):
        dialog = MaintenanceDialog(None, FakeMaintenanceFunctions())
        qtbot.addWidget(dialog)
        dialog.show()

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            qtbot.keyPress(dialog, Qt.Key.Key_Escape)


class TestAccessibilityContracts:
    def test_edit_settings_key_controls_have_accessibility_metadata(self, qtbot):
        dialog = EditSettingsDialog(None, {}, settings_provider=lambda: {})
        qtbot.addWidget(dialog)

        controls = [
            dialog._enable_email_cb,
            dialog._email_address,
            dialog._test_connection_btn,
            dialog._select_log_folder_btn,
            dialog._backup_interval_spin,
        ]
        for control in controls:
            assert control.accessibleName()
            assert control.accessibleDescription()

    def test_database_import_key_controls_have_accessibility_metadata(self, qtbot):
        dialog = DatabaseImportDialog(None, "/old.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        controls = [
            dialog._select_button,
            dialog._db_label,
            dialog._import_button,
            dialog._progress_bar,
            dialog._close_button,
        ]
        for control in controls:
            assert control.accessibleName()
            assert control.accessibleDescription()

    def test_processed_files_action_controls_have_accessibility_metadata(self, qtbot):
        db = FakeDatabaseObj(
            {
                "processed_files": [{"id": 1, "folder_id": 10, "file_name": "a.txt"}],
                "folders": [{"id": 10, "alias": "Alpha", "folder_name": "/tmp/a"}],
                "administrative": [{"id": 1}],
            }
        )
        with patch.object(
            ProcessedFilesDialog, "_get_folder_tuples", return_value=[(10, "Alpha")]
        ):
            dialog = ProcessedFilesDialog(None, db)
            qtbot.addWidget(dialog)

        dialog._on_folder_selected(10)
        assert dialog._export_btn.accessibleName()
        assert dialog._export_btn.accessibleDescription()


class TestValidationFocusContracts:
    def test_edit_settings_focuses_first_invalid_field(self, qtbot):
        dialog = EditSettingsDialog(None, {}, settings_provider=lambda: {})
        qtbot.addWidget(dialog)

        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("")
        dialog._email_smtp_server.setText("")
        dialog._email_smtp_port.setText("")

        with patch("interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical"):
            assert dialog.validate() is False
        assert dialog.focusWidget() is dialog._email_address

    def test_edit_folders_focuses_first_invalid_field(self, qtbot):
        dialog = EditFoldersDialog(
            None,
            {"folder_name": "/tmp/f", "folder_is_active": True, "alias": "alpha"},
        )
        qtbot.addWidget(dialog)

        invalid = ValidationResult(is_valid=False)
        invalid.add_error("ftp_server", "FTP server required")
        invalid.add_error("email_recipient", "Email required")
        validator = MagicMock()
        validator.validate_extracted_fields.return_value = invalid
        dialog._validator = validator
        dialog._fields["active_checkbutton"].setChecked(True)

        focused = {"widget": None}

        def _capture_focus(widget):
            focused["widget"] = widget

        dialog._focus_widget = _capture_focus

        with patch("interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical"):
            assert dialog.validate() is False
        assert focused["widget"] is dialog._fields["ftp_server_field"]


class TestBaseDialogHelperUsageGuards:
    def test_resend_empty_data_uses_show_info_helper(self, qtbot, monkeypatch):
        service = MagicMock()
        service.has_processed_files.return_value = False
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService", lambda *_args: service
        )

        with patch.object(BaseDialog, "show_info") as show_info:
            dialog = ResendDialog(None, FakeDatabaseObj())
            qtbot.addWidget(dialog)
            assert dialog._should_show is False
            show_info.assert_called_once()

    def test_resend_toggle_error_uses_show_error_helper(self, qtbot, monkeypatch):
        service = MagicMock()
        service.has_processed_files.return_value = True
        service.get_all_files_for_resend.return_value = []
        service.set_resend_flags_batch.side_effect = RuntimeError("boom")
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService", lambda *_args: service
        )

        dialog = ResendDialog(None, FakeDatabaseObj())
        qtbot.addWidget(dialog)

        # Select a file, then attempt to mark for resend which calls the service
        dialog._on_file_selected(1, selected=True)
        with patch.object(BaseDialog, "show_error") as show_error:
            dialog._mark_selected_for_resend()
            show_error.assert_called_once()

    def test_database_import_completion_paths_use_helpers(self, qtbot):
        dialog = DatabaseImportDialog(None, "/old.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)

        with patch.object(BaseDialog, "show_info") as show_info:
            dialog._on_finished(True, "ok")
            show_info.assert_called_once_with("Import Complete", "ok")

        with patch.object(BaseDialog, "show_error") as show_error:
            dialog._on_finished(False, "bad")
            dialog._on_error("err")
            assert show_error.call_count == 2

    def test_database_import_confirm_path_uses_helper(self, qtbot):
        import threading

        dialog = DatabaseImportDialog(None, "/old.db", "Linux", "/backup", "42")
        qtbot.addWidget(dialog)
        event = threading.Event()

        with patch.object(BaseDialog, "confirm_yes_no", return_value=True) as confirm:
            dialog._on_confirm_required("Title", "Body", event)
            confirm.assert_called_once_with("Title", "Body")
            assert event.is_set()
            assert event.result is True
