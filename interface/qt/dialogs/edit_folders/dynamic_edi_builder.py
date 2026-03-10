"""Dynamic EDI Builder for Qt Edit Folders Dialog.

Handles the construction and management of dynamic EDI configuration sections
that appear based on user selections in the EDI options dropdown.
"""

import logging
from typing import Dict, Optional, Callable, Any, List

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
    QFormLayout,
)
from PyQt6 import QtCore

from interface.plugins.plugin_manager import PluginManager
from interface.plugins.configuration_plugin import ConfigurationPlugin
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

        # State tracking
        self._edi_option_processing = False

    def _get_convert_formats(self) -> List[str]:
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
        """Clear dynamic EDI widgets and clean up field references."""
        logging.debug("Clearing dynamic EDI widgets")
        try:
            keys_to_remove = []

            # Store items to remove in a list to avoid modifying the layout during iteration
            items_to_remove = []
            for i in range(self.dynamic_layout.count()):
                items_to_remove.append(self.dynamic_layout.takeAt(0))

            # Process the removal of each item
            for item in items_to_remove:
                if item:
                    widget = item.widget()
                    if widget:
                        self._find_and_track_widget_keys(widget, keys_to_remove)
                        if widget and not widget.testAttribute(
                            QtCore.Qt.WidgetAttribute.WA_DeleteOnClose
                        ):
                            widget.setParent(None)
                            widget.deleteLater()

                    sub_layout = item.layout()
                    if sub_layout:
                        self._find_and_track_layout_keys(sub_layout, keys_to_remove)
                        sub_layout.deleteLater()

            # Remove all tracked keys from fields immediately
            for key in keys_to_remove:
                if key in self.fields:
                    del self.fields[key]

        except Exception as e:
            logging.error(f"Error in _clear_dynamic_edi: {e}")

    def _find_and_track_widget_keys(self, widget, keys_to_remove):
        """Recursively find all descendant widgets and track their field keys."""
        for key, value in list(self.fields.items()):
            if value is widget:
                if key not in keys_to_remove:
                    keys_to_remove.append(key)
                break

        for child in widget.findChildren(QWidget):
            for key, value in list(self.fields.items()):
                if value is child:
                    if key not in keys_to_remove:
                        keys_to_remove.append(key)
                    break

    def _find_and_track_layout_keys(self, layout, keys_to_remove):
        """Find all widgets in a layout and track their field keys."""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    for key, value in list(self.fields.items()):
                        if value is widget:
                            if key not in keys_to_remove:
                                keys_to_remove.append(key)
                            break
                    for child in widget.findChildren(QWidget):
                        for key, value in list(self.fields.items()):
                            if value is child:
                                if key not in keys_to_remove:
                                    keys_to_remove.append(key)
                                break
                sub_layout = item.layout()
                if sub_layout:
                    self._find_and_track_layout_keys(sub_layout, keys_to_remove)

    def _on_edi_option_changed(self, option: str):
        """Handle EDI option selection changes."""
        if self._edi_option_processing:
            return

        self._edi_option_processing = True
        try:
            self._clear_dynamic_edi()
            if option == "Do Nothing":
                self._build_do_nothing_area()
            elif option == "Convert EDI":
                self._build_convert_edi_area()
            elif option == "Tweak EDI":
                self._build_tweak_edi_area()
        finally:
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(100, self._clear_edi_processing_flag)

    def _clear_edi_processing_flag(self):
        """Clear the EDI processing flag after a delay."""
        self._edi_option_processing = False

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

        self.convert_format_combo.currentTextChanged.connect(
            self.handle_convert_format_changed
        )

        current_fmt = self.folder_config.get("convert_to_format", "csv")
        idx = self.convert_format_combo.findText(current_fmt)
        if idx >= 0:
            self.convert_format_combo.setCurrentIndex(idx)
        self.handle_convert_format_changed(self.convert_format_combo.currentText())

        self.dynamic_layout.addWidget(wrapper)

    def handle_convert_format_changed(self, fmt: str):
        """Handle convert format selection changes."""
        self._clear_convert_sub()
        fmt_lower = (fmt or "").lower()

        if fmt_lower == "csv":
            self._build_csv_sub()
        elif fmt_lower == "scannerware":
            self._build_scannerware_sub()
        elif fmt_lower == "simplified_csv":
            self._build_simplified_csv_sub()
        elif fmt_lower in ("estore einvoice", "estore einvoice generic"):
            self._build_estore_sub(fmt)
        elif fmt_lower == "fintech":
            self._build_fintech_sub()
        elif fmt_lower == "scansheet-type-a":
            pass
        elif fmt_lower in ("jolley_custom", "stewarts_custom", "yellowdog csv"):
            self._build_basic_options_sub()
        else:
            plugin = self.plugin_manager.get_configuration_plugin_by_format_name(fmt)
            if plugin:
                self._build_plugin_config_sub(plugin)

        if self.on_convert_format_changed:
            self.on_convert_format_changed(fmt)

    def _clear_convert_sub(self):
        """Clear convert sub-widgets and clean up field references."""
        if not self.convert_sub_layout:
            return

        logging.debug("Clearing convert sub widgets")
        try:
            keys_to_remove = []
            items_to_remove = []
            for i in range(self.convert_sub_layout.count()):
                items_to_remove.append(self.convert_sub_layout.takeAt(0))

            for item in items_to_remove:
                if item:
                    widget = item.widget()
                    if widget:
                        self._find_and_track_widget_keys(widget, keys_to_remove)
                        if widget and not widget.testAttribute(
                            QtCore.Qt.WidgetAttribute.WA_DeleteOnClose
                        ):
                            widget.setParent(None)
                            widget.deleteLater()
                    sub_layout = item.layout()
                    if sub_layout:
                        self._find_and_track_layout_keys(sub_layout, keys_to_remove)
                        sub_layout.deleteLater()

            for key in keys_to_remove:
                if key in self.fields:
                    del self.fields[key]

        except Exception as e:
            logging.error(f"Error in _clear_convert_sub: {e}")

    def _build_plugin_config_sub(self, plugin: ConfigurationPlugin):
        """Build plugin configuration sub-section."""
        schema = plugin.get_configuration_schema()
        if schema:
            form_generator = FormGeneratorFactory.create_form_generator(schema, "qt")
            plugin_config = self.folder_config.get("plugin_configurations", {}).get(
                plugin.get_format_name().lower(), {}
            )
            form_widget = form_generator.build_form(
                plugin_config, self.convert_sub_container
            )

            plugin_key = f"plugin_config_{plugin.get_identifier()}"
            self.fields[plugin_key] = form_widget
            self.fields[f"{plugin_key}_generator"] = form_generator
            self.convert_sub_layout.addWidget(form_widget)

    def _build_csv_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        upc_check = QCheckBox("Calculate UPC Check Digit")
        self.fields["upc_var_check"] = upc_check
        layout.addWidget(upc_check)

        a_rec_check = QCheckBox("Include A Records")
        self.fields["a_rec_var_check"] = a_rec_check
        layout.addWidget(a_rec_check)

        c_rec_check = QCheckBox("Include C Records")
        self.fields["c_rec_var_check"] = c_rec_check
        layout.addWidget(c_rec_check)

        headers_check = QCheckBox("Include Headings")
        self.fields["headers_check"] = headers_check
        layout.addWidget(headers_check)

        ampersand_check = QCheckBox("Filter Ampersand")
        self.fields["ampersand_check"] = ampersand_check
        layout.addWidget(ampersand_check)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)
        pad_arec_check = QCheckBox('Pad "A" Records')
        self.fields["pad_arec_check"] = pad_arec_check
        arec_layout.addWidget(pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        arec_padding_field = QLineEdit()
        arec_padding_field.setMaximumWidth(100)
        self.fields["a_record_padding_field"] = arec_padding_field
        pad_row.addWidget(arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        arec_padding_length = QComboBox()
        arec_padding_length.addItems(["6", "30"])
        self.fields["a_record_padding_length"] = arec_padding_length
        pad_row.addWidget(arec_padding_length)
        arec_layout.addLayout(pad_row)
        layout.addWidget(arec_group)

        upc_group = QGroupBox("Override UPC")
        upc_layout = QVBoxLayout(upc_group)
        override_upc_check = QCheckBox("Override UPC")
        self.fields["override_upc_bool"] = override_upc_check
        upc_layout.addWidget(override_upc_check)

        upc_row1 = QHBoxLayout()
        upc_row1.addWidget(QLabel("Level:"))
        override_upc_level = QComboBox()
        override_upc_level.addItems(["1", "2", "3", "4"])
        self.fields["override_upc_level"] = override_upc_level
        upc_row1.addWidget(override_upc_level)
        upc_row1.addWidget(QLabel("Category Filter:"))
        override_upc_cat_filter = QLineEdit()
        override_upc_cat_filter.setMaximumWidth(100)
        self.fields["override_upc_category_filter_entry"] = override_upc_cat_filter
        upc_row1.addWidget(override_upc_cat_filter)
        upc_layout.addLayout(upc_row1)

        upc_row2 = QHBoxLayout()
        upc_row2.addWidget(QLabel("UPC Target Length:"))
        upc_target_length = QLineEdit()
        upc_target_length.setMaximumWidth(50)
        self.fields["upc_target_length_entry"] = upc_target_length
        upc_row2.addWidget(upc_target_length)
        upc_layout.addLayout(upc_row2)

        upc_row3 = QHBoxLayout()
        upc_row3.addWidget(QLabel("UPC Padding Pattern:"))
        upc_padding_pattern = QLineEdit()
        upc_padding_pattern.setMaximumWidth(120)
        self.fields["upc_padding_pattern_entry"] = upc_padding_pattern
        upc_row3.addWidget(upc_padding_pattern)
        upc_layout.addLayout(upc_row3)
        layout.addWidget(upc_group)

        each_uom_check = QCheckBox("Each UOM")
        self.fields["edi_each_uom_tweak"] = each_uom_check
        layout.addWidget(each_uom_check)

        split_sales_tax_check = QCheckBox("Split Sales Tax 'C' Records")
        self.fields["split_sales_tax_prepaid_var"] = split_sales_tax_check
        layout.addWidget(split_sales_tax_check)

        include_item_numbers_check = QCheckBox("Include Item Numbers")
        self.fields["include_item_numbers"] = include_item_numbers_check
        layout.addWidget(include_item_numbers_check)

        include_item_desc_check = QCheckBox("Include Item Description")
        self.fields["include_item_description"] = include_item_desc_check
        layout.addWidget(include_item_desc_check)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("CSV Column Sort:"))
        column_sort_field = QLineEdit()
        self.fields["simple_csv_column_sorter"] = column_sort_field
        sort_row.addWidget(column_sort_field)
        layout.addLayout(sort_row)

        self._populate_csv_sub_fields(
            upc_check,
            a_rec_check,
            c_rec_check,
            headers_check,
            ampersand_check,
            pad_arec_check,
            arec_padding_field,
            arec_padding_length,
            override_upc_check,
            override_upc_level,
            override_upc_cat_filter,
            upc_target_length,
            upc_padding_pattern,
            each_uom_check,
            split_sales_tax_check,
            include_item_numbers_check,
            include_item_desc_check,
            column_sort_field,
        )
        self.convert_sub_layout.addWidget(wrapper)

    def _populate_csv_sub_fields(
        self,
        upc_check,
        a_rec_check,
        c_rec_check,
        headers_check,
        ampersand_check,
        pad_arec_check,
        arec_padding_field,
        arec_padding_length,
        override_upc_check,
        override_upc_level,
        override_upc_cat_filter,
        upc_target_length,
        upc_padding_pattern,
        each_uom_check,
        split_sales_tax_check,
        include_item_numbers_check,
        include_item_desc_check,
        column_sort_field,
    ):
        cfg = self.folder_config
        upc_check.setChecked(
            str(cfg.get("calculate_upc_check_digit", "False")) == "True"
        )
        a_rec_check.setChecked(str(cfg.get("include_a_records", "False")) == "True")
        c_rec_check.setChecked(str(cfg.get("include_c_records", "False")) == "True")
        headers_check.setChecked(str(cfg.get("include_headers", "False")) == "True")
        ampersand_check.setChecked(str(cfg.get("filter_ampersand", "False")) == "True")
        pad_arec_check.setChecked(str(cfg.get("pad_a_records", "False")) == "True")
        arec_padding_field.setText(str(cfg.get("a_record_padding", "")))

        pad_len = str(
            cfg.get("a_record_padding_length")
            if cfg.get("a_record_padding_length") is not None
            else 6
        )
        idx = arec_padding_length.findText(pad_len)
        if idx >= 0:
            arec_padding_length.setCurrentIndex(idx)

        override_upc_check.setChecked(bool(cfg.get("override_upc_bool", False)))

        lvl = str(
            cfg.get("override_upc_level")
            if cfg.get("override_upc_level") is not None
            else 1
        )
        idx = override_upc_level.findText(lvl)
        if idx >= 0:
            override_upc_level.setCurrentIndex(idx)

        override_upc_cat_filter.setText(
            str(cfg.get("override_upc_category_filter", ""))
        )
        upc_target_length.setText(
            str(
                cfg.get("upc_target_length")
                if cfg.get("upc_target_length") is not None
                else 11
            )
        )
        upc_padding_pattern.setText(str(cfg.get("upc_padding_pattern", "           ")))
        each_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        split_sales_tax_check.setChecked(
            bool(cfg.get("split_prepaid_sales_tax_crec", False))
        )
        include_item_numbers_check.setChecked(
            bool(cfg.get("include_item_numbers", False))
        )
        include_item_desc_check.setChecked(
            bool(cfg.get("include_item_description", False))
        )
        column_sort_field.setText(str(cfg.get("simple_csv_sort_order", "")))

    def _build_scannerware_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)
        pad_arec_check = QCheckBox('Pad "A" Records')
        self.fields["pad_arec_check"] = pad_arec_check
        arec_layout.addWidget(pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        arec_padding_field = QLineEdit()
        arec_padding_field.setMaximumWidth(100)
        self.fields["a_record_padding_field"] = arec_padding_field
        pad_row.addWidget(arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        arec_padding_length = QComboBox()
        arec_padding_length.addItems(["6", "30"])
        self.fields["a_record_padding_length"] = arec_padding_length
        pad_row.addWidget(arec_padding_length)
        arec_layout.addLayout(pad_row)

        append_arec_check = QCheckBox('Append to "A" Records (6 Characters) (Series2K)')
        self.fields["append_arec_check"] = append_arec_check
        arec_layout.addWidget(append_arec_check)

        append_row = QHBoxLayout()
        append_row.addWidget(QLabel("Append Text:"))
        arec_append_field = QLineEdit()
        arec_append_field.setMaximumWidth(100)
        self.fields["a_record_append_field"] = arec_append_field
        append_row.addWidget(arec_append_field)
        arec_layout.addLayout(append_row)
        layout.addWidget(arec_group)

        cfg = self.folder_config
        pad_arec_check.setChecked(str(cfg.get("pad_a_records", "False")) == "True")
        arec_padding_field.setText(str(cfg.get("a_record_padding", "")))
        pad_len = str(
            cfg.get("a_record_padding_length")
            if cfg.get("a_record_padding_length") is not None
            else 6
        )
        idx = arec_padding_length.findText(pad_len)
        if idx >= 0:
            arec_padding_length.setCurrentIndex(idx)
        append_arec_check.setChecked(
            str(cfg.get("append_a_records", "False")) == "True"
        )
        arec_append_field.setText(str(cfg.get("a_record_append_text", "")))

        self.convert_sub_layout.addWidget(wrapper)

    def _build_simplified_csv_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        headers_check = QCheckBox("Include Headings")
        self.fields["headers_check"] = headers_check
        layout.addWidget(headers_check)

        include_item_numbers_check = QCheckBox("Include Item Numbers")
        self.fields["include_item_numbers"] = include_item_numbers_check
        layout.addWidget(include_item_numbers_check)

        include_item_desc_check = QCheckBox("Include Item Description")
        self.fields["include_item_description"] = include_item_desc_check
        layout.addWidget(include_item_desc_check)

        each_uom_check = QCheckBox("Each UOM")
        self.fields["edi_each_uom_tweak"] = each_uom_check
        layout.addWidget(each_uom_check)

        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("CSV Column Sort:"))
        column_sort_field = QLineEdit()
        self.fields["simple_csv_column_sorter"] = column_sort_field
        sort_row.addWidget(column_sort_field)
        layout.addLayout(sort_row)

        cfg = self.folder_config
        headers_check.setChecked(str(cfg.get("include_headers", "False")) == "True")
        include_item_numbers_check.setChecked(
            bool(cfg.get("include_item_numbers", False))
        )
        include_item_desc_check.setChecked(
            bool(cfg.get("include_item_description", False))
        )
        each_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        column_sort_field.setText(str(cfg.get("simple_csv_sort_order", "")))

        self.convert_sub_layout.addWidget(wrapper)

    def _build_estore_sub(self, fmt: str):
        wrapper = QWidget()
        layout = QFormLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        estore_store_number_field = QLineEdit()
        self.fields["estore_store_number_field"] = estore_store_number_field
        layout.addRow("Estore Store Number:", estore_store_number_field)

        estore_vendor_oid_field = QLineEdit()
        self.fields["estore_Vendor_OId_field"] = estore_vendor_oid_field
        layout.addRow("Estore Vendor OId:", estore_vendor_oid_field)

        estore_vendor_name_field = QLineEdit()
        self.fields["estore_vendor_namevendoroid_field"] = estore_vendor_name_field
        layout.addRow("Estore Vendor Name OId:", estore_vendor_name_field)

        if fmt == "Estore eInvoice Generic":
            estore_c_record_oid_field = QLineEdit()
            self.fields["estore_c_record_oid_field"] = estore_c_record_oid_field
            layout.addRow("Estore C Record OId:", estore_c_record_oid_field)

        cfg = self.folder_config
        estore_store_number_field.setText(str(cfg.get("estore_store_number", "")))
        estore_vendor_oid_field.setText(str(cfg.get("estore_Vendor_OId", "")))
        estore_vendor_name_field.setText(
            str(cfg.get("estore_vendor_NameVendorOID", ""))
        )
        if fmt == "Estore eInvoice Generic":
            estore_c_record_oid_field.setText(str(cfg.get("estore_c_record_OID", "")))

        self.convert_sub_layout.addWidget(wrapper)

    def _build_fintech_sub(self):
        wrapper = QWidget()
        layout = QFormLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        fintech_division_field = QLineEdit()
        self.fields["fintech_divisionid_field"] = fintech_division_field
        layout.addRow("Fintech Division ID:", fintech_division_field)

        fintech_division_field.setText(
            str(self.folder_config.get("fintech_division_id", ""))
        )
        self.convert_sub_layout.addWidget(wrapper)

    def _build_basic_options_sub(self):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("No additional options for this format."))
        self.convert_sub_layout.addWidget(wrapper)

    def _build_tweak_edi_area(self):
        """Build the 'Tweak EDI' configuration section."""
        self.fields["process_edi"] = self._make_hidden_check(False)
        self.fields["tweak_edi"] = self._make_hidden_check(True)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        tweak_upc_check = QCheckBox("Calculate UPC Check Digit")
        self.fields["upc_var_check"] = tweak_upc_check
        wrapper_layout.addWidget(tweak_upc_check)

        arec_group = QGroupBox("A-Record Padding")
        arec_layout = QVBoxLayout(arec_group)
        tweak_pad_arec_check = QCheckBox('Pad "A" Records')
        self.fields["pad_arec_check"] = tweak_pad_arec_check
        arec_layout.addWidget(tweak_pad_arec_check)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding Text:"))
        tweak_arec_padding_field = QLineEdit()
        tweak_arec_padding_field.setMaximumWidth(100)
        self.fields["a_record_padding_field"] = tweak_arec_padding_field
        pad_row.addWidget(tweak_arec_padding_field)

        pad_row.addWidget(QLabel("Length:"))
        tweak_arec_padding_length = QComboBox()
        tweak_arec_padding_length.addItems(["6", "30"])
        self.fields["a_record_padding_length"] = tweak_arec_padding_length
        pad_row.addWidget(tweak_arec_padding_length)
        arec_layout.addLayout(pad_row)

        tweak_append_arec_check = QCheckBox(
            'Append to "A" Records (6 Characters) (Series2K)'
        )
        self.fields["append_arec_check"] = tweak_append_arec_check
        arec_layout.addWidget(tweak_append_arec_check)

        append_row = QHBoxLayout()
        append_row.addWidget(QLabel("Append Text:"))
        tweak_arec_append_field = QLineEdit()
        tweak_arec_append_field.setMaximumWidth(100)
        self.fields["a_record_append_field"] = tweak_arec_append_field
        append_row.addWidget(tweak_arec_append_field)
        arec_layout.addLayout(append_row)
        wrapper_layout.addWidget(arec_group)

        tweak_force_txt_check = QCheckBox("Force .txt file extension")
        self.fields["force_txt_file_ext_check"] = tweak_force_txt_check
        wrapper_layout.addWidget(tweak_force_txt_check)

        offset_row = QHBoxLayout()
        offset_row.addWidget(QLabel("Invoice Offset (Days):"))
        tweak_invoice_offset = QSpinBox()
        tweak_invoice_offset.setRange(-14, 14)
        self.fields["invoice_date_offset"] = tweak_invoice_offset
        offset_row.addWidget(tweak_invoice_offset)
        wrapper_layout.addLayout(offset_row)

        custom_date_row = QHBoxLayout()
        tweak_custom_date_check = QCheckBox("Custom Invoice Date Format")
        self.fields["invoice_date_custom_format"] = tweak_custom_date_check
        custom_date_row.addWidget(tweak_custom_date_check)
        tweak_custom_date_field = QLineEdit()
        tweak_custom_date_field.setMaximumWidth(100)
        self.fields["invoice_date_custom_format_field"] = tweak_custom_date_field
        custom_date_row.addWidget(tweak_custom_date_field)
        wrapper_layout.addLayout(custom_date_row)

        tweak_retail_uom_check = QCheckBox("Each UOM")
        self.fields["edi_each_uom_tweak"] = tweak_retail_uom_check
        wrapper_layout.addWidget(tweak_retail_uom_check)

        upc_override_group = QGroupBox("Override UPC")
        upc_layout = QVBoxLayout(upc_override_group)
        tweak_override_upc_check = QCheckBox("Override UPC")
        self.fields["override_upc_bool"] = tweak_override_upc_check
        upc_layout.addWidget(tweak_override_upc_check)

        upc_row1 = QHBoxLayout()
        upc_row1.addWidget(QLabel("Level:"))
        tweak_override_upc_level = QComboBox()
        tweak_override_upc_level.addItems(["1", "2", "3", "4"])
        self.fields["override_upc_level"] = tweak_override_upc_level
        upc_row1.addWidget(tweak_override_upc_level)
        upc_row1.addWidget(QLabel("Category Filter:"))
        tweak_override_upc_cat_filter = QLineEdit()
        tweak_override_upc_cat_filter.setMaximumWidth(100)
        self.fields["override_upc_category_filter_entry"] = (
            tweak_override_upc_cat_filter
        )
        upc_row1.addWidget(tweak_override_upc_cat_filter)
        upc_layout.addLayout(upc_row1)

        upc_row2 = QHBoxLayout()
        upc_row2.addWidget(QLabel("UPC Target Length:"))
        tweak_upc_target_length = QLineEdit()
        tweak_upc_target_length.setMaximumWidth(50)
        self.fields["upc_target_length_entry"] = tweak_upc_target_length
        upc_row2.addWidget(tweak_upc_target_length)
        upc_layout.addLayout(upc_row2)

        upc_row3 = QHBoxLayout()
        upc_row3.addWidget(QLabel("UPC Padding Pattern:"))
        tweak_upc_padding_pattern = QLineEdit()
        tweak_upc_padding_pattern.setMaximumWidth(120)
        self.fields["upc_padding_pattern_entry"] = tweak_upc_padding_pattern
        upc_row3.addWidget(tweak_upc_padding_pattern)
        upc_layout.addLayout(upc_row3)
        wrapper_layout.addWidget(upc_override_group)

        tweak_split_sales_tax_check = QCheckBox("Split Sales Tax 'C' Records")
        self.fields["split_sales_tax_prepaid_var"] = tweak_split_sales_tax_check
        wrapper_layout.addWidget(tweak_split_sales_tax_check)

        self._populate_tweak_fields_local(
            tweak_upc_check,
            tweak_pad_arec_check,
            tweak_arec_padding_field,
            tweak_arec_padding_length,
            tweak_append_arec_check,
            tweak_arec_append_field,
            tweak_force_txt_check,
            tweak_invoice_offset,
            tweak_custom_date_check,
            tweak_custom_date_field,
            tweak_retail_uom_check,
            tweak_override_upc_check,
            tweak_override_upc_level,
            tweak_override_upc_cat_filter,
            tweak_upc_target_length,
            tweak_upc_padding_pattern,
            tweak_split_sales_tax_check,
        )
        self.dynamic_layout.addWidget(wrapper)

    def _populate_tweak_fields_local(
        self,
        upc_check,
        pad_arec_check,
        arec_padding_field,
        arec_padding_length,
        append_arec_check,
        arec_append_field,
        force_txt_check,
        invoice_offset,
        custom_date_check,
        custom_date_field,
        retail_uom_check,
        override_upc_check,
        override_upc_level,
        override_upc_cat_filter,
        upc_target_length,
        upc_padding_pattern,
        split_sales_tax_check,
    ):
        cfg = self.folder_config
        upc_check.setChecked(
            str(cfg.get("calculate_upc_check_digit", "False")) == "True"
        )
        pad_arec_check.setChecked(str(cfg.get("pad_a_records", "False")) == "True")
        arec_padding_field.setText(str(cfg.get("a_record_padding") or ""))

        pad_len = str(
            cfg.get("a_record_padding_length")
            if cfg.get("a_record_padding_length") is not None
            else 6
        )
        idx = arec_padding_length.findText(pad_len)
        if idx >= 0:
            arec_padding_length.setCurrentIndex(idx)

        append_arec_check.setChecked(
            str(cfg.get("append_a_records", "False")) == "True"
        )
        arec_append_field.setText(str(cfg.get("a_record_append_text") or ""))
        force_txt_check.setChecked(
            str(cfg.get("force_txt_file_ext", "False")) == "True"
        )

        offset = cfg.get("invoice_date_offset")
        invoice_offset.setValue(int(offset) if offset is not None else 0)

        custom_date_check.setChecked(bool(cfg.get("invoice_date_custom_format", False)))
        custom_date_field.setText(
            str(cfg.get("invoice_date_custom_format_string") or "")
        )
        retail_uom_check.setChecked(bool(cfg.get("retail_uom", False)))
        override_upc_check.setChecked(bool(cfg.get("override_upc_bool", False)))

        lvl = str(
            cfg.get("override_upc_level")
            if cfg.get("override_upc_level") is not None
            else 1
        )
        idx = override_upc_level.findText(lvl)
        if idx >= 0:
            override_upc_level.setCurrentIndex(idx)

        override_upc_cat_filter.setText(
            str(cfg.get("override_upc_category_filter") or "")
        )
        upc_target_length.setText(
            str(
                cfg.get("upc_target_length")
                if cfg.get("upc_target_length") is not None
                else 11
            )
        )
        upc_padding_pattern.setText(
            str(cfg.get("upc_padding_pattern") or "           ")
        )
        split_sales_tax_check.setChecked(
            bool(cfg.get("split_prepaid_sales_tax_crec", False))
        )
