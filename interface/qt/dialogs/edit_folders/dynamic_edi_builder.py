"""Dynamic EDI Builder for Qt Edit Folders Dialog.

Handles the construction and management of dynamic EDI configuration sections
that appear based on user selections in the EDI options dropdown.
"""

from typing import Dict, Optional, Callable, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QGroupBox,
    QSpinBox,
)

from interface.plugins.plugin_manager import PluginManager
from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.models.folder_configuration import ConvertFormat
from interface.form.form_generator import FormGeneratorFactory


class DynamicEDIBuilder:
    """Builder class for dynamic EDI configuration sections.

    Manages the creation, display, and removal of dynamic EDI configuration
    sections based on user selections.
    """

    EDI_OPTIONS = ["Do Nothing", "Convert EDI", "Tweak EDI"]

    def __init__(
        self,
        fields: Dict[str, Any],
        folder_config: Dict[str, Any],
        dynamic_container: QWidget,
        dynamic_layout: QVBoxLayout,
        on_convert_format_changed: Optional[Callable[[str], None]] = None,
    ):
        """Initialize the dynamic EDI builder.

        Args:
            fields: Dictionary to store widget references
            folder_config: Current folder configuration
            dynamic_container: Container widget for dynamic content
            dynamic_layout: Layout to manage dynamic content
            on_convert_format_changed: Callback for convert format changes
        """
        self.fields = fields
        self.folder_config = folder_config
        self.dynamic_container = dynamic_container
        self.dynamic_layout = dynamic_layout
        self.on_convert_format_changed = on_convert_format_changed

        # Initialize plugin manager
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()

        # Get all configuration plugins
        self.configuration_plugins = self.plugin_manager.get_configuration_plugins()

        # Widget references
        self.edi_options_combo = None
        self.convert_format_combo = None
        self.convert_sub_container = None
        self.convert_sub_layout = None

        # Form generator for plugin configurations
        self.form_generator = None

        # Tweak EDI widgets
        self.tweak_upc_check = None
        self.tweak_pad_arec_check = None
        self.tweak_arec_padding_field = None
        self.tweak_arec_padding_length = None
        self.tweak_append_arec_check = None
        self.tweak_arec_append_field = None
        self.tweak_force_txt_check = None
        self.tweak_invoice_offset = None
        self.tweak_custom_date_check = None
        self.tweak_custom_date_field = None
        self.tweak_retail_uom_check = None
        self.tweak_override_upc_check = None
        self.tweak_override_upc_level = None
        self.tweak_override_upc_cat_filter = None
        self.tweak_upc_target_length = None
        self.tweak_upc_padding_pattern = None
        self.tweak_split_sales_tax_check = None

    def _get_convert_formats(self):
        """Get all available convert formats from configuration plugins."""
        formats = []
        for plugin in self.configuration_plugins:
            formats.append(plugin.get_format_name())
        # Add remaining hardcoded formats that don't have plugins yet
        hardcoded_formats = [
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
        for fmt in hardcoded_formats:
            if fmt not in formats:
                formats.append(fmt)
        return sorted(formats)

    def build_edi_options_combo(self) -> QComboBox:
        """Build and configure the EDI options dropdown."""
        self.edi_options_combo = QComboBox()
        self.edi_options_combo.addItems(self.EDI_OPTIONS)
        self.edi_options_combo.currentTextChanged.connect(self._on_edi_option_changed)
        return self.edi_options_combo

    def _clear_dynamic_edi(self):
        """Clear all widgets from the dynamic EDI container."""
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
                # Also remove any nested layouts
                sub_layout = item.layout()
                if sub_layout:
                    sub_layout.deleteLater()

    def _on_edi_option_changed(self, option: str):
        """Handle EDI option selection changes."""
        self._clear_dynamic_edi()
        if option == "Do Nothing":
            self._build_do_nothing_area()
        elif option == "Convert EDI":
            self._build_convert_edi_area()
        elif option == "Tweak EDI":
            self._build_tweak_edi_area()

    def _make_hidden_check(self, value: bool) -> QCheckBox:
        """Create a hidden checkbox for internal state tracking."""
        check = QCheckBox()
        check.setChecked(value)
        check.setVisible(False)
        return check

    def _build_do_nothing_area(self):
        """Build the 'Do Nothing' EDI configuration section."""
        self.fields["process_edi"] = self._make_hidden_check(False)
        self.fields["tweak_edi"] = self._make_hidden_check(False)
        label = QLabel("Send As Is")
        self.dynamic_layout.addWidget(label)

    def _build_convert_edi_area(self):
        """Build the 'Convert EDI' configuration section."""
        self.fields["process_edi"] = self._make_hidden_check(True)
        self.fields["tweak_edi"] = self._make_hidden_check(False)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Convert To:"))
        self.convert_format_combo = QComboBox()
        self.convert_format_combo.addItems(self._get_convert_formats())
        self.fields["convert_formats_var"] = self.convert_format_combo
        fmt_row.addWidget(self.convert_format_combo)
        wrapper_layout.addLayout(fmt_row)

        self.convert_sub_container = QWidget()
        self.convert_sub_layout = QVBoxLayout(self.convert_sub_container)
        self.convert_sub_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.convert_sub_container)

        if self.on_convert_format_changed:
            self.convert_format_combo.currentTextChanged.connect(
                self.on_convert_format_changed
            )

        current_fmt = self.folder_config.get("convert_to_format", "csv")
        idx = self.convert_format_combo.findText(current_fmt)
        if idx >= 0:
            self.convert_format_combo.setCurrentIndex(idx)
        if self.on_convert_format_changed:
            self.on_convert_format_changed(self.convert_format_combo.currentText())

        self.dynamic_layout.addWidget(wrapper)

    def _build_tweak_edi_area(self):
        """Build the 'Tweak EDI' configuration section."""
        self.fields["process_edi"] = self._make_hidden_check(False)
        self.fields["tweak_edi"] = self._make_hidden_check(True)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self.tweak_upc_check = QCheckBox("Calculate UPC Check Digit")
        self.fields["upc_var_check"] = self.tweak_upc_check
        wrapper_layout.addWidget(self.tweak_upc_check)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)

        self.tweak_pad_arec_check = QCheckBox('Pad "A" Records')
        self.fields["pad_arec_check"] = self.tweak_pad_arec_check
        arec_layout.addWidget(self.tweak_pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        self.tweak_arec_padding_field = QLineEdit()
        self.tweak_arec_padding_field.setMaximumWidth(100)
        self.fields["a_record_padding_field"] = self.tweak_arec_padding_field
        pad_row.addWidget(self.tweak_arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        self.tweak_arec_padding_length = QComboBox()
        self.tweak_arec_padding_length.addItems(["6", "30"])
        self.fields["a_record_padding_length"] = self.tweak_arec_padding_length
        pad_row.addWidget(self.tweak_arec_padding_length)
        arec_layout.addLayout(pad_row)

        self.tweak_append_arec_check = QCheckBox(
            'Append to "A" Records (6 Characters) (Series2K)'
        )
        self.fields["append_arec_check"] = self.tweak_append_arec_check
        arec_layout.addWidget(self.tweak_append_arec_check)

        append_row = QHBoxLayout()
        append_row.addWidget(QLabel("Append Text:"))
        self.tweak_arec_append_field = QLineEdit()
        self.tweak_arec_append_field.setMaximumWidth(100)
        self.fields["a_record_append_field"] = self.tweak_arec_append_field
        append_row.addWidget(self.tweak_arec_append_field)
        arec_layout.addLayout(append_row)

        wrapper_layout.addWidget(arec_group)

        self.tweak_force_txt_check = QCheckBox("Force .txt file extension")
        self.fields["force_txt_file_ext_check"] = self.tweak_force_txt_check
        wrapper_layout.addWidget(self.tweak_force_txt_check)

        offset_row = QHBoxLayout()
        offset_row.addWidget(QLabel("Invoice Offset (Days):"))
        self.tweak_invoice_offset = QSpinBox()
        self.tweak_invoice_offset.setRange(-14, 14)
        self.fields["invoice_date_offset"] = self.tweak_invoice_offset
        offset_row.addWidget(self.tweak_invoice_offset)
        wrapper_layout.addLayout(offset_row)

        custom_date_row = QHBoxLayout()
        self.tweak_custom_date_check = QCheckBox("Custom Invoice Date Format")
        self.fields["invoice_date_custom_format"] = self.tweak_custom_date_check
        custom_date_row.addWidget(self.tweak_custom_date_check)
        self.tweak_custom_date_field = QLineEdit()
        self.tweak_custom_date_field.setMaximumWidth(100)
        self.fields["invoice_date_custom_format_field"] = self.tweak_custom_date_field
        custom_date_row.addWidget(self.tweak_custom_date_field)
        wrapper_layout.addLayout(custom_date_row)

        self.tweak_retail_uom_check = QCheckBox("Each UOM")
        self.fields["edi_each_uom_tweak"] = self.tweak_retail_uom_check
        wrapper_layout.addWidget(self.tweak_retail_uom_check)

        upc_override_group = QGroupBox("Override UPC")
        upc_layout = QVBoxLayout(upc_override_group)

        self.tweak_override_upc_check = QCheckBox("Override UPC")
        self.fields["override_upc_bool"] = self.tweak_override_upc_check
        upc_layout.addWidget(self.tweak_override_upc_check)

        upc_row1 = QHBoxLayout()
        upc_row1.addWidget(QLabel("Level:"))
        self.tweak_override_upc_level = QComboBox()
        self.tweak_override_upc_level.addItems(["1", "2", "3", "4"])
        self.fields["override_upc_level"] = self.tweak_override_upc_level
        upc_row1.addWidget(self.tweak_override_upc_level)

        upc_row1.addWidget(QLabel("Category Filter:"))
        self.tweak_override_upc_cat_filter = QLineEdit()
        self.tweak_override_upc_cat_filter.setMaximumWidth(100)
        self.tweak_override_upc_cat_filter.setToolTip(
            "Enter 'ALL' or a comma separated list of numbers"
        )
        self.fields["override_upc_category_filter_entry"] = (
            self.tweak_override_upc_cat_filter
        )
        upc_row1.addWidget(self.tweak_override_upc_cat_filter)
        upc_layout.addLayout(upc_row1)

        upc_row2 = QHBoxLayout()
        upc_row2.addWidget(QLabel("UPC Target Length:"))
        self.tweak_upc_target_length = QLineEdit()
        self.tweak_upc_target_length.setMaximumWidth(50)
        self.fields["upc_target_length_entry"] = self.tweak_upc_target_length
        upc_row2.addWidget(self.tweak_upc_target_length)
        upc_layout.addLayout(upc_row2)

        upc_row3 = QHBoxLayout()
        upc_row3.addWidget(QLabel("UPC Padding Pattern:"))
        self.tweak_upc_padding_pattern = QLineEdit()
        self.tweak_upc_padding_pattern.setMaximumWidth(120)
        self.fields["upc_padding_pattern_entry"] = self.tweak_upc_padding_pattern
        upc_row3.addWidget(self.tweak_upc_padding_pattern)
        upc_layout.addLayout(upc_row3)

        wrapper_layout.addWidget(upc_override_group)

        self.tweak_split_sales_tax_check = QCheckBox("Split Sales Tax 'C' Records")
        self.fields["split_sales_tax_prepaid_var"] = self.tweak_split_sales_tax_check
        wrapper_layout.addWidget(self.tweak_split_sales_tax_check)

        self._populate_tweak_fields()

        self.dynamic_layout.addWidget(wrapper)

    def _populate_tweak_fields(self):
        """Populate the tweak EDI fields with values from folder config."""
        cfg = self.folder_config
        if self.tweak_upc_check:
            self.tweak_upc_check.setChecked(
                str(cfg.get("calculate_upc_check_digit", "False")) == "True"
            )
        if self.tweak_pad_arec_check:
            self.tweak_pad_arec_check.setChecked(
                str(cfg.get("pad_a_records", "False")) == "True"
            )
        if self.tweak_arec_padding_field:
            self.tweak_arec_padding_field.setText(str(cfg.get("a_record_padding", "")))
        if self.tweak_arec_padding_length:
            pad_len = str(cfg.get("a_record_padding_length", 6))
            idx = self.tweak_arec_padding_length.findText(pad_len)
            if idx >= 0:
                self.tweak_arec_padding_length.setCurrentIndex(idx)
        if self.tweak_append_arec_check:
            self.tweak_append_arec_check.setChecked(
                str(cfg.get("append_a_records", "False")) == "True"
            )
        if self.tweak_arec_append_field:
            self.tweak_arec_append_field.setText(str(cfg.get("a_record_append_text", "")))
        if self.tweak_force_txt_check:
            self.tweak_force_txt_check.setChecked(
                str(cfg.get("force_txt_file_ext", "False")) == "True"
            )
        if self.tweak_invoice_offset:
            self.tweak_invoice_offset.setValue(int(cfg.get("invoice_date_offset", 0)))
        if self.tweak_custom_date_check:
            self.tweak_custom_date_check.setChecked(
                bool(cfg.get("invoice_date_custom_format", False))
            )
        if self.tweak_custom_date_field:
            self.tweak_custom_date_field.setText(
                str(cfg.get("invoice_date_custom_format_string", ""))
            )
        if self.tweak_retail_uom_check:
            self.tweak_retail_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        if self.tweak_override_upc_check:
            self.tweak_override_upc_check.setChecked(
                bool(cfg.get("override_upc_bool", False))
            )
        if self.tweak_override_upc_level:
            lvl = str(cfg.get("override_upc_level", 1))
            idx = self.tweak_override_upc_level.findText(lvl)
            if idx >= 0:
                self.tweak_override_upc_level.setCurrentIndex(idx)
        if self.tweak_override_upc_cat_filter:
            self.tweak_override_upc_cat_filter.setText(
                str(cfg.get("override_upc_category_filter", ""))
            )
        if self.tweak_upc_target_length:
            self.tweak_upc_target_length.setText(str(cfg.get("upc_target_length", 11)))
        if self.tweak_upc_padding_pattern:
            self.tweak_upc_padding_pattern.setText(
                str(cfg.get("upc_padding_pattern", "           "))
            )
        if self.tweak_split_sales_tax_check:
            self.tweak_split_sales_tax_check.setChecked(
                bool(cfg.get("split_prepaid_sales_tax_crec", False))
            )

    def clear_convert_sub(self):
        """Clear all widgets from the convert sub-container."""
        if self.convert_sub_layout:
            while self.convert_sub_layout.count():
                item = self.convert_sub_layout.takeAt(0)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)
                        widget.deleteLater()
                    # Also remove any nested layouts
                    sub_layout = item.layout()
                    if sub_layout:
                        sub_layout.deleteLater()

    def handle_convert_format_changed(self, fmt: str):
        """Handle convert format selection changes."""
        self.clear_convert_sub()
        
        # Try to find a configuration plugin for this format
        plugin = self.plugin_manager.get_configuration_plugin_by_format_name(fmt)
        if plugin:
            self._build_plugin_config_sub(plugin)
        else:
            # Fall back to hardcoded implementations for formats without plugins
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
    
    def _build_plugin_config_sub(self, plugin: ConfigurationPlugin):
        """Build plugin configuration sub-section."""
        # Get plugin configuration schema
        schema = plugin.get_configuration_schema()
        if schema:
            # Create form generator
            form_generator = FormGeneratorFactory.create_form_generator(schema, 'qt')
            
            # Get existing plugin configuration from folder config
            plugin_config = self.folder_config.get('plugin_configurations', {}).get(plugin.get_format_name().lower(), {})
            
            # Build the form
            form_widget = form_generator.build_form(plugin_config, self.convert_sub_container)
            
            # Store widget reference and form generator
            plugin_key = f"plugin_config_{plugin.get_identifier()}"
            self.fields[plugin_key] = form_widget
            self.fields[f"{plugin_key}_generator"] = form_generator
            
            # Add to layout
            self.convert_sub_layout.addWidget(form_widget)

    # ------------------------------------------------------------------
    # Convert format sub-widget builders
    # ------------------------------------------------------------------
    def _build_csv_sub(self):
        """Build CSV conversion settings sub-section."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        include_items_check = QCheckBox("Include Item Numbers")
        self.fields["include_item_numbers"] = include_items_check
        wrapper_layout.addWidget(include_items_check)

        include_desc_check = QCheckBox("Include Item Descriptions")
        self.fields["include_item_description"] = include_desc_check
        wrapper_layout.addWidget(include_desc_check)

        # TODO: Add any additional CSV-specific settings

        self.convert_sub_layout.addWidget(wrapper)

    def _build_scannerware_sub(self):
        """Build ScannerWare conversion settings sub-section."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        # ScannerWare specific settings
        self._build_basic_options_sub()

        self.convert_sub_layout.addWidget(wrapper)

    def _build_simplified_csv_sub(self):
        """Build Simplified CSV conversion settings sub-section."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        # Simplified CSV specific settings
        sort_order_row = QHBoxLayout()
        sort_order_row.addWidget(QLabel("Column Sort Order:"))
        sort_order_field = QLineEdit()
        sort_order_field.setMaximumWidth(200)
        self.fields["simple_csv_column_sorter"] = sort_order_field
        sort_order_row.addWidget(sort_order_field)
        wrapper_layout.addLayout(sort_order_row)

        self.convert_sub_layout.addWidget(wrapper)

    def _build_estore_sub(self, fmt: str):
        """Build Estore eInvoice conversion settings sub-section."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        store_number_row = QHBoxLayout()
        store_number_row.addWidget(QLabel("Store Number:"))
        store_number_field = QLineEdit()
        store_number_field.setMaximumWidth(100)
        self.fields["estore_store_number_field"] = store_number_field
        store_number_row.addWidget(store_number_field)
        wrapper_layout.addLayout(store_number_row)

        vendor_oid_row = QHBoxLayout()
        vendor_oid_row.addWidget(QLabel("Vendor OID:"))
        vendor_oid_field = QLineEdit()
        vendor_oid_field.setMaximumWidth(100)
        self.fields["estore_Vendor_OId_field"] = vendor_oid_field
        vendor_oid_row.addWidget(vendor_oid_field)
        wrapper_layout.addLayout(vendor_oid_row)

        vendor_name_row = QHBoxLayout()
        vendor_name_row.addWidget(QLabel("Vendor Name/OID:"))
        vendor_name_field = QLineEdit()
        vendor_name_field.setMaximumWidth(100)
        self.fields["estore_vendor_namevendoroid_field"] = vendor_name_field
        vendor_name_row.addWidget(vendor_name_field)
        wrapper_layout.addLayout(vendor_name_row)

        self.convert_sub_layout.addWidget(wrapper)

    def _build_fintech_sub(self):
        """Build FinTech conversion settings sub-section."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        division_id_row = QHBoxLayout()
        division_id_row.addWidget(QLabel("Division ID:"))
        division_id_field = QLineEdit()
        division_id_field.setMaximumWidth(100)
        self.fields["fintech_divisionid_field"] = division_id_field
        division_id_row.addWidget(division_id_field)
        wrapper_layout.addLayout(division_id_row)

        self.convert_sub_layout.addWidget(wrapper)

    def _build_basic_options_sub(self):
        """Build basic conversion options sub-section."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        # Basic options shared by multiple formats
        self._build_common_conversion_options(wrapper_layout)

        self.convert_sub_layout.addWidget(wrapper)

    def _build_common_conversion_options(self, layout: QVBoxLayout):
        """Build common conversion options for multiple formats."""
        # Add common conversion settings here
        pass
