"""Qt reimplementation of EditFoldersDialog.

Provides a PyQt6-based dialog for editing folder configuration settings.
Uses a decomposed architecture with dedicated builders and handlers.
"""

import os
from typing import Dict, Any, Optional, Callable

from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
)

from interface.qt.dialogs.base_dialog import BaseDialog
from interface.validation.folder_settings_validator import FolderSettingsValidator
from interface.services.ftp_service import FTPServiceProtocol
from interface.plugins.plugin_manager import PluginManager
from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper

from interface.qt.dialogs.edit_folders.data_extractor import QtFolderDataExtractor
from interface.qt.dialogs.edit_folders.layout_builder import UILayoutBuilder
from interface.qt.dialogs.edit_folders.event_handlers import EventHandlers


class EditFoldersDialog(BaseDialog):
    """Qt-based dialog for editing folder configuration settings.

    Decomposed into helper classes for layout, EDI building, and event handling.
    """

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
        super().__init__(parent, title)
        self._folder_config = folder_config
        self._ftp_service = ftp_service
        self._validator = validator
        self._settings_provider = settings_provider
        self._alias_provider = alias_provider
        self._on_apply_success = on_apply_success

        # Shared state
        self._fields: Dict[str, Any] = {}
        self.copy_to_directory: str = folder_config.get("copy_to_directory", "")
        self._settings = self._load_settings()

        # Initialize plugin management
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
        self.plugin_config_mapper = PluginConfigurationMapper()

        # Initialize Handlers
        self.handlers = EventHandlers(
            dialog=self,
            folder_config=self._folder_config,
            fields=self._fields,
            copy_to_directory=self.copy_to_directory,
            validator=self._validator,
            settings_provider=self._settings_provider,
            alias_provider=self._alias_provider,
            on_apply_success=self._on_apply_success,
            data_extractor=QtFolderDataExtractor(self._fields),
            ftp_service=self._ftp_service,
        )

        # Initialize UI Builder
        self.ui_builder = UILayoutBuilder(
            dialog=self,
            fields=self._fields,
            folder_config=self._folder_config,
            alias_provider=self._alias_provider,
            on_copy_config=self.handlers.copy_config_from_other,
            on_select_copy_dir=self.handlers.select_copy_directory,
            on_show_path=self.handlers.show_folder_path,
            on_update_backend_states=self.handlers.update_active_state,
            on_convert_format_changed=None,  # Will be set by DynamicEDIBuilder
            on_ok=self._on_ok,
            on_cancel=self.reject,
        )

        self.setMinimumSize(1000, 700)
        self._build_ui()
        self._populate_fields(self._folder_config)

        # Initial state updates
        self.handlers.update_active_state()

    def _load_settings(self) -> dict:
        if self._settings_provider:
            return self._settings_provider() or {}
        return {}

    def _build_ui(self):
        """Delegate UI building to the UILayoutBuilder."""
        self.ui_builder.build_ui()

        # Link dynamic EDI builder back to dialog for population if needed
        self.dynamic_edi_builder = self.ui_builder.get_dynamic_edi_builder()

    def _populate_fields(self, config: Dict[str, Any]):
        """Populate UI fields from configuration."""

        def to_bool(val, default=False):
            if val is None:
                return default
            if isinstance(val, bool):
                return val
            return str(val).lower() == "true"

        # Active state
        active_btn = self._fields.get("active_checkbutton")
        if active_btn:
            active_btn.setChecked(to_bool(config.get("folder_is_active"), False))

        # Backend checks
        self._set_check(
            "process_backend_copy_check", to_bool(config.get("process_backend_copy"))
        )
        self._set_check(
            "process_backend_ftp_check", to_bool(config.get("process_backend_ftp"))
        )
        self._set_check(
            "process_backend_email_check", to_bool(config.get("process_backend_email"))
        )

        # Text fields
        self._set_text("folder_alias_field", str(config.get("alias") or ""))
        self._set_text("ftp_server_field", str(config.get("ftp_server") or ""))
        self._set_text("ftp_port_field", str(config.get("ftp_port") or ""))
        self._set_text("ftp_folder_field", str(config.get("ftp_folder") or ""))
        self._set_text("ftp_username_field", str(config.get("ftp_username") or ""))
        self._set_text("ftp_password_field", str(config.get("ftp_password") or ""))
        self._set_text("email_recipient_field", str(config.get("email_to") or ""))
        self._set_text(
            "email_sender_subject_field", str(config.get("email_subject_line") or "")
        )

        # EDI base settings
        self._set_check(
            "force_edi_check_var", to_bool(config.get("force_edi_validation"))
        )
        self._set_check("split_edi", to_bool(config.get("split_edi")))
        self._set_check(
            "split_edi_send_invoices", to_bool(config.get("split_edi_include_invoices"))
        )
        self._set_check(
            "split_edi_send_credits", to_bool(config.get("split_edi_include_credits"))
        )
        self._set_check("prepend_file_dates", to_bool(config.get("prepend_date_files")))
        self._set_text("rename_file_field", str(config.get("rename_file") or ""))
        self._set_text(
            "split_edi_filter_categories_entry",
            str(config.get("split_edi_filter_categories") or "ALL"),
        )

        # Filter mode
        mode_combo = self._fields.get("split_edi_filter_mode")
        if mode_combo:
            filter_mode = config.get("split_edi_filter_mode") or "include"
            idx = mode_combo.findText(str(filter_mode))
            if idx >= 0:
                mode_combo.setCurrentIndex(idx)

        # EDI Options combo
        edi_combo = self.dynamic_edi_builder.edi_options_combo
        if edi_combo:
            if str(config.get("process_edi")).lower() == "true":
                edi_combo.setCurrentText("Convert EDI")
            elif to_bool(config.get("tweak_edi")):
                edi_combo.setCurrentText("Tweak EDI")
            else:
                edi_combo.setCurrentText("Do Nothing")

    def _populate_fields_from_config(self, config: Dict[str, Any]):
        """Reload the dialog with a new configuration (e.g. after 'Copy Config')."""
        self._folder_config.update(config)
        self._populate_fields(self._folder_config)
        self.handlers.update_active_state()

    def _set_check(self, key: str, value: bool):
        widget = self._fields.get(key)
        if widget and hasattr(widget, "setChecked"):
            widget.setChecked(value)

    def _set_text(self, key: str, value: str):
        widget = self._fields.get(key)
        if widget and hasattr(widget, "setText"):
            widget.setText(value)

    def _on_ok(self):
        """Handle OK button: Validate and Apply."""
        if self.validate():
            self.apply()
            self.accept()

    def validate(self) -> bool:
        """Validate current UI state."""
        active_btn = self._fields.get("active_checkbutton")
        if active_btn and not active_btn.isChecked():
            return True

        extractor = QtFolderDataExtractor(self._fields)
        extracted = extractor.extract_all()
        extracted.copy_to_directory = self.handlers.copy_to_directory

        validator = self._create_validator()
        current_alias = self._folder_config.get("alias", "")
        result = validator.validate_extracted_fields(extracted, current_alias)

        if not result.is_valid:
            error_messages = [e.message for e in result.errors]
            QMessageBox.critical(self, "Validation Error", "\n".join(error_messages))
            return False

        return True

    def _create_validator(self) -> FolderSettingsValidator:
        if self._validator is not None:
            return self._validator

        existing_aliases = []
        if self._alias_provider:
            existing_aliases = self._alias_provider() or []

        return FolderSettingsValidator(
            ftp_service=self._ftp_service,
            existing_aliases=existing_aliases,
        )

    def apply(self):
        """Extract data from UI and update the configuration dictionary."""
        extractor = QtFolderDataExtractor(self._fields)
        extracted = extractor.extract_all()

        target = self._folder_config
        target["folder_is_active"] = extracted.folder_is_active

        if target.get("folder_name") != "template":
            alias = extracted.alias
            if not alias:
                alias = os.path.basename(target.get("folder_name", ""))
            target["alias"] = alias

        target["copy_to_directory"] = self.handlers.copy_to_directory
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

        # EDI settings
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
        target["invoice_date_custom_format_string"] = (
            extracted.invoice_date_custom_format_string
        )
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

        # Estore specific
        target["estore_store_number"] = extracted.estore_store_number
        target["estore_Vendor_OId"] = extracted.estore_vendor_oid
        target["estore_vendor_NameVendorOID"] = extracted.estore_vendor_namevendoroid
        target["estore_c_record_OID"] = self._get_estore_c_record_oid_local()
        target["fintech_division_id"] = extracted.fintech_division_id

        # Plugins
        self._apply_plugin_configurations(target)

        if self._on_apply_success:
            self._on_apply_success(target)

    def _get_estore_c_record_oid_local(self) -> str:
        widget = self._fields.get("estore_c_record_oid_field")
        if widget and hasattr(widget, "text"):
            return widget.text()
        return self._folder_config.get("estore_c_record_OID", "")

    def _apply_plugin_configurations(self, target: Dict[str, Any]) -> None:
        extracted_configs = self.plugin_config_mapper.extract_plugin_configurations(
            self._fields, framework="qt"
        )
        # Note: Don't add plugin_configurations to target dict for database storage.
        # The plugin configurations are managed separately and not persisted in the
        # folders table yet. Only update internal state for UI.
        self.plugin_config_mapper.state_manager.mark_saved()

    def get_fields(self) -> Dict[str, QWidget]:
        return dict(self._fields)
