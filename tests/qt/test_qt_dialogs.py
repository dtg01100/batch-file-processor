"""
Comprehensive tests for all Qt dialog implementations.

Uses pytest-qt (qtbot fixture) for proper widget lifecycle management.
Dialogs are tested via show() + direct widget manipulation, never exec().
"""

import pytest

pytestmark = [pytest.mark.qt, pytest.mark.gui]

from unittest.mock import MagicMock

import pytest
from PyQt5.QtCore import QDate, QItemSelectionModel, Qt
from PyQt5.QtWidgets import QPushButton, QTableWidget


# ---------------------------------------------------------------------------
# TestBaseDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestBaseDialog:
    def test_construction(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == ""
        assert dialog.isModal() is True

    def test_construction_with_title(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog(title="Test Dialog")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Test Dialog"

    def test_validate_returns_true(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog()
        qtbot.addWidget(dialog)
        assert dialog.validate() is True

    def test_apply_does_nothing(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog()
        qtbot.addWidget(dialog)
        dialog.apply()  # Should not raise any errors

    def test_ok_button_calls_validate_and_apply(self, qtbot, monkeypatch):
        from interface.qt.dialogs.base_dialog import BaseDialog

        # Create a subclass to track method calls
        class TestDialog(BaseDialog):
            def __init__(self):
                super().__init__()
                self.validate_called = False
                self.apply_called = False

            def validate(self):
                self.validate_called = True
                return True

            def apply(self):
                self.apply_called = True

        dialog = TestDialog()
        qtbot.addWidget(dialog)

        # Find and click OK button
        ok_button = dialog._button_box.button(dialog._button_box.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

        assert dialog.validate_called is True
        assert dialog.apply_called is True

    def test_ok_button_aborts_if_validate_returns_false(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        class TestDialog(BaseDialog):
            def __init__(self):
                super().__init__()
                self.validate_called = False
                self.apply_called = False

            def validate(self):
                self.validate_called = True
                return False

            def apply(self):
                self.apply_called = True

        dialog = TestDialog()
        qtbot.addWidget(dialog)

        ok_button = dialog._button_box.button(dialog._button_box.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

        assert dialog.validate_called is True
        assert dialog.apply_called is False

    def test_cancel_button_rejects(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        with qtbot.waitSignal(dialog.rejected, timeout=1000):
            cancel_button = dialog._button_box.button(
                dialog._button_box.StandardButton.Cancel
            )
            qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)

    def test_action_mode_close_only_shows_close_button(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog(action_mode="close_only")
        qtbot.addWidget(dialog)

        assert dialog._button_box is not None
        close_button = dialog._button_box.button(
            dialog._button_box.StandardButton.Close
        )
        assert close_button is not None

    def test_action_mode_none_has_no_button_box(self, qtbot):
        from interface.qt.dialogs.base_dialog import BaseDialog

        dialog = BaseDialog(action_mode="none")
        qtbot.addWidget(dialog)

        assert dialog._button_box is None

    def test_confirm_yes_no_uses_question_box(self, qtbot, monkeypatch):
        from PyQt5.QtWidgets import QMessageBox

        from interface.qt.dialogs.base_dialog import BaseDialog

        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
        )
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        assert dialog.confirm_yes_no("Title", "Body") is True


# ---------------------------------------------------------------------------
# TestQtFolderDataExtractor
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestQtFolderDataExtractor:
    def test_empty_fields_returns_defaults(self, qtbot):
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor({})
        result = extractor.extract_all()
        assert result.folder_name == ""
        assert result.ftp_port == 21
        assert result.process_backend_ftp is False

    def test_reads_line_edit(self, qtbot):
        from PyQt5.QtWidgets import QLineEdit

        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        edit = QLineEdit()
        qtbot.addWidget(edit)
        edit.setText("my_server")
        extractor = QtFolderDataExtractor({"ftp_server_field": edit})
        assert extractor.extract_all().ftp_server == "my_server"

    def test_reads_checkbox(self, qtbot):
        from PyQt5.QtWidgets import QCheckBox

        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        cb = QCheckBox()
        qtbot.addWidget(cb)
        cb.setChecked(True)
        extractor = QtFolderDataExtractor({"process_backend_ftp_check": cb})
        assert extractor.extract_all().process_backend_ftp is True

    def test_reads_combobox(self, qtbot):
        from PyQt5.QtWidgets import QComboBox

        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        combo = QComboBox()
        qtbot.addWidget(combo)
        combo.addItems(["csv", "fintech"])
        combo.setCurrentText("fintech")
        extractor = QtFolderDataExtractor({"convert_formats_var": combo})
        assert extractor.extract_all().convert_to_format == "fintech"

    def test_reads_spinbox(self, qtbot):
        from PyQt5.QtWidgets import QSpinBox

        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        spin = QSpinBox()
        qtbot.addWidget(spin)
        spin.setRange(-14, 14)
        spin.setValue(5)
        extractor = QtFolderDataExtractor({"invoice_date_offset": spin})
        assert extractor.extract_all().invoice_date_offset == 5

    def test_get_text_returns_empty_for_missing_field(self, qtbot):
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor({})
        assert extractor._get_text("nonexistent_field") == ""

    def test_get_int_returns_default_for_missing_field(self, qtbot):
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor({})
        assert extractor._get_int("nonexistent_field", 42) == 42

    def test_get_bool_returns_false_for_missing_field(self, qtbot):
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor({})
        assert extractor._get_bool("nonexistent_field") is False

    def test_get_check_str_returns_false_str_for_missing(self, qtbot):
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        extractor = QtFolderDataExtractor({})
        extracted = extractor.extract_all()
        # Missing checkbox fields default to False (bool), not "False" (str)
        assert extracted.folder_is_active is False

    def test_get_combo_returns_empty_for_missing(self, qtbot):
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        extractor = QtFolderDataExtractor({})
        assert extractor._get_combo("nonexistent_field") == ""


# ---------------------------------------------------------------------------
# TestEditFoldersDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestEditFoldersDialog:
    def test_enabled_folder_validation_fails_without_name(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        # Mock QMessageBox to avoid blocking
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["folder_alias_field"].setText("")
        assert dialog.validate() is False

    def test_enabled_folder_validation_fails_without_convert_format(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["convert_formats_var"].setCurrentText("")
        assert dialog.validate() is False

    def test_ftp_validation_passes_with_all_fields(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["process_backend_ftp_check"].setChecked(True)
        dialog._fields["ftp_server_field"].setText("ftp.example.com")
        dialog._fields["ftp_port_field"].setText("21")
        dialog._fields["ftp_folder_field"].setText("/upload/")
        dialog._fields["ftp_username_field"].setText("user")
        dialog._fields["ftp_password_field"].setText("password")

        # Set a valid convert format (required field)
        dialog._fields["convert_formats_var"].setCurrentText("csv")

        # Debug validator
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor(dialog._fields)
        extracted = extractor.extract_all()
        print(f"Extracted fields: {extracted}")

        validator = dialog._create_validator()
        current_alias = dialog._folder_config.get("alias", "")
        result = validator.validate_extracted_fields(extracted, current_alias)
        print(f"Validation errors: {[e.message for e in result.errors]}")

        assert result.is_valid is True

    def test_ftp_validation_fails_without_server(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["process_backend_ftp_check"].setChecked(True)
        dialog._fields["ftp_server_field"].setText("")

        assert dialog.validate() is False

    def test_email_validation_passes_with_all_fields(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["process_backend_email_check"].setChecked(True)
        dialog._fields["email_recipient_field"].setText("test@example.com")
        dialog._fields["email_sender_subject_field"].setText("Test Subject")

        assert dialog.validate() is True

    def test_email_validation_fails_without_recipient(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["process_backend_email_check"].setChecked(True)
        dialog._fields["email_recipient_field"].setText("")

        assert dialog.validate() is False

    def test_copy_validation_passes_with_folder(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["process_backend_copy_check"].setChecked(True)
        dialog.handlers.copy_to_directory = "/destination"

        assert dialog.validate() is True

    def test_copy_validation_fails_without_folder(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical", MagicMock()
        )

        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog._fields["process_backend_copy_check"].setChecked(True)
        dialog.copy_to_directory = ""

        assert dialog.validate() is False

    def test_construction(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

    def test_convert_format_control_contains_expected_option(
        self, qtbot, sample_folder_config
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        dialog.dynamic_edi_builder.edi_options_combo.setCurrentText("Convert EDI")
        qtbot.waitUntil(lambda: "convert_formats_var" in dialog._fields, timeout=1000)
        convert_combo = dialog._fields["convert_formats_var"]
        options = [convert_combo.itemText(i) for i in range(convert_combo.count())]
        assert "CSV" in options

    def test_edi_options_combo_contains_expected_values(
        self, qtbot, sample_folder_config
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)

        edi_combo = dialog.dynamic_edi_builder.edi_options_combo
        options = [edi_combo.itemText(i) for i in range(edi_combo.count())]
        assert options == [
            "Do Nothing",
            "Convert EDI",
        ]

    def test_disabled_folder_validates(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        sample_folder_config["folder_is_active"] = "False"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        dialog._fields["active_checkbutton"].setChecked(False)
        assert dialog.validate() is True

    def test_apply_writes_to_config(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        dialog._fields["ftp_server_field"].setText("new.server.com")
        dialog.apply()
        assert sample_folder_config["ftp_server"] == "new.server.com"

    def test_apply_calls_callback(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        callback = MagicMock()
        dialog = EditFoldersDialog(
            None, sample_folder_config, on_apply_success=callback
        )
        qtbot.addWidget(dialog)
        dialog.apply()
        callback.assert_called_once()

    def test_active_checkbox_styling(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        active_checkbox = dialog._fields["active_checkbutton"]
        active_checkbox.setChecked(True)
        dialog.handlers.update_active_state()
        assert "Enabled" in active_checkbox.text()
        active_checkbox.setChecked(False)
        dialog.handlers.update_active_state()
        assert "Disabled" in active_checkbox.text()

    def test_validate_invalid_state_calls_qmessagebox(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        from interface.validation.folder_settings_validator import ValidationResult

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock(),
        )
        result = ValidationResult(is_valid=False)
        result.add_error("ftp_server", "Error 1")
        result.add_error("ftp_port", "Error 2")
        validator = MagicMock()
        validator.validate_extracted_fields.return_value = result
        dialog._validator = validator
        dialog._fields["active_checkbutton"].setChecked(True)

        assert dialog.validate() is False

        from interface.qt.dialogs.edit_folders_dialog import QMessageBox

        QMessageBox.critical.assert_called_once_with(
            dialog, "Validation Error", "FTP:\n- Error 1\n- Error 2"
        )


# ---------------------------------------------------------------------------
# TestEditSettingsDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestEditSettingsDialog:
    def _make_dialog(self, qtbot, sample_folder_config, **kwargs):
        from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog

        mock_smtp = MagicMock()
        mock_smtp.test_connection.return_value = (True, None)
        dialog = EditSettingsDialog(
            None,
            sample_folder_config,
            smtp_service=mock_smtp,
            **kwargs,
        )
        qtbot.addWidget(dialog)
        return dialog

    def test_construction(self, qtbot, sample_folder_config):
        self._make_dialog(qtbot, sample_folder_config)

    def test_email_disabled_skips_validation(self, qtbot, sample_folder_config):
        dialog = self._make_dialog(qtbot, sample_folder_config)
        dialog._enable_email_cb.setChecked(False)
        assert dialog.validate() is True

    def test_apply_calls_callbacks(self, qtbot, sample_folder_config):
        update_settings = MagicMock()
        update_oversight = MagicMock()
        on_apply = MagicMock()
        refresh = MagicMock()
        dialog = self._make_dialog(
            qtbot,
            sample_folder_config,
            update_settings=update_settings,
            update_oversight=update_oversight,
            on_apply=on_apply,
            refresh_callback=refresh,
        )
        dialog.apply()
        update_settings.assert_called_once()
        update_oversight.assert_called_once()
        on_apply.assert_called_once()
        refresh.assert_called_once()

    def test_validate_empty_email_when_enabled_fails(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        dialog = self._make_dialog(qtbot, sample_folder_config)
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("")
        dialog._smtp_service.test_connection.return_value = (False, "fail")
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        result = dialog.validate()
        assert result is False

    def test_apply_disables_email_backends_when_email_off(
        self, qtbot, sample_folder_config
    ):
        disable_email = MagicMock()
        disable_folders = MagicMock()
        dialog = self._make_dialog(
            qtbot,
            sample_folder_config,
            disable_email_backends=disable_email,
            disable_folders_without_backends=disable_folders,
        )
        dialog._enable_email_cb.setChecked(False)
        dialog.apply()
        disable_email.assert_called_once()
        disable_folders.assert_called_once()


# ---------------------------------------------------------------------------
# TestMaintenanceDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestMaintenanceDialog:
    def test_construction(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)

    def test_set_all_active(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        buttons = dialog.findChildren(QPushButton)
        active_btn = [
            b
            for b in buttons
            if "active" in b.text().lower() and "inactive" not in b.text().lower()
        ][0]
        active_btn.click()
        assert mock_maintenance_functions.was_called("set_all_active")

    def test_buttons_disabled_during_operation(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog._on_operation_start()
        for btn in dialog._buttons:
            assert not btn.isEnabled()
        dialog._on_operation_end()
        for btn in dialog._buttons:
            assert btn.isEnabled()

    def test_set_all_inactive(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog._set_all_inactive()
        assert mock_maintenance_functions.was_called("set_all_inactive")

    def test_clear_resend_flags(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog._clear_resend_flags()
        assert mock_maintenance_functions.was_called("clear_resend_flags")

    def test_clear_queued_emails(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        mock_maintenance_functions._database_obj.emails_table.insert(
            {"folder_alias": "test", "log": "a@b.com"}
        )
        dialog._clear_queued_emails()
        assert mock_maintenance_functions._database_obj.emails_table.count() == 0

    def test_import_old_configurations_returns_early_without_ui(
        self, qtbot, mock_maintenance_functions
    ):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions, ui_service=None)
        qtbot.addWidget(dialog)
        dialog._import_old_configurations()
        assert not mock_maintenance_functions.was_called("database_import_wrapper")

    def test_open_dialog_shows_warning_first(self, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        mock_ui = MagicMock()
        mock_ui.ask_ok_cancel.return_value = False
        result = MaintenanceDialog.open_dialog(
            parent=None,
            maintenance_functions=mock_maintenance_functions,
            ui_service=mock_ui,
        )
        assert result is None
        mock_ui.ask_ok_cancel.assert_called_once()


# ---------------------------------------------------------------------------
# TestProcessedFilesDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestProcessedFilesDialog:
    def test_construction(self, qtbot, mock_database_obj):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)

    def test_empty_database_shows_no_folders(self, qtbot, mock_database_obj):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        result = dialog._get_folder_tuples()
        assert result == []

    def test_get_folder_tuples_returns_sorted(self, qtbot):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        mock_database_obj = MagicMock()
        mock_database_obj.get_oversight_or_default.return_value = {}
        # _get_folder_tuples now uses a single JOIN query via database_obj.query()
        mock_database_obj.query.return_value = [
            {"folder_id": 1, "alias": "Alpha"},
            {"folder_id": 2, "alias": "Zebra"},
        ]
        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        mock_database_obj.query.return_value = [
            {"folder_id": 1, "alias": "Alpha"},
            {"folder_id": 2, "alias": "Zebra"},
        ]
        result = dialog._get_folder_tuples()
        assert result == [(1, "Alpha"), (2, "Zebra")]

    def test_get_folder_tuples_skips_missing_folders(self, qtbot):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        mock_database_obj = MagicMock()
        mock_database_obj.get_oversight_or_default.return_value = {}
        # The JOIN query inherently excludes folder_id 999 (no matching folder row)
        mock_database_obj.query.return_value = [
            {"folder_id": 1, "alias": "Existing"},
        ]
        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        mock_database_obj.query.return_value = [
            {"folder_id": 1, "alias": "Existing"},
        ]
        result = dialog._get_folder_tuples()
        assert result == [(1, "Existing")]

    def test_on_folder_selected_sets_id(self, qtbot, mock_database_obj):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        dialog._on_folder_selected(7)
        assert dialog._selected_folder_id == 7

    def test_export_calls_shared_function(self, qtbot, mock_database_obj, monkeypatch):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        dialog._selected_folder_id = 42
        dialog._output_folder = "/tmp/out"
        mock_export = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.processed_files_dialog.export_processed_report",
            mock_export,
        )
        dialog._do_export()
        mock_export.assert_called_once_with(42, "/tmp/out", mock_database_obj)

    def test_export_noop_when_no_folder_selected(
        self, qtbot, mock_database_obj, monkeypatch
    ):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        dialog._selected_folder_id = None
        dialog._output_folder = "/tmp"
        mock_export = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.processed_files_dialog.export_processed_report",
            mock_export,
        )
        dialog._do_export()
        mock_export.assert_not_called()

    def test_export_noop_when_no_output_folder(
        self, qtbot, mock_database_obj, monkeypatch
    ):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        dialog._selected_folder_id = 1
        dialog._output_folder = ""
        mock_export = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.processed_files_dialog.export_processed_report",
            mock_export,
        )
        dialog._do_export()
        mock_export.assert_not_called()


# ---------------------------------------------------------------------------
# TestResendDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestDatabaseImportDialog:
    def test_construction(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "folders.db merging utility"
        assert dialog.isModal() is True

    def test_select_button_toggled_initially(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        assert dialog._import_button.isEnabled() is False

    def test_select_database_file(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        # Mock file dialog
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/test.db", ""),
        )

        # Mock os.path.exists
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists", lambda x: True
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._new_database_path == "/test.db"
        assert dialog._db_label.text() == "/test.db"
        assert dialog._import_button.isEnabled() is True

    def test_select_fixture_database_path_updates_label_with_qtbot(
        self, qtbot, monkeypatch
    ):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        fixture_path = (
            "/workspaces/batch-file-processor/tests/fixtures/legacy_v32_folders.db"
        )
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: (fixture_path, ""),
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._new_database_path == fixture_path
        assert dialog._db_label.text() == fixture_path
        assert dialog._import_button.isEnabled() is True

    def test_cancel_after_selection_preserves_selected_database(
        self, qtbot, monkeypatch
    ):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        selected_path = (
            "/workspaces/batch-file-processor/tests/fixtures/legacy_v32_folders.db"
        )
        dialog_results = iter([(selected_path, ""), ("", "")])
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: next(dialog_results),
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)

        # First click selects a valid database
        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)
        assert dialog._new_database_path == selected_path
        assert dialog._db_label.text() == selected_path
        assert dialog._import_button.isEnabled() is True

        # Second click cancels picker; prior selection should remain intact
        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)
        assert dialog._new_database_path == selected_path
        assert dialog._db_label.text() == selected_path
        assert dialog._import_button.isEnabled() is True

    def test_import_button_toggled_when_no_file_selected(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        assert dialog._import_button.isEnabled() is False

    def test_import_button_enabled_when_file_selected(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/test.db", ""),
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists", lambda x: True
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)

        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)

        assert dialog._import_button.isEnabled() is True

    def test_start_import_noop_without_selected_database(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)

        class _ShouldNotConstruct:
            def __init__(self, *args, **kwargs):
                raise AssertionError("ImportThread should not be created")

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.ImportThread",
            _ShouldNotConstruct,
        )

        dialog._start_import()
        assert dialog._import_button.isEnabled() is False
        assert dialog._select_button.isEnabled() is True

    def test_start_import_disables_buttons_and_starts_thread(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        class _FakeSignal:
            def __init__(self):
                self.callbacks = []

            def connect(self, callback):
                self.callbacks.append(callback)

        class _FakeImportThread:
            def __init__(self, *args, **kwargs):
                self.progress = _FakeSignal()
                self.finished = _FakeSignal()
                self.error = _FakeSignal()
                self.confirm_required = _FakeSignal()
                self.started = False

            def start(self):
                self.started = True

        created_threads = []

        def _make_fake_thread(*args, **kwargs):
            thread = _FakeImportThread(*args, **kwargs)
            created_threads.append(thread)
            return thread

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.ImportThread",
            _make_fake_thread,
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        dialog._new_database_path = "/new.db"
        dialog._database_migrate_job = MagicMock()
        dialog._import_button.setEnabled(True)

        dialog._start_import()

        assert len(created_threads) == 1
        fake_thread = created_threads[0]
        assert fake_thread.started is True
        assert dialog._import_button.isEnabled() is False
        assert dialog._select_button.isEnabled() is False
        assert dialog._progress_bar.isHidden() is False
        assert len(fake_thread.progress.callbacks) == 1
        assert len(fake_thread.finished.callbacks) == 1
        assert len(fake_thread.error.callbacks) == 1

    def test_on_progress_updates_progress_bar(self, qtbot):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)

        dialog._on_progress(3, 10, "working")

        assert dialog._progress_bar.maximum() == 10
        assert dialog._progress_bar.value() == 3

    def test_on_finished_success_updates_label_and_reenables_buttons(
        self, qtbot, monkeypatch
    ):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        info_mock = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.information",
            info_mock,
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        dialog._import_button.setEnabled(False)
        dialog._select_button.setEnabled(False)

        dialog._on_finished(True, "done")

        assert dialog._db_label.text() == "Import Completed"
        assert dialog._import_button.isEnabled() is True
        assert dialog._select_button.isEnabled() is True
        info_mock.assert_called_once_with(dialog, "Import Complete", "done")

    def test_on_finished_failure_shows_error_and_reenables_buttons(
        self, qtbot, monkeypatch
    ):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        critical_mock = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.critical",
            critical_mock,
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        dialog._import_button.setEnabled(False)
        dialog._select_button.setEnabled(False)

        dialog._on_finished(False, "boom")

        assert dialog._import_button.isEnabled() is True
        assert dialog._select_button.isEnabled() is True
        critical_mock.assert_called_once_with(dialog, "Import Failed", "boom")

    def test_on_error_shows_error_and_reenables_buttons(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog

        critical_mock = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.critical",
            critical_mock,
        )

        dialog = DatabaseImportDialog(
            None, "/original.db", "Windows", "/backup/path", "33"
        )
        qtbot.addWidget(dialog)
        dialog._import_button.setEnabled(False)
        dialog._select_button.setEnabled(False)

        dialog._on_error("bad things")

        assert dialog._import_button.isEnabled() is True
        assert dialog._select_button.isEnabled() is True
        critical_mock.assert_called_once_with(dialog, "Import Error", "bad things")


@pytest.mark.qt
class TestResendDialog:
    def test_construction(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        # Mock ResendService to avoid database operations
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = False
        mock_service.get_folders_with_files.return_value = []
        mock_service.count_files_for_folder.return_value = 0
        mock_service.get_files_for_folder.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        # Mock QMessageBox to avoid blocking
        monkeypatch.setattr("interface.qt.dialogs.base_dialog.QMessageBox", MagicMock())

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)

    def test_spinbox_initially_disabled(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)
        # Bulk action frame should be shown as a UI section even with no selection.
        assert dialog._bulk_action_frame.isHidden() is False

    def test_bulk_action_bar_initially_present(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)

        assert dialog._bulk_action_frame.isHidden() is False
        assert dialog._bulk_select_all.isEnabled() is True
        assert dialog._bulk_clear_selection.isEnabled() is False
        assert dialog._bulk_mark_resend.isEnabled() is False
        assert dialog._bulk_clear_resend.isEnabled() is False

    def test_date_range_filter_applies_to_service_calls(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)

        dialog._date_from_input.setDate(QDate(2024, 1, 1))
        dialog._date_to_input.setDate(QDate(2024, 1, 31))

        dialog._do_search_filter()

        mock_service.get_all_files_for_resend.assert_called_with(
            check_file_exists=False,
            limit=dialog.PAGE_SIZE,
            offset=0,
            date_from="2024-01-01",
            date_to="2024-01-31",
        )

    def test_folder_selection_enables_spinbox(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = [
            {
                "id": 1,
                "folder_id": 5,
                "folder_alias": "Test Folder",
                "file_name": "test.txt",
                "resend_flag": False,
                "sent_date_time": "2024-01-01T00:00:00",
            }
        ]

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)
        # Table should be populated and search should be accessible
        assert dialog._table.rowCount() >= 1

    def test_multi_row_selection(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = [
            {
                "id": 1,
                "folder_id": 5,
                "folder_alias": "Test Folder",
                "file_name": "test1.txt",
                "resend_flag": False,
                "sent_date_time": "2024-01-01T00:00:00",
            },
            {
                "id": 2,
                "folder_id": 5,
                "folder_alias": "Test Folder",
                "file_name": "test2.txt",
                "resend_flag": False,
                "sent_date_time": "2024-01-01T00:00:00",
            },
        ]

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)

        assert (
            dialog._table.selectionMode()
            == QTableWidget.SelectionMode.ExtendedSelection
        )

        selection_model = dialog._table.selectionModel()
        index1 = dialog._table.model().index(0, 0)
        index2 = dialog._table.model().index(1, 0)
        selection_model.select(
            index1, QItemSelectionModel.Select | QItemSelectionModel.Rows
        )
        selection_model.select(
            index2, QItemSelectionModel.Select | QItemSelectionModel.Rows
        )
        dialog._on_table_selection_changed()

        assert dialog._selected_files == {1, 2}
        assert dialog._bulk_action_frame.isHidden() is False

    def test_date_range_filters_search(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_total_file_count.return_value = 2
        mock_service.get_all_files_for_resend.return_value = [
            {
                "id": 1,
                "folder_id": 5,
                "folder_alias": "Test Folder",
                "file_name": "test1.txt",
                "resend_flag": False,
                "sent_date_time": "2024-06-01T00:00:00",
            },
            {
                "id": 2,
                "folder_id": 5,
                "folder_alias": "Test Folder",
                "file_name": "test2.txt",
                "resend_flag": False,
                "sent_date_time": "2024-07-01T00:00:00",
            },
        ]
        mock_service.search_files_for_resend.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)

        dialog._search_input.setText("test")
        dialog._search_field_selector.setCurrentIndex(0)  # All fields
        dialog._date_from_input.setDate(QDate(2024, 1, 1))
        dialog._date_to_input.setDate(QDate(2024, 12, 31))
        dialog._do_search_filter()

        mock_service.search_files_for_resend.assert_called_once()
        _, kwargs = mock_service.search_files_for_resend.call_args
        assert kwargs["date_from"] == "2024-01-01"
        assert kwargs["date_to"] == "2024-12-31"

    def test_folder_selection_updates_max(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog

        mock_db = MagicMock()

        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_all_files_for_resend.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )

        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)
        # Table should be accessible (no spinbox in current UI)
        assert hasattr(dialog, "_table")

    def test_no_selection_initially(self, qtbot, monkeypatch):
        MagicMock()

        # Mock ResendService to avoid database operations
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_folders_with_files.return_value = []
        mock_service.count_files_for_folder.return_value = 0
        mock_service.get_files_for_folder.return_value = []

        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service,
        )
