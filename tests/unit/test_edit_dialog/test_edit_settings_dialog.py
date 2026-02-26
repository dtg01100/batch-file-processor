"""Tests for EditSettingsDialog to verify initialization, field population, and functionality.

Dialogs are tested via direct widget manipulation, never exec() or show().
Uses pytest-qt (qtbot fixture) for proper widget lifecycle management.
"""

import pytest
from unittest.mock import MagicMock, patch

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog


def _make_dialog(qtbot, settings_data=None, **kwargs):
    """Helper to create an EditSettingsDialog with a mock SMTP service."""
    if settings_data is None:
        settings_data = {}
    mock_smtp = MagicMock()
    mock_smtp.test_connection.return_value = (True, None)
    dialog = EditSettingsDialog(
        None,
        settings_data,
        smtp_service=mock_smtp,
        **kwargs,
    )
    qtbot.addWidget(dialog)
    return dialog


class TestEditSettingsDialogInitialization:
    """Test suite for EditSettingsDialog initialization."""

    def test_dialog_inherits_from_base_dialog(self):
        """Test that EditSettingsDialog inherits from BaseDialog."""
        from interface.qt.dialogs.base_dialog import BaseDialog
        assert issubclass(EditSettingsDialog, BaseDialog)

    def test_dialog_initialization_with_minimal_parameters(self, qtbot):
        """Test that dialog can be initialized with minimal parameters."""
        dialog = _make_dialog(qtbot)

        assert dialog is not None
        assert dialog.windowTitle() == "Edit Settings"
        assert dialog.isModal()

    def test_dialog_initialization_with_custom_title(self, qtbot):
        """Test that dialog accepts custom title parameter."""
        dialog = _make_dialog(qtbot, title="Custom Settings Dialog")

        assert dialog.windowTitle() == "Custom Settings Dialog"

    def test_dialog_initialization_with_all_parameters(self, qtbot):
        """Test that dialog accepts all optional callback parameters."""
        mock_settings_provider = MagicMock(return_value={})
        mock_oversight_provider = MagicMock()
        mock_update_settings = MagicMock()
        mock_update_oversight = MagicMock()
        mock_on_apply = MagicMock()
        mock_refresh_callback = MagicMock()
        mock_count_email_backends = MagicMock(return_value=0)
        mock_count_disabled_folders = MagicMock(return_value=0)
        mock_disable_email_backends = MagicMock()
        mock_disable_folders_without_backends = MagicMock()

        dialog = _make_dialog(
            qtbot,
            settings_data={},
            title="Test Settings",
            settings_provider=mock_settings_provider,
            oversight_provider=mock_oversight_provider,
            update_settings=mock_update_settings,
            update_oversight=mock_update_oversight,
            on_apply=mock_on_apply,
            refresh_callback=mock_refresh_callback,
            count_email_backends=mock_count_email_backends,
            count_disabled_folders=mock_count_disabled_folders,
            disable_email_backends=mock_disable_email_backends,
            disable_folders_without_backends=mock_disable_folders_without_backends,
        )

        assert dialog is not None
        assert dialog.windowTitle() == "Test Settings"

    def test_dialog_stores_settings_data(self, qtbot):
        """Test that dialog stores a copy of the settings_data dict."""
        settings_data = {"enable_reporting": "True", "logs_directory": "/logs"}
        dialog = _make_dialog(qtbot, settings_data=settings_data)

        # Dialog should have stored the settings data
        assert dialog._settings_data is not settings_data  # should be a copy
        assert dialog._settings_data["enable_reporting"] == "True"
        assert dialog._settings_data["logs_directory"] == "/logs"

    def test_dialog_calls_settings_provider_on_init(self, qtbot):
        """Test that dialog calls settings_provider during initialization."""
        mock_settings = {"as400_address": "test.server.com"}
        mock_settings_provider = MagicMock(return_value=mock_settings)

        dialog = _make_dialog(qtbot, settings_provider=mock_settings_provider)

        mock_settings_provider.assert_called_once()


class TestEditSettingsDialogOpening:
    """Test suite for EditSettingsDialog opening behavior."""

    def test_dialog_has_minimum_size(self, qtbot):
        """Test that dialog has appropriate minimum size."""
        dialog = _make_dialog(qtbot)

        assert dialog.minimumWidth() == 550
        assert dialog.minimumHeight() == 500

    def test_dialog_is_modal(self, qtbot):
        """Test that dialog is modal."""
        dialog = _make_dialog(qtbot)

        assert dialog.isModal() is True

    def test_dialog_has_button_box(self, qtbot):
        """Test that dialog has standard OK/Cancel button box."""
        dialog = _make_dialog(qtbot)

        assert dialog._button_box is not None
        assert dialog._button_box.button(dialog._button_box.StandardButton.Ok) is not None
        assert dialog._button_box.button(dialog._button_box.StandardButton.Cancel) is not None


class TestEditSettingsDialogFieldPopulation:
    """Test suite for verifying fields are populated with settings data."""

    def test_as400_fields_populated_from_settings(self, qtbot):
        """Test that AS400 fields are populated from settings provider."""
        mock_settings = {
            "as400_address": "AS400.example.com",
            "as400_username": "user123",
            "as400_password": "password123",
        }
        dialog = _make_dialog(qtbot, settings_provider=MagicMock(return_value=mock_settings))

        assert dialog._as400_address.text() == "AS400.example.com"
        assert dialog._as400_username.text() == "user123"
        assert dialog._as400_password.text() == "password123"

    def test_email_fields_populated_from_settings(self, qtbot):
        """Test that email fields are populated from settings provider."""
        mock_settings = {
            "enable_email": True,
            "email_address": "sender@example.com",
            "email_username": "smtpuser",
            "email_password": "smtppass",
            "email_smtp_server": "smtp.example.com",
            "smtp_port": "587",
        }
        dialog = _make_dialog(qtbot, settings_provider=MagicMock(return_value=mock_settings))

        assert dialog._enable_email_cb.isChecked() is True
        assert dialog._email_address.text() == "sender@example.com"
        assert dialog._email_username.text() == "smtpuser"
        assert dialog._email_password.text() == "smtppass"
        assert dialog._email_smtp_server.text() == "smtp.example.com"
        assert dialog._email_smtp_port.text() == "587"

    def test_reporting_fields_populated_from_settings_data(self, qtbot):
        """Test that reporting fields are populated from settings_data dict.

        Note: reporting requires email to be enabled; the dialog enforces this
        by unchecking reporting when email is off. We enable email via the
        settings provider so the reporting checkbox stays checked.
        """
        settings_data = {
            "enable_reporting": "True",
            "report_email_destination": "test@example.com",
            "report_edi_errors": True,
            "report_printing_fallback": "False",
        }
        # Enable email so that reporting can remain checked
        mock_settings = {"enable_email": True}
        dialog = _make_dialog(
            qtbot,
            settings_data=settings_data,
            settings_provider=MagicMock(return_value=mock_settings),
        )

        assert dialog._enable_reporting_cb.isChecked() is True
        assert dialog._email_destination.text() == "test@example.com"
        assert dialog._report_edi_warnings_cb.isChecked() is True
        assert dialog._enable_report_printing_cb.isChecked() is False

    def test_backup_fields_populated_from_settings(self, qtbot):
        """Test that backup fields are populated from settings provider."""
        mock_settings = {
            "enable_interval_backups": True,
            "backup_counter_maximum": 200,
        }
        dialog = _make_dialog(qtbot, settings_provider=MagicMock(return_value=mock_settings))

        assert dialog._enable_backup_cb.isChecked() is True
        assert dialog._backup_interval_spin.value() == 200

    def test_odbc_driver_added_when_not_in_list(self, qtbot):
        """Test that a custom ODBC driver is added to the combo if not present."""
        mock_settings = {"odbc_driver": "My Custom ODBC Driver"}
        dialog = _make_dialog(qtbot, settings_provider=MagicMock(return_value=mock_settings))

        assert dialog._odbc_driver_combo.currentText() == "My Custom ODBC Driver"

    def test_empty_settings_use_defaults(self, qtbot):
        """Test that empty settings result in sensible defaults."""
        dialog = _make_dialog(qtbot)

        assert dialog._enable_email_cb.isChecked() is False
        assert dialog._enable_reporting_cb.isChecked() is False
        assert dialog._enable_backup_cb.isChecked() is False
        assert dialog._backup_interval_spin.value() == 100


class TestEditSettingsDialogFieldInteraction:
    """Test suite for field interaction and UI behavior."""

    def test_email_fields_enabled_when_email_checked(self, qtbot):
        """Test that email fields are enabled when 'Enable Email' is checked."""
        dialog = _make_dialog(qtbot)

        dialog._enable_email_cb.setChecked(True)

        assert dialog._email_fields_widget.isEnabled() is True
        assert dialog._enable_reporting_cb.isEnabled() is True

    def test_email_fields_disabled_when_email_unchecked(self, qtbot):
        """Test that email fields are disabled when 'Enable Email' is unchecked."""
        dialog = _make_dialog(qtbot)

        dialog._enable_email_cb.setChecked(False)

        assert dialog._email_fields_widget.isEnabled() is False
        assert dialog._enable_reporting_cb.isEnabled() is False
        assert dialog._enable_reporting_cb.isChecked() is False

    def test_reporting_fields_enabled_when_reporting_checked(self, qtbot):
        """Test that reporting fields are enabled when 'Enable Reporting' is checked."""
        dialog = _make_dialog(qtbot)

        dialog._enable_email_cb.setChecked(True)
        dialog._enable_reporting_cb.setChecked(True)

        assert dialog._reporting_fields_widget.isEnabled() is True
        assert dialog._report_edi_warnings_cb.isEnabled() is True

    def test_reporting_fields_disabled_when_reporting_unchecked(self, qtbot):
        """Test that reporting fields are disabled when 'Enable Reporting' is unchecked."""
        dialog = _make_dialog(qtbot)

        dialog._enable_email_cb.setChecked(True)
        dialog._enable_reporting_cb.setChecked(False)

        assert dialog._reporting_fields_widget.isEnabled() is False
        assert dialog._report_edi_warnings_cb.isEnabled() is False

    def test_backup_spinbox_enabled_when_backup_checked(self, qtbot):
        """Test that backup interval spinbox is enabled when 'Enable Backup' is checked."""
        dialog = _make_dialog(qtbot)

        dialog._enable_backup_cb.setChecked(True)

        assert dialog._backup_interval_spin.isEnabled() is True

    def test_backup_spinbox_disabled_when_backup_unchecked(self, qtbot):
        """Test that backup interval spinbox is disabled when 'Enable Backup' is unchecked."""
        dialog = _make_dialog(qtbot)

        dialog._enable_backup_cb.setChecked(False)

        assert dialog._backup_interval_spin.isEnabled() is False

    def test_disabling_email_also_disables_reporting(self, qtbot):
        """Test that disabling email also disables and unchecks reporting."""
        dialog = _make_dialog(qtbot)

        # Enable both first
        dialog._enable_email_cb.setChecked(True)
        dialog._enable_reporting_cb.setChecked(True)

        # Now disable email
        dialog._enable_email_cb.setChecked(False)

        assert dialog._enable_reporting_cb.isChecked() is False
        assert dialog._enable_reporting_cb.isEnabled() is False


class TestEditSettingsDialogValidation:
    """Test suite for validation logic."""

    def test_validation_passes_when_email_disabled(self, qtbot):
        """Test that validation passes when email is disabled."""
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(False)

        assert dialog.validate() is True

    def test_validation_fails_with_empty_email_address(self, qtbot, monkeypatch):
        """Test that validation fails when email is enabled but address is empty."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("")

        assert dialog.validate() is False

    def test_validation_fails_with_invalid_email_format(self, qtbot, monkeypatch):
        """Test that validation fails with invalid email format."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("not-a-valid-email")
        dialog._smtp_service.test_connection.return_value = (True, None)

        assert dialog.validate() is False

    def test_validation_fails_with_smtp_connection_error(self, qtbot, monkeypatch):
        """Test that validation fails when SMTP connection test fails."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("test@example.com")
        dialog._email_smtp_server.setText("smtp.example.com")
        dialog._email_smtp_port.setText("587")
        dialog._smtp_service.test_connection.return_value = (False, "Connection refused")

        assert dialog.validate() is False

    def test_validation_fails_with_missing_smtp_server(self, qtbot, monkeypatch):
        """Test that validation fails when SMTP server is missing."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("test@example.com")
        dialog._email_smtp_server.setText("")
        dialog._smtp_service.test_connection.return_value = (True, None)

        assert dialog.validate() is False

    def test_validation_fails_with_missing_smtp_port(self, qtbot, monkeypatch):
        """Test that validation fails when SMTP port is missing."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("test@example.com")
        dialog._email_smtp_server.setText("smtp.example.com")
        dialog._email_smtp_port.setText("")
        dialog._smtp_service.test_connection.return_value = (True, None)

        assert dialog.validate() is False

    def test_validation_fails_with_invalid_reporting_email(self, qtbot, monkeypatch):
        """Test that validation fails with invalid reporting email destination."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._enable_reporting_cb.setChecked(True)
        dialog._email_destination.setText("not-valid-email")

        assert dialog.validate() is False

    def test_validation_fails_with_missing_reporting_email(self, qtbot, monkeypatch):
        """Test that validation fails when reporting is enabled but destination is empty."""
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_settings_dialog.QMessageBox.critical",
            MagicMock(),
        )
        dialog = _make_dialog(qtbot)
        dialog._enable_email_cb.setChecked(True)
        dialog._enable_reporting_cb.setChecked(True)
        dialog._email_destination.setText("")

        assert dialog.validate() is False


class TestEditSettingsDialogSaveFunctionality:
    """Test suite for settings save functionality."""

    def test_apply_calls_update_settings(self, qtbot):
        """Test that apply() calls update_settings callback."""
        update_settings = MagicMock()
        dialog = _make_dialog(qtbot, update_settings=update_settings)

        dialog.apply()

        update_settings.assert_called_once()

    def test_apply_calls_update_oversight(self, qtbot):
        """Test that apply() calls update_oversight callback."""
        update_oversight = MagicMock()
        dialog = _make_dialog(qtbot, update_oversight=update_oversight)

        dialog.apply()

        update_oversight.assert_called_once()

    def test_apply_calls_on_apply(self, qtbot):
        """Test that apply() calls on_apply callback."""
        on_apply = MagicMock()
        dialog = _make_dialog(qtbot, on_apply=on_apply)

        dialog.apply()

        on_apply.assert_called_once()

    def test_apply_calls_refresh_callback(self, qtbot):
        """Test that apply() calls refresh_callback."""
        refresh = MagicMock()
        dialog = _make_dialog(qtbot, refresh_callback=refresh)

        dialog.apply()

        refresh.assert_called_once()

    def test_apply_calls_all_callbacks(self, qtbot):
        """Test that apply() calls all registered callbacks."""
        update_settings = MagicMock()
        update_oversight = MagicMock()
        on_apply = MagicMock()
        refresh = MagicMock()

        dialog = _make_dialog(
            qtbot,
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

    def test_apply_updates_settings_with_field_values(self, qtbot):
        """Test that apply() passes correct field values to update_settings."""
        update_settings = MagicMock()
        dialog = _make_dialog(qtbot, update_settings=update_settings)

        dialog._as400_address.setText("new-as400.example.com")
        dialog._as400_username.setText("newuser")
        dialog._as400_password.setText("newpass")
        dialog._enable_email_cb.setChecked(True)
        dialog._email_address.setText("new@example.com")
        dialog._enable_backup_cb.setChecked(True)
        dialog._backup_interval_spin.setValue(300)

        dialog.apply()

        updated_settings = update_settings.call_args[0][0]
        assert updated_settings["as400_address"] == "new-as400.example.com"
        assert updated_settings["as400_username"] == "newuser"
        assert updated_settings["as400_password"] == "newpass"
        assert updated_settings["enable_email"] is True
        assert updated_settings["email_address"] == "new@example.com"
        assert updated_settings["enable_interval_backups"] is True
        assert updated_settings["backup_counter_maximum"] == 300

    def test_apply_updates_oversight_with_reporting_values(self, qtbot):
        """Test that apply() passes correct reporting values to update_oversight."""
        update_oversight = MagicMock()
        dialog = _make_dialog(qtbot, update_oversight=update_oversight)

        dialog._enable_email_cb.setChecked(True)
        dialog._enable_reporting_cb.setChecked(True)
        dialog._email_destination.setText("recipient@example.com")
        dialog._report_edi_warnings_cb.setChecked(True)
        dialog._enable_report_printing_cb.setChecked(True)

        dialog.apply()

        updated_oversight = update_oversight.call_args[0][0]
        assert updated_oversight["enable_reporting"] == "True"
        assert updated_oversight["report_email_destination"] == "recipient@example.com"
        assert updated_oversight["report_edi_errors"] is True
        assert updated_oversight["report_printing_fallback"] == "True"

    def test_apply_disables_email_backends_when_email_off(self, qtbot):
        """Test that apply() calls disable_email_backends when email is disabled."""
        disable_email = MagicMock()
        disable_folders = MagicMock()

        dialog = _make_dialog(
            qtbot,
            disable_email_backends=disable_email,
            disable_folders_without_backends=disable_folders,
        )
        dialog._enable_email_cb.setChecked(False)
        dialog.apply()

        disable_email.assert_called_once()
        disable_folders.assert_called_once()

    def test_apply_does_not_disable_backends_when_email_on(self, qtbot):
        """Test that apply() does not call disable callbacks when email is enabled."""
        disable_email = MagicMock()
        disable_folders = MagicMock()

        dialog = _make_dialog(
            qtbot,
            disable_email_backends=disable_email,
            disable_folders_without_backends=disable_folders,
        )
        dialog._enable_email_cb.setChecked(True)
        dialog.apply()

        disable_email.assert_not_called()
        disable_folders.assert_not_called()

    def test_ok_button_triggers_validate_and_apply(self, qtbot):
        """Test that clicking OK button triggers validation and apply."""
        from PyQt6.QtCore import Qt

        dialog = _make_dialog(qtbot)

        with patch.object(dialog, 'validate', return_value=True) as mock_validate:
            with patch.object(dialog, 'apply') as mock_apply:
                ok_button = dialog._button_box.button(dialog._button_box.StandardButton.Ok)
                qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

                assert mock_validate.called
                assert mock_apply.called

    def test_ok_button_aborts_when_validation_fails(self, qtbot):
        """Test that clicking OK button does not call apply when validation fails."""
        from PyQt6.QtCore import Qt

        dialog = _make_dialog(qtbot)

        with patch.object(dialog, 'validate', return_value=False) as mock_validate:
            with patch.object(dialog, 'apply') as mock_apply:
                ok_button = dialog._button_box.button(dialog._button_box.StandardButton.Ok)
                qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

                assert mock_validate.called
                assert not mock_apply.called


class TestEditSettingsDialogBaseDialogPattern:
    """Test that EditSettingsDialog follows the BaseDialog pattern."""

    def test_has_body_method(self):
        """Test that dialog has required body() method."""
        assert hasattr(EditSettingsDialog, 'body')
        assert callable(getattr(EditSettingsDialog, 'body'))

    def test_has_apply_method(self):
        """Test that dialog has required apply() method."""
        assert hasattr(EditSettingsDialog, 'apply')
        assert callable(getattr(EditSettingsDialog, 'apply'))

    def test_has_validate_method(self):
        """Test that dialog has required validate() method."""
        assert hasattr(EditSettingsDialog, 'validate')
        assert callable(getattr(EditSettingsDialog, 'validate'))

    def test_dialog_is_subclass_of_qdialog(self):
        """Test that dialog is ultimately a QDialog subclass."""
        from PyQt6.QtWidgets import QDialog
        assert issubclass(EditSettingsDialog, QDialog)

    def test_dialog_has_four_sections(self, qtbot):
        """Test that dialog body builds all four expected sections."""
        dialog = _make_dialog(qtbot)

        # Verify all four section widgets exist
        assert hasattr(dialog, '_odbc_driver_combo')       # AS400 section
        assert hasattr(dialog, '_enable_email_cb')          # Email section
        assert hasattr(dialog, '_enable_reporting_cb')      # Reporting section
        assert hasattr(dialog, '_enable_backup_cb')         # Backup section
