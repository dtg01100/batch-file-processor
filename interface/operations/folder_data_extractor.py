"""Data extraction logic for EditDialog fields.

This module provides classes for extracting folder configuration data
from dialog fields and converting them to structured formats.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import os

import tkinter as tk
from tkinter import ttk


@dataclass
class ExtractedDialogFields:
    """Container for extracted dialog field values."""
    # Identity
    folder_name: str = ""
    alias: str = ""
    folder_is_active: str = "False"

    # Backend toggles
    process_backend_copy: bool = False
    process_backend_ftp: bool = False
    process_backend_email: bool = False

    # FTP fields
    ftp_server: str = ""
    ftp_port: int = 21
    ftp_folder: str = ""
    ftp_username: str = ""
    ftp_password: str = ""

    # Email fields
    email_to: str = ""
    email_subject_line: str = ""

    # EDI fields
    process_edi: str = "False"
    convert_to_format: str = ""
    tweak_edi: bool = False
    split_edi: bool = False
    split_edi_include_invoices: bool = False
    split_edi_include_credits: bool = False
    prepend_date_files: bool = False
    rename_file: str = ""
    split_edi_filter_categories: str = "ALL"
    split_edi_filter_mode: str = "include"

    # EDI options
    calculate_upc_check_digit: str = "True"
    include_a_records: str = "True"
    include_c_records: str = "False"
    include_headers: str = "True"
    filter_ampersand: str = "False"
    force_edi_validation: bool = False

    # A-record
    pad_a_records: str = "False"
    a_record_padding: str = ""
    a_record_padding_length: int = 6
    append_a_records: str = "False"
    a_record_append_text: str = ""
    force_txt_file_ext: str = "False"

    # Invoice date
    invoice_date_offset: int = 0
    invoice_date_custom_format: bool = False
    invoice_date_custom_format_string: str = ""
    retail_uom: bool = False

    # UPC override
    override_upc_bool: bool = False
    override_upc_level: int = 1
    override_upc_category_filter: str = ""
    upc_target_length: int = 11
    upc_padding_pattern: str = "           "

    # Item fields
    include_item_numbers: bool = False
    include_item_description: bool = False

    # CSV sort
    simple_csv_sort_order: str = ""

    # Tax
    split_prepaid_sales_tax_crec: bool = False

    # Backend-specific
    estore_store_number: str = ""
    estore_vendor_oid: str = ""
    estore_vendor_namevendoroid: str = ""
    fintech_division_id: str = ""

    # Copy destination
    copy_to_directory: str = ""


class FolderDataExtractor:
    """
    Extracts folder configuration data from dialog fields.

    This class centralizes the logic for extracting values from
    tkinter widgets and converting them to a consistent format.
    """

    def __init__(self, dialog_fields: Dict[str, Any]):
        """
        Initialize extractor with dialog field references.

        Args:
            dialog_fields: Dictionary mapping field names to tkinter widget references
        """
        self.fields = dialog_fields

    def extract_all(self) -> ExtractedDialogFields:
        """Extract all field values from the dialog."""
        return ExtractedDialogFields(
            # Identity
            folder_name=self._get_text("foldersnameinput", "folder_name"),
            alias=self._get_text("folder_alias_field"),
            folder_is_active=self._get_value("active_checkbutton"),

            # Backend toggles
            process_backend_copy=self._get_bool("process_backend_copy_check"),
            process_backend_ftp=self._get_bool("process_backend_ftp_check"),
            process_backend_email=self._get_bool("process_backend_email_check"),

            # FTP
            ftp_server=self._get_text("ftp_server_field"),
            ftp_port=self._get_int("ftp_port_field"),
            ftp_folder=self._get_text("ftp_folder_field"),
            ftp_username=self._get_text("ftp_username_field"),
            ftp_password=self._get_text("ftp_password_field"),

            # Email
            email_to=self._get_text("email_recepient_field"),
            email_subject_line=self._get_text("email_sender_subject_field"),

            # EDI
            process_edi=self._get_value("process_edi"),
            convert_to_format=self._get_value("convert_formats_var"),
            tweak_edi=self._get_bool("tweak_edi"),
            split_edi=self._get_bool("split_edi"),
            split_edi_include_invoices=self._get_bool("split_edi_send_invoices"),
            split_edi_include_credits=self._get_bool("split_edi_send_credits"),
            prepend_date_files=self._get_bool("prepend_file_dates"),
            rename_file=self._get_text("rename_file_field"),
            split_edi_filter_categories=self._get_text("split_edi_filter_categories_entry"),
            split_edi_filter_mode=self._get_value("split_edi_filter_mode"),

            # EDI options
            calculate_upc_check_digit=self._get_value("upc_var_check"),
            include_a_records=self._get_value("a_rec_var_check"),
            include_c_records=self._get_value("c_rec_var_check"),
            include_headers=self._get_value("headers_check"),
            filter_ampersand=self._get_value("ampersand_check"),
            force_edi_validation=self._get_bool("force_edi_check_var"),

            # A-record
            pad_a_records=self._get_value("pad_arec_check"),
            a_record_padding=self._get_text("a_record_padding_field"),
            a_record_padding_length=self._get_int("a_record_padding_length"),
            append_a_records=self._get_value("append_arec_check"),
            a_record_append_text=self._get_text("a_record_append_field"),
            force_txt_file_ext=self._get_value("force_txt_file_ext_check"),

            # Invoice date
            invoice_date_offset=self._get_int("invoice_date_offset"),
            invoice_date_custom_format=self._get_bool("invoice_date_custom_format"),
            invoice_date_custom_format_string=self._get_text("invoice_date_custom_format_field"),
            retail_uom=self._get_bool("edi_each_uom_tweak"),

            # UPC override
            override_upc_bool=self._get_bool("override_upc_bool"),
            override_upc_level=self._get_int("override_upc_level"),
            override_upc_category_filter=self._get_text("override_upc_category_filter_entry"),
            upc_target_length=self._get_int("upc_target_length_entry"),
            upc_padding_pattern=self._get_text("upc_padding_pattern_entry"),

            # Item fields
            include_item_numbers=self._get_bool("include_item_numbers"),
            include_item_description=self._get_bool("include_item_description"),

            # CSV sort
            simple_csv_sort_order=self._get_value("simple_csv_column_sorter"),

            # Tax
            split_prepaid_sales_tax_crec=self._get_bool("split_sales_tax_prepaid_var"),

            # Backend-specific
            estore_store_number=self._get_text("estore_store_number_field"),
            estore_vendor_oid=self._get_text("estore_Vendor_OId_field"),
            estore_vendor_namevendoroid=self._get_text("estore_vendor_namevendoroid_field"),
            fintech_division_id=self._get_text("fintech_divisionid_field"),

            # Copy destination
            copy_to_directory=""
        )

    def _get_alias(self, extracted: ExtractedDialogFields) -> str:
        """Get alias value, using folder name basename if empty."""
        if extracted.alias:
            return str(extracted.alias)
        if extracted.folder_name and extracted.folder_name != "template":
            return os.path.basename(extracted.folder_name)
        return ""

    def _get_text(self, field_name: str, key: Optional[str] = None) -> str:
        """Get text value from Entry widget."""
        widget = self.fields.get(field_name)
        if widget is None:
            return ""
        if key:
            return str(widget.get(key, ""))
        return str(widget.get())

    def _get_int(self, field_name: str) -> int:
        """Get integer value from widget."""
        widget = self.fields.get(field_name)
        if widget is None:
            return 0
        try:
            return int(widget.get())
        except (ValueError, tk.TclError):
            return 0

    def _get_bool(self, field_name: str) -> bool:
        """Get boolean value from widget."""
        widget = self.fields.get(field_name)
        if widget is None:
            return False
        return bool(widget.get())

    def _get_value(self, field_name: str) -> str:
        """Get value from StringVar/BooleanVar."""
        widget = self.fields.get(field_name)
        if widget is None:
            return ""
        return str(widget.get())
