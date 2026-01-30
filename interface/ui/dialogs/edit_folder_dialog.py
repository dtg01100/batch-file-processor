"""
Edit folder dialog module for PyQt6 interface.

This module contains the EditFolderDialog implementation.
A tabbed dialog that handles folder configuration with support for:
- General settings (alias, active state, backends)
- Copy backend settings
- FTP backend settings
- Email backend settings
- EDI processing settings
- Conversion format settings
"""

import os
from typing import TYPE_CHECKING, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
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
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal as Signal

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager

from interface.utils.qt_validators import (
    PORT_VALIDATOR,
    EMAIL_VALIDATOR,
    FTP_HOST_VALIDATOR,
)
from interface.utils.validation_feedback import add_validation_to_fields


class EditFolderDialog(QDialog):
    """Tabbed dialog for editing folder configuration."""

    # Conversion format options
    CONVERT_FORMATS = [
        "csv",
        "ScannerWare",
        "scansheet-type-a",
        "jolley_custom",
        "stewarts_custom",
        "simplified_csv",
        "Estore eInvoice",
        "Estore eInvoice Generic",
        "YellowDog CSV",
        "fintech",
    ]

    def __init__(
        self,
        parent: QWidget = None,
        folder_data: Optional[Dict[str, Any]] = None,
        db_manager: "DatabaseManager" = None,
        settings: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the edit folder dialog.

        Args:
            parent: Parent window.
            folder_data: Folder configuration dictionary from database.
            db_manager: Database manager instance.
            settings: Global settings dictionary.
        """
        super().__init__(parent)

        self.folder_data = folder_data or {}
        self.db_manager = db_manager
        self.settings = settings or {}
        self._result: Optional[Dict[str, Any]] = None

        self.setWindowTitle("Edit Folder" if folder_data else "Add Folder")
        self.setModal(True)
        self.resize(700, 500)

        self._setup_ui()
        self._set_dialog_values()
        self._setup_validation_feedback()

    def _setup_validation_feedback(self) -> None:
        add_validation_to_fields(
            self._ftp_server_field,
            self._ftp_port_field,
            self._email_recipient_field,
            self._email_cc_field,
        )

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        # Tab widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Create tabs
        self._general_tab = self._build_general_tab()
        self._copy_tab = self._build_copy_backend_tab()
        self._ftp_tab = self._build_ftp_backend_tab()
        self._email_tab = self._build_email_backend_tab()
        self._edi_tab = self._build_edi_tab()
        self._convert_tab = self._build_convert_format_tab()

        self._tabs.addTab(self._general_tab, "General")
        self._tabs.addTab(self._copy_tab, "Copy Backend")
        self._tabs.addTab(self._ftp_tab, "FTP Backend")
        self._tabs.addTab(self._email_tab, "Email Backend")
        self._tabs.addTab(self._edi_tab, "EDI Processing")
        self._tabs.addTab(self._convert_tab, "Conversion Format")

        # Button box
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def _build_general_tab(self) -> QWidget:
        """Build the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Active state
        self._active_check = QCheckBox("Active")
        self._active_check.setChecked(
            str(self.folder_data.get("folder_is_active", "True")) == "True"
        )
        layout.addWidget(self._active_check)

        # Folder alias
        alias_group = QGroupBox("Folder Alias")
        alias_layout = QVBoxLayout(alias_group)

        self._alias_field = QLineEdit()
        self._alias_field.setPlaceholderText("Enter folder alias...")
        alias_layout.addWidget(self._alias_field)

        show_path_btn = QPushButton("Show Folder Path")
        show_path_btn.clicked.connect(self._show_folder_path)
        alias_layout.addWidget(show_path_btn)

        layout.addWidget(alias_group)

        # Backend selection
        backend_group = QGroupBox("Backends")
        backend_layout = QVBoxLayout(backend_group)

        self._copy_backend_check = QCheckBox("Copy Backend")
        self._copy_backend_check.setChecked(
            self.folder_data.get("process_backend_copy", False)
        )
        self._copy_backend_check.toggled.connect(self._on_backend_state_change)
        backend_layout.addWidget(self._copy_backend_check)

        self._ftp_backend_check = QCheckBox("FTP Backend")
        self._ftp_backend_check.setChecked(
            self.folder_data.get("process_backend_ftp", False)
        )
        self._ftp_backend_check.toggled.connect(self._on_backend_state_change)
        backend_layout.addWidget(self._ftp_backend_check)

        self._email_backend_check = QCheckBox("Email Backend")
        self._email_backend_check.setChecked(
            self.folder_data.get("process_backend_email", False)
        )
        self._email_backend_check.toggled.connect(self._on_backend_state_change)
        backend_layout.addWidget(self._email_backend_check)

        layout.addWidget(backend_group)

        layout.addStretch(1)
        return tab

    def _build_copy_backend_tab(self) -> QWidget:
        """Build the Copy backend tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Copy Backend Settings")
        group_layout = QGridLayout(group)

        row = 0
        group_layout.addWidget(QLabel("Destination Folder:"), row, 0)

        self._copy_directory_field = QLineEdit()
        self._copy_directory_field.setText(
            self.folder_data.get("copy_to_directory", "")
        )
        group_layout.addWidget(self._copy_directory_field, row, 1)

        row += 1
        browse_btn = QPushButton("Select...")
        browse_btn.clicked.connect(self._select_copy_directory)
        group_layout.addWidget(
            browse_btn, row, 1, alignment=Qt.AlignmentFlag.AlignRight
        )

        layout.addWidget(group)
        layout.addStretch(1)
        return tab

    def _build_ftp_backend_tab(self) -> QWidget:
        """Build the FTP backend tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("FTP Backend Settings")
        group_layout = QGridLayout(group)

        row = 0
        group_layout.addWidget(QLabel("FTP Server:"), row, 0)
        self._ftp_server_field = QLineEdit()
        self._ftp_server_field.setValidator(FTP_HOST_VALIDATOR)
        self._ftp_server_field.setPlaceholderText("example.com or 192.168.1.1")
        self._ftp_server_field.setText(self.folder_data.get("ftp_server", ""))
        group_layout.addWidget(self._ftp_server_field, row, 1)

        row += 1
        group_layout.addWidget(QLabel("FTP Port:"), row, 0)
        self._ftp_port_field = QLineEdit()
        self._ftp_port_field.setValidator(PORT_VALIDATOR)
        self._ftp_port_field.setPlaceholderText("1-65535")
        self._ftp_port_field.setText(str(self.folder_data.get("ftp_port", 21)))
        group_layout.addWidget(self._ftp_port_field, row, 1)

        row += 1
        group_layout.addWidget(QLabel("FTP Folder:"), row, 0)
        self._ftp_folder_field = QLineEdit()
        self._ftp_folder_field.setText(self.folder_data.get("ftp_folder", ""))
        group_layout.addWidget(self._ftp_folder_field, row, 1)

        row += 1
        group_layout.addWidget(QLabel("Username:"), row, 0)
        self._ftp_username_field = QLineEdit()
        self._ftp_username_field.setText(self.folder_data.get("ftp_username", ""))
        group_layout.addWidget(self._ftp_username_field, row, 1)

        row += 1
        group_layout.addWidget(QLabel("Password:"), row, 0)
        self._ftp_password_field = QLineEdit()
        self._ftp_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._ftp_password_field.setText(self.folder_data.get("ftp_password", ""))
        group_layout.addWidget(self._ftp_password_field, row, 1)

        row += 1
        self._ftp_passive_check = QCheckBox("Passive Mode")
        self._ftp_passive_check.setChecked(self.folder_data.get("ftp_passive", True))
        group_layout.addWidget(self._ftp_passive_check, row, 0, 1, 2)

        layout.addWidget(group)
        layout.addStretch(1)
        return tab

    def _build_email_backend_tab(self) -> QWidget:
        """Build the Email backend tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Email Backend Settings")
        group_layout = QGridLayout(group)

        row = 0
        group_layout.addWidget(QLabel("Email Recipient:"), row, 0)
        self._email_recipient_field = QLineEdit()
        self._email_recipient_field.setValidator(EMAIL_VALIDATOR)
        self._email_recipient_field.setPlaceholderText("user@example.com")
        self._email_recipient_field.setText(self.folder_data.get("email_to", ""))
        group_layout.addWidget(self._email_recipient_field, row, 1)

        row += 1
        group_layout.addWidget(QLabel("Email CC:"), row, 0)
        self._email_cc_field = QLineEdit()
        self._email_cc_field.setValidator(EMAIL_VALIDATOR)
        self._email_cc_field.setPlaceholderText("user@example.com (optional)")
        self._email_cc_field.setText(self.folder_data.get("email_cc", ""))
        group_layout.addWidget(self._email_cc_field, row, 1)

        row += 1
        group_layout.addWidget(QLabel("Email Subject:"), row, 0)
        self._email_subject_field = QLineEdit()
        self._email_subject_field.setText(
            self.folder_data.get("email_subject_line", "")
        )
        group_layout.addWidget(self._email_subject_field, row, 1)

        layout.addWidget(group)
        layout.addStretch(1)
        return tab

    def _build_edi_tab(self) -> QWidget:
        """Build the EDI processing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # EDI options
        self._force_edi_check = QCheckBox("Force EDI Validation")
        self._force_edi_check.setChecked(
            self.folder_data.get("force_edi_validation", False)
        )
        layout.addWidget(self._force_edi_check)

        # Split EDI
        self._split_edi_check = QCheckBox("Split EDI Documents")
        self._split_edi_check.setChecked(self.folder_data.get("split_edi", False))
        layout.addWidget(self._split_edi_check)

        self._split_invoices_check = QCheckBox("Include Invoices in Split")
        self._split_invoices_check.setChecked(
            self.folder_data.get("split_edi_include_invoices", False)
        )
        layout.addWidget(self._split_invoices_check)

        self._split_credits_check = QCheckBox("Include Credits in Split")
        self._split_credits_check.setChecked(
            self.folder_data.get("split_edi_include_credits", False)
        )
        layout.addWidget(self._split_credits_check)

        # Prepend dates
        self._prepend_dates_check = QCheckBox("Prepend Dates to Files")
        self._prepend_dates_check.setChecked(
            self.folder_data.get("prepend_date_files", False)
        )
        layout.addWidget(self._prepend_dates_check)

        # Rename file
        rename_layout = QHBoxLayout()
        rename_layout.addWidget(QLabel("Rename File:"))
        self._rename_field = QLineEdit()
        self._rename_field.setText(self.folder_data.get("rename_file", ""))
        rename_layout.addWidget(self._rename_field)
        layout.addLayout(rename_layout)

        # EDI options menu
        edi_options_layout = QHBoxLayout()
        edi_options_layout.addWidget(QLabel("EDI Options:"))
        self._edi_options_combo = QComboBox()
        self._edi_options_combo.addItems(["Do Nothing", "Convert EDI", "Tweak EDI"])
        self._edi_options_combo.setCurrentText(
            "Convert EDI"
            if self.folder_data.get("process_edi") == "True"
            else "Tweak EDI"
            if self.folder_data.get("tweak_edi")
            else "Do Nothing"
        )
        self._edi_options_combo.currentTextChanged.connect(self._on_edi_option_changed)
        edi_options_layout.addWidget(self._edi_options_combo)
        layout.addLayout(edi_options_layout)

        layout.addStretch(1)
        return tab

    def _build_convert_format_tab(self) -> QWidget:
        """Build the conversion format tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._process_edi_check = QCheckBox("Process EDI")
        self._process_edi_check.setChecked(
            self.folder_data.get("process_edi", "False") == "True"
        )
        layout.addWidget(self._process_edi_check)

        edi_format_layout = QHBoxLayout()
        edi_format_layout.addWidget(QLabel("EDI Format:"))
        self._edi_format_combo = QComboBox()
        try:
            from edi_format_parser import EDIFormatParser

            available_formats = EDIFormatParser.list_available_formats()
            self._edi_format_combo.addItems(available_formats)
        except Exception:
            self._edi_format_combo.addItems(["default"])
        self._edi_format_combo.setCurrentText(
            self.folder_data.get("edi_format", "default")
        )
        edi_format_layout.addWidget(self._edi_format_combo)
        layout.addLayout(edi_format_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Convert To:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(self.CONVERT_FORMATS)
        self._format_combo.setCurrentText(
            self.folder_data.get("convert_to_format", "csv")
        )
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self._format_combo)
        layout.addLayout(format_layout)

        # Format-specific options
        self._format_options_stack = QStackedWidget()
        self._format_options_stack.addWidget(self._build_csv_options())
        self._format_options_stack.addWidget(self._build_scannerware_options())
        self._format_options_stack.addWidget(self._build_simplified_csv_options())
        self._format_options_stack.addWidget(self._build_estore_options())
        self._format_options_stack.addWidget(self._build_estore_generic_options())
        self._format_options_stack.addWidget(self._build_fintech_options())
        self._format_options_stack.addWidget(
            self._build_default_options()
        )  # jolley_custom
        self._format_options_stack.addWidget(
            self._build_default_options()
        )  # stewarts_custom
        self._format_options_stack.addWidget(
            self._build_default_options()
        )  # scansheet-type-a
        self._format_options_stack.addWidget(
            self._build_default_options()
        )  # YellowDog CSV
        layout.addWidget(self._format_options_stack)

        # Apply EDI tweaks
        self._tweak_edi_check = QCheckBox("Apply EDI Tweaks")
        self._tweak_edi_check.setChecked(self.folder_data.get("tweak_edi", False))
        layout.addWidget(self._tweak_edi_check)

        layout.addStretch(1)
        return tab

    def _build_csv_options(self) -> QWidget:
        """Build CSV format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._upc_check = QCheckBox("Calculate UPC Check Digit")
        self._upc_check.setChecked(
            self.folder_data.get("calculate_upc_check_digit", "False") == "True"
        )
        layout.addWidget(self._upc_check)

        self._a_records_check = QCheckBox("Include A Records")
        self._a_records_check.setChecked(
            self.folder_data.get("include_a_records", "False") == "True"
        )
        layout.addWidget(self._a_records_check)

        self._c_records_check = QCheckBox("Include C Records")
        self._c_records_check.setChecked(
            self.folder_data.get("include_c_records", "False") == "True"
        )
        layout.addWidget(self._c_records_check)

        self._headers_check = QCheckBox("Include Headings")
        self._headers_check.setChecked(
            self.folder_data.get("include_headers", "False") == "True"
        )
        layout.addWidget(self._headers_check)

        return widget

    def _build_scannerware_options(self) -> QWidget:
        """Build ScannerWare format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._pad_a_records_check = QCheckBox('Pad "A" Records')
        self._pad_a_records_check.setChecked(
            self.folder_data.get("pad_a_records", "False") == "True"
        )
        layout.addWidget(self._pad_a_records_check)

        return widget

    def _build_simplified_csv_options(self) -> QWidget:
        """Build Simplified CSV format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._item_numbers_check = QCheckBox("Include Item Numbers")
        self._item_numbers_check.setChecked(
            self.folder_data.get("include_item_numbers", False)
        )
        layout.addWidget(self._item_numbers_check)

        self._item_description_check = QCheckBox("Include Item Description")
        self._item_description_check.setChecked(
            self.folder_data.get("include_item_description", False)
        )
        layout.addWidget(self._item_description_check)

        return widget

    def _build_estore_options(self) -> QWidget:
        """Build Estore eInvoice format options."""
        widget = QWidget()
        layout = QGridLayout(widget)

        row = 0
        layout.addWidget(QLabel("Store Number:"), row, 0)
        self._estore_store_field = QLineEdit()
        self._estore_store_field.setText(
            self.folder_data.get("estore_store_number", "")
        )
        layout.addWidget(self._estore_store_field, row, 1)

        row += 1
        layout.addWidget(QLabel("Vendor OId:"), row, 0)
        self._estore_vendor_oid_field = QLineEdit()
        self._estore_vendor_oid_field.setText(
            self.folder_data.get("estore_Vendor_OId", "")
        )
        layout.addWidget(self._estore_vendor_oid_field, row, 1)

        return widget

    def _build_estore_generic_options(self) -> QWidget:
        """Build Estore eInvoice Generic format options."""
        widget = QWidget()
        layout = QGridLayout(widget)

        row = 0
        layout.addWidget(QLabel("Store Number:"), row, 0)
        self._estore_generic_store_field = QLineEdit()
        self._estore_generic_store_field.setText(
            self.folder_data.get("estore_store_number", "")
        )
        layout.addWidget(self._estore_generic_store_field, row, 1)

        row += 1
        layout.addWidget(QLabel("Vendor OId:"), row, 0)
        self._estore_generic_vendor_oid_field = QLineEdit()
        self._estore_generic_vendor_oid_field.setText(
            self.folder_data.get("estore_Vendor_OId", "")
        )
        layout.addWidget(self._estore_generic_vendor_oid_field, row, 1)

        row += 1
        layout.addWidget(QLabel("C Record OId:"), row, 0)
        self._estore_generic_c_oid_field = QLineEdit()
        self._estore_generic_c_oid_field.setText(
            self.folder_data.get("estore_c_record_OID", "")
        )
        layout.addWidget(self._estore_generic_c_oid_field, row, 1)

        return widget

    def _build_fintech_options(self) -> QWidget:
        """Build Fintech format options."""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QLabel("Division ID:"))
        self._fintech_division_field = QLineEdit()
        self._fintech_division_field.setText(
            self.folder_data.get("fintech_division_id", "")
        )
        layout.addWidget(self._fintech_division_field)

        return widget

    def _build_default_options(self) -> QWidget:
        """Build default/empty format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("No format-specific options"))
        return widget

    def _set_dialog_values(self) -> None:
        """Set initial dialog values from folder data."""
        if self.folder_data:
            self._alias_field.setText(self.folder_data.get("alias", ""))

    def _show_folder_path(self) -> None:
        """Show the folder path in a message box."""
        path = self.folder_data.get("folder_name", "")
        QMessageBox.information(self, "Folder Path", path)

    def _select_copy_directory(self) -> None:
        """Select the copy backend destination directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Copy Destination",
            self._copy_directory_field.text() or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly,
        )
        if directory:
            self._copy_directory_field.setText(directory)

    def _on_backend_state_change(self) -> None:
        """Handle backend state changes."""
        # Enable/disable tabs based on backend selection
        self._copy_tab.setEnabled(self._copy_backend_check.isChecked())
        self._ftp_tab.setEnabled(self._ftp_backend_check.isChecked())
        self._email_tab.setEnabled(self._email_backend_check.isChecked())

    def _on_edi_option_changed(self, text: str) -> None:
        """Handle EDI option selection change."""
        pass

    def _on_format_changed(self, text: str) -> None:
        """Handle format selection change."""
        format_index_map = {
            "csv": 0,
            "ScannerWare": 1,
            "simplified_csv": 2,
            "Estore eInvoice": 3,
            "Estore eInvoice Generic": 4,
            "fintech": 5,
            "jolley_custom": 6,
            "stewarts_custom": 7,
            "scansheet-type-a": 8,
            "YellowDog CSV": 9,
        }
        index = format_index_map.get(text, 0)
        self._format_options_stack.setCurrentIndex(index)

    def _validate(self) -> bool:
        """Validate dialog input using Qt validators."""
        errors = []

        # Check at least one backend is selected
        backend_count = (
            int(self._copy_backend_check.isChecked())
            + int(self._ftp_backend_check.isChecked())
            + int(self._email_backend_check.isChecked())
        )

        if backend_count == 0 and self._active_check.isChecked():
            errors.append("No backend is selected")

        # FTP validation - Qt validators handle format, we check required fields
        if self._ftp_backend_check.isChecked():
            if not self._ftp_server_field.text():
                errors.append("FTP Server is required")
            elif not self._ftp_server_field.hasAcceptableInput():
                errors.append("FTP Server format is invalid")

            if not self._ftp_port_field.text():
                errors.append("FTP Port is required")
            elif not self._ftp_port_field.hasAcceptableInput():
                errors.append("FTP Port must be between 1 and 65535")

        # Email validation - Qt validators handle format, we check required fields
        if self._email_backend_check.isChecked():
            if not self._email_recipient_field.text():
                errors.append("Email recipient is required")
            elif not self._email_recipient_field.hasAcceptableInput():
                errors.append("Email recipient format is invalid")

            # CC is optional, but if provided must be valid
            if (
                self._email_cc_field.text()
                and not self._email_cc_field.hasAcceptableInput()
            ):
                errors.append("Email CC format is invalid")

        if errors:
            QMessageBox.critical(self, "Validation Error", "\\n".join(errors))
            return False

        return True

    def _on_ok(self) -> None:
        """Handle OK button click."""
        if not self._validate():
            return

        self._result = self._apply()
        self.accept()

    def _apply(self) -> Dict[str, Any]:
        """Apply dialog changes and return result."""
        result = dict(self.folder_data)

        result["folder_is_active"] = str(self._active_check.isChecked())
        result["alias"] = self._alias_field.text() or os.path.basename(
            self.folder_data.get("folder_name", "")
        )

        # Backend settings
        result["process_backend_copy"] = self._copy_backend_check.isChecked()
        result["process_backend_ftp"] = self._ftp_backend_check.isChecked()
        result["process_backend_email"] = self._email_backend_check.isChecked()

        # Copy backend
        result["copy_to_directory"] = self._copy_directory_field.text()

        # FTP backend
        result["ftp_server"] = self._ftp_server_field.text()
        result["ftp_port"] = (
            int(self._ftp_port_field.text()) if self._ftp_port_field.text() else 21
        )
        result["ftp_folder"] = self._ftp_folder_field.text()
        result["ftp_username"] = self._ftp_username_field.text()
        result["ftp_password"] = self._ftp_password_field.text()
        result["ftp_passive"] = self._ftp_passive_check.isChecked()

        # Email backend
        result["email_to"] = self._email_recipient_field.text()
        result["email_cc"] = self._email_cc_field.text()
        result["email_subject_line"] = self._email_subject_field.text()

        # EDI settings
        result["force_edi_validation"] = self._force_edi_check.isChecked()
        result["process_edi"] = str(self._process_edi_check.isChecked())
        result["edi_format"] = self._edi_format_combo.currentText()
        result["tweak_edi"] = self._tweak_edi_check.isChecked()
        result["split_edi"] = self._split_edi_check.isChecked()
        result["split_edi_include_invoices"] = self._split_invoices_check.isChecked()
        result["split_edi_include_credits"] = self._split_credits_check.isChecked()
        result["prepend_date_files"] = self._prepend_dates_check.isChecked()
        result["rename_file"] = self._rename_field.text()

        # Conversion format
        result["convert_to_format"] = self._format_combo.currentText()

        return result

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Get the dialog result."""
        return self._result
