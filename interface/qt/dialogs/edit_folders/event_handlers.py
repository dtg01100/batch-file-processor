"""Event Handlers for Qt Edit Folders Dialog.

Manages all user interaction event handlers for the Qt edit folders dialog.
Provides callback functions for various user actions such as button clicks,
checkbox toggles, and dropdown selections.
"""

import os
import logging
from typing import Dict, Any, Optional, Callable, List

from PyQt6.QtWidgets import QDialog, QWidget, QFileDialog, QMessageBox, QPushButton, QCheckBox


class EventHandlers:
    """Handler class for user interaction events in the edit folders dialog.

    Provides callback functions for various user actions such as button clicks,
    checkbox toggles, and dropdown selections.
    """

    def __init__(
        self,
        dialog: QDialog,
        folder_config: Dict[str, Any],
        fields: Dict[str, QWidget],
        copy_to_directory: str,
        validator: Any,
        settings_provider: Optional[Callable] = None,
        alias_provider: Optional[Callable] = None,
        on_apply_success: Optional[Callable] = None,
        data_extractor: Optional[Any] = None,
        ftp_service: Optional[Any] = None,
    ):
        """Initialize event handlers.

        Args:
            dialog: Reference to the dialog widget
            folder_config: Current folder configuration
            fields: Dictionary of widget references
            copy_to_directory: Current copy directory
            validator: Settings validator instance
            settings_provider: Callback to get global settings
            alias_provider: Callback to get all folder aliases
            on_apply_success: Callback for successful application
            data_extractor: Data extractor instance
            ftp_service: FTP service instance
        """
        self.dialog = dialog
        self.folder_config = folder_config
        self.fields = fields
        self.copy_to_directory = copy_to_directory
        self.validator = validator
        self.settings_provider = settings_provider
        self.alias_provider = alias_provider
        self.on_apply_success = on_apply_success
        self.data_extractor = data_extractor
        self.ftp_service = ftp_service

    def update_active_state(self):
        """Update the active state of the folder and all child widgets."""
        active_btn = self.fields.get("active_checkbutton")
        if not isinstance(active_btn, QCheckBox):
            return

        is_active = active_btn.isChecked()
        if is_active:
            active_btn.setText("Folder Is Enabled")
            active_btn.setStyleSheet(
                "QPushButton { background-color: green; color: white; padding: 8px; }"
            )
        else:
            active_btn.setText("Folder Is Disabled")
            active_btn.setStyleSheet(
                "QPushButton { background-color: red; color: white; padding: 8px; }"
            )

        # Update enabled state of other widgets
        for key in ["process_backend_copy_check", "process_backend_ftp_check"]:
            widget = self.fields.get(key)
            if widget:
                widget.setEnabled(is_active)

        # Email backend depends on global settings too
        email_check = self.fields.get("process_backend_email_check")
        if email_check:
            settings = self.settings_provider() if self.settings_provider else {}
            email_globally_enabled = settings.get("enable_email", False)
            email_check.setEnabled(is_active and email_globally_enabled)

        self.update_backend_states()

    def update_backend_states(self):
        """Update the enabled/disabled state of backend-specific widgets."""
        active_btn = self.fields.get("active_checkbutton")
        is_active = active_btn.isChecked() if active_btn else False
        
        settings = self.settings_provider() if self.settings_provider else {}
        email_globally_enabled = settings.get("enable_email", False)

        # Copy backend
        copy_check = self.fields.get("process_backend_copy_check")
        copy_on = is_active and (copy_check.isChecked() if copy_check else False)
        copy_btn = self.fields.get("copy_dest_btn")
        if copy_btn:
            copy_btn.setEnabled(copy_on)

        # FTP backend
        ftp_check = self.fields.get("process_backend_ftp_check")
        ftp_on = is_active and (ftp_check.isChecked() if ftp_check else False)
        for key in [
            "ftp_server_field", "ftp_port_field", "ftp_folder_field",
            "ftp_username_field", "ftp_password_field"
        ]:
            widget = self.fields.get(key)
            if widget:
                widget.setEnabled(ftp_on)

        # Email backend
        email_check = self.fields.get("process_backend_email_check")
        email_on = (
            is_active and 
            (email_check.isChecked() if email_check else False) and 
            email_globally_enabled
        )
        for key in ["email_recipient_field", "email_sender_subject_field"]:
            widget = self.fields.get(key)
            if widget:
                widget.setEnabled(email_on)

        # EDI settings enabled if folder is active and ANY backend is selected
        any_backend = (
            (copy_check.isChecked() if copy_check else False) or
            (ftp_check.isChecked() if ftp_check else False) or
            (email_check.isChecked() if email_check else False)
        )
        edi_enabled = is_active and any_backend
        
        for key in [
            "split_edi", "force_edi_check_var", "split_edi_send_invoices",
            "split_edi_send_credits", "prepend_file_dates", "rename_file_field",
            "split_edi_filter_categories_entry", "split_edi_filter_mode"
        ]:
            widget = self.fields.get(key)
            if widget:
                widget.setEnabled(edi_enabled)
        
        # We don't have direct access to edi_options_combo here yet, 
        # it's managed by DynamicEDIBuilder

    def copy_config_from_other(self):
        """Copy configuration from another selected folder."""
        others_list = self.fields.get("others_list")
        if not others_list:
            return
            
        current_item = others_list.currentItem()
        if not current_item:
            return
            
        selected_alias = current_item.text()
        other_config = None
        
        if self.alias_provider and self.settings_provider:
            all_aliases = self.alias_provider() or []
            if selected_alias in all_aliases:
                settings = self.settings_provider()
                if settings and "folders" in settings:
                    for folder in settings["folders"]:
                        if folder.get("alias") == selected_alias:
                            other_config = folder
                            break

        if other_config is None:
            try:
                import database_import
                other_config = database_import.database_obj_instance.folders_table.find_one(
                    alias=selected_alias
                )
            except Exception as e:
                logging.error(f"Error finding config for {selected_alias}: {e}")
                return

        if other_config and hasattr(self.dialog, "_populate_fields_from_config"):
            self.dialog._populate_fields_from_config(other_config)

    def show_folder_path(self):
        """Show the full path of the current folder."""
        path = self.folder_config.get("folder_name", "Unknown")
        QMessageBox.information(self.dialog, "Folder Path", path)

    def select_copy_directory(self):
        """Select the directory for the copy backend."""
        initial = self.copy_to_directory
        if not initial or not os.path.isdir(initial):
            initial = os.getcwd()
            
        folder = QFileDialog.getExistingDirectory(
            self.dialog,
            "Select Copy Backend Destination Folder",
            initial
        )
        if folder:
            self.copy_to_directory = folder
            if hasattr(self.dialog, "copy_to_directory"):
                self.dialog.copy_to_directory = folder

    def on_ok(self):
        """Handle OK button click - validate and apply settings."""
        if hasattr(self.dialog, "_on_ok"):
            self.dialog._on_ok()
        else:
            self.dialog.accept()

    def on_cancel(self):
        """Handle Cancel button click."""
        self.dialog.reject()
