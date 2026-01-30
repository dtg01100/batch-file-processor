"""
Edit settings dialog module for PyQt6 interface.

This module contains the EditSettingsDialog implementation.
A tabbed dialog that handles global application settings including:
- AS400 Connection settings
- Email settings
- Backup settings
- Reporting options
"""

from typing import TYPE_CHECKING, Dict, Any, Optional
import os

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QDialogButtonBox,
    QGroupBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager

from interface.utils.qt_validators import EMAIL_VALIDATOR
from interface.utils.validation_feedback import add_validation_to_fields


class EditSettingsDialog(QDialog):
    """Tabbed dialog for editing global settings."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        settings: Optional[Dict[str, Any]] = None,
        oversight: Optional[Dict[str, Any]] = None,
        db_manager: Optional["DatabaseManager"] = None,
    ):
        """
        Initialize the edit settings dialog.

        Args:
            parent: Parent window.
            settings: Settings dictionary from database.
            oversight: Oversight and defaults dictionary from database.
            db_manager: Database manager instance.
        """
        super().__init__(parent)

        self.settings = settings or {}
        self.oversight = oversight or {}
        self.db_manager = db_manager

        self.setWindowTitle("Edit Settings")
        self.setModal(True)
        self.resize(600, 400)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Tab widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Create tabs
        self._as400_tab = self._build_as400_tab()
        self._email_tab = self._build_email_tab()
        self._backup_tab = self._build_backup_tab()
        self._reporting_tab = self._build_reporting_tab()

        self._tabs.addTab(self._as400_tab, "AS400 Connection")
        self._tabs.addTab(self._email_tab, "Email Settings")
        self._tabs.addTab(self._backup_tab, "Backup Settings")
        self._tabs.addTab(self._reporting_tab, "Reporting Options")

        # Button box
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def _build_as400_tab(self) -> QWidget:
        """Build the AS400 connection settings tab."""
        tab = QWidget()
        layout = QGridLayout(tab)

        row = 0
        layout.addWidget(QLabel("ODBC Driver:"), row, 0)
        self._odbc_driver_combo = QComboBox()
        self._odbc_driver_combo.addItems(
            self.settings.get("available_odbc_drivers", [])
        )
        self._odbc_driver_combo.setCurrentText(self.settings.get("odbc_driver", ""))
        layout.addWidget(self._odbc_driver_combo, row, 1)

        row += 1
        layout.addWidget(QLabel("AS400 Address:"), row, 0)
        self._as400_address_field = QLineEdit()
        self._as400_address_field.setText(self.settings.get("as400_address", ""))
        layout.addWidget(self._as400_address_field, row, 1)

        row += 1
        layout.addWidget(QLabel("AS400 Username:"), row, 0)
        self._as400_username_field = QLineEdit()
        self._as400_username_field.setText(self.settings.get("as400_username", ""))
        layout.addWidget(self._as400_username_field, row, 1)

        row += 1
        layout.addWidget(QLabel("AS400 Password:"), row, 0)
        self._as400_password_field = QLineEdit()
        self._as400_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._as400_password_field.setText(self.settings.get("as400_password", ""))
        layout.addWidget(self._as400_password_field, row, 1)

        return tab

    def _build_email_tab(self) -> QWidget:
        """Build the email settings tab."""
        tab = QWidget()
        layout = QGridLayout(tab)

        row = 0
        self._enable_email_check = QCheckBox("Enable Email")
        self._enable_email_check.setChecked(self.settings.get("enable_email", False))
        self._enable_email_check.toggled.connect(self._on_email_enabled_changed)
        layout.addWidget(self._enable_email_check, row, 0, 1, 2)

        row += 1
        layout.addWidget(QLabel("Email Address:"), row, 0)
        self._email_address_field = QLineEdit()
        self._email_address_field.setValidator(EMAIL_VALIDATOR)
        self._email_address_field.setPlaceholderText("user@example.com")
        self._email_address_field.setText(self.settings.get("email_address", ""))
        layout.addWidget(self._email_address_field, row, 1)

        row += 1
        layout.addWidget(QLabel("Email Username:"), row, 0)
        self._email_username_field = QLineEdit()
        self._email_username_field.setText(self.settings.get("email_username", ""))
        layout.addWidget(self._email_username_field, row, 1)

        row += 1
        layout.addWidget(QLabel("Email Password:"), row, 0)
        self._email_password_field = QLineEdit()
        self._email_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._email_password_field.setText(self.settings.get("email_password", ""))
        layout.addWidget(self._email_password_field, row, 1)

        row += 1
        layout.addWidget(QLabel("SMTP Server:"), row, 0)
        self._smtp_server_field = QLineEdit()
        self._smtp_server_field.setText(self.settings.get("email_smtp_server", ""))
        layout.addWidget(self._smtp_server_field, row, 1)

        row += 1
        layout.addWidget(QLabel("SMTP Port:"), row, 0)
        self._smtp_port_spinbox = QSpinBox()
        self._smtp_port_spinbox.setRange(1, 65535)
        self._smtp_port_spinbox.setValue(self.settings.get("smtp_port", 25))
        layout.addWidget(self._smtp_port_spinbox, row, 1)

        return tab

    def _build_backup_tab(self) -> QWidget:
        """Build the backup settings tab."""
        tab = QWidget()
        layout = QGridLayout(tab)

        row = 0
        self._enable_backup_check = QCheckBox("Enable Interval Backup")
        self._enable_backup_check.setChecked(
            self.settings.get("enable_interval_backups", False)
        )
        layout.addWidget(self._enable_backup_check, row, 0, 1, 2)

        row += 1
        layout.addWidget(QLabel("Backup Interval:"), row, 0)
        self._backup_interval_spinbox = QSpinBox()
        self._backup_interval_spinbox.setRange(1, 5000)
        self._backup_interval_spinbox.setValue(
            self.settings.get("backup_counter_maximum", 100)
        )
        layout.addWidget(self._backup_interval_spinbox, row, 1)

        row += 1
        layout.addWidget(QLabel("Logs Directory:"), row, 0)
        self._logs_directory_field = QLineEdit()
        self._logs_directory_field.setText(self.oversight.get("logs_directory", ""))
        layout.addWidget(self._logs_directory_field, row, 1)

        row += 1
        browse_btn = QPushButton("Select...")
        browse_btn.clicked.connect(self._select_logs_directory)
        layout.addWidget(browse_btn, row, 1, alignment=Qt.AlignmentFlag.AlignRight)

        return tab

    def _build_reporting_tab(self) -> QWidget:
        """Build the reporting options tab."""
        tab = QWidget()
        layout = QGridLayout(tab)

        row = 0
        self._enable_reporting_check = QCheckBox("Enable Report Sending")
        self._enable_reporting_check.setChecked(
            self.oversight.get("enable_reporting", "False") == "True"
        )
        layout.addWidget(self._enable_reporting_check, row, 0, 1, 2)

        row += 1
        self._report_warnings_check = QCheckBox("Report EDI Validator Warnings")
        self._report_warnings_check.setChecked(
            self.oversight.get("report_edi_errors", False)
        )
        layout.addWidget(self._report_warnings_check, row, 0, 1, 2)

        row += 1
        layout.addWidget(QLabel("Report Email:"), row, 0)
        self._report_email_field = QLineEdit()
        self._report_email_field.setValidator(EMAIL_VALIDATOR)
        self._report_email_field.setPlaceholderText("user@example.com")
        self._report_email_field.setText(
            self.oversight.get("report_email_destination", "")
        )
        layout.addWidget(self._report_email_field, row, 1)

        row += 1
        self._printing_fallback_check = QCheckBox("Enable Report Printing Fallback")
        self._printing_fallback_check.setChecked(
            self.oversight.get("report_printing_fallback", "False") == "True"
        )
        layout.addWidget(self._printing_fallback_check, row, 0, 1, 2)

        return tab

    def _on_email_enabled_changed(self, enabled: bool) -> None:
        """Handle enable email checkbox change."""
        # Enable/disable email fields based on checkbox
        state = (
            Qt.CheckState.Checked.value if enabled else Qt.CheckState.Unchecked.value
        )
        # Add logic to enable/disable fields

    def _select_logs_directory(self) -> None:
        """Select the logs directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Logs Directory",
            self._logs_directory_field.text() or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly,
        )
        if directory:
            self._logs_directory_field.setText(directory)

    def _validate(self) -> bool:
        errors = []

        if self._enable_email_check.isChecked():
            if not self._email_address_field.text():
                errors.append("Email address is required when email is enabled")
            elif not self._email_address_field.hasAcceptableInput():
                errors.append("Email address format is invalid")

            if not self._smtp_server_field.text():
                errors.append("SMTP server is required when email is enabled")

        if errors:
            QMessageBox.critical(self, "Validation Error", "\\n".join(errors))
            return False

        return True

    def _on_ok(self) -> None:
        """Handle OK button click."""
        if not self._validate():
            return

        self._apply()
        self.accept()

    def _apply(self) -> None:
        """Apply dialog changes to settings."""
        # Update settings
        self.settings["odbc_driver"] = self._odbc_driver_combo.currentText()
        self.settings["as400_address"] = self._as400_address_field.text()
        self.settings["as400_username"] = self._as400_username_field.text()
        self.settings["as400_password"] = self._as400_password_field.text()
        self.settings["enable_email"] = self._enable_email_check.isChecked()
        self.settings["email_address"] = self._email_address_field.text()
        self.settings["email_username"] = self._email_username_field.text()
        self.settings["email_password"] = self._email_password_field.text()
        self.settings["email_smtp_server"] = self._smtp_server_field.text()
        self.settings["smtp_port"] = self._smtp_port_spinbox.value()
        self.settings["enable_interval_backups"] = self._enable_backup_check.isChecked()
        self.settings["backup_counter_maximum"] = self._backup_interval_spinbox.value()

        # Update oversight
        self.oversight["logs_directory"] = self._logs_directory_field.text()
        self.oversight["enable_reporting"] = str(
            self._enable_reporting_check.isChecked()
        )
        self.oversight["report_email_destination"] = self._report_email_field.text()
        self.oversight["report_edi_errors"] = self._report_warnings_check.isChecked()
        self.oversight["report_printing_fallback"] = str(
            self._printing_fallback_check.isChecked()
        )

        # Save to database
        if self.db_manager:
            if self.settings.get("id") and self.db_manager.settings is not None:
                self.db_manager.settings.update(self.settings, ["id"])
            if (
                self.oversight.get("id")
                and self.db_manager.oversight_and_defaults is not None
            ):
                self.db_manager.oversight_and_defaults.update(self.oversight, ["id"])

    def get_settings(self) -> Dict[str, Any]:
        """Get the updated settings."""
        return self.settings

    def get_oversight(self) -> Dict[str, Any]:
        """Get the updated oversight."""
        return self.oversight
