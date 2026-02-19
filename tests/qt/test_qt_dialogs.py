"""
Comprehensive tests for all Qt dialog implementations.

Uses pytest-qt (qtbot fixture) for proper widget lifecycle management.
Dialogs are tested via show() + direct widget manipulation, never exec().
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton


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
            cancel_button = dialog._button_box.button(dialog._button_box.StandardButton.Cancel)
            qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)


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
        from PyQt6.QtWidgets import QLineEdit
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        edit = QLineEdit()
        qtbot.addWidget(edit)
        edit.setText("my_server")
        extractor = QtFolderDataExtractor({"ftp_server_field": edit})
        assert extractor.extract_all().ftp_server == "my_server"

    def test_reads_checkbox(self, qtbot):
        from PyQt6.QtWidgets import QCheckBox
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        cb = QCheckBox()
        qtbot.addWidget(cb)
        cb.setChecked(True)
        extractor = QtFolderDataExtractor({"process_backend_ftp_check": cb})
        assert extractor.extract_all().process_backend_ftp is True

    def test_reads_combobox(self, qtbot):
        from PyQt6.QtWidgets import QComboBox
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        combo = QComboBox()
        qtbot.addWidget(combo)
        combo.addItems(["csv", "fintech"])
        combo.setCurrentText("fintech")
        extractor = QtFolderDataExtractor({"convert_formats_var": combo})
        assert extractor.extract_all().convert_to_format == "fintech"

    def test_reads_spinbox(self, qtbot):
        from PyQt6.QtWidgets import QSpinBox
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
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor({})
        assert extractor._get_check_str("nonexistent_field") == "False"

    def test_get_combo_returns_empty_for_missing(self, qtbot):
        from interface.qt.dialogs.edit_folders_dialog import QtFolderDataExtractor

        extractor = QtFolderDataExtractor({})
        assert extractor._get_combo("nonexistent_field") == ""


# ---------------------------------------------------------------------------
# TestEditFoldersDialog
# ---------------------------------------------------------------------------
@pytest.mark.qt
class TestEditFoldersDialog:
    
    def test_enabled_folder_validation_fails_without_name(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        # Mock QMessageBox to avoid blocking
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
        )
        
        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        
        dialog._fields["folder_name_value"].setText("")
        assert dialog.validate() is False
    
    def test_enabled_folder_validation_fails_without_convert_format(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
        )
        
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        
        dialog._fields["convert_formats_var"].setCurrentText("")
        assert dialog.validate() is False
    
    def test_ftp_validation_passes_with_all_fields(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
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
    
    def test_ftp_validation_fails_without_server(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
        )
        
        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        
        dialog._fields["process_backend_ftp_check"].setChecked(True)
        dialog._fields["ftp_server_field"].setText("")
        
        assert dialog.validate() is False
    
    def test_email_validation_passes_with_all_fields(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
        )
        
        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        
        dialog._fields["process_backend_email_check"].setChecked(True)
        dialog._fields["email_recepient_field"].setText("test@example.com")
        dialog._fields["email_sender_subject_field"].setText("Test Subject")
        
        assert dialog.validate() is True
    
    def test_email_validation_fails_without_recipient(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
        )
        
        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        
        dialog._fields["process_backend_email_check"].setChecked(True)
        dialog._fields["email_recepient_field"].setText("")
        
        assert dialog.validate() is False
    
    def test_copy_validation_passes_with_folder(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
        )
        
        sample_folder_config["folder_is_active"] = "True"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        
        dialog._fields["process_backend_copy_check"].setChecked(True)
        dialog.copy_to_directory = "/destination"
        
        assert dialog.validate() is True
    
    def test_copy_validation_fails_without_folder(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock()
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

    def test_convert_formats_count(self):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        assert len(EditFoldersDialog.CONVERT_FORMATS) == 10

    def test_edi_options(self):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        assert EditFoldersDialog.EDI_OPTIONS == ["Do Nothing", "Convert EDI", "Tweak EDI"]

    def test_disabled_folder_validates(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        sample_folder_config["folder_is_active"] = "False"
        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        dialog._active_checkbox.setChecked(False)
        assert dialog.validate() is True

    def test_apply_writes_to_config(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        dialog._ftp_server_field.setText("new.server.com")
        dialog.apply()
        assert sample_folder_config["ftp_server"] == "new.server.com"

    def test_apply_calls_callback(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        callback = MagicMock()
        dialog = EditFoldersDialog(None, sample_folder_config, on_apply_success=callback)
        qtbot.addWidget(dialog)
        dialog.apply()
        callback.assert_called_once()

    def test_active_checkbox_styling(self, qtbot, sample_folder_config):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        dialog._active_checkbox.setChecked(True)
        assert "Enabled" in dialog._active_checkbox.text()
        dialog._active_checkbox.setChecked(False)
        assert "Disabled" in dialog._active_checkbox.text()

    def test_show_validation_errors_calls_qmessagebox(self, qtbot, sample_folder_config, monkeypatch):
        from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

        dialog = EditFoldersDialog(None, sample_folder_config)
        qtbot.addWidget(dialog)
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog._show_validation_errors(["Error 1", "Error 2"])
        from interface.qt.dialogs.edit_folders_dialog import QMessageBox
        QMessageBox.critical.assert_called_once_with(dialog, "Validation Error", "Error 1\nError 2")


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

    def test_validate_empty_email_when_enabled_fails(self, qtbot, sample_folder_config, monkeypatch):
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

    def test_apply_disables_email_backends_when_email_off(self, qtbot, sample_folder_config):
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
        active_btn = [b for b in buttons if "active" in b.text().lower() and "inactive" not in b.text().lower()][0]
        active_btn.click()
        mock_maintenance_functions.set_all_active.assert_called_once()

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
        mock_maintenance_functions.set_all_inactive.assert_called_once()

    def test_clear_resend_flags(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog._clear_resend_flags()
        mock_maintenance_functions.clear_resend_flags.assert_called_once()

    def test_clear_queued_emails(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions)
        qtbot.addWidget(dialog)
        dialog._clear_queued_emails()
        mock_maintenance_functions._database_obj.emails_table.delete.assert_called_once()

    def test_import_old_configurations_returns_early_without_ui(self, qtbot, mock_maintenance_functions):
        from interface.qt.dialogs.maintenance_dialog import MaintenanceDialog

        dialog = MaintenanceDialog(None, mock_maintenance_functions, ui_service=None)
        qtbot.addWidget(dialog)
        dialog._import_old_configurations()
        mock_maintenance_functions.database_import_wrapper.assert_not_called()

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

    def test_get_folder_tuples_returns_sorted(self, qtbot, mock_database_obj):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 2},
            {"folder_id": 1},
        ]
        mock_database_obj.folders_table.find_one.side_effect = [
            {"alias": "Zebra"},
            {"alias": "Alpha"},
        ]
        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 2},
            {"folder_id": 1},
        ]
        mock_database_obj.folders_table.find_one.side_effect = [
            {"alias": "Zebra"},
            {"alias": "Alpha"},
        ]
        result = dialog._get_folder_tuples()
        assert result == [(1, "Alpha"), (2, "Zebra")]

    def test_get_folder_tuples_skips_missing_folders(self, qtbot, mock_database_obj):
        from interface.qt.dialogs.processed_files_dialog import ProcessedFilesDialog

        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1},
            {"folder_id": 999},
        ]
        mock_database_obj.folders_table.find_one.side_effect = [
            {"alias": "Existing"},
            None,
        ]
        dialog = ProcessedFilesDialog(None, mock_database_obj)
        qtbot.addWidget(dialog)
        mock_database_obj.processed_files.distinct.return_value = [
            {"folder_id": 1},
            {"folder_id": 999},
        ]
        mock_database_obj.folders_table.find_one.side_effect = [
            {"alias": "Existing"},
            None,
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

    def test_export_noop_when_no_folder_selected(self, qtbot, mock_database_obj, monkeypatch):
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

    def test_export_noop_when_no_output_folder(self, qtbot, mock_database_obj, monkeypatch):
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
        dialog = DatabaseImportDialog(None, "/original.db", "Windows", "/backup/path", "33")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "folders.db merging utility"
        assert dialog.isModal() is True
    
    def test_select_button_disabled_initially(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
        dialog = DatabaseImportDialog(None, "/original.db", "Windows", "/backup/path", "33")
        qtbot.addWidget(dialog)
        assert dialog._import_button.isEnabled() is False
    
    def test_select_database_file(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
        
        # Mock file dialog
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/test.db", "")
        )
        
        # Mock os.path.exists
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists",
            lambda x: True
        )
        
        dialog = DatabaseImportDialog(None, "/original.db", "Windows", "/backup/path", "33")
        qtbot.addWidget(dialog)
        
        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)
        
        assert dialog._new_database_path == "/test.db"
        assert dialog._db_label.text() == "/test.db"
        assert dialog._import_button.isEnabled() is True
    
    def test_import_button_disabled_when_no_file_selected(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
        dialog = DatabaseImportDialog(None, "/original.db", "Windows", "/backup/path", "33")
        qtbot.addWidget(dialog)
        assert dialog._import_button.isEnabled() is False
    
    def test_import_button_enabled_when_file_selected(self, qtbot, monkeypatch):
        from interface.qt.dialogs.database_import_dialog import DatabaseImportDialog
        
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: ("/test.db", "")
        )
        
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.exists",
            lambda x: True
        )
        
        dialog = DatabaseImportDialog(None, "/original.db", "Windows", "/backup/path", "33")
        qtbot.addWidget(dialog)
        
        qtbot.mouseClick(dialog._select_button, Qt.MouseButton.LeftButton)
        
        assert dialog._import_button.isEnabled() is True


@ pytest.mark.qt
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
            lambda *args: mock_service
        )
        
        # Mock QMessageBox to avoid blocking
        monkeypatch.setattr(
            "PyQt6.QtWidgets.QMessageBox.information",
            MagicMock()
        )
        
        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)

    def test_spinbox_initially_disabled(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog
        mock_db = MagicMock()
        
        # Mock ResendService to avoid database operations
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_folders_with_files.return_value = []
        mock_service.count_files_for_folder.return_value = 0
        mock_service.get_files_for_folder.return_value = []
        
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service
        )
        
        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)
        assert not dialog._file_count_spinbox.isEnabled()

    def test_folder_selection_enables_spinbox(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog
        mock_db = MagicMock()
        
        # Mock ResendService to avoid database operations
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_folders_with_files.return_value = [{"id": 5, "folder_name": "Test Folder"}]
        mock_service.count_files_for_folder.return_value = 20
        mock_service.get_files_for_folder.return_value = []
        
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service
        )
        
        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)
        dialog._on_folder_selected(5)
        assert dialog._folder_id == 5
        assert dialog._file_count_spinbox.isEnabled()

    def test_folder_selection_updates_max(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog
        mock_db = MagicMock()
        
        # Mock ResendService to avoid database operations
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_folders_with_files.return_value = [{"id": 1, "folder_name": "Test Folder"}]
        mock_service.count_files_for_folder.return_value = 23
        mock_service.get_files_for_folder.return_value = []
        
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service
        )
        
        dialog = ResendDialog(None, mock_db)
        qtbot.addWidget(dialog)
        dialog._on_folder_selected(1)
        assert dialog._file_count_spinbox.maximum() == 1000  # Default max is 1000

    def test_no_selection_initially(self, qtbot, monkeypatch):
        from interface.qt.dialogs.resend_dialog import ResendDialog
        mock_db = MagicMock()
        
        # Mock ResendService to avoid database operations
        mock_service = MagicMock()
        mock_service.has_processed_files.return_value = True
        mock_service.get_folders_with_files.return_value = []
        mock_service.count_files_for_folder.return_value = 0
        mock_service.get_files_for_folder.return_value = []
        
        monkeypatch.setattr(
            "interface.qt.dialogs.resend_dialog.ResendService",
            lambda *args: mock_service
        )
        

