"""
Edit folder dialog module for PyQt6 interface.

This module contains the EditFolderDialog implementation.
A tabbed dialog that handles folder configuration with support for:
- General settings (alias, active state, backends)
- Dynamic send backend settings (discovered from *_backend.py plugins)
- EDI processing settings
- Conversion format settings

**Lifecycle Pattern (BaseDialog):**
1. __init__ — initialize and setup UI
2. _setup_ui() — build widget hierarchy
3. _set_dialog_values() — load folder_data into UI
4. User interacts with widgets
5. OK clicked → validate() → apply() → close dialog
6. Cancel clicked → discard changes, close dialog
"""

import os
from typing import TYPE_CHECKING, Dict, Any, Optional, Callable, Tuple

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QStackedWidget,
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager

from interface.ui.base_dialog import BaseDialog
from interface.ui.plugin_ui_generator import PluginUIGenerator
from plugin_config import PluginRegistry


class EditFolderDialog(BaseDialog):
    """Tabbed dialog for editing folder configuration.

    Implements BaseDialog lifecycle:
    - _setup_ui() builds tabs and widgets
    - _set_dialog_values() loads folder_data into UI
    - validate() checks backend and plugin config validity
    - apply() writes UI state back to self.data
    """

    # Conversion format options
    CONVERT_FORMATS = [
        "csv",
        "EDI Tweaks",
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
        parent: Optional[QWidget] = None,
        folder_data: Optional[Dict[str, Any]] = None,
        db_manager: Optional["DatabaseManager"] = None,
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
        title = "Edit Folder" if folder_data else "Add Folder"

        # Store folder data before calling super().__init__() because BaseDialog._setup_ui() is called from super()
        self.folder_data = folder_data or {}

        # Discover plugins BEFORE calling super().__init__() because BaseDialog._setup_ui() is called from super()
        PluginRegistry.discover_plugins()
        self._send_plugins = PluginRegistry.list_send_plugins()
        self._backend_checks: Dict[str, QCheckBox] = {}
        self._backend_tabs: Dict[str, QWidget] = {}
        self._backend_value_getters: Dict[str, Dict[str, Callable]] = {}

        super().__init__(parent, title=title, data=self.folder_data)

        self.db_manager = db_manager
        self.settings = settings or {}

        self.resize(700, 500)

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        self._tabs = QTabWidget()
        self._layout.addWidget(self._tabs)

        self._general_tab = self._build_general_tab()
        self._edi_tab = self._build_edi_tab()
        self._convert_tab = self._build_convert_format_tab()

        self._tabs.addTab(self._general_tab, "General")

        for plugin_id, plugin_name, _ in self._send_plugins:
            plugin_class = PluginRegistry.get_send_plugin(plugin_id)
            if plugin_class:
                fields = plugin_class.get_config_fields()
                tab_widget, value_getters = (
                    PluginUIGenerator.create_plugin_config_widget(
                        fields, parent=None, current_values=self.folder_data
                    )
                )
                self._backend_tabs[plugin_id] = tab_widget
                self._backend_value_getters[plugin_id] = value_getters
                self._tabs.addTab(tab_widget, f"{plugin_name}")

        self._tabs.addTab(self._edi_tab, "EDI Processing")
        self._tabs.addTab(self._convert_tab, "Conversion Format")

        self._on_backend_state_change()

    def _build_general_tab(self) -> QWidget:
        """Build the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._active_check = QCheckBox("Active")
        # Handle both native bool and legacy string "True"/"False"
        is_active = self.data.get("folder_is_active", True)
        if isinstance(is_active, str):
            is_active = is_active == "True"
        self._active_check.setChecked(is_active)
        layout.addWidget(self._active_check)

        alias_group = QGroupBox("Folder Alias")
        alias_layout = QVBoxLayout(alias_group)

        self._alias_field = QLineEdit()
        self._alias_field.setPlaceholderText("Enter folder alias...")
        alias_layout.addWidget(self._alias_field)

        show_path_btn = QPushButton("Show Folder Path")
        show_path_btn.clicked.connect(self._show_folder_path)
        alias_layout.addWidget(show_path_btn)

        layout.addWidget(alias_group)

        backend_group = QGroupBox("Backends")
        backend_layout = QVBoxLayout(backend_group)

        for plugin_id, plugin_name, _ in self._send_plugins:
            check = QCheckBox(plugin_name)
            check.setChecked(self.data.get(f"process_backend_{plugin_id}", False))
            check.toggled.connect(self._on_backend_state_change)
            backend_layout.addWidget(check)
            self._backend_checks[plugin_id] = check

        layout.addWidget(backend_group)

        layout.addStretch(1)
        return tab

    def _build_edi_tab(self) -> QWidget:
        """Build the EDI processing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # EDI options
        self._force_edi_check = QCheckBox("Force EDI Validation")
        self._force_edi_check.setChecked(self.data.get("force_edi_validation", False))
        layout.addWidget(self._force_edi_check)

        # Split EDI
        self._split_edi_check = QCheckBox("Split EDI Documents")
        self._split_edi_check.setChecked(self.data.get("split_edi", False))
        layout.addWidget(self._split_edi_check)

        self._split_invoices_check = QCheckBox("Include Invoices in Split")
        self._split_invoices_check.setChecked(
            self.data.get("split_edi_include_invoices", False)
        )
        layout.addWidget(self._split_invoices_check)

        self._split_credits_check = QCheckBox("Include Credits in Split")
        self._split_credits_check.setChecked(
            self.data.get("split_edi_include_credits", False)
        )
        layout.addWidget(self._split_credits_check)

        # Prepend dates
        self._prepend_dates_check = QCheckBox("Prepend Dates to Files")
        self._prepend_dates_check.setChecked(self.data.get("prepend_date_files", False))
        layout.addWidget(self._prepend_dates_check)

        # Rename file
        rename_layout = QHBoxLayout()
        rename_layout.addWidget(QLabel("Rename File:"))
        self._rename_field = QLineEdit()
        self._rename_field.setText(self.data.get("rename_file", ""))
        rename_layout.addWidget(self._rename_field)
        layout.addLayout(rename_layout)

        # EDI options menu
        edi_options_layout = QHBoxLayout()
        edi_options_layout.addWidget(QLabel("EDI Options:"))
        self._edi_options_combo = QComboBox()
        self._edi_options_combo.addItems(["Do Nothing", "Convert EDI", "Tweak EDI"])
        # Handle both native bool and legacy string "True"/"False"
        process_edi = self.data.get("process_edi", False)
        if isinstance(process_edi, str):
            process_edi = process_edi == "True"
        self._edi_options_combo.setCurrentText(
            "Convert EDI"
            if process_edi
            else "Tweak EDI"
            if self.data.get("tweak_edi")
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
        # Handle both native bool and legacy string "True"/"False"
        process_edi = self.data.get("process_edi", False)
        if isinstance(process_edi, str):
            process_edi = process_edi == "True"
        self._process_edi_check.setChecked(process_edi)
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
        self._edi_format_combo.setCurrentText(self.data.get("edi_format", "default"))
        edi_format_layout.addWidget(self._edi_format_combo)
        layout.addLayout(edi_format_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Convert To:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(self.CONVERT_FORMATS)
        self._format_combo.setCurrentText(self.data.get("convert_to_format", "csv"))
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self._format_combo)
        layout.addLayout(format_layout)

        # Format-specific options
        self._format_options_stack = QStackedWidget()
        self._format_options_stack.addWidget(self._build_csv_options())
        self._format_options_stack.addWidget(
            self._build_edi_tweaks_options()
        )  # EDI Tweaks
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
        self._tweak_edi_check.setChecked(self.data.get("tweak_edi", False))
        layout.addWidget(self._tweak_edi_check)

        layout.addStretch(1)
        return tab

    def _build_csv_options(self) -> QWidget:
        """Build CSV format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._upc_check = QCheckBox("Calculate UPC Check Digit")
        # Handle both native bool and legacy string "True"/"False"
        upc_check = self.data.get("calculate_upc_check_digit", False)
        if isinstance(upc_check, str):
            upc_check = upc_check == "True"
        self._upc_check.setChecked(upc_check)
        layout.addWidget(self._upc_check)

        self._a_records_check = QCheckBox("Include A Records")
        # Handle both native bool and legacy string "True"/"False"
        a_records = self.data.get("include_a_records", False)
        if isinstance(a_records, str):
            a_records = a_records == "True"
        self._a_records_check.setChecked(a_records)
        layout.addWidget(self._a_records_check)

        self._c_records_check = QCheckBox("Include C Records")
        # Handle both native bool and legacy string "True"/"False"
        c_records = self.data.get("include_c_records", False)
        if isinstance(c_records, str):
            c_records = c_records == "True"
        self._c_records_check.setChecked(c_records)
        layout.addWidget(self._c_records_check)

        self._headers_check = QCheckBox("Include Headings")
        # Handle both native bool and legacy string "True"/"False"
        headers = self.data.get("include_headers", False)
        if isinstance(headers, str):
            headers = headers == "True"
        self._headers_check.setChecked(headers)
        layout.addWidget(self._headers_check)

        return widget

    def _build_scannerware_options(self) -> QWidget:
        """Build ScannerWare format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._pad_a_records_check = QCheckBox('Pad "A" Records')
        # Handle both native bool and legacy string "True"/"False"
        pad_a = self.data.get("pad_a_records", False)
        if isinstance(pad_a, str):
            pad_a = pad_a == "True"
        self._pad_a_records_check.setChecked(pad_a)
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
            str(self.folder_data.get("estore_store_number", ""))
        )
        layout.addWidget(self._estore_store_field, row, 1)

        row += 1
        layout.addWidget(QLabel("Vendor OId:"), row, 0)
        self._estore_vendor_oid_field = QLineEdit()
        self._estore_vendor_oid_field.setText(
            str(self.folder_data.get("estore_Vendor_OId", ""))
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
            str(self.folder_data.get("estore_store_number", ""))
        )
        layout.addWidget(self._estore_generic_store_field, row, 1)

        row += 1
        layout.addWidget(QLabel("Vendor OId:"), row, 0)
        self._estore_generic_vendor_oid_field = QLineEdit()
        self._estore_generic_vendor_oid_field.setText(
            str(self.folder_data.get("estore_Vendor_OId", ""))
        )
        layout.addWidget(self._estore_generic_vendor_oid_field, row, 1)

        row += 1
        layout.addWidget(QLabel("C Record OId:"), row, 0)
        self._estore_generic_c_oid_field = QLineEdit()
        self._estore_generic_c_oid_field.setText(
            str(self.folder_data.get("estore_c_record_OID", ""))
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
            str(self.folder_data.get("fintech_division_id", ""))
        )
        layout.addWidget(self._fintech_division_field)

        return widget

    def _build_edi_tweaks_options(self) -> QWidget:
        """Build EDI Tweaks format options."""
        # Import here to avoid circular imports
        from interface.ui.plugin_ui_generator import PluginUIGenerator
        from plugin_config import PluginRegistry

        # Get the EDI tweaks plugin
        plugin_class = PluginRegistry.get_convert_plugin("edi_tweaks")
        if plugin_class:
            # Get the configuration fields for the plugin
            config_fields = plugin_class.get_config_fields()
            # Create widget with current values
            current_values = {
                k: v
                for k, v in self.data.items()
                if k in [field.key for field in config_fields]
            }
            widget, self._edi_tweaks_value_getters = (
                PluginUIGenerator.create_plugin_config_widget(
                    config_fields, parent=self, current_values=current_values
                )
            )
            return widget
        else:
            # Fallback to default options if plugin not found
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(QLabel("EDI Tweaks plugin not found"))
            return widget

    def _build_default_options(self) -> QWidget:
        """Build default/empty format options."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("No format-specific options"))
        return widget

    def _set_dialog_values(self) -> None:
        """Load initial folder data into UI widgets (BaseDialog lifecycle hook)."""
        if self.data:
            self._alias_field.setText(self.data.get("alias", ""))

    def _show_folder_path(self) -> None:
        """Show the folder path in a message box."""
        path = self.data.get("folder_name", "")
        QMessageBox.information(self, "Folder Path", path)

    def _on_backend_state_change(self) -> None:
        """Handle backend state changes - enable/disable tabs based on selection."""
        for plugin_id, tab in self._backend_tabs.items():
            check = self._backend_checks.get(plugin_id)
            if check and tab:
                tab.setEnabled(check.isChecked())

    def _on_edi_option_changed(self, text: str) -> None:
        """Handle EDI option selection change."""
        pass

    def _on_format_changed(self, text: str) -> None:
        """Handle format selection change."""
        format_index_map = {
            "csv": 0,
            "EDI Tweaks": 1,
            "ScannerWare": 2,
            "simplified_csv": 3,
            "Estore eInvoice": 4,
            "Estore eInvoice Generic": 5,
            "fintech": 6,
            "jolley_custom": 7,
            "stewarts_custom": 8,
            "scansheet-type-a": 9,
            "YellowDog CSV": 10,
        }
        index = format_index_map.get(text, 0)
        self._format_options_stack.setCurrentIndex(index)

    def validate(self) -> Tuple[bool, str]:
        """Validate dialog input using plugin validation.

        Returns:
            (is_valid, error_message) tuple
        """
        errors = []

        backend_count = sum(
            1 for check in self._backend_checks.values() if check.isChecked()
        )

        if backend_count == 0 and self._active_check.isChecked():
            errors.append("No backend is selected")

        for plugin_id, check in self._backend_checks.items():
            if check.isChecked():
                plugin_class = PluginRegistry.get_send_plugin(plugin_id)
                if plugin_class:
                    value_getters = self._backend_value_getters.get(plugin_id, {})
                    config = PluginUIGenerator.get_config_values(value_getters)
                    is_valid, plugin_errors = plugin_class.validate_config(config)
                    errors.extend(plugin_errors)

        if errors:
            return (False, "\n".join(errors))

        return (True, "")

    def apply(self) -> None:
        """Write UI state back to self.data (BaseDialog lifecycle hook)."""
        self.data["folder_is_active"] = self._active_check.isChecked()
        self.data["alias"] = self._alias_field.text() or os.path.basename(
            self.data.get("folder_name", "")
        )

        for plugin_id, check in self._backend_checks.items():
            self.data[f"process_backend_{plugin_id}"] = check.isChecked()

        for plugin_id, value_getters in self._backend_value_getters.items():
            config = PluginUIGenerator.get_config_values(value_getters)
            self.data.update(config)

        self.data["force_edi_validation"] = self._force_edi_check.isChecked()
        self.data["process_edi"] = self._process_edi_check.isChecked()
        self.data["edi_format"] = self._edi_format_combo.currentText()
        self.data["tweak_edi"] = self._tweak_edi_check.isChecked()
        self.data["split_edi"] = self._split_edi_check.isChecked()
        self.data["split_edi_include_invoices"] = self._split_invoices_check.isChecked()
        self.data["split_edi_include_credits"] = self._split_credits_check.isChecked()
        self.data["prepend_date_files"] = self._prepend_dates_check.isChecked()
        self.data["rename_file"] = self._rename_field.text()

        self.data["convert_to_format"] = self._format_combo.currentText()

        # CSV options
        self.data["calculate_upc_check_digit"] = self._upc_check.isChecked()
        self.data["include_a_records"] = self._a_records_check.isChecked()
        self.data["include_c_records"] = self._c_records_check.isChecked()
        self.data["include_headers"] = self._headers_check.isChecked()

        # EDI Tweaks options - only save if the current format is EDI Tweaks
        if self._format_combo.currentText() == "EDI Tweaks" and hasattr(
            self, "_edi_tweaks_value_getters"
        ):
            edi_tweaks_config = PluginUIGenerator.get_config_values(
                self._edi_tweaks_value_getters
            )
            self.data.update(edi_tweaks_config)

        # ScannerWare options
        self.data["pad_a_records"] = self._pad_a_records_check.isChecked()

        # Simplified CSV options
        self.data["include_item_numbers"] = self._item_numbers_check.isChecked()
        self.data["include_item_description"] = self._item_description_check.isChecked()

        # Estore options
        self.data["estore_store_number"] = self._estore_store_field.text()
        self.data["estore_Vendor_OId"] = self._estore_vendor_oid_field.text()

        # Estore Generic options
        self.data["estore_store_number"] = self._estore_generic_store_field.text()
        self.data["estore_Vendor_OId"] = self._estore_generic_vendor_oid_field.text()
        self.data["estore_c_record_OID"] = self._estore_generic_c_oid_field.text()

        # Fintech options
        self.data["fintech_division_id"] = self._fintech_division_field.text()
