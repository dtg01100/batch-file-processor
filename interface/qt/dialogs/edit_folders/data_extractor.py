"""Qt Folder Data Extractor.

Extracts folder configuration data from Qt widgets. Reads from a dict of
field name -> QWidget mappings and produces an ExtractedDialogFields dataclass,
mirroring the Tkinter-based FolderDataExtractor but operating on PyQt6 widgets.
"""

from typing import Dict

from PyQt6.QtWidgets import QWidget, QLineEdit, QCheckBox, QComboBox, QSpinBox

from interface.operations.folder_data_extractor import ExtractedDialogFields


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
        )

    def _get_text(self, key: str) -> str:
        widget = self.fields.get(key)
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def _get_bool(self, key: str) -> bool:
        widget = self.fields.get(key)
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        return False

    def _get_check_str(self, key: str) -> str:
        widget = self.fields.get(key)
        if isinstance(widget, QCheckBox):
            return "True" if widget.isChecked() else "False"
        return "False"

    def _get_int(self, key: str, default: int = 0) -> int:
        widget = self.fields.get(key)
        if isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QLineEdit):
            try:
                return int(widget.text().strip())
            except (TypeError, ValueError):
                pass
        return default

    def _get_combo(self, key: str) -> str:
        widget = self.fields.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return ""
