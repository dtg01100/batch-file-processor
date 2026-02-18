"""Qt reimplementation of EditFoldersDialog.

Provides a PyQt6-based dialog for editing folder configuration settings.
All dependencies are injectable via the constructor for testability.
"""

import os
from typing import Dict, Any, Optional, List, Callable

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QPushButton,
    QListWidget,
    QSpinBox,
    QWidget,
    QScrollArea,
    QFrame,
    QDialogButtonBox,
    QMessageBox,
    QFileDialog,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

from interface.validation.folder_settings_validator import (
    FolderSettingsValidator,
    ValidationResult,
)
from interface.operations.folder_data_extractor import ExtractedDialogFields
from interface.services.ftp_service import FTPServiceProtocol


class QtFolderDataExtractor:
    """Extracts folder configuration data from Qt widgets.

    Reads from a dict of field name -> QWidget mappings and produces
    an ExtractedDialogFields dataclass, mirroring the Tkinter-based
    FolderDataExtractor but operating on PyQt6 widgets.
    """

    def __init__(self, fields: Dict[str, QWidget]):
        self.fields = fields

    def extract_all(self) -> ExtractedDialogFields:
        return ExtractedDialogFields(
            folder_name=self._get_text("folder_name_value"),
            alias=self._get_text("folder_alias_field"),
            folder_is_active=self._get_check_str("active_checkbutton"),
            process_backend_copy=self._get_bool("process_backend_copy_check"),
            process_backend_ftp=self._get_bool("process_backend_ftp_check"),
            process_backend_email=self._get_bool("process_backend_email_check"),
            ftp_server=self._get_text("ftp_server_field"),
            ftp_port=self._get_int("ftp_port_field", 21),
            ftp_folder=self._get_text("ftp_folder_field"),
            ftp_username=self._get_text("ftp_username_field"),
            ftp_password=self._get_text("ftp_password_field"),
            email_to=self._get_text("email_recepient_field"),
            email_subject_line=self._get_text("email_sender_subject_field"),
            process_edi=self._get_check_str("process_edi"),
            convert_to_format=self._get_combo("convert_formats_var"),
            tweak_edi=self._get_bool("tweak_edi"),
            split_edi=self._get_bool("split_edi"),
            split_edi_include_invoices=self._get_bool("split_edi_send_invoices"),
            split_edi_include_credits=self._get_bool("split_edi_send_credits"),
            prepend_date_files=self._get_bool("prepend_file_dates"),
            rename_file=self._get_text("rename_file_field"),
            split_edi_filter_categories=self._get_text("split_edi_filter_categories_entry"),
            split_edi_filter_mode=self._get_combo("split_edi_filter_mode"),
            calculate_upc_check_digit=self._get_check_str("upc_var_check"),
            include_a_records=self._get_check_str("a_rec_var_check"),
            include_c_records=self._get_check_str("c_rec_var_check"),
            include_headers=self._get_check_str("headers_check"),
            filter_ampersand=self._get_check_str("ampersand_check"),
            force_edi_validation=self._get_bool("force_edi_check_var"),
            pad_a_records=self._get_check_str("pad_arec_check"),
            a_record_padding=self._get_text("a_record_padding_field"),
            a_record_padding_length=self._get_int("a_record_padding_length", 6),
            append_a_records=self._get_check_str("append_arec_check"),
            a_record_append_text=self._get_text("a_record_append_field"),
            force_txt_file_ext=self._get_check_str("force_txt_file_ext_check"),
            invoice_date_offset=self._get_int("invoice_date_offset", 0),
            invoice_date_custom_format=self._get_bool("invoice_date_custom_format"),
            invoice_date_custom_format_string=self._get_text("invoice_date_custom_format_field"),
            retail_uom=self._get_bool("edi_each_uom_tweak"),
            override_upc_bool=self._get_bool("override_upc_bool"),
            override_upc_level=self._get_int("override_upc_level", 1),
            override_upc_category_filter=self._get_text("override_upc_category_filter_entry"),
            upc_target_length=self._get_int("upc_target_length_entry", 11),
            upc_padding_pattern=self._get_text("upc_padding_pattern_entry"),
            include_item_numbers=self._get_bool("include_item_numbers"),
            include_item_description=self._get_bool("include_item_description"),
            simple_csv_sort_order=self._get_text("simple_csv_column_sorter"),
            split_prepaid_sales_tax_crec=self._get_bool("split_sales_tax_prepaid_var"),
            estore_store_number=self._get_text("estore_store_number_field"),
            estore_vendor_oid=self._get_text("estore_Vendor_OId_field"),
            estore_vendor_namevendoroid=self._get_text("estore_vendor_namevendoroid_field"),
            fintech_division_id=self._get_text("fintech_divisionid_field"),
            copy_to_directory="",
        )

    def _get_text(self, field_name: str) -> str:
        widget = self.fields.get(field_name)
        if widget is None:
            return ""
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return ""

    def _get_int(self, field_name: str, default: int = 0) -> int:
        widget = self.fields.get(field_name)
        if widget is None:
            return default
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QComboBox):
            try:
                return int(widget.currentText())
            except (ValueError, TypeError):
                return default
        if isinstance(widget, QLineEdit):
            try:
                return int(widget.text())
            except (ValueError, TypeError):
                return default
        return default

    def _get_bool(self, field_name: str) -> bool:
        widget = self.fields.get(field_name)
        if widget is None:
            return False
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        return False

    def _get_check_str(self, field_name: str) -> str:
        widget = self.fields.get(field_name)
        if widget is None:
            return "False"
        if isinstance(widget, QCheckBox):
            return "True" if widget.isChecked() else "False"
        return "False"

    def _get_combo(self, field_name: str) -> str:
        widget = self.fields.get(field_name)
        if widget is None:
            return ""
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return ""


class EditFoldersDialog(QDialog):
    """Qt-based dialog for editing folder configuration settings.

    All dependencies are injectable via the constructor for testability.
    """

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

    EDI_OPTIONS = ["Do Nothing", "Convert EDI", "Tweak EDI"]

    def __init__(
        self,
        parent: Optional[QWidget],
        folder_config: Dict[str, Any],
        title: str = "Edit Folder",
        ftp_service: Optional[FTPServiceProtocol] = None,
        validator: Optional[FolderSettingsValidator] = None,
        settings_provider: Optional[Callable] = None,
        alias_provider: Optional[Callable] = None,
        on_apply_success: Optional[Callable] = None,
    ):
        super().__init__(parent)
        self._folder_config = folder_config
        self._ftp_service = ftp_service
        self._validator = validator
        self._settings_provider = settings_provider
        self._alias_provider = alias_provider
        self._on_apply_success = on_apply_success

        self._fields: Dict[str, QWidget] = {}
        self.copy_to_directory: str = folder_config.get("copy_to_directory", "")

        self._settings = self._load_settings()

        self.setWindowTitle(title)
        self.setModal(True)
        self._build_ui()
        self._populate_fields(folder_config)
        self._update_active_state()
        self._update_backend_states()

    def _load_settings(self) -> dict:
        if self._settings_provider:
            return self._settings_provider() or {}
        return {}

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)

        self._active_checkbox = QCheckBox("Folder Is Disabled")
        self._active_checkbox.setStyleSheet("QCheckBox { background-color: red; padding: 4px; }")
        self._active_checkbox.toggled.connect(self._update_active_state)
        self._fields["active_checkbutton"] = self._active_checkbox
        main_layout.addWidget(self._active_checkbox)

        columns_layout = QHBoxLayout()

        columns_layout.addWidget(self._build_others_column())
        columns_layout.addWidget(self._make_vseparator())
        columns_layout.addWidget(self._build_folder_column())
        columns_layout.addWidget(self._make_vseparator())
        columns_layout.addWidget(self._build_backend_column())
        columns_layout.addWidget(self._make_vseparator())
        columns_layout.addWidget(self._build_edi_column())

        main_layout.addLayout(columns_layout)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_ok)
        button_box.rejected.connect(self.reject)
        outer_layout.addWidget(button_box)

    @staticmethod
    def _make_vseparator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    # ------------------------------------------------------------------
    # Column 1 – Others List
    # ------------------------------------------------------------------
    def _build_others_column(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        layout.addWidget(QLabel("Other Folders:"))

        self._others_list = QListWidget()
        self._others_list.setMaximumWidth(180)
        aliases: List[str] = []
        if self._alias_provider:
            aliases = sorted(self._alias_provider() or [])
        for alias in aliases:
            self._others_list.addItem(alias)
        layout.addWidget(self._others_list)

        self._copy_config_btn = QPushButton("Copy Config")
        self._copy_config_btn.clicked.connect(self._copy_config_from_other)
        layout.addWidget(self._copy_config_btn)

        return container

    # ------------------------------------------------------------------
    # Column 2 – Folder Settings
    # ------------------------------------------------------------------
    def _build_folder_column(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        layout.addWidget(QLabel("Backends:"))

        self._copy_backend_check = QCheckBox("Copy Backend")
        self._copy_backend_check.toggled.connect(self._update_backend_states)
        self._fields["process_backend_copy_check"] = self._copy_backend_check
        layout.addWidget(self._copy_backend_check)

        self._ftp_backend_check = QCheckBox("FTP Backend")
        self._ftp_backend_check.toggled.connect(self._update_backend_states)
        self._fields["process_backend_ftp_check"] = self._ftp_backend_check
        layout.addWidget(self._ftp_backend_check)

        self._email_backend_check = QCheckBox("Email Backend")
        self._email_backend_check.toggled.connect(self._update_backend_states)
        self._fields["process_backend_email_check"] = self._email_backend_check
        layout.addWidget(self._email_backend_check)

        if self._folder_config.get("folder_name") != "template":
            alias_group = QGroupBox("Folder Alias")
            alias_layout = QFormLayout(alias_group)
            self._folder_alias_field = QLineEdit()
            self._fields["folder_alias_field"] = self._folder_alias_field
            alias_layout.addRow("Alias:", self._folder_alias_field)

            show_path_btn = QPushButton("Show Folder Path")
            show_path_btn.clicked.connect(self._show_folder_path)
            alias_layout.addRow(show_path_btn)
            layout.addWidget(alias_group)

        layout.addStretch()
        return container

    # ------------------------------------------------------------------
    # Column 3 – Backend Settings
    # ------------------------------------------------------------------
    def _build_backend_column(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        copy_group = QGroupBox("Copy Backend Settings")
        copy_layout = QVBoxLayout(copy_group)
        self._copy_dest_btn = QPushButton("Select Copy Backend Destination Folder...")
        self._copy_dest_btn.clicked.connect(self._select_copy_directory)
        copy_layout.addWidget(self._copy_dest_btn)
        layout.addWidget(copy_group)

        ftp_group = QGroupBox("FTP Backend Settings")
        ftp_layout = QFormLayout(ftp_group)
        self._ftp_server_field = QLineEdit()
        self._fields["ftp_server_field"] = self._ftp_server_field
        ftp_layout.addRow("FTP Server:", self._ftp_server_field)

        self._ftp_port_field = QLineEdit()
        self._fields["ftp_port_field"] = self._ftp_port_field
        ftp_layout.addRow("FTP Port:", self._ftp_port_field)

        self._ftp_folder_field = QLineEdit()
        self._fields["ftp_folder_field"] = self._ftp_folder_field
        ftp_layout.addRow("FTP Folder:", self._ftp_folder_field)

        self._ftp_username_field = QLineEdit()
        self._fields["ftp_username_field"] = self._ftp_username_field
        ftp_layout.addRow("FTP Username:", self._ftp_username_field)

        self._ftp_password_field = QLineEdit()
        self._ftp_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._fields["ftp_password_field"] = self._ftp_password_field
        ftp_layout.addRow("FTP Password:", self._ftp_password_field)
        layout.addWidget(ftp_group)

        email_group = QGroupBox("Email Backend Settings")
        email_layout = QFormLayout(email_group)
        self._email_recipient_field = QLineEdit()
        self._fields["email_recepient_field"] = self._email_recipient_field
        email_layout.addRow("Recipient Address:", self._email_recipient_field)

        self._email_subject_field = QLineEdit()
        self._fields["email_sender_subject_field"] = self._email_subject_field
        email_layout.addRow("Email Subject:", self._email_subject_field)
        layout.addWidget(email_group)

        layout.addStretch()
        return container

    # ------------------------------------------------------------------
    # Column 4 – EDI Settings
    # ------------------------------------------------------------------
    def _build_edi_column(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        self._force_edi_check = QCheckBox("Force EDI Validation")
        self._fields["force_edi_check_var"] = self._force_edi_check
        layout.addWidget(self._force_edi_check)

        split_group = QGroupBox("Split EDI")
        split_layout = QVBoxLayout(split_group)

        self._split_edi_check = QCheckBox("Split EDI")
        self._fields["split_edi"] = self._split_edi_check
        split_layout.addWidget(self._split_edi_check)

        self._send_invoices_check = QCheckBox("Send Invoices")
        self._fields["split_edi_send_invoices"] = self._send_invoices_check
        split_layout.addWidget(self._send_invoices_check)

        self._send_credits_check = QCheckBox("Send Credits")
        self._fields["split_edi_send_credits"] = self._send_credits_check
        split_layout.addWidget(self._send_credits_check)

        self._prepend_dates_check = QCheckBox("Prepend File Dates")
        self._fields["prepend_file_dates"] = self._prepend_dates_check
        split_layout.addWidget(self._prepend_dates_check)

        rename_row = QHBoxLayout()
        rename_row.addWidget(QLabel("Rename File:"))
        self._rename_file_field = QLineEdit()
        self._rename_file_field.setMaximumWidth(100)
        self._fields["rename_file_field"] = self._rename_file_field
        rename_row.addWidget(self._rename_file_field)
        split_layout.addLayout(rename_row)

        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Filter Categories:"))
        self._filter_categories_field = QLineEdit()
        self._filter_categories_field.setMaximumWidth(120)
        self._filter_categories_field.setToolTip(
            "Enter 'ALL' or a comma separated list of category numbers (e.g., 1,5,12)"
        )
        self._fields["split_edi_filter_categories_entry"] = self._filter_categories_field
        cat_row.addWidget(self._filter_categories_field)
        split_layout.addLayout(cat_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self._filter_mode_combo = QComboBox()
        self._filter_mode_combo.addItems(["include", "exclude"])
        self._fields["split_edi_filter_mode"] = self._filter_mode_combo
        mode_row.addWidget(self._filter_mode_combo)
        split_layout.addLayout(mode_row)

        layout.addWidget(split_group)

        edi_opt_row = QHBoxLayout()
        edi_opt_row.addWidget(QLabel("EDI Options:"))
        self._edi_options_combo = QComboBox()
        self._edi_options_combo.addItems(self.EDI_OPTIONS)
        self._edi_options_combo.currentTextChanged.connect(self._on_edi_option_changed)
        edi_opt_row.addWidget(self._edi_options_combo)
        layout.addLayout(edi_opt_row)

        self._dynamic_edi_container = QWidget()
        self._dynamic_edi_layout = QVBoxLayout(self._dynamic_edi_container)
        self._dynamic_edi_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._dynamic_edi_container)

        layout.addStretch()
        return container

    # ------------------------------------------------------------------
    # Dynamic EDI area builders
    # ------------------------------------------------------------------
    def _clear_dynamic_edi(self):
        while self._dynamic_edi_layout.count():
            item = self._dynamic_edi_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _on_edi_option_changed(self, option: str):
        self._clear_dynamic_edi()
        if option == "Do Nothing":
            self._build_do_nothing_area()
        elif option == "Convert EDI":
            self._build_convert_edi_area()
        elif option == "Tweak EDI":
            self._build_tweak_edi_area()

    def _build_do_nothing_area(self):
        self._fields["process_edi"] = self._make_hidden_check(False)
        self._fields["tweak_edi"] = self._make_hidden_check(False)
        label = QLabel("Send As Is")
        self._dynamic_edi_layout.addWidget(label)

    def _build_convert_edi_area(self):
        self._fields["process_edi"] = self._make_hidden_check(True)
        self._fields["tweak_edi"] = self._make_hidden_check(False)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Convert To:"))
        self._convert_format_combo = QComboBox()
        self._convert_format_combo.addItems(self.CONVERT_FORMATS)
        self._fields["convert_formats_var"] = self._convert_format_combo
        fmt_row.addWidget(self._convert_format_combo)
        wrapper_layout.addLayout(fmt_row)

        self._convert_sub_container = QWidget()
        self._convert_sub_layout = QVBoxLayout(self._convert_sub_container)
        self._convert_sub_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self._convert_sub_container)

        self._convert_format_combo.currentTextChanged.connect(self._on_convert_format_changed)

        current_fmt = self._folder_config.get("convert_to_format", "csv")
        idx = self._convert_format_combo.findText(current_fmt)
        if idx >= 0:
            self._convert_format_combo.setCurrentIndex(idx)
        self._on_convert_format_changed(self._convert_format_combo.currentText())

        self._dynamic_edi_layout.addWidget(wrapper)

    def _build_tweak_edi_area(self):
        self._fields["process_edi"] = self._make_hidden_check(False)
        self._fields["tweak_edi"] = self._make_hidden_check(True)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self._tweak_upc_check = QCheckBox("Calculate UPC Check Digit")
        self._fields["upc_var_check"] = self._tweak_upc_check
        wrapper_layout.addWidget(self._tweak_upc_check)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)

        self._tweak_pad_arec_check = QCheckBox('Pad "A" Records')
        self._fields["pad_arec_check"] = self._tweak_pad_arec_check
        arec_layout.addWidget(self._tweak_pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        self._tweak_arec_padding_field = QLineEdit()
        self._tweak_arec_padding_field.setMaximumWidth(100)
        self._fields["a_record_padding_field"] = self._tweak_arec_padding_field
        pad_row.addWidget(self._tweak_arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        self._tweak_arec_padding_length = QComboBox()
        self._tweak_arec_padding_length.addItems(["6", "30"])
        self._fields["a_record_padding_length"] = self._tweak_arec_padding_length
        pad_row.addWidget(self._tweak_arec_padding_length)
        arec_layout.addLayout(pad_row)

        self._tweak_append_arec_check = QCheckBox('Append to "A" Records (6 Characters) (Series2K)')
        self._fields["append_arec_check"] = self._tweak_append_arec_check
        arec_layout.addWidget(self._tweak_append_arec_check)

        append_row = QHBoxLayout()
        append_row.addWidget(QLabel("Append Text:"))
        self._tweak_arec_append_field = QLineEdit()
        self._tweak_arec_append_field.setMaximumWidth(100)
        self._fields["a_record_append_field"] = self._tweak_arec_append_field
        append_row.addWidget(self._tweak_arec_append_field)
        arec_layout.addLayout(append_row)

        wrapper_layout.addWidget(arec_group)

        self._tweak_force_txt_check = QCheckBox("Force .txt file extension")
        self._fields["force_txt_file_ext_check"] = self._tweak_force_txt_check
        wrapper_layout.addWidget(self._tweak_force_txt_check)

        offset_row = QHBoxLayout()
        offset_row.addWidget(QLabel("Invoice Offset (Days):"))
        self._tweak_invoice_offset = QSpinBox()
        self._tweak_invoice_offset.setRange(-14, 14)
        self._fields["invoice_date_offset"] = self._tweak_invoice_offset
        offset_row.addWidget(self._tweak_invoice_offset)
        wrapper_layout.addLayout(offset_row)

        custom_date_row = QHBoxLayout()
        self._tweak_custom_date_check = QCheckBox("Custom Invoice Date Format")
        self._fields["invoice_date_custom_format"] = self._tweak_custom_date_check
        custom_date_row.addWidget(self._tweak_custom_date_check)
        self._tweak_custom_date_field = QLineEdit()
        self._tweak_custom_date_field.setMaximumWidth(100)
        self._fields["invoice_date_custom_format_field"] = self._tweak_custom_date_field
        custom_date_row.addWidget(self._tweak_custom_date_field)
        wrapper_layout.addLayout(custom_date_row)

        self._tweak_retail_uom_check = QCheckBox("Each UOM")
        self._fields["edi_each_uom_tweak"] = self._tweak_retail_uom_check
        wrapper_layout.addWidget(self._tweak_retail_uom_check)

        upc_override_group = QGroupBox("Override UPC")
        upc_layout = QVBoxLayout(upc_override_group)

        self._tweak_override_upc_check = QCheckBox("Override UPC")
        self._fields["override_upc_bool"] = self._tweak_override_upc_check
        upc_layout.addWidget(self._tweak_override_upc_check)

        upc_row1 = QHBoxLayout()
        upc_row1.addWidget(QLabel("Level:"))
        self._tweak_override_upc_level = QComboBox()
        self._tweak_override_upc_level.addItems(["1", "2", "3", "4"])
        self._fields["override_upc_level"] = self._tweak_override_upc_level
        upc_row1.addWidget(self._tweak_override_upc_level)

        upc_row1.addWidget(QLabel("Category Filter:"))
        self._tweak_override_upc_cat_filter = QLineEdit()
        self._tweak_override_upc_cat_filter.setMaximumWidth(100)
        self._tweak_override_upc_cat_filter.setToolTip(
            "Enter 'ALL' or a comma separated list of numbers"
        )
        self._fields["override_upc_category_filter_entry"] = self._tweak_override_upc_cat_filter
        upc_row1.addWidget(self._tweak_override_upc_cat_filter)
        upc_layout.addLayout(upc_row1)

        upc_row2 = QHBoxLayout()
        upc_row2.addWidget(QLabel("UPC Target Length:"))
        self._tweak_upc_target_length = QLineEdit()
        self._tweak_upc_target_length.setMaximumWidth(50)
        self._fields["upc_target_length_entry"] = self._tweak_upc_target_length
        upc_row2.addWidget(self._tweak_upc_target_length)
        upc_layout.addLayout(upc_row2)

        upc_row3 = QHBoxLayout()
        upc_row3.addWidget(QLabel("UPC Padding Pattern:"))
        self._tweak_upc_padding_pattern = QLineEdit()
        self._tweak_upc_padding_pattern.setMaximumWidth(120)
        self._fields["upc_padding_pattern_entry"] = self._tweak_upc_padding_pattern
        upc_row3.addWidget(self._tweak_upc_padding_pattern)
        upc_layout.addLayout(upc_row3)

        wrapper_layout.addWidget(upc_override_group)

        self._tweak_split_sales_tax_check = QCheckBox("Split Sales Tax 'C' Records")
        self._fields["split_sales_tax_prepaid_var"] = self._tweak_split_sales_tax_check
        wrapper_layout.addWidget(self._tweak_split_sales_tax_check)

        self._populate_tweak_fields()

        self._dynamic_edi_layout.addWidget(wrapper)

    def _populate_tweak_fields(self):
        cfg = self._folder_config
        self._tweak_upc_check.setChecked(str(cfg.get("calculate_upc_check_digit", "False")) == "True")
        self._tweak_pad_arec_check.setChecked(str(cfg.get("pad_a_records", "False")) == "True")
        self._tweak_arec_padding_field.setText(str(cfg.get("a_record_padding", "")))
        pad_len = str(cfg.get("a_record_padding_length", 6))
        idx = self._tweak_arec_padding_length.findText(pad_len)
        if idx >= 0:
            self._tweak_arec_padding_length.setCurrentIndex(idx)
        self._tweak_append_arec_check.setChecked(str(cfg.get("append_a_records", "False")) == "True")
        self._tweak_arec_append_field.setText(str(cfg.get("a_record_append_text", "")))
        self._tweak_force_txt_check.setChecked(str(cfg.get("force_txt_file_ext", "False")) == "True")
        self._tweak_invoice_offset.setValue(int(cfg.get("invoice_date_offset", 0)))
        self._tweak_custom_date_check.setChecked(bool(cfg.get("invoice_date_custom_format", False)))
        self._tweak_custom_date_field.setText(str(cfg.get("invoice_date_custom_format_string", "")))
        self._tweak_retail_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        self._tweak_override_upc_check.setChecked(bool(cfg.get("override_upc_bool", False)))
        lvl = str(cfg.get("override_upc_level", 1))
        idx = self._tweak_override_upc_level.findText(lvl)
        if idx >= 0:
            self._tweak_override_upc_level.setCurrentIndex(idx)
        self._tweak_override_upc_cat_filter.setText(str(cfg.get("override_upc_category_filter", "")))
        self._tweak_upc_target_length.setText(str(cfg.get("upc_target_length", 11)))
        self._tweak_upc_padding_pattern.setText(str(cfg.get("upc_padding_pattern", "           ")))
        self._tweak_split_sales_tax_check.setChecked(bool(cfg.get("split_prepaid_sales_tax_crec", False)))

    # ------------------------------------------------------------------
    # Convert format sub-widgets
    # ------------------------------------------------------------------
    def _clear_convert_sub(self):
        while self._convert_sub_layout.count():
            item = self._convert_sub_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _on_convert_format_changed(self, fmt: str):
        self._clear_convert_sub()
        if fmt == "csv":
            self._build_csv_sub()
        elif fmt == "ScannerWare":
            self._build_scannerware_sub()
        elif fmt == "simplified_csv":
            self._build_simplified_csv_sub()
        elif fmt in ("Estore eInvoice", "Estore eInvoice Generic"):
            self._build_estore_sub(fmt)
        elif fmt == "fintech":
            self._build_fintech_sub()
        elif fmt == "scansheet-type-a":
            pass
        elif fmt in ("jolley_custom", "stewarts_custom", "YellowDog CSV"):
            self._build_basic_options_sub()

    def _build_csv_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self._csv_upc_check = QCheckBox("Calculate UPC Check Digit")
        self._fields["upc_var_check"] = self._csv_upc_check
        layout.addWidget(self._csv_upc_check)

        self._csv_a_rec_check = QCheckBox("Include A Records")
        self._fields["a_rec_var_check"] = self._csv_a_rec_check
        layout.addWidget(self._csv_a_rec_check)

        self._csv_c_rec_check = QCheckBox("Include C Records")
        self._fields["c_rec_var_check"] = self._csv_c_rec_check
        layout.addWidget(self._csv_c_rec_check)

        self._csv_headers_check = QCheckBox("Include Headings")
        self._fields["headers_check"] = self._csv_headers_check
        layout.addWidget(self._csv_headers_check)

        self._csv_ampersand_check = QCheckBox("Filter Ampersand")
        self._fields["ampersand_check"] = self._csv_ampersand_check
        layout.addWidget(self._csv_ampersand_check)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)

        self._csv_pad_arec_check = QCheckBox('Pad "A" Records')
        self._fields["pad_arec_check"] = self._csv_pad_arec_check
        arec_layout.addWidget(self._csv_pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        self._csv_arec_padding_field = QLineEdit()
        self._csv_arec_padding_field.setMaximumWidth(100)
        self._fields["a_record_padding_field"] = self._csv_arec_padding_field
        pad_row.addWidget(self._csv_arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        self._csv_arec_padding_length = QComboBox()
        self._csv_arec_padding_length.addItems(["6", "30"])
        self._fields["a_record_padding_length"] = self._csv_arec_padding_length
        pad_row.addWidget(self._csv_arec_padding_length)
        arec_layout.addLayout(pad_row)

        layout.addWidget(arec_group)

        upc_group = QGroupBox("Override UPC")
        upc_layout = QVBoxLayout(upc_group)

        self._csv_override_upc_check = QCheckBox("Override UPC")
        self._fields["override_upc_bool"] = self._csv_override_upc_check
        upc_layout.addWidget(self._csv_override_upc_check)

        upc_row1 = QHBoxLayout()
        upc_row1.addWidget(QLabel("Level:"))
        self._csv_override_upc_level = QComboBox()
        self._csv_override_upc_level.addItems(["1", "2", "3", "4"])
        self._fields["override_upc_level"] = self._csv_override_upc_level
        upc_row1.addWidget(self._csv_override_upc_level)
        upc_row1.addWidget(QLabel("Category Filter:"))
        self._csv_override_upc_cat_filter = QLineEdit()
        self._csv_override_upc_cat_filter.setMaximumWidth(100)
        self._csv_override_upc_cat_filter.setToolTip(
            "Enter 'ALL' or a comma separated list of numbers"
        )
        self._fields["override_upc_category_filter_entry"] = self._csv_override_upc_cat_filter
        upc_row1.addWidget(self._csv_override_upc_cat_filter)
        upc_layout.addLayout(upc_row1)

        upc_row2 = QHBoxLayout()
        upc_row2.addWidget(QLabel("UPC Target Length:"))
        self._csv_upc_target_length = QLineEdit()
        self._csv_upc_target_length.setMaximumWidth(50)
        self._fields["upc_target_length_entry"] = self._csv_upc_target_length
        upc_row2.addWidget(self._csv_upc_target_length)
        upc_layout.addLayout(upc_row2)

        upc_row3 = QHBoxLayout()
        upc_row3.addWidget(QLabel("UPC Padding Pattern:"))
        self._csv_upc_padding_pattern = QLineEdit()
        self._csv_upc_padding_pattern.setMaximumWidth(120)
        self._fields["upc_padding_pattern_entry"] = self._csv_upc_padding_pattern
        upc_row3.addWidget(self._csv_upc_padding_pattern)
        upc_layout.addLayout(upc_row3)

        layout.addWidget(upc_group)

        self._csv_each_uom_check = QCheckBox("Each UOM")
        self._fields["edi_each_uom_tweak"] = self._csv_each_uom_check
        layout.addWidget(self._csv_each_uom_check)

        self._csv_split_sales_tax_check = QCheckBox("Split Sales Tax 'C' Records")
        self._fields["split_sales_tax_prepaid_var"] = self._csv_split_sales_tax_check
        layout.addWidget(self._csv_split_sales_tax_check)

        self._csv_include_item_numbers_check = QCheckBox("Include Item Numbers")
        self._fields["include_item_numbers"] = self._csv_include_item_numbers_check
        layout.addWidget(self._csv_include_item_numbers_check)

        self._csv_include_item_desc_check = QCheckBox("Include Item Description")
        self._fields["include_item_description"] = self._csv_include_item_desc_check
        layout.addWidget(self._csv_include_item_desc_check)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("CSV Column Sort:"))
        self._csv_column_sort_field = QLineEdit()
        self._fields["simple_csv_column_sorter"] = self._csv_column_sort_field
        sort_row.addWidget(self._csv_column_sort_field)
        layout.addLayout(sort_row)

        self._populate_csv_sub_fields()
        self._convert_sub_layout.addWidget(wrapper)

    def _populate_csv_sub_fields(self):
        cfg = self._folder_config
        self._csv_upc_check.setChecked(str(cfg.get("calculate_upc_check_digit", "False")) == "True")
        self._csv_a_rec_check.setChecked(str(cfg.get("include_a_records", "False")) == "True")
        self._csv_c_rec_check.setChecked(str(cfg.get("include_c_records", "False")) == "True")
        self._csv_headers_check.setChecked(str(cfg.get("include_headers", "False")) == "True")
        self._csv_ampersand_check.setChecked(str(cfg.get("filter_ampersand", "False")) == "True")
        self._csv_pad_arec_check.setChecked(str(cfg.get("pad_a_records", "False")) == "True")
        self._csv_arec_padding_field.setText(str(cfg.get("a_record_padding", "")))
        pad_len = str(cfg.get("a_record_padding_length", 6))
        idx = self._csv_arec_padding_length.findText(pad_len)
        if idx >= 0:
            self._csv_arec_padding_length.setCurrentIndex(idx)
        self._csv_override_upc_check.setChecked(bool(cfg.get("override_upc_bool", False)))
        lvl = str(cfg.get("override_upc_level", 1))
        idx = self._csv_override_upc_level.findText(lvl)
        if idx >= 0:
            self._csv_override_upc_level.setCurrentIndex(idx)
        self._csv_override_upc_cat_filter.setText(str(cfg.get("override_upc_category_filter", "")))
        self._csv_upc_target_length.setText(str(cfg.get("upc_target_length", 11)))
        self._csv_upc_padding_pattern.setText(str(cfg.get("upc_padding_pattern", "           ")))
        self._csv_each_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        self._csv_split_sales_tax_check.setChecked(bool(cfg.get("split_prepaid_sales_tax_crec", False)))
        self._csv_include_item_numbers_check.setChecked(bool(cfg.get("include_item_numbers", False)))
        self._csv_include_item_desc_check.setChecked(bool(cfg.get("include_item_description", False)))
        self._csv_column_sort_field.setText(str(cfg.get("simple_csv_sort_order", "")))

    def _build_scannerware_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)

        self._sw_pad_arec_check = QCheckBox('Pad "A" Records')
        self._fields["pad_arec_check"] = self._sw_pad_arec_check
        arec_layout.addWidget(self._sw_pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        self._sw_arec_padding_field = QLineEdit()
        self._sw_arec_padding_field.setMaximumWidth(100)
        self._fields["a_record_padding_field"] = self._sw_arec_padding_field
        pad_row.addWidget(self._sw_arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        self._sw_arec_padding_length = QComboBox()
        self._sw_arec_padding_length.addItems(["6", "30"])
        self._fields["a_record_padding_length"] = self._sw_arec_padding_length
        pad_row.addWidget(self._sw_arec_padding_length)
        arec_layout.addLayout(pad_row)

        self._sw_append_arec_check = QCheckBox('Append to "A" Records (6 Characters) (Series2K)')
        self._fields["append_arec_check"] = self._sw_append_arec_check
        arec_layout.addWidget(self._sw_append_arec_check)

        append_row = QHBoxLayout()
        append_row.addWidget(QLabel("Append Text:"))
        self._sw_arec_append_field = QLineEdit()
        self._sw_arec_append_field.setMaximumWidth(100)
        self._fields["a_record_append_field"] = self._sw_arec_append_field
        append_row.addWidget(self._sw_arec_append_field)
        arec_layout.addLayout(append_row)

        layout.addWidget(arec_group)

        cfg = self._folder_config
        self._sw_pad_arec_check.setChecked(str(cfg.get("pad_a_records", "False")) == "True")
        self._sw_arec_padding_field.setText(str(cfg.get("a_record_padding", "")))
        pad_len = str(cfg.get("a_record_padding_length", 6))
        idx = self._sw_arec_padding_length.findText(pad_len)
        if idx >= 0:
            self._sw_arec_padding_length.setCurrentIndex(idx)
        self._sw_append_arec_check.setChecked(str(cfg.get("append_a_records", "False")) == "True")
        self._sw_arec_append_field.setText(str(cfg.get("a_record_append_text", "")))

        self._convert_sub_layout.addWidget(wrapper)

    def _build_simplified_csv_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self._simp_headers_check = QCheckBox("Include Headings")
        self._fields["headers_check"] = self._simp_headers_check
        layout.addWidget(self._simp_headers_check)

        self._simp_include_item_numbers_check = QCheckBox("Include Item Numbers")
        self._fields["include_item_numbers"] = self._simp_include_item_numbers_check
        layout.addWidget(self._simp_include_item_numbers_check)

        self._simp_include_item_desc_check = QCheckBox("Include Item Description")
        self._fields["include_item_description"] = self._simp_include_item_desc_check
        layout.addWidget(self._simp_include_item_desc_check)

        self._simp_each_uom_check = QCheckBox("Each UOM")
        self._fields["edi_each_uom_tweak"] = self._simp_each_uom_check
        layout.addWidget(self._simp_each_uom_check)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("CSV Column Sort:"))
        self._simp_column_sort_field = QLineEdit()
        self._fields["simple_csv_column_sorter"] = self._simp_column_sort_field
        sort_row.addWidget(self._simp_column_sort_field)
        layout.addLayout(sort_row)

        cfg = self._folder_config
        self._simp_headers_check.setChecked(str(cfg.get("include_headers", "False")) == "True")
        self._simp_include_item_numbers_check.setChecked(bool(cfg.get("include_item_numbers", False)))
        self._simp_include_item_desc_check.setChecked(bool(cfg.get("include_item_description", False)))
        self._simp_each_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        self._simp_column_sort_field.setText(str(cfg.get("simple_csv_sort_order", "")))

        self._convert_sub_layout.addWidget(wrapper)

    def _build_estore_sub(self, fmt: str):
        wrapper = QWidget()
        layout = QFormLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self._estore_store_number_field = QLineEdit()
        self._fields["estore_store_number_field"] = self._estore_store_number_field
        layout.addRow("Estore Store Number:", self._estore_store_number_field)

        self._estore_vendor_oid_field = QLineEdit()
        self._fields["estore_Vendor_OId_field"] = self._estore_vendor_oid_field
        layout.addRow("Estore Vendor OId:", self._estore_vendor_oid_field)

        self._estore_vendor_name_field = QLineEdit()
        self._fields["estore_vendor_namevendoroid_field"] = self._estore_vendor_name_field
        layout.addRow("Estore Vendor Name OId:", self._estore_vendor_name_field)

        if fmt == "Estore eInvoice Generic":
            self._estore_c_record_oid_field = QLineEdit()
            self._fields["estore_c_record_oid_field"] = self._estore_c_record_oid_field
            layout.addRow("Estore C Record OId:", self._estore_c_record_oid_field)

        cfg = self._folder_config
        self._estore_store_number_field.setText(str(cfg.get("estore_store_number", "")))
        self._estore_vendor_oid_field.setText(str(cfg.get("estore_Vendor_OId", "")))
        self._estore_vendor_name_field.setText(str(cfg.get("estore_vendor_NameVendorOID", "")))
        if fmt == "Estore eInvoice Generic":
            self._estore_c_record_oid_field.setText(str(cfg.get("estore_c_record_OID", "")))

        self._convert_sub_layout.addWidget(wrapper)

    def _build_fintech_sub(self):
        wrapper = QWidget()
        layout = QFormLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        self._fintech_division_field = QLineEdit()
        self._fields["fintech_divisionid_field"] = self._fintech_division_field
        layout.addRow("Fintech Division ID:", self._fintech_division_field)

        self._fintech_division_field.setText(
            str(self._folder_config.get("fintech_division_id", ""))
        )
        self._convert_sub_layout.addWidget(wrapper)

    def _build_basic_options_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("No additional options for this format."))
        self._convert_sub_layout.addWidget(wrapper)

    # ------------------------------------------------------------------
    # Field population
    # ------------------------------------------------------------------
    def _populate_fields(self, config: Dict[str, Any]):
        self._active_checkbox.setChecked(str(config.get("folder_is_active", "False")) == "True")

        self._copy_backend_check.setChecked(bool(config.get("process_backend_copy", False)))
        self._ftp_backend_check.setChecked(bool(config.get("process_backend_ftp", False)))
        self._email_backend_check.setChecked(bool(config.get("process_backend_email", False)))

        if hasattr(self, "_folder_alias_field"):
            self._folder_alias_field.setText(str(config.get("alias", "")))

        self._ftp_server_field.setText(str(config.get("ftp_server", "")))
        self._ftp_port_field.setText(str(config.get("ftp_port", "")))
        self._ftp_folder_field.setText(str(config.get("ftp_folder", "")))
        self._ftp_username_field.setText(str(config.get("ftp_username", "")))
        self._ftp_password_field.setText(str(config.get("ftp_password", "")))

        self._email_recipient_field.setText(str(config.get("email_to", "")))
        self._email_subject_field.setText(str(config.get("email_subject_line", "")))

        self._force_edi_check.setChecked(bool(config.get("force_edi_validation", False)))

        self._split_edi_check.setChecked(bool(config.get("split_edi", False)))
        self._send_invoices_check.setChecked(bool(config.get("split_edi_include_invoices", False)))
        self._send_credits_check.setChecked(bool(config.get("split_edi_include_credits", False)))
        self._prepend_dates_check.setChecked(bool(config.get("prepend_date_files", False)))
        self._rename_file_field.setText(str(config.get("rename_file", "")))
        self._filter_categories_field.setText(str(config.get("split_edi_filter_categories", "ALL")))

        filter_mode = config.get("split_edi_filter_mode", "include")
        idx = self._filter_mode_combo.findText(str(filter_mode))
        if idx >= 0:
            self._filter_mode_combo.setCurrentIndex(idx)

        if config.get("process_edi") == "True":
            self._edi_options_combo.setCurrentText("Convert EDI")
        elif config.get("tweak_edi") is True:
            self._edi_options_combo.setCurrentText("Tweak EDI")
        else:
            self._edi_options_combo.setCurrentText("Do Nothing")

        self._fields["folder_name_value"] = self._make_hidden_line_edit(
            str(config.get("folder_name", ""))
        )

    def _populate_fields_from_config(self, config: Dict[str, Any]):
        self._folder_config = config
        self._populate_fields(config)
        self._update_active_state()
        self._update_backend_states()

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def _update_active_state(self):
        is_active = self._active_checkbox.isChecked()
        if is_active:
            self._active_checkbox.setText("Folder Is Enabled")
            self._active_checkbox.setStyleSheet(
                "QCheckBox { background-color: green; color: white; padding: 4px; }"
            )
        else:
            self._active_checkbox.setText("Folder Is Disabled")
            self._active_checkbox.setStyleSheet(
                "QCheckBox { background-color: red; color: white; padding: 4px; }"
            )

        self._copy_backend_check.setEnabled(is_active)
        self._ftp_backend_check.setEnabled(is_active)

        email_enabled = is_active and self._settings.get("enable_email", False)
        self._email_backend_check.setEnabled(email_enabled)

        if not is_active:
            self._update_backend_states()

    def _update_backend_states(self):
        is_active = self._active_checkbox.isChecked()
        any_backend = (
            self._copy_backend_check.isChecked()
            or self._ftp_backend_check.isChecked()
            or self._email_backend_check.isChecked()
        )

        copy_on = is_active and self._copy_backend_check.isChecked()
        self._copy_dest_btn.setEnabled(copy_on)

        ftp_on = is_active and self._ftp_backend_check.isChecked()
        for w in (
            self._ftp_server_field,
            self._ftp_port_field,
            self._ftp_folder_field,
            self._ftp_username_field,
            self._ftp_password_field,
        ):
            w.setEnabled(ftp_on)

        email_on = (
            is_active
            and self._email_backend_check.isChecked()
            and self._settings.get("enable_email", False)
        )
        self._email_recipient_field.setEnabled(email_on)
        self._email_subject_field.setEnabled(email_on)

        if not self._settings.get("enable_email", False):
            self._email_backend_check.setEnabled(False)

        edi_enabled = is_active and any_backend
        self._split_edi_check.setEnabled(edi_enabled)
        self._send_invoices_check.setEnabled(edi_enabled)
        self._send_credits_check.setEnabled(edi_enabled)
        self._prepend_dates_check.setEnabled(edi_enabled)
        self._rename_file_field.setEnabled(edi_enabled)
        self._edi_options_combo.setEnabled(edi_enabled)
        self._filter_categories_field.setEnabled(edi_enabled)
        self._filter_mode_combo.setEnabled(edi_enabled)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _show_folder_path(self):
        QMessageBox.information(
            self,
            "Folder Path",
            self._folder_config.get("folder_name", ""),
        )

    def _select_copy_directory(self):
        initial = self.copy_to_directory
        if not initial or not os.path.isdir(initial):
            initial = os.getcwd()
        directory = QFileDialog.getExistingDirectory(self, "Select Copy Destination", initial)
        if directory and os.path.isdir(directory):
            self.copy_to_directory = directory

    def _copy_config_from_other(self):
        current_item = self._others_list.currentItem()
        if not current_item:
            return
        selected_alias = current_item.text()

        other_config: Optional[Dict[str, Any]] = None
        if self._alias_provider and self._settings_provider:
            pass

        if other_config is None:
            try:
                import database_import
                other_config = database_import.database_obj_instance.folders_table.find_one(
                    alias=selected_alias
                )
            except (ImportError, AttributeError):
                return

        if other_config:
            self._populate_fields_from_config(other_config)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> bool:
        if not self._active_checkbox.isChecked():
            return True

        extractor = QtFolderDataExtractor(self._fields)
        extracted = extractor.extract_all()
        extracted.copy_to_directory = self.copy_to_directory

        validator = self._create_validator()

        current_alias = self._folder_config.get("alias", "")
        result = validator.validate_extracted_fields(extracted, current_alias)

        if not result.is_valid:
            error_messages = [e.message for e in result.errors]
            self._show_validation_errors(error_messages)
            return False

        return True

    def _create_validator(self) -> FolderSettingsValidator:
        if self._validator is not None:
            return self._validator

        existing_aliases: List[str] = []
        if self._alias_provider:
            existing_aliases = self._alias_provider() or []

        return FolderSettingsValidator(
            ftp_service=self._ftp_service,
            existing_aliases=existing_aliases,
        )

    def _show_validation_errors(self, errors: List[str]):
        error_string = "\n".join(errors)
        QMessageBox.critical(self, "Validation Error", error_string)

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def apply(self):
        extractor = QtFolderDataExtractor(self._fields)
        extracted = extractor.extract_all()
        self._apply_to_folder(extracted, self._folder_config)

        if self._on_apply_success:
            self._on_apply_success(self._folder_config)

    def _apply_to_folder(self, extracted: ExtractedDialogFields, target: Dict[str, Any]):
        target["folder_is_active"] = extracted.folder_is_active

        if self._folder_config.get("folder_name") != "template":
            alias = extracted.alias
            if not alias:
                alias = os.path.basename(self._folder_config.get("folder_name", ""))
            target["alias"] = alias

        target["copy_to_directory"] = self.copy_to_directory
        target["process_backend_copy"] = extracted.process_backend_copy
        target["process_backend_ftp"] = extracted.process_backend_ftp
        target["process_backend_email"] = extracted.process_backend_email

        target["ftp_server"] = extracted.ftp_server
        try:
            target["ftp_port"] = int(extracted.ftp_port)
        except (ValueError, TypeError):
            target["ftp_port"] = 21
        target["ftp_folder"] = extracted.ftp_folder
        target["ftp_username"] = extracted.ftp_username
        target["ftp_password"] = extracted.ftp_password

        target["email_to"] = extracted.email_to
        target["email_subject_line"] = extracted.email_subject_line

        target["process_edi"] = extracted.process_edi
        target["convert_to_format"] = extracted.convert_to_format
        target["calculate_upc_check_digit"] = extracted.calculate_upc_check_digit
        target["include_a_records"] = extracted.include_a_records
        target["include_c_records"] = extracted.include_c_records
        target["include_headers"] = extracted.include_headers
        target["filter_ampersand"] = extracted.filter_ampersand
        target["force_edi_validation"] = extracted.force_edi_validation
        target["tweak_edi"] = extracted.tweak_edi
        target["split_edi"] = extracted.split_edi
        target["split_edi_include_invoices"] = extracted.split_edi_include_invoices
        target["split_edi_include_credits"] = extracted.split_edi_include_credits
        target["prepend_date_files"] = extracted.prepend_date_files
        target["split_edi_filter_categories"] = extracted.split_edi_filter_categories
        target["split_edi_filter_mode"] = extracted.split_edi_filter_mode
        target["rename_file"] = extracted.rename_file
        target["pad_a_records"] = extracted.pad_a_records
        target["a_record_padding"] = extracted.a_record_padding
        try:
            target["a_record_padding_length"] = int(extracted.a_record_padding_length)
        except (ValueError, TypeError):
            target["a_record_padding_length"] = 6
        target["append_a_records"] = extracted.append_a_records
        target["a_record_append_text"] = extracted.a_record_append_text
        target["force_txt_file_ext"] = extracted.force_txt_file_ext
        try:
            target["invoice_date_offset"] = int(extracted.invoice_date_offset)
        except (ValueError, TypeError):
            target["invoice_date_offset"] = 0
        target["invoice_date_custom_format"] = extracted.invoice_date_custom_format
        target["invoice_date_custom_format_string"] = extracted.invoice_date_custom_format_string
        target["retail_uom"] = extracted.retail_uom
        target["override_upc_bool"] = extracted.override_upc_bool
        target["override_upc_level"] = extracted.override_upc_level
        target["override_upc_category_filter"] = extracted.override_upc_category_filter
        try:
            target["upc_target_length"] = int(extracted.upc_target_length)
        except (ValueError, TypeError):
            target["upc_target_length"] = 11
        target["upc_padding_pattern"] = extracted.upc_padding_pattern
        target["include_item_numbers"] = extracted.include_item_numbers
        target["include_item_description"] = extracted.include_item_description
        target["simple_csv_sort_order"] = extracted.simple_csv_sort_order
        target["split_prepaid_sales_tax_crec"] = extracted.split_prepaid_sales_tax_crec
        target["estore_store_number"] = extracted.estore_store_number
        target["estore_Vendor_OId"] = extracted.estore_vendor_oid
        target["estore_vendor_NameVendorOID"] = extracted.estore_vendor_namevendoroid
        target["estore_c_record_OID"] = self._get_estore_c_record_oid()
        target["fintech_division_id"] = extracted.fintech_division_id

    def _get_estore_c_record_oid(self) -> str:
        widget = self._fields.get("estore_c_record_oid_field")
        if widget and isinstance(widget, QLineEdit):
            return widget.text()
        return self._folder_config.get("estore_c_record_OID", "")

    # ------------------------------------------------------------------
    # OK / Cancel
    # ------------------------------------------------------------------
    def _on_ok(self):
        if self.validate():
            self.apply()
            self.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_hidden_check(self, checked: bool) -> QCheckBox:
        cb = QCheckBox()
        cb.setChecked(checked)
        cb.setVisible(False)
        return cb

    def _make_hidden_line_edit(self, text: str) -> QLineEdit:
        le = QLineEdit()
        le.setText(text)
        le.setVisible(False)
        return le

    def get_fields(self) -> Dict[str, QWidget]:
        return dict(self._fields)

    def get_extracted_fields(self) -> ExtractedDialogFields:
        extractor = QtFolderDataExtractor(self._fields)
        extracted = extractor.extract_all()
        extracted.copy_to_directory = self.copy_to_directory
        return extracted
