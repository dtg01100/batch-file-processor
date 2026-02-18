"""Qt reimplementation of EditSettingsDialog for editing application-wide settings."""

import os
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interface.services.smtp_service import SMTPService, SMTPServiceProtocol
from interface.validation.email_validator import validate_email as validate_email_format
import utils


class EditSettingsDialog(QDialog):
    """Modal dialog for editing application settings.

    Handles email configuration, AS400 database settings, reporting options,
    and backup settings. Dependencies are injected for testability.
    """

    def __init__(
        self,
        parent: Optional[QWidget],
        settings_data: Dict[str, Any],
        title: str = "Edit Settings",
        settings_provider: Optional[Callable[[], Dict]] = None,
        oversight_provider: Optional[Callable[[], Dict]] = None,
        update_settings: Optional[Callable[[Dict], None]] = None,
        update_oversight: Optional[Callable[[Dict], None]] = None,
        on_apply: Optional[Callable[[Dict], None]] = None,
        refresh_callback: Optional[Callable[[], None]] = None,
        count_email_backends: Optional[Callable[[], int]] = None,
        count_disabled_folders: Optional[Callable[[], int]] = None,
        disable_email_backends: Optional[Callable[[], None]] = None,
        disable_folders_without_backends: Optional[Callable[[], None]] = None,
        smtp_service: Optional[SMTPServiceProtocol] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        self._settings_data = dict(settings_data)
        self._settings_provider = settings_provider
        self._oversight_provider = oversight_provider
        self._update_settings = update_settings
        self._update_oversight = update_oversight
        self._on_apply = on_apply
        self._refresh_callback = refresh_callback
        self._count_email_backends = count_email_backends
        self._count_disabled_folders = count_disabled_folders
        self._disable_email_backends = disable_email_backends
        self._disable_folders_without_backends = disable_folders_without_backends
        self._smtp_service = smtp_service or SMTPService()

        self._settings = self._get_settings()
        self._logs_directory = self._settings_data.get("logs_directory", "")

        self._build_ui()
        self._populate_fields()
        self._connect_signals()
        self._on_enable_email_toggled()
        self._on_enable_backup_toggled()

    def _get_settings(self) -> Dict[str, Any]:
        if self._settings_provider:
            return self._settings_provider()
        return {}

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(self._build_as400_section())
        layout.addWidget(self._build_email_section())
        layout.addWidget(self._build_reporting_section())
        layout.addWidget(self._build_backup_section())

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setSizeGripEnabled(False)

    def _build_as400_section(self) -> QGroupBox:
        group = QGroupBox("AS400 Database Connection")
        form = QFormLayout(group)

        self._odbc_driver_combo = QComboBox()
        try:
            import pyodbc
            self._odbc_driver_combo.addItems(pyodbc.drivers())
        except ImportError:
            pass

        self._as400_address = QLineEdit()
        self._as400_username = QLineEdit()
        self._as400_password = QLineEdit()
        self._as400_password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("ODBC Driver:", self._odbc_driver_combo)
        form.addRow("AS400 Address:", self._as400_address)
        form.addRow("AS400 Username:", self._as400_username)
        form.addRow("AS400 Password:", self._as400_password)

        return group

    def _build_email_section(self) -> QGroupBox:
        group = QGroupBox("Email Settings")
        outer = QVBoxLayout(group)

        self._enable_email_cb = QCheckBox("Enable Email")
        outer.addWidget(self._enable_email_cb)

        self._email_fields_widget = QWidget()
        form = QFormLayout(self._email_fields_widget)
        form.setContentsMargins(0, 0, 0, 0)

        self._email_address = QLineEdit()
        self._email_username = QLineEdit()
        self._email_password = QLineEdit()
        self._email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._email_smtp_server = QLineEdit()
        self._email_smtp_port = QLineEdit()

        form.addRow("Email Address:", self._email_address)
        form.addRow("Email Username:", self._email_username)
        form.addRow("Email Password:", self._email_password)
        form.addRow("Email SMTP Server:", self._email_smtp_server)
        form.addRow("Email SMTP Port:", self._email_smtp_port)

        outer.addWidget(self._email_fields_widget)
        return group

    def _build_reporting_section(self) -> QGroupBox:
        self._reporting_group = QGroupBox("Reporting")
        outer = QVBoxLayout(self._reporting_group)

        self._enable_reporting_cb = QCheckBox("Enable Report Sending")
        self._report_edi_warnings_cb = QCheckBox("Report EDI Validator Warnings")
        outer.addWidget(self._enable_reporting_cb)
        outer.addWidget(self._report_edi_warnings_cb)

        self._reporting_fields_widget = QWidget()
        form = QFormLayout(self._reporting_fields_widget)
        form.setContentsMargins(0, 0, 0, 0)

        self._email_destination = QLineEdit()
        self._enable_report_printing_cb = QCheckBox("Enable Report Printing Fallback")

        form.addRow("Email Destination:", self._email_destination)
        form.addRow(self._enable_report_printing_cb)

        outer.addWidget(self._reporting_fields_widget)

        self._select_log_folder_btn = QPushButton("Select Log Folder...")
        self._select_log_folder_btn.clicked.connect(self._select_log_directory)
        outer.addWidget(self._select_log_folder_btn)

        return self._reporting_group

    def _build_backup_section(self) -> QGroupBox:
        group = QGroupBox("Backup")
        layout = QHBoxLayout(group)

        self._enable_backup_cb = QCheckBox("Enable Interval Backup")
        self._backup_interval_spin = QSpinBox()
        self._backup_interval_spin.setRange(1, 5000)
        self._backup_interval_spin.setValue(100)

        layout.addWidget(self._enable_backup_cb)
        layout.addStretch()
        layout.addWidget(self._backup_interval_spin)

        return group

    def _populate_fields(self) -> None:
        current_driver = self._settings.get("odbc_driver", "")
        idx = self._odbc_driver_combo.findText(current_driver)
        if idx >= 0:
            self._odbc_driver_combo.setCurrentIndex(idx)
        elif current_driver:
            self._odbc_driver_combo.addItem(current_driver)
            self._odbc_driver_combo.setCurrentText(current_driver)

        self._as400_address.setText(self._settings.get("as400_address", ""))
        self._as400_username.setText(self._settings.get("as400_username", ""))
        self._as400_password.setText(self._settings.get("as400_password", ""))

        self._enable_email_cb.setChecked(
            utils.normalize_bool(self._settings.get("enable_email", False))
        )
        self._email_address.setText(self._settings.get("email_address", ""))
        self._email_username.setText(self._settings.get("email_username", ""))
        self._email_password.setText(self._settings.get("email_password", ""))
        self._email_smtp_server.setText(self._settings.get("email_smtp_server", ""))
        self._email_smtp_port.setText(str(self._settings.get("smtp_port", "")))

        self._enable_reporting_cb.setChecked(
            utils.normalize_bool(self._settings_data.get("enable_reporting", False))
        )
        self._report_edi_warnings_cb.setChecked(
            utils.normalize_bool(self._settings_data.get("report_edi_errors", False))
        )
        self._email_destination.setText(
            self._settings_data.get("report_email_destination", "")
        )
        self._enable_report_printing_cb.setChecked(
            utils.normalize_bool(
                self._settings_data.get("report_printing_fallback", False)
            )
        )

        self._enable_backup_cb.setChecked(
            utils.normalize_bool(self._settings.get("enable_interval_backups", False))
        )
        self._backup_interval_spin.setValue(
            int(self._settings.get("backup_counter_maximum", 100) or 100)
        )

    def _connect_signals(self) -> None:
        self._enable_email_cb.toggled.connect(self._on_enable_email_toggled)
        self._enable_reporting_cb.toggled.connect(self._on_enable_reporting_toggled)
        self._enable_backup_cb.toggled.connect(self._on_enable_backup_toggled)

    def _on_enable_email_toggled(self) -> None:
        email_on = self._enable_email_cb.isChecked()
        self._email_fields_widget.setEnabled(email_on)
        if not email_on:
            self._enable_reporting_cb.setChecked(False)
        self._enable_reporting_cb.setEnabled(email_on)
        self._on_enable_reporting_toggled()

    def _on_enable_reporting_toggled(self) -> None:
        reporting_on = self._enable_reporting_cb.isChecked()
        self._reporting_fields_widget.setEnabled(reporting_on)
        self._report_edi_warnings_cb.setEnabled(reporting_on)

    def _on_enable_backup_toggled(self) -> None:
        self._backup_interval_spin.setEnabled(self._enable_backup_cb.isChecked())

    def _select_log_directory(self) -> None:
        try:
            if os.path.exists(self._logs_directory):
                initial = self._logs_directory
            else:
                initial = os.getcwd()
        except Exception:
            initial = os.getcwd()

        chosen = QFileDialog.getExistingDirectory(self, "Select Log Folder", initial)
        if chosen:
            self._logs_directory = chosen

    def validate(self) -> bool:
        errors: list[str] = []

        if self._enable_email_cb.isChecked():
            if not self._email_address.text():
                errors.append("Email Address Is A Required Field")
            elif not validate_email_format(self._email_address.text()):
                errors.append("Invalid Email Origin Address")

            success, error_msg = self._smtp_service.test_connection(
                smtp_server=self._email_smtp_server.text(),
                smtp_port=self._email_smtp_port.text(),
                username=self._email_username.text(),
                password=self._email_password.text(),
            )
            if not success:
                errors.append("Test Login Failed With Error\n" + (error_msg or ""))

            if not self._email_username.text() and self._email_password.text():
                errors.append("Email Username Required If Password Is Set")
            if not self._email_password.text() and self._email_username.text():
                errors.append("Email Username Without Password Is Not Supported")
            if not self._email_smtp_server.text():
                errors.append("SMTP Server Address Is A Required Field")
            if not self._email_smtp_port.text():
                errors.append("SMTP Port Is A Required Field")

        if self._enable_reporting_cb.isChecked():
            if not self._email_destination.text():
                errors.append("Reporting Email Destination Is A Required Field")
            else:
                for addr in self._email_destination.text().split(", "):
                    if not validate_email_format(addr.strip()):
                        errors.append("Invalid Email Destination Address")
                        break

        if self._enable_backup_cb.isChecked():
            val = self._backup_interval_spin.value()
            if val < 1 or val > 5000:
                errors.append("Backup Interval Needs To Be A Number Between 1 and 5000")

        if errors:
            QMessageBox.critical(self, "Validation Error", "\n".join(errors))
            return False

        if not self._enable_email_cb.isChecked():
            num_backends = (
                self._count_email_backends() if self._count_email_backends else 0
            )
            num_disabled = (
                self._count_disabled_folders() if self._count_disabled_folders else 0
            )
            if num_disabled != 0:
                result = QMessageBox.question(
                    self,
                    "Confirm",
                    f"This will disable the email backend in {num_backends} folders.\n"
                    f"As a result, {num_disabled} folders will be disabled",
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if result != QMessageBox.StandardButton.Ok:
                    return False

        return True

    def apply(self) -> None:
        self._settings_data["enable_reporting"] = str(
            self._enable_reporting_cb.isChecked()
        )
        self._settings_data["logs_directory"] = self._logs_directory
        self._settings_data["report_email_destination"] = self._email_destination.text()
        self._settings_data["report_edi_errors"] = (
            self._report_edi_warnings_cb.isChecked()
        )
        self._settings_data["report_printing_fallback"] = str(
            self._enable_report_printing_cb.isChecked()
        )

        self._settings["odbc_driver"] = self._odbc_driver_combo.currentText()
        self._settings["as400_address"] = self._as400_address.text()
        self._settings["as400_username"] = self._as400_username.text()
        self._settings["as400_password"] = self._as400_password.text()
        self._settings["enable_email"] = self._enable_email_cb.isChecked()
        self._settings["email_address"] = self._email_address.text()
        self._settings["email_username"] = self._email_username.text()
        self._settings["email_password"] = self._email_password.text()
        self._settings["email_smtp_server"] = self._email_smtp_server.text()
        self._settings["smtp_port"] = self._email_smtp_port.text()
        self._settings["enable_interval_backups"] = self._enable_backup_cb.isChecked()
        self._settings["backup_counter_maximum"] = self._backup_interval_spin.value()

        if not self._enable_email_cb.isChecked():
            if self._disable_email_backends:
                self._disable_email_backends()
            if self._disable_folders_without_backends:
                self._disable_folders_without_backends()
            self._settings_data["folder_is_active"] = "False"
            self._settings_data["process_backend_email"] = False

        if self._update_settings:
            self._update_settings(self._settings)
        if self._update_oversight:
            self._update_oversight(self._settings_data)
        if self._on_apply:
            self._on_apply(self._settings_data)
        if self._refresh_callback:
            self._refresh_callback()

    def _on_ok(self) -> None:
        if not self.validate():
            return
        self.apply()
        self.accept()
