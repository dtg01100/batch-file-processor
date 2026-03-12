"""Qt reimplementation of EditSettingsDialog for editing application-wide settings."""

import os
from typing import Any, Callable, Dict, Optional

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from interface.qt.dialogs.base_dialog import BaseDialog

from interface.services.smtp_service import SMTPService, SMTPServiceProtocol
from interface.validation.email_validator import validate_email as validate_email_format
import utils


class EditSettingsDialog(BaseDialog):
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
        self._settings_data = dict(settings_data) if settings_data else {}
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

        super().__init__(parent, title)

        # Set minimum size for comfortable viewing of all form fields
        self.setMinimumSize(700, 700)

    def _get_settings(self) -> Dict[str, Any]:
        if self._settings_provider:
            result = self._settings_provider()
            return result if result else {}
        return {}

    def body(self, parent: QWidget) -> Optional[QWidget]:
        """Create dialog body."""
        # Use parent's existing layout instead of creating a new one
        layout = parent.layout()
        if layout is None:
            layout = QVBoxLayout(parent)

        layout.addWidget(self._build_as400_section())
        layout.addWidget(self._build_email_section())
        layout.addWidget(self._build_reporting_section())
        layout.addWidget(self._build_backup_section())

        self.setSizeGripEnabled(False)

        # Now that UI is built, populate fields and connect signals
        self._populate_fields()
        self._connect_signals()
        self._on_enable_email_toggled()
        self._on_enable_backup_toggled()

        return None

    def _build_as400_section(self) -> QGroupBox:
        group = QGroupBox("AS400 Database Connection")
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

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
        self._as400_address.setMinimumWidth(260)
        self._as400_username.setMinimumWidth(260)
        self._as400_password.setMinimumWidth(260)

        self._odbc_driver_combo.setAccessibleName("ODBC driver")
        self._odbc_driver_combo.setAccessibleDescription(
            "ODBC driver for AS400 database connection"
        )
        self._as400_address.setAccessibleName("AS400 address")
        self._as400_address.setAccessibleDescription("Hostname or IP of AS400 server")
        self._as400_username.setAccessibleName("AS400 username")
        self._as400_username.setAccessibleDescription("Username for AS400 login")
        self._as400_password.setAccessibleName("AS400 password")
        self._as400_password.setAccessibleDescription("Password for AS400 login")

        form.addRow("ODBC &Driver:", self._odbc_driver_combo)
        form.addRow("AS400 &Address:", self._as400_address)
        form.addRow("AS400 &Username:", self._as400_username)
        form.addRow("AS400 &Password:", self._as400_password)

        return group

    def _build_email_section(self) -> QGroupBox:
        group = QGroupBox("Email Settings")
        outer = QVBoxLayout(group)

        self._enable_email_cb = QCheckBox("Enable &Email")
        self._enable_email_cb.setAccessibleName("Enable email")
        self._enable_email_cb.setAccessibleDescription(
            "Enable outbound email backend configuration"
        )
        outer.addWidget(self._enable_email_cb)

        self._email_fields_widget = QWidget()
        form = QFormLayout(self._email_fields_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._email_address = QLineEdit()
        self._email_username = QLineEdit()
        self._email_password = QLineEdit()
        self._email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._email_smtp_server = QLineEdit()
        self._email_smtp_port = QLineEdit()
        self._email_address.setMinimumWidth(260)
        self._email_username.setMinimumWidth(260)
        self._email_password.setMinimumWidth(260)
        self._email_smtp_server.setMinimumWidth(260)
        self._email_smtp_port.setMinimumWidth(260)

        self._email_address.setAccessibleName("Email address")
        self._email_address.setAccessibleDescription("From address for outgoing email")
        self._email_username.setAccessibleName("Email username")
        self._email_username.setAccessibleDescription("SMTP account username")
        self._email_password.setAccessibleName("Email password")
        self._email_password.setAccessibleDescription("SMTP account password")
        self._email_smtp_server.setAccessibleName("SMTP server")
        self._email_smtp_server.setAccessibleDescription("SMTP server hostname")
        self._email_smtp_port.setAccessibleName("SMTP port")
        self._email_smtp_port.setAccessibleDescription("SMTP server port")

        form.addRow("Email &Address:", self._email_address)
        form.addRow("Email &Username:", self._email_username)
        form.addRow("Email &Password:", self._email_password)
        form.addRow("Email S&MTP Server:", self._email_smtp_server)
        form.addRow("Email SMTP &Port:", self._email_smtp_port)

        self._test_connection_btn = QPushButton("&Test Connection")
        self._test_connection_btn.setAccessibleName("Test SMTP connection")
        self._test_connection_btn.setAccessibleDescription(
            "Tests SMTP server connectivity using current email settings"
        )
        form.addRow("", self._test_connection_btn)

        outer.addWidget(self._email_fields_widget)
        return group

    def _build_reporting_section(self) -> QGroupBox:
        self._reporting_group = QGroupBox("Reporting")
        outer = QVBoxLayout(self._reporting_group)

        self._enable_reporting_cb = QCheckBox("Enable &Report Sending")
        self._report_edi_warnings_cb = QCheckBox("Report EDI Validator &Warnings")
        self._enable_reporting_cb.setAccessibleName("Enable report sending")
        self._enable_reporting_cb.setAccessibleDescription(
            "Enable sending processing reports by email"
        )
        self._report_edi_warnings_cb.setAccessibleName("Report EDI validator warnings")
        self._report_edi_warnings_cb.setAccessibleDescription(
            "Include EDI validator warnings in reporting"
        )
        outer.addWidget(self._enable_reporting_cb)
        outer.addWidget(self._report_edi_warnings_cb)

        self._reporting_fields_widget = QWidget()
        form = QFormLayout(self._reporting_fields_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._email_destination = QLineEdit()
        self._email_destination.setMinimumWidth(260)
        self._enable_report_printing_cb = QCheckBox(
            "Enable Report Printing &Fallback"
        )
        self._email_destination.setAccessibleName("Report email destination")
        self._email_destination.setAccessibleDescription(
            "Comma-separated recipient addresses for reports"
        )
        self._enable_report_printing_cb.setAccessibleName(
            "Enable report printing fallback"
        )
        self._enable_report_printing_cb.setAccessibleDescription(
            "Print reports when email sending is unavailable"
        )

        form.addRow("Email &Destination:", self._email_destination)
        form.addRow(self._enable_report_printing_cb)

        outer.addWidget(self._reporting_fields_widget)

        self._select_log_folder_btn = QPushButton("Select &Log Folder...")
        self._select_log_folder_btn.clicked.connect(self._select_log_directory)
        self._select_log_folder_btn.setAccessibleName("Select log folder")
        self._select_log_folder_btn.setAccessibleDescription(
            "Choose directory where report logs are stored"
        )
        outer.addWidget(self._select_log_folder_btn)

        return self._reporting_group

    def _build_backup_section(self) -> QGroupBox:
        group = QGroupBox("Backup")
        layout = QHBoxLayout(group)

        self._enable_backup_cb = QCheckBox("Enable Interval &Backup")
        self._backup_interval_spin = QSpinBox()
        self._backup_interval_spin.setRange(1, 5000)
        self._backup_interval_spin.setValue(100)
        self._enable_backup_cb.setAccessibleName("Enable interval backup")
        self._enable_backup_cb.setAccessibleDescription(
            "Enable periodic backup creation"
        )
        self._backup_interval_spin.setAccessibleName("Backup interval")
        self._backup_interval_spin.setAccessibleDescription(
            "Number of cycles before automatic backup"
        )

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
        self._test_connection_btn.clicked.connect(self._test_smtp_connection)

    def _on_enable_email_toggled(self) -> None:
        email_on = self._enable_email_cb.isChecked()
        self._email_fields_widget.setEnabled(email_on)
        self._test_connection_btn.setEnabled(email_on)
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

    def _focus_invalid_field(self, widget: Optional[QWidget]) -> None:
        if widget is None:
            return
        widget.setFocus()
        if isinstance(widget, QLineEdit):
            widget.selectAll()

    def _format_grouped_errors(self, errors_by_section: Dict[str, list[str]]) -> str:
        lines: list[str] = []
        for section, messages in errors_by_section.items():
            if not messages:
                continue
            lines.append(f"{section}:")
            for message in messages:
                lines.append(f"- {message}")
            lines.append("")
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    def _test_smtp_connection(self) -> None:
        if not self._enable_email_cb.isChecked():
            QMessageBox.information(
                self,
                "SMTP Test",
                "Enable Email before testing SMTP connection.",
            )
            return

        try:
            success, error_msg = self._smtp_service.test_connection(
                smtp_server=self._email_smtp_server.text(),
                smtp_port=self._email_smtp_port.text(),
                username=self._email_username.text(),
                password=self._email_password.text(),
            )
        except Exception as e:
            success = False
            error_msg = str(e)

        if success:
            QMessageBox.information(
                self,
                "SMTP Test",
                "SMTP connection test succeeded.",
            )
            return

        QMessageBox.critical(
            self,
            "SMTP Test Failed",
            "Test Login Failed With Error\n" + (error_msg or ""),
        )

    def validate(self) -> bool:
        errors_by_section: Dict[str, list[str]] = {
            "Email Settings": [],
            "Reporting": [],
            "Backup": [],
        }
        first_invalid_widget: Optional[QWidget] = None

        def add_error(section: str, message: str, widget: Optional[QWidget] = None) -> None:
            nonlocal first_invalid_widget
            errors_by_section[section].append(message)
            if first_invalid_widget is None and widget is not None:
                first_invalid_widget = widget

        if self._enable_email_cb.isChecked():
            if not self._email_address.text():
                add_error(
                    "Email Settings",
                    "Email Address Is A Required Field",
                    self._email_address,
                )
            elif not validate_email_format(self._email_address.text()):
                add_error(
                    "Email Settings",
                    "Invalid Email Origin Address",
                    self._email_address,
                )

            if not self._email_username.text() and self._email_password.text():
                add_error(
                    "Email Settings",
                    "Email Username Required If Password Is Set",
                    self._email_username,
                )
            if not self._email_password.text() and self._email_username.text():
                add_error(
                    "Email Settings",
                    "Email Username Without Password Is Not Supported",
                    self._email_password,
                )
            if not self._email_smtp_server.text():
                add_error(
                    "Email Settings",
                    "SMTP Server Address Is A Required Field",
                    self._email_smtp_server,
                )
            if not self._email_smtp_port.text():
                add_error(
                    "Email Settings",
                    "SMTP Port Is A Required Field",
                    self._email_smtp_port,
                )

        if self._enable_reporting_cb.isChecked():
            if not self._email_destination.text():
                add_error(
                    "Reporting",
                    "Reporting Email Destination Is A Required Field",
                    self._email_destination,
                )
            else:
                for addr in [a.strip() for a in self._email_destination.text().split(",")]:
                    if not validate_email_format(addr):
                        add_error(
                            "Reporting",
                            "Invalid Email Destination Address",
                            self._email_destination,
                        )
                        break

        if self._enable_backup_cb.isChecked():
            val = self._backup_interval_spin.value()
            if val < 1 or val > 5000:
                add_error(
                    "Backup",
                    "Backup Interval Needs To Be A Number Between 1 and 5000",
                    self._backup_interval_spin,
                )

        grouped_errors = self._format_grouped_errors(errors_by_section)
        if grouped_errors:
            self._focus_invalid_field(first_invalid_widget)
            QMessageBox.critical(self, "Validation Error", grouped_errors)
            return False

        if not self._enable_email_cb.isChecked():
            num_backends = (
                self._count_email_backends() if self._count_email_backends else 0
            )
            num_disabled = (
                self._count_disabled_folders() if self._count_disabled_folders else 0
            )
            if num_disabled > 0 or num_backends > 0:
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
        self._settings_data["enable_reporting"] = self._enable_reporting_cb.isChecked()
        self._settings_data["logs_directory"] = self._logs_directory
        self._settings_data["report_email_destination"] = self._email_destination.text()
        self._settings_data["report_edi_errors"] = (
            self._report_edi_warnings_cb.isChecked()
        )
        self._settings_data["report_printing_fallback"] = (
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
            for folder_key, folder_data in self._settings_data.items():
                if isinstance(folder_data, dict):
                    folder_data["folder_is_active"] = False
                    folder_data["process_backend_email"] = False

        if self._update_settings:
            self._update_settings(self._settings)
        if self._update_oversight:
            self._update_oversight(self._settings_data)
        if self._on_apply:
            self._on_apply(self._settings_data)
        if self._refresh_callback:
            self._refresh_callback()


