"""Refactored EditFoldersDialog with dependency injection for testability.

This module provides the refactored EditFoldersDialog class with
dependency injection for comprehensive testability.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List, Callable

import sys
import os

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
interface_dir = os.path.dirname(current_dir)
sys.path.insert(0, interface_dir)

from dialog import Dialog

from interface.models.folder_configuration import FolderConfiguration
from interface.validation.folder_settings_validator import (
    FolderSettingsValidator,
    ValidationResult,
)
from interface.operations.folder_data_extractor import (
    FolderDataExtractor,
    ExtractedDialogFields,
)
from interface.services.ftp_service import (
    FTPService,
    FTPServiceProtocol,
    MockFTPService,
)


class EditFoldersDialog(Dialog):
    """
    Refactored dialog for editing folder settings.

    This dialog accepts injectable dependencies for:
    - FTPService: For connection testing (mockable for tests)
    - FolderSettingsValidator: For validation logic
    - FolderDataExtractor: For field extraction

    This design enables comprehensive unit testing without:
    - Real network connections
    - Database access
    - Global state dependencies
    """

    # Default dependencies (can be overridden for testing)
    DEFAULT_FTP_SERVICE: FTPServiceProtocol = None
    DEFAULT_VALIDATOR_CLASS = FolderSettingsValidator
    DEFAULT_EXTRACTOR_CLASS = FolderDataExtractor

    def __init__(
        self,
        parent,
        foldersnameinput: Dict[str, Any],
        title: Optional[str] = None,
        ftp_service: Optional[FTPServiceProtocol] = None,
        validator: Optional[FolderSettingsValidator] = None,
        extractor: Optional[FolderDataExtractor] = None,
        settings_provider: Optional[Callable] = None,
        alias_provider: Optional[Callable] = None,
        on_apply_success: Optional[Callable] = None,
    ):
        """
        Initialize EditFoldersDialog with dependencies.

        Args:
            parent: Parent window
            foldersnameinput: Folder configuration dictionary
            title: Dialog title
            ftp_service: Optional FTP service for connection testing
            validator: Optional custom validator instance
            extractor: Optional custom extractor instance
            settings_provider: Callable to get settings (defaults to database)
            alias_provider: Callable to get existing aliases (defaults to database)
            on_apply_success: Callback after successful apply
        """
        # Store dependencies
        self._ftp_service = ftp_service or self.DEFAULT_FTP_SERVICE
        self._validator = validator
        self._validator_class = self.DEFAULT_VALIDATOR_CLASS
        self._extractor_class = self.DEFAULT_EXTRACTOR_CLASS
        self._settings_provider = settings_provider
        self._alias_provider = alias_provider
        self._on_apply_success = on_apply_success

        # Store for use after base class initialization
        self._foldersnameinput = foldersnameinput

        # Initialize base dialog
        super().__init__(parent, foldersnameinput, title)

    def _create_validator(self) -> FolderSettingsValidator:
        """Create validator with current dependencies."""
        if self._validator is not None:
            return self._validator

        # Get existing aliases if provider available
        existing_aliases = []
        if self._alias_provider:
            existing_aliases = self._alias_provider()

        return self._validator_class(
            ftp_service=self._ftp_service,
            existing_aliases=existing_aliases
        )

    def _create_extractor(self, field_refs: Dict[str, Any]) -> FolderDataExtractor:
        """Create extractor with dialog field references."""
        return self._extractor_class(field_refs)

    def body(self, master) -> tk.Widget:
        """
        Create dialog body with all widgets.

        This replicates the exact widget layout from the original
        EditDialog.body() in main_interface.py.
        """
        # Store widget references for extractor
        self._field_refs: Dict[str, Any] = {}

        # Initialize settings
        settings = None
        if self._settings_provider:
            settings = self._settings_provider()
        else:
            try:
                import database_import
                settings = database_import.database_obj_instance.settings.find_one(id=1)
            except (ImportError, AttributeError):
                settings = {}

        self.settings = settings
        self.resizable(width=tk.FALSE, height=tk.FALSE)

        # Store copy_to_directory as instance variable (not global)
        self.copy_to_directory = self.foldersnameinput.get("copy_to_directory", "")

        self.convert_formats_var = tk.StringVar(master)
        self.title("Folder Settings")

        # --- Frames ---
        self.bodyframe = ttk.Frame(master)
        self.othersframe = ttk.Frame(self.bodyframe)
        self.folderframe = ttk.Frame(self.bodyframe)
        self.prefsframe = ttk.Frame(self.bodyframe)
        self.ediframe = ttk.Frame(self.bodyframe)
        self.convert_options_frame = ttk.Frame(self.ediframe)

        # --- Separators ---
        self.separatorv0 = ttk.Separator(self.bodyframe, orient=tk.VERTICAL)
        self.separatorv1 = ttk.Separator(self.bodyframe, orient=tk.VERTICAL)
        self.separatorv2 = ttk.Separator(self.bodyframe, orient=tk.VERTICAL)

        # --- Variables ---
        self.backendvariable = tk.StringVar(master)
        self.active_checkbutton = tk.StringVar(master)
        self.split_edi = tk.BooleanVar(master)
        self.split_edi_send_credits = tk.BooleanVar(master)
        self.split_edi_send_invoices = tk.BooleanVar(master)
        self.split_edi_filter_categories = tk.StringVar(master)
        self.split_edi_filter_mode = tk.StringVar(master)
        self.prepend_file_dates = tk.BooleanVar(master)
        self.ediconvert_options = tk.StringVar(master)
        self.process_edi = tk.StringVar(master)
        self.upc_var_check = tk.StringVar(master)
        self.a_rec_var_check = tk.StringVar(master)
        self.c_rec_var_check = tk.StringVar(master)
        self.headers_check = tk.StringVar(master)
        self.ampersand_check = tk.StringVar(master)
        self.tweak_edi = tk.BooleanVar(master)
        self.pad_arec_check = tk.StringVar(master)
        self.a_record_padding_length = tk.IntVar(master)
        self.append_arec_check = tk.StringVar(master)
        self.force_txt_file_ext_check = tk.StringVar(master)
        self.process_backend_copy_check = tk.BooleanVar(master)
        self.process_backend_ftp_check = tk.BooleanVar(master)
        self.process_backend_email_check = tk.BooleanVar(master)
        self.force_edi_check_var = tk.BooleanVar(master)
        self.header_frame_frame = ttk.Frame(master)
        self.invoice_date_offset = tk.IntVar(master)
        self.invoice_date_custom_format_string = tk.StringVar(master)
        self.invoice_date_custom_format = tk.BooleanVar(master)
        self.edi_each_uom_tweak = tk.BooleanVar(master)
        self.include_item_numbers = tk.BooleanVar(master)
        self.include_item_description = tk.BooleanVar(master)
        self.split_sales_tax_prepaid_var = tk.BooleanVar(master)
        self.override_upc_bool = tk.BooleanVar(master)
        self.override_upc_level = tk.IntVar(master)
        self.override_upc_category_filter = tk.StringVar(master)
        self.upc_target_length = tk.IntVar(master)
        self.upc_padding_pattern = tk.StringVar(master)

        # --- Others listbox ---
        self.otherslistboxframe = ttk.Frame(master=self.othersframe)
        self.otherslistbox = tk.Listbox(master=self.otherslistboxframe)
        self.otherslistboxscrollbar = ttk.Scrollbar(
            master=self.otherslistboxframe, orient=tk.VERTICAL
        )
        self.otherslistboxscrollbar.config(command=self.otherslistbox.yview)
        self.otherslistbox.config(yscrollcommand=self.otherslistboxscrollbar.set)
        self.copyconfigbutton = ttk.Button(
            master=self.othersframe, text="Copy Config"
        )

        # --- Folder frame labels ---
        ttk.Label(self.folderframe, text="Backends:").grid(
            row=2, sticky=tk.W
        )

        # --- Prefs frame labels and separators ---
        ttk.Label(self.prefsframe, text="Copy Backend Settings:").grid(
            row=3, columnspan=2, pady=3
        )
        ttk.Separator(self.prefsframe, orient=tk.HORIZONTAL).grid(
            row=5, columnspan=2, sticky=tk.E + tk.W, pady=2
        )
        ttk.Label(self.prefsframe, text="Ftp Backend Settings:").grid(
            row=6, columnspan=2, pady=3
        )
        ttk.Label(self.prefsframe, text="FTP Server:").grid(
            row=7, sticky=tk.E
        )
        ttk.Label(self.prefsframe, text="FTP Port:").grid(
            row=8, sticky=tk.E
        )
        ttk.Label(self.prefsframe, text="FTP Folder:").grid(
            row=9, sticky=tk.E
        )
        ttk.Label(self.prefsframe, text="FTP Username:").grid(
            row=10, sticky=tk.E
        )
        ttk.Label(self.prefsframe, text="FTP Password:").grid(
            row=11, sticky=tk.E
        )
        ttk.Separator(self.prefsframe, orient=tk.HORIZONTAL).grid(
            row=12, columnspan=2, sticky=tk.E + tk.W, pady=2
        )
        ttk.Label(self.prefsframe, text="Email Backend Settings:").grid(
            row=13, columnspan=2, pady=3
        )
        ttk.Label(self.prefsframe, text="Recipient Address:").grid(
            row=14, sticky=tk.E
        )
        ttk.Label(self.prefsframe, text="Email Subject:").grid(
            row=18, sticky=tk.E
        )

        # --- EDI frame labels ---
        ttk.Label(self.ediframe, text="EDI Convert Settings:").grid(
            row=0, column=0, columnspan=2, pady=3
        )
        ttk.Separator(self.ediframe, orient=tk.HORIZONTAL).grid(
            row=6, columnspan=2, sticky=tk.E + tk.W, pady=1
        )
        self.convert_options_frame.grid(
            column=0, row=7, columnspan=2, sticky=tk.W
        )

        # --- Convert to selector ---
        self.convert_to_selector_frame = ttk.Frame(
            self.convert_options_frame
        )
        self.convert_to_selector_label = ttk.Label(
            self.convert_to_selector_frame, text="Convert To: "
        )

        # --- make_convert_to_options callback ---
        def make_convert_to_options(_=None):
            for frameentry in [
                self.upc_variable_process_checkbutton,
                self.a_record_checkbutton,
                self.c_record_checkbutton,
                self.headers_checkbutton,
                self.ampersand_checkbutton,
                self.pad_a_records_checkbutton,
                self.a_record_padding_frame,
                self.a_record_padding_field,
                self.pad_a_records_length_optionmenu,
                self.append_a_records_checkbutton,
                self.a_record_append_field,
                self.override_upc_checkbutton,
                self.override_upc_level_optionmenu,
                self.override_upc_category_filter_entry,
                self.upc_target_length_label,
                self.upc_target_length_entry,
                self.upc_padding_pattern_label,
                self.upc_padding_pattern_entry,
                self.each_uom_edi_tweak_checkbutton,
                self.include_item_numbers_checkbutton,
                self.include_item_description_checkbutton,
                self.simple_csv_column_sorter.containerframe,
                self.a_record_padding_field,
                self.estore_store_number_label,
                self.estore_store_number_field,
                self.estore_Vendor_OId_label,
                self.estore_Vendor_OId_field,
                self.estore_vendor_namevendoroid_label,
                self.estore_vendor_namevendoroid_field,
                self.fintech_divisionid_field,
                self.fintech_divisionid_label,
            ]:
                frameentry.grid_forget()
            if self.convert_formats_var.get() == "csv":
                self.upc_variable_process_checkbutton.grid(
                    row=2, column=0, sticky=tk.W, padx=3
                )
                self.a_record_checkbutton.grid(
                    row=4, column=0, sticky=tk.W, padx=3
                )
                self.c_record_checkbutton.grid(
                    row=5, column=0, sticky=tk.W, padx=3
                )
                self.headers_checkbutton.grid(
                    row=6, column=0, sticky=tk.W, padx=3
                )
                self.ampersand_checkbutton.grid(
                    row=7, column=0, sticky=tk.W, padx=3
                )
                self.pad_a_records_checkbutton.grid(
                    row=0, column=0, sticky=tk.W
                )
                self.a_record_padding_frame.grid(
                    row=9, column=0, columnspan=2, sticky=tk.W, padx=3
                )
                self.a_record_padding_field.grid(row=9, column=1, sticky=tk.W)
                self.override_upc_checkbutton.grid(
                    row=10, column=0, sticky=tk.W, padx=3
                )
                self.override_upc_level_optionmenu.grid(
                    row=10, column=1, sticky=tk.W
                )
                self.override_upc_category_filter_entry.grid(
                    row=10, column=2, sticky=tk.W
                )
                self.upc_target_length_label.grid(
                    row=11, column=0, sticky=tk.W, padx=3
                )
                self.upc_target_length_entry.grid(
                    row=11, column=1, sticky=tk.W
                )
                self.upc_padding_pattern_label.grid(
                    row=12, column=0, sticky=tk.W, padx=3
                )
                self.upc_padding_pattern_entry.grid(
                    row=12, column=1, sticky=tk.W
                )
                self.each_uom_edi_tweak_checkbutton.grid(
                    row=13, column=0, sticky=tk.W, padx=3
                )
            if self.convert_formats_var.get() == "ScannerWare":
                self.pad_a_records_checkbutton.grid(
                    row=0, column=0, sticky=tk.W
                )
                self.a_record_padding_field.grid(row=2, column=2)
                self.a_record_padding_frame.grid(
                    row=2, column=0, columnspan=2, sticky=tk.W, padx=3
                )
                self.append_a_records_checkbutton.grid(
                    row=3, column=0, sticky=tk.W, padx=3
                )
                self.a_record_append_field.grid(row=3, column=2)
            if self.convert_formats_var.get() == "simplified_csv":
                self.headers_checkbutton.grid(
                    row=2, column=0, sticky=tk.W, padx=3
                )
                self.include_item_numbers_checkbutton.grid(
                    row=3, column=0, sticky=tk.W, padx=3
                )
                self.include_item_description_checkbutton.grid(
                    row=4, column=0, sticky=tk.W, padx=3
                )
                self.each_uom_edi_tweak_checkbutton.grid(
                    row=5, column=0, sticky=tk.W, padx=3
                )
                self.simple_csv_column_sorter.containerframe.grid(
                    row=6, column=0, sticky=tk.W, padx=3, columnspan=2
                )
            if self.convert_formats_var.get() == "Estore eInvoice":
                self.estore_store_number_label.grid(
                    row=2, column=0, sticky=tk.W, padx=3
                )
                self.estore_store_number_field.grid(
                    row=2, column=1, sticky=tk.E, padx=3
                )
                self.estore_Vendor_OId_label.grid(
                    row=3, column=0, sticky=tk.W, padx=3
                )
                self.estore_Vendor_OId_field.grid(
                    row=3, column=1, sticky=tk.E, padx=3
                )
                self.estore_vendor_namevendoroid_label.grid(
                    row=4, column=0, sticky=tk.W, padx=3
                )
                self.estore_vendor_namevendoroid_field.grid(
                    row=4, column=1, sticky=tk.E, padx=3
                )
            if self.convert_formats_var.get() == "Estore eInvoice Generic":
                self.estore_store_number_label.grid(
                    row=2, column=0, sticky=tk.W, padx=3
                )
                self.estore_store_number_field.grid(
                    row=2, column=1, sticky=tk.E, padx=3
                )
                self.estore_Vendor_OId_label.grid(
                    row=3, column=0, sticky=tk.W, padx=3
                )
                self.estore_Vendor_OId_field.grid(
                    row=3, column=1, sticky=tk.E, padx=3
                )
                self.estore_vendor_namevendoroid_label.grid(
                    row=4, column=0, sticky=tk.W, padx=3
                )
                self.estore_vendor_namevendoroid_field.grid(
                    row=4, column=1, sticky=tk.E, padx=3
                )
                self.estore_c_record_oid_label.grid(
                    row=5, column=0, sticky=tk.W, padx=3
                )
                self.estore_c_record_oid_field.grid(
                    row=5, column=1, sticky=tk.E, padx=3
                )
            if self.convert_formats_var.get() == "fintech":
                self.fintech_divisionid_label.grid(
                    row=2, column=0, sticky=tk.W, padx=3
                )
                self.fintech_divisionid_field.grid(
                    row=2, column=1, sticky=tk.E, padx=3
                )

        # --- Convert to selector menu ---
        self.convert_to_selector_menu = ttk.OptionMenu(
            self.convert_to_selector_frame,
            self.convert_formats_var,
            self.foldersnameinput.get("convert_to_format", "csv"),
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
            command=make_convert_to_options,
        )

        # --- show_folder_path callback ---
        def show_folder_path():
            from tkinter.messagebox import showinfo
            showinfo(
                parent=master,
                title="Folder Path",
                message=self.foldersnameinput.get("folder_name", ""),
            )

        # --- select_copy_to_directory callback ---
        def select_copy_to_directory():
            try:
                if self.copy_to_directory and os.path.exists(self.copy_to_directory):
                    initial_directory = self.copy_to_directory
                else:
                    initial_directory = os.getcwd()
            except Exception:
                initial_directory = os.getcwd()
            from tkinter.filedialog import askdirectory
            proposed_copy_to_directory = str(
                askdirectory(parent=self.prefsframe, initialdir=initial_directory)
            )
            if os.path.isdir(proposed_copy_to_directory):
                self.copy_to_directory = proposed_copy_to_directory

        # --- set_send_options_fields_state callback ---
        def set_send_options_fields_state():
            if not self.settings.get("enable_email", False):
                self.email_backend_checkbutton.configure(state=tk.DISABLED)
            category_filter_state = tk.NORMAL
            if (
                self.process_backend_copy_check.get() is False
                and self.process_backend_ftp_check.get() is False
                and self.process_backend_email_check.get() is False
            ):
                category_filter_state = tk.DISABLED
                self.split_edi_checkbutton.configure(state=tk.DISABLED)
                self.split_edi_send_invoices_checkbutton.configure(
                    state=tk.DISABLED
                )
                self.split_edi_send_credits_checkbutton.configure(
                    state=tk.DISABLED
                )
                self.prepend_file_dates_checkbutton.configure(
                    state=tk.DISABLED
                )
                self.rename_file_field.configure(state=tk.DISABLED)
                self.edi_options_menu.configure(state=tk.DISABLED)
                for child in self.convert_options_frame.winfo_children():
                    try:
                        child.configure(state=tk.DISABLED)
                    except tk.TclError:
                        pass
                for child in self.convert_to_selector_frame.winfo_children():
                    try:
                        child.configure(state=tk.DISABLED)
                    except tk.TclError:
                        pass
            else:
                self.split_edi_checkbutton.configure(state=tk.NORMAL)
                self.split_edi_send_invoices_checkbutton.configure(
                    state=tk.NORMAL
                )
                self.split_edi_send_credits_checkbutton.configure(
                    state=tk.NORMAL
                )
                self.prepend_file_dates_checkbutton.configure(state=tk.NORMAL)
                self.rename_file_field.configure(state=tk.NORMAL)
                self.edi_options_menu.configure(state=tk.NORMAL)
                for child in self.convert_options_frame.winfo_children():
                    try:
                        child.configure(state=tk.NORMAL)
                    except tk.TclError:
                        pass
                for child in self.convert_to_selector_frame.winfo_children():
                    try:
                        child.configure(state=tk.NORMAL)
                    except tk.TclError:
                        pass
            for child in self.category_filter_frame.winfo_children():
                try:
                    child.configure(state=category_filter_state)
                except tk.TclError:
                    pass
            if self.process_backend_copy_check.get() is False:
                copy_state = tk.DISABLED
            else:
                copy_state = tk.NORMAL
            if (
                self.process_backend_email_check.get() is False
                or self.settings.get("enable_email", False) is False
            ):
                email_state = tk.DISABLED
            else:
                email_state = tk.NORMAL
            if self.process_backend_ftp_check.get() is False:
                ftp_state = tk.DISABLED
            else:
                ftp_state = tk.NORMAL
            self.copy_backend_folder_selection_button.configure(state=copy_state)
            self.email_recepient_field.configure(state=email_state)
            self.email_sender_subject_field.configure(state=email_state)
            self.ftp_server_field.configure(state=ftp_state)
            self.ftp_port_field.configure(state=ftp_state)
            self.ftp_folder_field.configure(state=ftp_state)
            self.ftp_username_field.configure(state=ftp_state)
            self.ftp_password_field.configure(state=ftp_state)

        # --- set_header_state callback ---
        def set_header_state():
            if self.active_checkbutton.get() == "False":
                self.active_checkbutton_object.configure(
                    text="Folder Is Disabled", activebackground="green"
                )
                self.copy_backend_checkbutton.configure(state=tk.DISABLED)
                self.ftp_backend_checkbutton.configure(state=tk.DISABLED)
                self.email_backend_checkbutton.configure(state=tk.DISABLED)
            else:
                self.active_checkbutton_object.configure(
                    text="Folder Is Enabled", activebackground="red"
                )
                self.copy_backend_checkbutton.configure(state=tk.NORMAL)
                self.ftp_backend_checkbutton.configure(state=tk.NORMAL)
                if self.settings.get("enable_email", False):
                    self.email_backend_checkbutton.configure(state=tk.NORMAL)

        # --- Active checkbutton ---
        self.active_checkbutton_object = tk.Checkbutton(
            self.header_frame_frame,
            text="Active",
            variable=self.active_checkbutton,
            onvalue="True",
            offvalue="False",
            command=set_header_state,
            indicatoron=tk.FALSE,
            selectcolor="green",
            background="red",
        )

        # --- Backend checkbuttons ---
        self.copy_backend_checkbutton = ttk.Checkbutton(
            self.folderframe,
            text="Copy Backend",
            variable=self.process_backend_copy_check,
            onvalue=True,
            offvalue=False,
            command=set_send_options_fields_state,
        )
        self.ftp_backend_checkbutton = ttk.Checkbutton(
            self.folderframe,
            text="FTP Backend",
            variable=self.process_backend_ftp_check,
            onvalue=True,
            offvalue=False,
            command=set_send_options_fields_state,
        )
        self.email_backend_checkbutton = ttk.Checkbutton(
            self.folderframe,
            text="Email Backend",
            variable=self.process_backend_email_check,
            onvalue=True,
            offvalue=False,
            command=set_send_options_fields_state,
        )

        # --- Folder alias frame ---
        if self.foldersnameinput.get("folder_name") != "template":
            self.folder_alias_frame = ttk.Frame(self.folderframe)
            ttk.Label(self.folder_alias_frame, text="Folder Alias:").grid(
                row=0, sticky=tk.W
            )
            self.folder_alias_field = ttk.Entry(
                self.folder_alias_frame, width=30
            )
            try:
                import tk_extra_widgets
                rclick_folder_alias_field = tk_extra_widgets.RightClickMenu(
                    self.folder_alias_field
                )
                self.folder_alias_field.bind("<3>", rclick_folder_alias_field)
            except ImportError:
                pass
            self.folder_alias_field.grid(row=0, column=1)
            ttk.Button(
                master=self.folder_alias_frame,
                text="Show Folder Path",
                command=show_folder_path,
            ).grid(row=1, columnspan=2, sticky=tk.W, pady=5)

        # --- Copy backend button ---
        self.copy_backend_folder_selection_button = ttk.Button(
            self.prefsframe,
            text="Select Copy Backend Destination Folder...",
            command=lambda: select_copy_to_directory(),
        )

        # --- FTP fields ---
        self.ftp_server_field = ttk.Entry(self.prefsframe, width=30)
        try:
            import tk_extra_widgets
            rclick_ftp_server_field = tk_extra_widgets.RightClickMenu(
                self.ftp_server_field
            )
            self.ftp_server_field.bind("<3>", rclick_ftp_server_field)
        except ImportError:
            pass
        self.ftp_port_field = ttk.Entry(self.prefsframe, width=30)
        try:
            import tk_extra_widgets
            rclick_ftp_port_field = tk_extra_widgets.RightClickMenu(self.ftp_port_field)
            self.ftp_port_field.bind("<3>", rclick_ftp_port_field)
        except ImportError:
            pass
        self.ftp_folder_field = ttk.Entry(self.prefsframe, width=30)
        try:
            import tk_extra_widgets
            rclick_ftp_folder_field = tk_extra_widgets.RightClickMenu(
                self.ftp_folder_field
            )
            self.ftp_folder_field.bind("<3>", rclick_ftp_folder_field)
        except ImportError:
            pass
        self.ftp_username_field = ttk.Entry(self.prefsframe, width=30)
        try:
            import tk_extra_widgets
            rclick_ftp_username_field = tk_extra_widgets.RightClickMenu(
                self.ftp_username_field
            )
            self.ftp_username_field.bind("<3>", rclick_ftp_username_field)
        except ImportError:
            pass
        self.ftp_password_field = ttk.Entry(
            self.prefsframe, show="*", width=30
        )

        # --- Email fields ---
        self.email_recepient_field = ttk.Entry(self.prefsframe, width=30)
        try:
            import tk_extra_widgets
            rclick_email_recepient_field = tk_extra_widgets.RightClickMenu(
                self.email_recepient_field
            )
            self.email_recepient_field.bind("<3>", rclick_email_recepient_field)
        except ImportError:
            pass
        self.email_sender_subject_field = ttk.Entry(
            self.prefsframe, width=30
        )
        try:
            import tk_extra_widgets
            rclick_email_sender_subject_field = tk_extra_widgets.RightClickMenu(
                self.email_sender_subject_field
            )
            self.email_sender_subject_field.bind(
                "<3>", rclick_email_sender_subject_field
            )
        except ImportError:
            pass

        # --- Invoice date custom format field ---
        self.invoice_date_custom_format_field = ttk.Entry(
            self.convert_options_frame, width=10
        )
        try:
            import tk_extra_widgets
            rclick_invoice_date_custom_format_field = tk_extra_widgets.RightClickMenu(
                self.invoice_date_custom_format_field
            )
            self.invoice_date_custom_format_field.bind(
                "<3>", rclick_invoice_date_custom_format_field
            )
        except ImportError:
            pass

        # --- Force EDI check ---
        self.force_edi_check_checkbutton = ttk.Checkbutton(
            self.ediframe,
            variable=self.force_edi_check_var,
            text="Force EDI Validation",
            onvalue=True,
            offvalue=False,
        )

        # --- Split EDI frame and checkbuttons ---
        self.split_edi_frame = ttk.Frame(self.ediframe)

        self.split_edi_checkbutton = ttk.Checkbutton(
            self.split_edi_frame,
            variable=self.split_edi,
            text="Split EDI",
            onvalue=True,
            offvalue=False,
        )
        self.split_edi_send_invoices_checkbutton = ttk.Checkbutton(
            self.split_edi_frame,
            variable=self.split_edi_send_invoices,
            text="Split EDI Send Invoices",
            onvalue=True,
            offvalue=False,
        )
        self.split_edi_send_credits_checkbutton = ttk.Checkbutton(
            self.split_edi_frame,
            variable=self.split_edi_send_credits,
            text="Split EDI Send Credits",
            onvalue=True,
            offvalue=False,
        )
        self.prepend_file_dates_checkbutton = ttk.Checkbutton(
            self.split_edi_frame,
            variable=self.prepend_file_dates,
            text="Prepend dates",
            onvalue=True,
            offvalue=False,
        )

        # --- Category filter frame ---
        self.category_filter_frame = ttk.Frame(self.ediframe)
        self.split_edi_filter_categories_label = ttk.Label(
            self.category_filter_frame, text="Filter Categories:"
        )
        self.split_edi_filter_categories_entry = ttk.Entry(
            self.category_filter_frame, width=15
        )
        try:
            import tk_extra_widgets
            self.split_edi_filter_categories_tooltip = tk_extra_widgets.CreateToolTip(
                self.split_edi_filter_categories_entry,
                "Enter 'ALL' or a comma separated list of category numbers (e.g., 1,5,12)",
            )
        except ImportError:
            pass
        self.split_edi_filter_mode_label = ttk.Label(
            self.category_filter_frame, text="Mode:"
        )
        self.split_edi_filter_mode_optionmenu = ttk.OptionMenu(
            self.category_filter_frame,
            self.split_edi_filter_mode,
            "include",
            "include",
            "exclude",
        )

        # --- Convert options checkbuttons ---
        self.process_edi_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.process_edi,
            text="Process EDI",
            onvalue="True",
            offvalue="False",
        )
        self.upc_variable_process_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.upc_var_check,
            text="Calculate UPC Check Digit",
            onvalue="True",
            offvalue="False",
        )
        self.a_record_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.a_rec_var_check,
            text="Include " + "A " + "Records",
            onvalue="True",
            offvalue="False",
        )
        self.c_record_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.c_rec_var_check,
            text="Include " + "C " + "Records",
            onvalue="True",
            offvalue="False",
        )
        self.headers_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.headers_check,
            text="Include Headings",
            onvalue="True",
            offvalue="False",
        )
        self.ampersand_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.ampersand_check,
            text="Filter Ampersand:",
            onvalue="True",
            offvalue="False",
        )
        self.tweak_edi_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.tweak_edi,
            text="Apply Edi Tweaks",
            onvalue=True,
            offvalue=False,
        )

        self.rename_file_field = ttk.Entry(self.split_edi_frame, width=10)

        # --- A record padding ---
        self.a_record_padding_frame = ttk.Frame(self.convert_options_frame)

        self.pad_a_records_checkbutton = ttk.Checkbutton(
            self.a_record_padding_frame,
            variable=self.pad_arec_check,
            text='Pad "A" Records',
            onvalue="True",
            offvalue="False",
        )

        self.pad_a_records_length_optionmenu = ttk.OptionMenu(
            self.a_record_padding_frame,
            self.a_record_padding_length,
            self.a_record_padding_length.get(),
            6,
            30,
        )

        self.a_record_padding_field = ttk.Entry(
            self.convert_options_frame, width=10
        )

        self.append_a_records_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.append_arec_check,
            text='Append to "A" Records (6 Characters)\n(Series2K)',
            onvalue="True",
            offvalue="False",
        )
        self.a_record_append_field = ttk.Entry(
            self.convert_options_frame, width=10
        )

        self.invoice_date_custom_format_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.invoice_date_custom_format,
            text="Custom Invoice Date Format",
            onvalue=True,
            offvalue=False,
        )

        self.force_txt_file_ext_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.force_txt_file_ext_check,
            text="Force .txt file extension",
            onvalue="True",
            offvalue="False",
        )
        self.invoice_date_offset_spinbox_label = ttk.Label(
            self.convert_options_frame, text="Invoice Offset (Days)"
        )
        self.invoice_date_offset_spinbox = ttk.Spinbox(
            self.convert_options_frame,
            textvariable=self.invoice_date_offset,
            from_=-14,
            to=14,
            width=3,
        )
        self.each_uom_edi_tweak_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.edi_each_uom_tweak,
            text="Each UOM",
        )
        self.override_upc_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.override_upc_bool,
            text="Override UPC",
        )
        self.override_upc_level_optionmenu = ttk.OptionMenu(
            self.convert_options_frame,
            self.override_upc_level,
            self.override_upc_level.get(),
            *range(1, 5),
        )
        self.override_upc_category_filter_entry = ttk.Entry(
            self.convert_options_frame, width=10
        )
        try:
            import tk_extra_widgets
            self.override_upc_category_filter_tooltip = tk_extra_widgets.CreateToolTip(
                self.override_upc_category_filter_entry,
                "Enter 'ALL' or a comma separated list of numbers",
            )
        except ImportError:
            pass

        self.upc_target_length_label = ttk.Label(
            self.convert_options_frame, text="UPC Target Length:"
        )
        self.upc_target_length_entry = ttk.Entry(
            self.convert_options_frame, width=5
        )
        self.upc_target_length_entry.insert(0, "11")
        self.upc_padding_pattern_label = ttk.Label(
            self.convert_options_frame, text="UPC Padding Pattern:"
        )
        self.upc_padding_pattern_entry = ttk.Entry(
            self.convert_options_frame, width=15
        )
        self.upc_padding_pattern_entry.insert(0, "           ")

        self.split_prepaid_sales_tax_crec = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.split_sales_tax_prepaid_var,
            text="Split Sales Tax 'C' Records",
        )

        self.include_item_numbers_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.include_item_numbers,
            text="Include Item Numbers",
        )

        self.include_item_description_checkbutton = ttk.Checkbutton(
            self.convert_options_frame,
            variable=self.include_item_description,
            text="Include Item Description",
        )

        # Column sorter widget - try to import, create stub if unavailable
        try:
            from tk_extra_widgets import columnSorterWidget
            self.simple_csv_column_sorter = columnSorterWidget(
                self.convert_options_frame
            )
        except ImportError:
            # Create a minimal stub with a containerframe attribute
            class _StubColumnSorter:
                def __init__(self, parent):
                    self.containerframe = ttk.Frame(parent)
                def set_columnstring(self, val):
                    pass
                def get_columnstring(self):
                    return ""
            self.simple_csv_column_sorter = _StubColumnSorter(
                self.convert_options_frame
            )

        # --- Estore fields ---
        self.estore_store_number_label = ttk.Label(
            self.convert_options_frame, text="Estore Store Number"
        )
        self.estore_Vendor_OId_label = ttk.Label(
            self.convert_options_frame, text="Estore Vendor OId"
        )
        self.estore_vendor_namevendoroid_label = ttk.Label(
            self.convert_options_frame, text="Estore Vendor Name OId"
        )
        self.estore_store_number_field = ttk.Entry(
            self.convert_options_frame, width=10
        )
        self.estore_Vendor_OId_field = ttk.Entry(
            self.convert_options_frame, width=10
        )
        self.estore_vendor_namevendoroid_field = ttk.Entry(
            self.convert_options_frame, width=10
        )
        self.estore_c_record_oid_label = ttk.Label(
            self.convert_options_frame, text="Estore C Record OId"
        )
        self.estore_c_record_oid_field = ttk.Entry(
            self.convert_options_frame, width=10
        )
        self.fintech_divisionid_label = ttk.Label(
            self.convert_options_frame, text="Fintech Division_id"
        )
        self.fintech_divisionid_field = ttk.Entry(
            self.convert_options_frame, width=10
        )

        # --- set_dialog_variables ---
        def set_dialog_variables(config_dict, copied):
            if copied:
                for child in self.bodyframe.winfo_children():
                    try:
                        child.configure(state=tk.NORMAL)
                    except Exception:
                        pass
            self.active_checkbutton.set(config_dict.get("folder_is_active", "False"))
            if config_dict.get("folder_name") != "template" and not copied:
                if hasattr(self, "folder_alias_field"):
                    self.folder_alias_field.insert(0, config_dict.get("alias", ""))
            self.process_backend_copy_check.set(config_dict.get("process_backend_copy", False))
            self.process_backend_ftp_check.set(config_dict.get("process_backend_ftp", False))
            self.process_backend_email_check.set(
                config_dict.get("process_backend_email", False)
            )

            self.ftp_server_field.delete(0, tk.END)
            self.ftp_port_field.delete(0, tk.END)
            self.ftp_folder_field.delete(0, tk.END)
            self.ftp_username_field.delete(0, tk.END)
            self.ftp_password_field.delete(0, tk.END)
            self.email_recepient_field.delete(0, tk.END)
            self.email_sender_subject_field.delete(0, tk.END)

            self.ftp_server_field.insert(0, config_dict.get("ftp_server", ""))
            self.ftp_port_field.insert(0, config_dict.get("ftp_port", ""))
            self.ftp_folder_field.insert(0, config_dict.get("ftp_folder", ""))
            self.ftp_username_field.insert(0, config_dict.get("ftp_username", ""))
            self.ftp_password_field.insert(0, config_dict.get("ftp_password", ""))
            self.email_recepient_field.insert(0, config_dict.get("email_to", ""))
            self.email_sender_subject_field.insert(
                0, config_dict.get("email_subject_line", "")
            )

            self.force_edi_check_var.set(config_dict.get("force_edi_validation", False))
            self.process_edi.set(config_dict.get("process_edi", "False"))
            self.upc_var_check.set(config_dict.get("calculate_upc_check_digit", "False"))
            self.a_rec_var_check.set(config_dict.get("include_a_records", "False"))
            self.c_rec_var_check.set(config_dict.get("include_c_records", "False"))
            self.headers_check.set(config_dict.get("include_headers", "False"))
            self.ampersand_check.set(config_dict.get("filter_ampersand", "False"))
            self.pad_arec_check.set(config_dict.get("pad_a_records", "False"))
            self.tweak_edi.set(config_dict.get("tweak_edi", False))
            self.split_edi.set(config_dict.get("split_edi", False))
            self.split_edi_send_credits.set(
                config_dict.get("split_edi_include_credits", False)
            )
            self.split_edi_send_invoices.set(
                config_dict.get("split_edi_include_invoices", False)
            )
            self.prepend_file_dates.set(config_dict.get("prepend_date_files", False))
            self.split_edi_filter_categories_entry.delete(0, tk.END)
            self.split_edi_filter_categories_entry.insert(
                0, config_dict.get("split_edi_filter_categories", "ALL")
            )
            self.split_edi_filter_mode.set(
                config_dict.get("split_edi_filter_mode", "include")
            )
            self.rename_file_field.delete(0, tk.END)
            self.rename_file_field.insert(0, config_dict.get("rename_file", ""))
            self.a_record_padding_field.delete(0, tk.END)
            self.a_record_padding_field.insert(0, config_dict.get("a_record_padding", ""))
            self.a_record_padding_length.set(config_dict.get("a_record_padding_length", 6))
            self.append_arec_check.set(config_dict.get("append_a_records", "False"))
            self.a_record_append_field.delete(0, tk.END)
            self.a_record_append_field.insert(
                0, config_dict.get("a_record_append_text", "")
            )
            self.force_txt_file_ext_check.set(config_dict.get("force_txt_file_ext", "False"))
            self.invoice_date_offset.set(config_dict.get("invoice_date_offset", 0))
            self.invoice_date_custom_format.set(
                config_dict.get("invoice_date_custom_format", False)
            )
            self.invoice_date_custom_format_field.delete(0, tk.END)
            self.invoice_date_custom_format_field.insert(
                0, config_dict.get("invoice_date_custom_format_string", "")
            )
            self.edi_each_uom_tweak.set(config_dict.get("retail_uom", False))
            self.override_upc_bool.set(config_dict.get("override_upc_bool", False))
            self.override_upc_level.set(config_dict.get("override_upc_level", 1))
            self.override_upc_category_filter_entry.delete(0, tk.END)
            self.override_upc_category_filter_entry.insert(
                0, config_dict.get("override_upc_category_filter", "")
            )
            self.upc_target_length_entry.delete(0, tk.END)
            self.upc_target_length_entry.insert(
                0, config_dict.get("upc_target_length", 11)
            )
            self.upc_padding_pattern_entry.delete(0, tk.END)
            self.upc_padding_pattern_entry.insert(
                0, config_dict.get("upc_padding_pattern", "           ")
            )
            self.include_item_numbers.set(config_dict.get("include_item_numbers", False))
            self.include_item_description.set(
                config_dict.get("include_item_description", False)
            )
            self.simple_csv_column_sorter.set_columnstring(
                config_dict.get("simple_csv_sort_order", "")
            )
            self.split_sales_tax_prepaid_var.set(
                config_dict.get("split_prepaid_sales_tax_crec", False)
            )
            self.estore_store_number_field.delete(0, tk.END)
            self.estore_store_number_field.insert(
                0, config_dict.get("estore_store_number", "")
            )
            self.estore_Vendor_OId_field.delete(0, tk.END)
            self.estore_Vendor_OId_field.insert(0, config_dict.get("estore_Vendor_OId", ""))
            self.estore_vendor_namevendoroid_field.delete(0, tk.END)
            self.estore_vendor_namevendoroid_field.insert(
                0, config_dict.get("estore_vendor_NameVendorOID", "")
            )
            self.estore_c_record_oid_field.delete(0, tk.END)
            self.estore_c_record_oid_field.insert(
                0, config_dict.get("estore_c_record_OID", "")
            )
            self.fintech_divisionid_field.delete(0, tk.END)
            self.fintech_divisionid_field.insert(
                0, config_dict.get("fintech_division_id", "")
            )

            if copied:
                self.convert_formats_var.set(config_dict.get("convert_to_format", "csv"))
                if config_dict.get("process_edi") == "True":
                    self.ediconvert_options.set("Convert EDI")
                    reset_ediconvert_options("Convert EDI")
                elif config_dict.get("tweak_edi") is True:
                    self.ediconvert_options.set("Tweak EDI")
                    reset_ediconvert_options("Tweak EDI")
                else:
                    self.ediconvert_options.set("Do Nothing")
                    reset_ediconvert_options("Do Nothing")

        set_dialog_variables(self.foldersnameinput, False)

        # --- reset/make ediconvert options ---
        def reset_ediconvert_options(argument):
            for child in self.convert_options_frame.winfo_children():
                child.grid_forget()
            make_ediconvert_options(argument)

        # --- Grid split_edi_frame and its children ---
        self.split_edi_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        self.split_edi_checkbutton.grid(
            row=0, column=0, columnspan=2, sticky=tk.W
        )
        self.split_edi_send_invoices_checkbutton.grid(
            row=1, column=0, columnspan=2, sticky=tk.W
        )
        self.split_edi_send_credits_checkbutton.grid(
            row=2, column=0, columnspan=2, sticky=tk.W
        )
        self.prepend_file_dates_checkbutton.grid(
            row=3, column=0, columnspan=2, sticky=tk.W
        )
        self.split_edi_rename_file_label = ttk.Label(
            self.split_edi_frame, text="Rename File:"
        )
        self.split_edi_rename_file_label.grid(row=4, column=0, sticky=tk.W)
        self.rename_file_field.grid(row=4, column=1, sticky=tk.W)

        # --- Category filter frame grid ---
        self.category_filter_frame.grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(5, 0)
        )
        self.split_edi_filter_categories_label.grid(
            row=0, column=0, sticky=tk.W
        )
        self.split_edi_filter_categories_entry.grid(
            row=0, column=1, sticky=tk.W
        )
        self.split_edi_filter_mode_label.grid(row=1, column=0, sticky=tk.W)
        self.split_edi_filter_mode_optionmenu.grid(
            row=1, column=1, sticky=tk.W
        )

        # --- make_ediconvert_options ---
        def make_ediconvert_options(argument):
            if argument == "Do Nothing":
                self.tweak_edi.set(False)
                self.process_edi.set("False")
                ttk.Label(
                    self.convert_options_frame, text="Send As Is"
                ).grid()
            if argument == "Convert EDI":
                self.process_edi.set("True")
                self.tweak_edi.set(False)
                self.convert_to_selector_frame.grid(row=0, column=0, columnspan=2)
                self.convert_to_selector_label.grid(
                    row=0, column=0, sticky=tk.W
                )
                self.convert_to_selector_menu.grid(
                    row=0, column=1, sticky=tk.W
                )
                make_convert_to_options()
            if argument == "Tweak EDI":
                self.tweak_edi.set(True)
                self.process_edi.set("False")
                self.upc_variable_process_checkbutton.grid(
                    row=2, column=0, sticky=tk.W, padx=3
                )
                self.a_record_padding_frame.grid(
                    row=9,
                    column=0,
                    columnspan=2,
                    sticky=tk.W + tk.E,
                    padx=3,
                )
                self.pad_a_records_checkbutton.grid(
                    row=0, column=0, sticky=tk.W
                )
                self.pad_a_records_length_optionmenu.grid(
                    row=0, column=1, sticky=tk.E
                )
                self.a_record_padding_field.grid(
                    row=9, column=2, sticky=tk.W, padx=3
                )
                self.append_a_records_checkbutton.grid(
                    row=10, column=0, sticky=tk.W, padx=3
                )
                self.a_record_append_field.grid(row=10, column=2)
                self.force_txt_file_ext_checkbutton.grid(
                    row=11, column=0, sticky=tk.W, padx=3
                )
                self.invoice_date_offset_spinbox_label.grid(
                    row=12, column=0, sticky=tk.W, padx=3
                )
                self.invoice_date_offset_spinbox.grid(
                    row=12, column=2, sticky=tk.W, padx=3
                )
                self.invoice_date_custom_format_checkbutton.grid(
                    row=13, column=0, sticky=tk.W, padx=3
                )
                self.invoice_date_custom_format_field.grid(
                    row=13, column=2, sticky=tk.W, padx=3
                )
                self.each_uom_edi_tweak_checkbutton.grid(
                    row=14, column=0, sticky=tk.W, padx=3
                )
                self.override_upc_checkbutton.grid(
                    row=15, column=0, sticky=tk.W, padx=3
                )
                self.override_upc_level_optionmenu.grid(
                    row=15, column=1, sticky=tk.W, padx=3
                )
                self.override_upc_category_filter_entry.grid(
                    row=15, column=2, sticky=tk.W, padx=3
                )
                self.upc_target_length_label.grid(
                    row=16, column=0, sticky=tk.W, padx=3
                )
                self.upc_target_length_entry.grid(
                    row=16, column=1, sticky=tk.W
                )
                self.upc_padding_pattern_label.grid(
                    row=17, column=0, sticky=tk.W, padx=3
                )
                self.upc_padding_pattern_entry.grid(
                    row=17, column=1, sticky=tk.W
                )
                self.split_prepaid_sales_tax_crec.grid(
                    row=18, column=0, sticky=tk.W, padx=3
                )

        # --- Initial EDI convert options ---
        if self.foldersnameinput.get("process_edi") == "True":
            self.ediconvert_options.set("Convert EDI")
            make_ediconvert_options("Convert EDI")
        elif self.foldersnameinput.get("tweak_edi") is True:
            self.ediconvert_options.set("Tweak EDI")
            make_ediconvert_options("Tweak EDI")
        else:
            self.ediconvert_options.set("Do Nothing")
            make_ediconvert_options("Do Nothing")

        self.edi_options_menu = ttk.OptionMenu(
            self.ediframe,
            self.ediconvert_options,
            self.ediconvert_options.get(),
            "Do Nothing",
            "Convert EDI",
            "Tweak EDI",
            command=reset_ediconvert_options,
        )

        # --- config_from_others callback ---
        def config_from_others():
            def recurse_set_default(parent):
                for child in parent.winfo_children():
                    try:
                        child.configure(state=tk.NORMAL)
                    except Exception:
                        pass
                    recurse_set_default(child)

            recurse_set_default(master)
            if self._alias_provider:
                # Use alias provider to look up config
                pass
            else:
                try:
                    import database_import
                    settings_table = database_import.database_obj_instance.folders_table.find_one(
                        alias=self.otherslistbox.get(tk.ACTIVE)
                    )
                    set_dialog_variables(settings_table, True)
                except (ImportError, AttributeError):
                    pass
            set_header_state()
            set_send_options_fields_state()

        self.copyconfigbutton.configure(command=config_from_others)

        set_header_state()
        set_send_options_fields_state()

        # --- Grid/pack remaining widgets ---
        self.force_edi_check_checkbutton.grid(
            row=1, column=0, columnspan=2, sticky=tk.W
        )
        self.edi_options_menu.grid(row=5)
        self.active_checkbutton_object.pack(fill=tk.X)
        self.copy_backend_checkbutton.grid(row=3, column=0, sticky=tk.W)
        self.ftp_backend_checkbutton.grid(row=4, column=0, sticky=tk.W)
        self.email_backend_checkbutton.grid(row=5, column=0, sticky=tk.W)
        if self.foldersnameinput.get("folder_name") != "template":
            self.folder_alias_frame.grid(row=6, column=0, columnspan=2)
        self.copy_backend_folder_selection_button.grid(
            row=4, column=0, columnspan=2
        )
        self.ftp_server_field.grid(row=7, column=1)
        self.ftp_port_field.grid(row=8, column=1)
        self.ftp_folder_field.grid(row=9, column=1)
        self.ftp_username_field.grid(row=10, column=1)
        self.ftp_password_field.grid(row=11, column=1)
        self.email_recepient_field.grid(row=14, column=1)
        self.email_sender_subject_field.grid(row=18, column=1)
        self.otherslistbox.pack(side=tk.LEFT, fill=tk.Y)
        self.otherslistboxscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.copyconfigbutton.pack()

        # --- Populate others listbox ---
        self.aliaslist = []
        if self._alias_provider:
            aliases = self._alias_provider()
            if aliases:
                self.aliaslist = sorted(aliases)
        else:
            try:
                import database_import
                for entry in database_import.database_obj_instance.folders_table.all():
                    self.aliaslist.append(entry["alias"])
                self.aliaslist.sort()
            except (ImportError, AttributeError):
                pass
        for alias in self.aliaslist:
            self.otherslistbox.insert(tk.END, alias)
        self.otherslistbox.config(width=0, height=10)

        # --- Final pack layout (matches original exactly) ---
        self.header_frame_frame.pack(fill=tk.X)
        self.bodyframe.pack()

        self.othersframe.pack(side=tk.LEFT, fill=tk.Y)
        self.otherslistboxframe.pack(side=tk.LEFT, fill=tk.Y)
        self.separatorv0.pack(side=tk.LEFT, fill=tk.Y, padx=2)
        self.folderframe.pack(side=tk.LEFT, anchor="n")
        self.separatorv1.pack(side=tk.LEFT, fill=tk.Y, padx=2)
        self.prefsframe.pack(side=tk.LEFT, anchor="n")
        self.separatorv2.pack(side=tk.LEFT, fill=tk.Y, padx=2)
        self.ediframe.pack(side=tk.LEFT, anchor="n")

        # Store field refs for extractor compatibility
        self._field_refs["active_checkbutton"] = self.active_checkbutton
        self._field_refs["process_backend_copy_check"] = self.process_backend_copy_check
        self._field_refs["process_backend_ftp_check"] = self.process_backend_ftp_check
        self._field_refs["process_backend_email_check"] = self.process_backend_email_check
        self._field_refs["ftp_server_field"] = self.ftp_server_field
        self._field_refs["ftp_port_field"] = self.ftp_port_field
        self._field_refs["ftp_folder_field"] = self.ftp_folder_field
        self._field_refs["ftp_username_field"] = self.ftp_username_field
        self._field_refs["ftp_password_field"] = self.ftp_password_field
        self._field_refs["email_recepient_field"] = self.email_recepient_field
        self._field_refs["email_sender_subject_field"] = self.email_sender_subject_field
        self._field_refs["process_edi"] = self.process_edi
        self._field_refs["convert_formats_var"] = self.convert_formats_var
        self._field_refs["tweak_edi"] = self.tweak_edi
        self._field_refs["split_edi"] = self.split_edi
        self._field_refs["split_edi_send_invoices"] = self.split_edi_send_invoices
        self._field_refs["split_edi_send_credits"] = self.split_edi_send_credits
        self._field_refs["prepend_file_dates"] = self.prepend_file_dates
        self._field_refs["upc_var_check"] = self.upc_var_check
        self._field_refs["a_rec_var_check"] = self.a_rec_var_check
        self._field_refs["c_rec_var_check"] = self.c_rec_var_check
        self._field_refs["headers_check"] = self.headers_check
        self._field_refs["ampersand_check"] = self.ampersand_check
        self._field_refs["force_edi_check_var"] = self.force_edi_check_var
        self._field_refs["pad_arec_check"] = self.pad_arec_check
        self._field_refs["a_record_padding_length"] = self.a_record_padding_length
        self._field_refs["append_arec_check"] = self.append_arec_check
        self._field_refs["force_txt_file_ext_check"] = self.force_txt_file_ext_check
        self._field_refs["invoice_date_offset"] = self.invoice_date_offset
        self._field_refs["invoice_date_custom_format"] = self.invoice_date_custom_format
        self._field_refs["edi_each_uom_tweak"] = self.edi_each_uom_tweak
        self._field_refs["override_upc_bool"] = self.override_upc_bool
        self._field_refs["override_upc_level"] = self.override_upc_level
        self._field_refs["split_sales_tax_prepaid_var"] = self.split_sales_tax_prepaid_var
        self._field_refs["include_item_numbers"] = self.include_item_numbers
        self._field_refs["include_item_description"] = self.include_item_description
        if hasattr(self, "folder_alias_field"):
            self._field_refs["folder_alias_field"] = self.folder_alias_field

        # Add missing field refs for text entry widgets
        self._field_refs["split_edi_filter_categories_entry"] = self.split_edi_filter_categories_entry
        self._field_refs["split_edi_filter_mode"] = self.split_edi_filter_mode
        self._field_refs["rename_file_field"] = self.rename_file_field
        self._field_refs["a_record_padding_field"] = self.a_record_padding_field
        self._field_refs["a_record_append_field"] = self.a_record_append_field
        self._field_refs["override_upc_category_filter_entry"] = self.override_upc_category_filter_entry
        self._field_refs["upc_padding_pattern_entry"] = self.upc_padding_pattern_entry
        self._field_refs["simple_csv_column_sorter"] = self.simple_csv_column_sorter
        self._field_refs["invoice_date_custom_format_field"] = self.invoice_date_custom_format_field
        self._field_refs["estore_store_number_field"] = self.estore_store_number_field
        self._field_refs["estore_Vendor_OId_field"] = self.estore_Vendor_OId_field
        self._field_refs["estore_vendor_namevendoroid_field"] = self.estore_vendor_namevendoroid_field
        self._field_refs["fintech_divisionid_field"] = self.fintech_divisionid_field

        return self.active_checkbutton_object  # initial focus

    def validate(self) -> bool:
        """
        Validate dialog fields.

        Delegates to injected validator while keeping UI feedback logic.

        Returns:
            True if validation passes, False otherwise
        """
        # Skip validation if folder is disabled
        if self.active_checkbutton.get() == "False":
            return True

        # Create validator with dependencies
        validator = self._create_validator()

        # Extract current field values
        extractor = self._create_extractor(self._field_refs)
        extracted = extractor.extract_all()

        # Get current alias if editing
        current_alias = ""
        if self._foldersnameinput:
            current_alias = self._foldersnameinput.get("alias", "")

        # Perform validation
        result = validator.validate_extracted_fields(extracted, current_alias)

        # Handle errors (keep original UI feedback)
        if not result.is_valid:
            error_messages = [e.message for e in result.errors]
            self._show_validation_errors(error_messages)
            return False

        return True

    def apply(self, apply_to_folder: Dict[str, Any] = None):
        """
        Apply dialog changes.

        Delegates to extractor while keeping database update logic.

        Args:
            apply_to_folder: Dictionary to update with changes. If None, uses
                            the input folder dictionary from construction.
        """
        # Use stored folder dictionary if not provided
        if apply_to_folder is None:
            apply_to_folder = self._foldersnameinput
        # Extract field values
        extractor = self._create_extractor(self._field_refs)
        extracted = extractor.extract_all()

        # Apply values to folder dictionary
        self._apply_to_folder(extracted, apply_to_folder)

        # Handle template vs regular folder
        if self._foldersnameinput.get("folder_name") != "template":
            try:
                from interface.operations.folder_operations import update_folder_alias
                update_folder_alias(apply_to_folder)
            except ImportError:
                pass
        else:
            try:
                from interface.operations.folder_operations import update_reporting
                update_reporting(apply_to_folder)
            except ImportError:
                pass

        # Notify main window
        try:
            from interface.ui.main_window import set_main_button_states
            set_main_button_states()
        except ImportError:
            pass

        # Callback if provided
        if self._on_apply_success:
            self._on_apply_success(apply_to_folder)

    def _apply_to_folder(
        self,
        extracted: ExtractedDialogFields,
        apply_to_folder: Dict[str, Any]
    ):
        """Apply extracted values to folder dictionary."""
        apply_to_folder["folder_is_active"] = str(self.active_checkbutton.get())

        if self._foldersnameinput.get("folder_name") != "template":
            if str(self._field_refs.get("folder_alias_field", tk.Entry()).get()) == "":
                apply_to_folder["alias"] = os.path.basename(
                    self._foldersnameinput["folder_name"]
                )
            else:
                apply_to_folder["alias"] = str(
                    self._field_refs.get("folder_alias_field", tk.Entry()).get()
                )

        apply_to_folder["copy_to_directory"] = self.copy_to_directory
        apply_to_folder["process_backend_copy"] = self.process_backend_copy_check.get()
        apply_to_folder["process_backend_ftp"] = self.process_backend_ftp_check.get()
        apply_to_folder["process_backend_email"] = self.process_backend_email_check.get()

        apply_to_folder["ftp_server"] = str(self._field_refs["ftp_server_field"].get())
        apply_to_folder["ftp_port"] = int(self._field_refs["ftp_port_field"].get())
        apply_to_folder["ftp_folder"] = str(self._field_refs["ftp_folder_field"].get())
        apply_to_folder["ftp_username"] = str(self._field_refs["ftp_username_field"].get())
        apply_to_folder["ftp_password"] = str(self._field_refs["ftp_password_field"].get())

        apply_to_folder["email_to"] = str(self._field_refs["email_recepient_field"].get())
        apply_to_folder["email_subject_line"] = str(
            self._field_refs["email_sender_subject_field"].get()
        )

        apply_to_folder["process_edi"] = str(self.process_edi.get())
        apply_to_folder["convert_to_format"] = str(self.convert_formats_var.get())
        apply_to_folder["calculate_upc_check_digit"] = str(self.upc_var_check.get())
        apply_to_folder["include_a_records"] = str(self.a_rec_var_check.get())
        apply_to_folder["include_c_records"] = str(self.c_rec_var_check.get())
        apply_to_folder["include_headers"] = str(self.headers_check.get())
        apply_to_folder["filter_ampersand"] = str(self.ampersand_check.get())
        apply_to_folder["force_edi_validation"] = self.force_edi_check_var.get()
        apply_to_folder["tweak_edi"] = self.tweak_edi.get()
        apply_to_folder["split_edi"] = self.split_edi.get()
        apply_to_folder["split_edi_include_invoices"] = self.split_edi_send_invoices.get()
        apply_to_folder["split_edi_include_credits"] = self.split_edi_send_credits.get()
        apply_to_folder["prepend_date_files"] = self.prepend_file_dates.get()
        apply_to_folder["split_edi_filter_categories"] = str(self._field_refs["split_edi_filter_categories_entry"].get())
        apply_to_folder["split_edi_filter_mode"] = str(self._field_refs["split_edi_filter_mode"].get())
        apply_to_folder["rename_file"] = str(self._field_refs["rename_file_field"].get())
        apply_to_folder["pad_a_records"] = str(self.pad_arec_check.get())
        apply_to_folder["a_record_padding"] = str(self._field_refs["a_record_padding_field"].get())
        apply_to_folder["a_record_padding_length"] = int(self.a_record_padding_length.get())
        apply_to_folder["append_a_records"] = str(self.append_arec_check.get())
        apply_to_folder["a_record_append_text"] = str(self._field_refs["a_record_append_field"].get())
        apply_to_folder["force_txt_file_ext"] = str(self.force_txt_file_ext_check.get())
        apply_to_folder["invoice_date_offset"] = int(self.invoice_date_offset.get())
        apply_to_folder["retail_uom"] = self.edi_each_uom_tweak.get()
        apply_to_folder["override_upc_bool"] = self.override_upc_bool.get()
        apply_to_folder["override_upc_level"] = self.override_upc_level.get()
        apply_to_folder["override_upc_category_filter"] = str(self._field_refs["override_upc_category_filter_entry"].get())
        apply_to_folder["upc_target_length"] = int(self.upc_target_length.get())
        apply_to_folder["upc_padding_pattern"] = str(self._field_refs["upc_padding_pattern_entry"].get())
        apply_to_folder["include_item_numbers"] = self.include_item_numbers.get()
        apply_to_folder["include_item_description"] = self.include_item_description.get()
        apply_to_folder["simple_csv_sort_order"] = str(self._field_refs["simple_csv_column_sorter"].get_columnstring())
        apply_to_folder["invoice_date_custom_format"] = self.invoice_date_custom_format.get()
        apply_to_folder["invoice_date_custom_format_string"] = str(self._field_refs["invoice_date_custom_format_field"].get())
        apply_to_folder["split_prepaid_sales_tax_crec"] = self.split_sales_tax_prepaid_var.get()
        apply_to_folder["estore_store_number"] = str(self._field_refs["estore_store_number_field"].get())
        apply_to_folder["estore_Vendor_OId"] = str(self._field_refs["estore_Vendor_OId_field"].get())
        apply_to_folder["estore_vendor_NameVendorOID"] = str(self._field_refs["estore_vendor_namevendoroid_field"].get())
        apply_to_folder["fintech_division_id"] = str(self._field_refs["fintech_divisionid_field"].get())

    def _show_validation_errors(self, errors: List[str]):
        """Show validation errors in dialog."""
        error_string = "\r\n".join(errors)
        from tkinter.messagebox import showerror
        showerror(parent=self, message=error_string)

    # Testing helper methods
    @classmethod
    def create_for_testing(
        cls,
        parent=None,
        foldersnameinput: Optional[Dict[str, Any]] = None,
        ftp_service: Optional[FTPServiceProtocol] = None,
        mock_validator: Optional[FolderSettingsValidator] = None,
        mock_extractor: Optional[FolderDataExtractor] = None,
    ) -> "EditFoldersDialog":
        """
        Create dialog configured for testing.

        This is the primary entry point for tests.

        Args:
            parent: Test parent (can be tkinter.Tk or None)
            foldersnameinput: Test folder data
            ftp_service: Mock FTP service
            mock_validator: Pre-configured validator with controlled behavior
            mock_extractor: Pre-configured extractor

        Returns:
            EditFoldersDialog configured for testing
        """
        # Create mock validator if not provided
        if mock_validator is None:
            mock_validator = FolderSettingsValidator(
                ftp_service=ftp_service or MockFTPService(should_succeed=True)
            )

        # Create mock FTP service
        if ftp_service is None:
            ftp_service = MockFTPService(should_succeed=True)

        return cls(
            parent=parent,
            foldersnameinput=foldersnameinput or {},
            ftp_service=ftp_service,
            validator=mock_validator,
            extractor=mock_extractor,
        )
