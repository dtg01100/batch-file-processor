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
from interface.plugins.plugin_manager_provider import get_shared_plugin_manager
from interface.operations.plugin_configuration_mapper import PluginConfigurationMapper
from core.utils.bool_utils import normalize_bool

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
        plugin_manager: Optional[PluginManager] = None,
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

        # Shared plugin management
        self.plugin_manager = plugin_manager or get_shared_plugin_manager()
        self.plugin_config_mapper = PluginConfigurationMapper(
            plugin_manager=self.plugin_manager
        )

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
            data_extractor=QtFolderDataExtractor(
                self._fields, plugin_manager=self.plugin_manager
            ),
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
            on_dynamic_form_changed=self._refresh_tab_order,
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
        if self.dynamic_edi_builder and self.dynamic_edi_builder.edi_options_combo:
            self.dynamic_edi_builder.edi_options_combo.currentTextChanged.connect(
                lambda _text: self._refresh_tab_order()
            )

    def _populate_fields(self, config: Dict[str, Any]):
        """Populate UI fields from configuration."""

        def to_bool(val, default=False):
            if val is None:
                return default
            if isinstance(val, bool):
                return val
            return normalize_bool(val)

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
            if normalize_bool(config.get("process_edi")):
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
        self._refresh_tab_order()

    def _refresh_tab_order(self) -> None:
        ordered_keys = [
            "active_checkbutton",
            "folder_alias_field",
            "process_backend_copy_check",
            "process_backend_ftp_check",
            "process_backend_email_check",
            "copy_dest_btn",
            "ftp_server_field",
            "ftp_port_field",
            "ftp_folder_field",
            "ftp_username_field",
            "ftp_password_field",
            "email_recipient_field",
            "email_sender_subject_field",
            "force_edi_check_var",
            "split_edi",
            "split_edi_send_invoices",
            "split_edi_send_credits",
            "prepend_file_dates",
            "rename_file_field",
            "split_edi_filter_categories_entry",
            "split_edi_filter_mode",
            "convert_formats_var",
            "upc_var_check",
            "a_rec_var_check",
            "c_rec_var_check",
            "headers_check",
            "ampersand_check",
            "pad_arec_check",
            "a_record_padding_field",
            "a_record_padding_length",
            "append_arec_check",
            "a_record_append_field",
            "force_txt_file_ext_check",
            "invoice_date_offset",
            "invoice_date_custom_format",
            "invoice_date_custom_format_field",
            "override_upc_bool",
            "override_upc_level",
            "override_upc_category_filter_entry",
            "upc_target_length_entry",
            "upc_padding_pattern_entry",
        ]

        widgets = [
            self._fields.get(key)
            for key in ordered_keys
            if self._fields.get(key) is not None
            and hasattr(self._fields.get(key), "setFocus")
            and hasattr(self._fields.get(key), "isVisible")
            and self._fields.get(key).isVisible()
        ]

        for idx in range(len(widgets) - 1):
            self.setTabOrder(widgets[idx], widgets[idx + 1])

    def _focus_widget(self, widget: Optional[QWidget]) -> None:
        if widget is None:
            return
        widget.setFocus()
        if hasattr(widget, "selectAll"):
            widget.selectAll()

    def _widget_for_validation_field(self, field: str) -> Optional[QWidget]:
        field_map = {
            "alias": "folder_alias_field",
            "ftp_server": "ftp_server_field",
            "ftp_port": "ftp_port_field",
            "ftp_folder": "ftp_folder_field",
            "ftp_username": "ftp_username_field",
            "ftp_password": "ftp_password_field",
            "email_recipient": "email_recipient_field",
            "copy_destination": "copy_dest_btn",
            "backends": "process_backend_copy_check",
        }
        key = field_map.get(field)
        if not key:
            return None
        return self._fields.get(key)

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

        extractor = QtFolderDataExtractor(
            self._fields,
            plugin_manager=self.plugin_manager,
            copy_to_directory=self.handlers.copy_to_directory,
        )
        extracted = extractor.extract_all()

        validator = self._create_validator()
        current_alias = self._folder_config.get("alias", "")
        result = validator.validate_extracted_fields(extracted, current_alias)

        if not result.is_valid:
            first_invalid_widget = None
            grouped: Dict[str, list[str]] = {
                "Folder": [],
                "Backends": [],
                "FTP": [],
                "Email": [],
                "Copy": [],
                "Other": [],
            }

            def section_for_field(field_name: str) -> str:
                if field_name.startswith("ftp_"):
                    return "FTP"
                if field_name.startswith("email_"):
                    return "Email"
                if field_name.startswith("copy_"):
                    return "Copy"
                if field_name in {"alias"}:
                    return "Folder"
                if field_name in {"backends"}:
                    return "Backends"
                return "Other"

            for error in result.errors:
                grouped[section_for_field(error.field)].append(error.message)
                if first_invalid_widget is None:
                    first_invalid_widget = self._widget_for_validation_field(
                        error.field
                    )

            lines = []
            for section, messages in grouped.items():
                if not messages:
                    continue
                lines.append(f"{section}:")
                for msg in messages:
                    lines.append(f"- {msg}")
                lines.append("")
            while lines and not lines[-1]:
                lines.pop()

            self._focus_widget(first_invalid_widget)
            QMessageBox.critical(self, "Validation Error", "\n".join(lines))
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
        extractor = QtFolderDataExtractor(
            self._fields,
            plugin_manager=self.plugin_manager,
            copy_to_directory=self.handlers.copy_to_directory,
        )
        extracted = extractor.extract_all()

        target = self._folder_config
        target["folder_is_active"] = normalize_bool(extracted.folder_is_active)

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
        target["process_edi"] = normalize_bool(extracted.process_edi)
        target["convert_to_format"] = extracted.convert_to_format
        target["calculate_upc_check_digit"] = normalize_bool(
            extracted.calculate_upc_check_digit
        )
        target["include_a_records"] = normalize_bool(extracted.include_a_records)
        target["include_c_records"] = normalize_bool(extracted.include_c_records)
        target["include_headers"] = normalize_bool(extracted.include_headers)
        target["filter_ampersand"] = normalize_bool(extracted.filter_ampersand)
        target["force_edi_validation"] = extracted.force_edi_validation
        target["tweak_edi"] = extracted.tweak_edi
        target["split_edi"] = extracted.split_edi
        target["split_edi_include_invoices"] = extracted.split_edi_include_invoices
        target["split_edi_include_credits"] = extracted.split_edi_include_credits
        target["prepend_date_files"] = extracted.prepend_date_files
        target["split_edi_filter_categories"] = extracted.split_edi_filter_categories
        target["split_edi_filter_mode"] = extracted.split_edi_filter_mode
        target["rename_file"] = extracted.rename_file
        target["pad_a_records"] = normalize_bool(extracted.pad_a_records)
        target["a_record_padding"] = extracted.a_record_padding
        try:
            target["a_record_padding_length"] = int(extracted.a_record_padding_length)
        except (ValueError, TypeError):
            target["a_record_padding_length"] = 6
        target["append_a_records"] = normalize_bool(extracted.append_a_records)
        target["a_record_append_text"] = extracted.a_record_append_text
        target["force_txt_file_ext"] = normalize_bool(extracted.force_txt_file_ext)
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
        target["estore_c_record_OID"] = extracted.estore_c_record_oid
        target["fintech_division_id"] = extracted.fintech_division_id

        # Plugins
        self._apply_plugin_configurations(target)

        if self._on_apply_success:
            self._on_apply_success(target)

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
