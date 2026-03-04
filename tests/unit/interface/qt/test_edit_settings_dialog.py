"""Comprehensive tests for EditSettingsDialog.

Tests cover:
- UI initialization and widget creation
- AS400 section functionality
- Email section functionality and validation
- Reporting section functionality
- Backup section functionality
- Field population and signal connections
- Validation logic and error messages
- Save/cancel operations
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialogButtonBox, QMessageBox, QLineEdit
from PyQt6.QtCore import Qt

from interface.qt.dialogs.edit_settings_dialog import EditSettingsDialog
from interface.services.smtp_service import SMTPService


@pytest.fixture
def sample_settings():
    """Provide sample settings data (from settings_provider)."""
    return {
        "odbc_driver": "iSeries Access ODBC Driver",
        "as400_address": "test.server.com",
        "as400_username": "testuser",
        "as400_password": "testpass",
        "enable_email": True,
        "email_address": "test@example.com",
        "email_username": "emailuser",
        "email_password": "emailpass",
        "email_smtp_server": "smtp.example.com",
        "smtp_port": "587",
        "enable_interval_backups": False,
        "backup_counter_maximum": 100,
    }


@pytest.fixture
def sample_oversight():
    """Provide sample oversight data (settings_data parameter)."""
    return {
        "enable_reporting": False,
        "report_edi_errors": False,
        "report_email_destination": "",
        "report_printing_fallback": False,
        "logs_directory": "/var/log",
    }


@pytest.fixture
def mock_smtp_service():
    """Provide a mock SMTP service."""
    service = MagicMock(spec=SMTPService)
    service.test_connection.return_value = (True, None)
    return service


@pytest.fixture
def mock_callbacks():
    """Provide mock callbacks."""
    return {
        "oversight_provider": MagicMock(return_value={}),
        "update_settings": MagicMock(),
        "update_oversight": MagicMock(),
        "on_apply": MagicMock(),
        "refresh_callback": MagicMock(),
        "count_email_backends": MagicMock(return_value=2),
        "count_disabled_folders": MagicMock(return_value=1),
        "disable_email_backends": MagicMock(),
        "disable_folders_without_backends": MagicMock(),
    }


def _make_dialog(settings_data, settings_provider=None, **kwargs):
    """Helper to create EditSettingsDialog with proper parameter passing."""
    # Remove settings_provider from kwargs if present to avoid duplication
    kwargs.pop('settings_provider', None)
    return EditSettingsDialog(
        None,
        settings_data,
        settings_provider=settings_provider,
        **kwargs
    )


class TestEditSettingsDialogUI:
    """Test UI initialization and widget creation."""

    def test_dialog_initialization(self, qtbot, sample_settings, sample_oversight):
        """Test dialog can be initialized with all parameters."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            oversight_provider=MagicMock(return_value=sample_oversight),
            title="Test Settings",
        )
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert dialog.windowTitle() == "Test Settings"
        assert dialog.isModal()
        assert dialog.minimumWidth() >= 550
        assert dialog.minimumHeight() >= 500

    def test_widget_creation(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test all required widgets are created."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Check AS400 section widgets
        assert hasattr(dialog, "_odbc_driver_combo")
        assert hasattr(dialog, "_as400_address")
        assert hasattr(dialog, "_as400_username")
        assert hasattr(dialog, "_as400_password")

        # Check email section widgets
        assert hasattr(dialog, "_enable_email_cb")
        assert hasattr(dialog, "_email_fields_widget")
        assert hasattr(dialog, "_email_address")
        assert hasattr(dialog, "_email_username")
        assert hasattr(dialog, "_email_password")
        assert hasattr(dialog, "_email_smtp_server")
        assert hasattr(dialog, "_email_smtp_port")

        # Check reporting section widgets
        assert hasattr(dialog, "_reporting_group")
        assert hasattr(dialog, "_enable_reporting_cb")
        assert hasattr(dialog, "_report_edi_warnings_cb")
        assert hasattr(dialog, "_email_destination")
        assert hasattr(dialog, "_enable_report_printing_cb")
        assert hasattr(dialog, "_select_log_folder_btn")

        # Check backup section widgets
        assert hasattr(dialog, "_enable_backup_cb")
        assert hasattr(dialog, "_backup_interval_spin")

    def test_dialog_buttons(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test dialog has OK and Cancel buttons."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        buttons = dialog.findChildren(QDialogButtonBox)
        assert len(buttons) == 1

        button_box = buttons[0]
        assert button_box.button(QDialogButtonBox.StandardButton.Ok) is not None
        assert button_box.button(QDialogButtonBox.StandardButton.Cancel) is not None


class TestEditSettingsDialogAS400:
    """Test AS400 section functionality."""

    def test_as400_field_population(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test AS400 fields are populated from settings."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._as400_address.text() == sample_settings["as400_address"]
        assert dialog._as400_username.text() == sample_settings["as400_username"]
        assert dialog._as400_password.text() == sample_settings["as400_password"]

    def test_odbc_driver_combo(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test ODBC driver combo box is populated."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Should have driver set from settings or default
        current_text = dialog._odbc_driver_combo.currentText()
        assert current_text is not None

    def test_odbc_driver_custom_value(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test custom ODBC driver is added to combo."""
        custom_driver = "Custom ODBC Driver"
        custom_settings = sample_settings.copy()
        custom_settings["odbc_driver"] = custom_driver

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=custom_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._odbc_driver_combo.currentText() == custom_driver


class TestEditSettingsDialogEmail:
    """Test email section functionality."""

    def test_email_field_population(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test email fields are populated from settings."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._email_address.text() == sample_settings["email_address"]
        assert dialog._email_username.text() == sample_settings["email_username"]
        assert dialog._email_password.text() == sample_settings["email_password"]
        assert dialog._email_smtp_server.text() == sample_settings["email_smtp_server"]
        assert dialog._email_smtp_port.text() == sample_settings["smtp_port"]

    def test_email_enabled_check_state(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test email enable checkbox is set correctly."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._enable_email_cb.isChecked() is True

    def test_email_toggle_enables_fields(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test toggling email enables/disables fields."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Initially enabled
        assert dialog._email_fields_widget.isEnabled() is True

        # Disable email by toggling checkbox
        dialog._enable_email_cb.setChecked(False)
        assert dialog._email_fields_widget.isEnabled() is False

        # Enable email
        dialog._enable_email_cb.setChecked(True)
        assert dialog._email_fields_widget.isEnabled() is True

    def test_email_disables_reporting(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test disabling email also disables reporting."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Enable reporting first
        dialog._enable_reporting_cb.setChecked(True)
        assert dialog._enable_reporting_cb.isEnabled() is True

        # Disable email
        dialog._enable_email_cb.setChecked(False)
        assert dialog._enable_reporting_cb.isChecked() is False
        assert dialog._enable_reporting_cb.isEnabled() is False

    def test_password_echo_mode(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test password fields use password echo mode."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._as400_password.echoMode() == QLineEdit.EchoMode.Password
        assert dialog._email_password.echoMode() == QLineEdit.EchoMode.Password


class TestEditSettingsDialogReporting:
    """Test reporting section functionality."""

    def test_reporting_field_population(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test reporting fields are populated from oversight data."""
        oversight = sample_oversight.copy()
        oversight["enable_reporting"] = True
        oversight["report_edi_errors"] = True
        oversight["report_email_destination"] = "report@example.com"
        oversight["report_printing_fallback"] = True

        dialog = _make_dialog(
            settings_data=oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._enable_reporting_cb.isChecked() is True
        assert dialog._report_edi_warnings_cb.isChecked() is True
        assert dialog._email_destination.text() == "report@example.com"
        assert dialog._enable_report_printing_cb.isChecked() is True

    def test_reporting_toggle_enables_fields(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test toggling reporting enables/disables fields."""
        oversight = sample_oversight.copy()
        oversight["enable_reporting"] = True

        dialog = _make_dialog(
            settings_data=oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Initially enabled
        assert dialog._reporting_fields_widget.isEnabled() is True

        # Disable reporting
        dialog._enable_reporting_cb.setChecked(False)
        assert dialog._reporting_fields_widget.isEnabled() is False

        # Enable reporting
        dialog._enable_reporting_cb.setChecked(True)
        assert dialog._reporting_fields_widget.isEnabled() is True

    def test_reporting_toggle_enables_edi_warnings(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test toggling reporting enables/disables EDI warnings checkbox."""
        oversight = sample_oversight.copy()
        oversight["enable_reporting"] = True

        dialog = _make_dialog(
            settings_data=oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Initially enabled
        assert dialog._report_edi_warnings_cb.isEnabled() is True

        # Disable reporting
        dialog._enable_reporting_cb.setChecked(False)
        assert dialog._report_edi_warnings_cb.isEnabled() is False

    def test_log_directory_selection(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test log directory selection button."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        test_dir = os.getcwd()
        dialog._logs_directory = test_dir

        # Mock file dialog to return test directory
        with patch.object(
            dialog,
            "_select_log_directory",
            lambda: setattr(dialog, "_logs_directory", test_dir),
        ):
            # Verify button exists
            assert dialog._select_log_folder_btn is not None
            assert dialog._select_log_folder_btn.text() == "Select Log Folder..."


class TestEditSettingsDialogBackup:
    """Test backup section functionality."""

    def test_backup_field_population(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test backup fields are populated from settings."""
        settings = sample_settings.copy()
        settings["enable_interval_backups"] = True
        settings["backup_counter_maximum"] = 150

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._enable_backup_cb.isChecked() is True
        assert dialog._backup_interval_spin.value() == 150

    def test_backup_toggle_enables_spinbox(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test toggling backup enables/disables spinbox."""
        settings = sample_settings.copy()
        settings["enable_interval_backups"] = True

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Initially enabled
        assert dialog._backup_interval_spin.isEnabled() is True

        # Disable backup
        dialog._enable_backup_cb.setChecked(False)
        assert dialog._backup_interval_spin.isEnabled() is False

        # Enable backup
        dialog._enable_backup_cb.setChecked(True)
        assert dialog._backup_interval_spin.isEnabled() is True

    def test_backup_spinbox_range(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test backup spinbox has correct range."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._backup_interval_spin.minimum() == 1
        assert dialog._backup_interval_spin.maximum() == 5000

    def test_backup_default_value(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test backup spinbox has correct default value."""
        settings = sample_settings.copy()
        del settings["backup_counter_maximum"]

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog._backup_interval_spin.value() == 100


class TestEditSettingsDialogValidation:
    """Test validation logic and error messages."""

    def test_validation_passes_with_valid_data(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation passes with all valid data."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog.validate() is True

    def test_validation_fails_missing_email_address(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails when email address is missing."""
        settings = sample_settings.copy()
        settings["email_address"] = ""

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Email Address Is A Required Field" in args[2]

    def test_validation_fails_invalid_email_format(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails with invalid email format."""
        settings = sample_settings.copy()
        settings["email_address"] = "invalid-email"

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Invalid Email Origin Address" in args[2]

    def test_validation_fails_smtp_connection(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test validation fails when SMTP connection fails."""
        mock_smtp = MagicMock(spec=SMTPService)
        mock_smtp.test_connection.return_value = (False, "Connection failed")

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Test Login Failed" in args[2]

    def test_validation_fails_missing_smtp_server(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails when SMTP server is missing."""
        settings = sample_settings.copy()
        settings["email_smtp_server"] = ""

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "SMTP Server Address Is A Required Field" in args[2]

    def test_validation_fails_missing_smtp_port(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails when SMTP port is missing."""
        settings = sample_settings.copy()
        settings["smtp_port"] = ""

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "SMTP Port Is A Required Field" in args[2]

    def test_validation_fails_password_without_username(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails when password is set but username is missing."""
        settings = sample_settings.copy()
        settings["email_username"] = ""

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Email Username Required If Password Is Set" in args[2]

    def test_validation_fails_username_without_password(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails when username is set but password is missing."""
        settings = sample_settings.copy()
        settings["email_password"] = ""

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Email Username Without Password Is Not Supported" in args[2]

    def test_validation_fails_missing_report_destination(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails when reporting destination is missing."""
        oversight = sample_oversight.copy()
        oversight["enable_reporting"] = True

        dialog = _make_dialog(
            settings_data=oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Reporting Email Destination Is A Required Field" in args[2]

    def test_validation_fails_invalid_report_destination(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation fails with invalid report destination format."""
        oversight = sample_oversight.copy()
        oversight["enable_reporting"] = True
        oversight["report_email_destination"] = "invalid-email"

        dialog = _make_dialog(
            settings_data=oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, "critical") as mock_critical:
            result = dialog.validate()
            assert result is False
            mock_critical.assert_called_once()
            args = mock_critical.call_args[0]
            assert "Invalid Email Destination Address" in args[2]

    def test_validation_multiple_report_destinations(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation handles multiple report destinations."""
        oversight = sample_oversight.copy()
        oversight["enable_reporting"] = True
        oversight["report_email_destination"] = "report1@example.com, report2@example.com"

        dialog = _make_dialog(
            settings_data=oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Should pass with valid multiple addresses
        assert dialog.validate() is True

    def test_validation_passes_with_valid_backup_interval(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation passes with valid backup interval."""
        settings = sample_settings.copy()
        settings["enable_interval_backups"] = True
        settings["backup_counter_maximum"] = 500  # Valid value
        settings["enable_email"] = False  # Disable email to avoid email validation

        # Set callbacks to return 0 (no email backends to disable)
        mock_callbacks_no_backends = mock_callbacks.copy()
        mock_callbacks_no_backends["count_email_backends"] = MagicMock(return_value=0)
        mock_callbacks_no_backends["count_disabled_folders"] = MagicMock(return_value=0)

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks_no_backends,
        )
        qtbot.addWidget(dialog)

        # Verify the spinbox has the valid value
        assert dialog._backup_interval_spin.value() == 500
        assert dialog._enable_backup_cb.isChecked() is True

        # Validation should pass
        assert dialog.validate() is True

    def test_validation_passes_when_email_disabled(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test validation passes when email is disabled."""
        settings = sample_settings.copy()
        settings["enable_email"] = False
        settings["email_address"] = ""  # Empty but OK when disabled

        # Set callbacks to return 0 (no email backends to disable)
        mock_callbacks_no_backends = mock_callbacks.copy()
        mock_callbacks_no_backends["count_email_backends"] = MagicMock(return_value=0)
        mock_callbacks_no_backends["count_disabled_folders"] = MagicMock(return_value=0)

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks_no_backends,
        )
        qtbot.addWidget(dialog)

        assert dialog.validate() is True


class TestEditSettingsDialogApply:
    """Test save/cancel operations and callbacks."""

    def test_apply_updates_settings(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test apply method updates settings correctly."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        dialog.apply()

        # Check update_settings was called
        mock_callbacks["update_settings"].assert_called_once()
        updated_settings = mock_callbacks["update_settings"].call_args[0][0]

        assert updated_settings["as400_address"] == sample_settings["as400_address"]
        assert updated_settings["email_address"] == sample_settings["email_address"]
        assert updated_settings["enable_email"] is True

    def test_apply_updates_oversight(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test apply method updates oversight data correctly."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        dialog.apply()

        # Check update_oversight was called
        mock_callbacks["update_oversight"].assert_called_once()
        updated_oversight = mock_callbacks["update_oversight"].call_args[0][0]

        assert "enable_reporting" in updated_oversight
        assert "report_email_destination" in updated_oversight

    def test_apply_calls_on_apply_callback(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test apply method calls on_apply callback."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        dialog.apply()

        mock_callbacks["on_apply"].assert_called_once()

    def test_apply_calls_refresh_callback(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test apply method calls refresh callback."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        dialog.apply()

        mock_callbacks["refresh_callback"].assert_called_once()

    def test_ok_button_validates_and_applies(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test OK button validates and applies settings."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Call the OK handler directly
        dialog._on_ok()

        # Should have called apply
        mock_callbacks["update_settings"].assert_called_once()

    def test_ok_button_fails_validation(self, qtbot, sample_settings, sample_oversight, mock_callbacks):
        """Test OK button fails when validation fails."""
        settings = sample_settings.copy()
        settings["email_address"] = ""  # Invalid

        mock_smtp = MagicMock(spec=SMTPService)
        mock_smtp.test_connection.return_value = (True, None)

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Call the OK handler directly
        with patch.object(QMessageBox, "critical"):
            dialog._on_ok()

        # Should not have called apply (validation failed)
        mock_callbacks["update_settings"].assert_not_called()

    def test_cancel_button_closes_dialog(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test Cancel button closes dialog without saving."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Call the cancel handler directly
        dialog.reject()

        # Should not have called apply
        mock_callbacks["update_settings"].assert_not_called()

    def test_disabling_email_disables_backends(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test disabling email disables email backends."""
        settings = sample_settings.copy()
        settings["enable_email"] = False

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        dialog.apply()

        # Should have called disable functions
        mock_callbacks["disable_email_backends"].assert_called_once()
        mock_callbacks["disable_folders_without_backends"].assert_called_once()

    def test_confirmation_when_disabling_email(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test confirmation dialog when disabling email with active backends."""
        settings = sample_settings.copy()
        settings["enable_email"] = False

        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        # Mock confirmation to return Cancel
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            result = dialog.validate()
            assert result is False

        # Mock confirmation to return Ok
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Ok):
            result = dialog.validate()
            assert result is True


class TestEditSettingsDialogEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_settings(self, qtbot, mock_callbacks, mock_smtp_service):
        """Test dialog with empty settings."""
        dialog = _make_dialog(
            settings_data={},
            settings_provider=MagicMock(return_value={}),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog is not None

    def test_none_settings_provider(self, qtbot, mock_smtp_service):
        """Test dialog with None settings provider."""
        dialog = _make_dialog(
            settings_data={},
            settings_provider=None,
            oversight_provider=None,
            smtp_service=mock_smtp_service,
        )
        qtbot.addWidget(dialog)

        # Should use empty dict
        assert dialog._settings == {}

    def test_none_callbacks(self, qtbot, sample_settings, sample_oversight, mock_smtp_service):
        """Test dialog with None callbacks."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=None,
            oversight_provider=None,
            update_settings=None,
            update_oversight=None,
            on_apply=None,
            refresh_callback=None,
            smtp_service=mock_smtp_service,
        )
        qtbot.addWidget(dialog)

        # Should not raise errors
        dialog.apply()
        assert True

    def test_default_smtp_service(self, qtbot, sample_settings, sample_oversight):
        """Test dialog creates default SMTP service if not provided."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=None,
        )
        qtbot.addWidget(dialog)

        # Should have created default service
        assert dialog._smtp_service is not None
        assert isinstance(dialog._smtp_service, SMTPService)

    def test_size_grip_disabled(self, qtbot, sample_settings, sample_oversight, mock_callbacks, mock_smtp_service):
        """Test dialog has size grip disabled."""
        dialog = _make_dialog(
            settings_data=sample_oversight,
            settings_provider=MagicMock(return_value=sample_settings),
            smtp_service=mock_smtp_service,
            **mock_callbacks,
        )
        qtbot.addWidget(dialog)

        assert dialog.isSizeGripEnabled() is False