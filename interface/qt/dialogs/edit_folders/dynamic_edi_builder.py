"""Dynamic EDI Builder for Qt Edit Folders Dialog.

Handles the construction and management of dynamic EDI configuration sections
that appear based on user selections in the EDI options dropdown.
"""

import logging
from typing import Any, Callable, Optional

from core.structured_logging import (
    generate_correlation_id,
    get_correlation_id,
    get_logger,
    log_with_context,
    set_correlation_id,
)

logger = get_logger(__name__)

from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.utils.bool_utils import normalize_bool
from interface.form.form_generator import FormGeneratorFactory
from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.plugins.plugin_manager import PluginManager
from interface.plugins.plugin_manager_provider import get_shared_plugin_manager


class DynamicEDIBuilder:
    """Builder class for dynamic EDI configuration sections.

    Manages the creation, display, and removal of dynamic EDI configuration
    sections based on user selections.
    """

    def __init__(
        self,
        fields: dict[str, Any],
        folder_config: dict[str, Any],
        dynamic_container: QWidget,
        dynamic_layout: QVBoxLayout,
        on_convert_format_changed: Callable[[str], None] | None = None,
        on_dynamic_form_changed: Callable[[], None] | None = None,
        plugin_manager: Optional["PluginManager"] = None,
    ) -> None:
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
        self.on_dynamic_form_changed = on_dynamic_form_changed

        # Use injected plugin manager or fall back to the shared singleton
        self.plugin_manager = plugin_manager or get_shared_plugin_manager()
        self.configuration_plugins = self.plugin_manager.get_configuration_plugins()

        # Widget references
        self.edi_options_check = None
        self.convert_format_combo = None
        self.convert_sub_container = None
        self.convert_sub_layout = None

        # State tracking
        self._edi_option_processing = False
        self._correlation_id = generate_correlation_id()
        set_correlation_id(self._correlation_id)
        log_with_context(
            logger,
            logging.DEBUG,  # DEBUG
            "Dynamic EDI Builder initialized",
            correlation_id=self._correlation_id,
            component="dynamic_edi_builder",
            operation="__init__",
            context={
                "folder_alias": folder_config.get("alias", "unknown"),
                "convert_to_format": folder_config.get("convert_to_format", "csv"),
            },
        )

        # Preserved UPC override values (plain Python, not widgets) so they
        # survive _clear_dynamic_edi / _clear_convert_sub calls.
        self._saved_upc_override: dict = {
            "override_upc_bool": normalize_bool(
                folder_config.get("override_upc_bool", False)
            ),
            "override_upc_level": str(
                folder_config.get("override_upc_level", 1)
                if folder_config.get("override_upc_level") is not None
                else 1
            ),
            "override_upc_category_filter_entry": str(
                folder_config.get("override_upc_category_filter", "")
            ),
            "upc_target_length_entry": str(
                folder_config.get("upc_target_length", 11)
                if folder_config.get("upc_target_length") is not None
                else 11
            ),
            "upc_padding_pattern_entry": str(
                folder_config.get("upc_padding_pattern", "           ")
            ),
        }

    def _get_convert_formats(self) -> list[str]:
        """Get all available convert formats from configuration plugins."""
        formats = []
        for plugin in self.configuration_plugins:
            formats.append(plugin.get_format_name())
        return sorted(formats)

    def _resolve_format_display_name(self, stored_value: str) -> str:
        """Resolve a stored format value to its display name for the combo.

        Handles both display names (e.g. "Simplified CSV") already stored
        directly and legacy internal enum values (e.g. "simplified_csv") that
        were stored by older versions of the dialog.

        Args:
            stored_value: The format string as stored in the database.

        Returns:
            The display name that matches a combo item, or the original value
            if no match is found.

        """
        if not stored_value:
            return stored_value

        # 1. Try a direct display-name match (case-insensitive)
        plugin = self.plugin_manager.get_configuration_plugin_by_format_name(
            stored_value
        )
        if plugin:
            return plugin.get_format_name()

        # 2. Try matching against ConvertFormat enum values (legacy DB records)
        from interface.models.folder_configuration import ConvertFormat

        for fmt_enum in ConvertFormat:
            if fmt_enum.value.lower() == stored_value.lower():
                # Found the enum; now look up the plugin for it
                enum_plugin = self.plugin_manager.get_configuration_plugin_by_format(
                    fmt_enum
                )
                if enum_plugin:
                    return enum_plugin.get_format_name()

        # No match found — return as-is and let the caller handle it
        return stored_value

    @staticmethod
    def _find_combo_index_case_insensitive(combo: QComboBox, text: str) -> int:
        """Find combo index by text case-insensitively."""
        if not text:
            return -1
        text_lower = text.lower()
        return next(
            (
                i
                for i in range(combo.count())
                if combo.itemText(i).lower() == text_lower
            ),
            -1,
        )

    def build_edi_options_check(self) -> QCheckBox:
        """Build and configure the Convert EDI checkbox."""
        self.edi_options_check = QCheckBox("Convert EDI")
        self.edi_options_check.setAccessibleName("Convert EDI")
        self.edi_options_check.setAccessibleDescription(
            "Check to convert EDI files to another format; uncheck to send as-is"
        )
        self.edi_options_check.toggled.connect(self._on_edi_check_toggled)
        self.fields["edi_options_check"] = self.edi_options_check
        return self.edi_options_check

    _UPC_OVERRIDE_KEYS = [
        "override_upc_bool",
        "override_upc_level",
        "override_upc_category_filter_entry",
        "upc_target_length_entry",
        "upc_padding_pattern_entry",
    ]

    def _snapshot_upc_override(self) -> None:
        """Save current UPC override widget values as plain Python values.

        Called before any clear that would destroy these widgets, so that
        the extractor can still read the last user-chosen values.
        """
        from PyQt5.QtWidgets import QCheckBox, QComboBox, QLineEdit

        for key in self._UPC_OVERRIDE_KEYS:
            widget = self.fields.get(key)
            if widget is None:
                continue
            try:
                if isinstance(widget, (QCheckBox,)):
                    self._saved_upc_override[key] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    self._saved_upc_override[key] = widget.currentText().strip()
                elif isinstance(widget, QLineEdit):
                    self._saved_upc_override[key] = widget.text().strip()
                elif isinstance(widget, (bool, int, float, str)):
                    # Already a plain value -- keep as-is
                    self._saved_upc_override[key] = widget
            except RuntimeError:
                # Widget may have been deleted during form cleanup; ignore
                pass

    def _restore_upc_override_as_plain_values(self) -> None:
        """Write saved UPC override values as plain Python values into self.fields.

        This ensures the data extractor returns the last known user values
        rather than defaults when the UPC override widgets are absent.
        """
        for key, value in self._saved_upc_override.items():
            self.fields[key] = value

    def _clear_dynamic_edi(self) -> None:
        """Clear dynamic EDI widgets and clean up field references."""
        log_with_context(
            logger,
            logging.DEBUG,  # DEBUG
            "Clearing dynamic EDI widgets",
            correlation_id=get_correlation_id(),
            component="dynamic_edi_builder",
            operation="_clear_dynamic_edi",
        )
        self._snapshot_upc_override()
        try:
            keys_to_remove = []

        # Store items to remove in a list to avoid modifying
        # the layout during iteration
            items_to_remove = []
            while self.dynamic_layout.count():
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
            self._prune_stale_plugin_generator_keys(keys_to_remove)

        except Exception as e:
            log_with_context(
                logger,
                40,  # ERROR
                f"Error in _clear_dynamic_edi: {e}",
                correlation_id=get_correlation_id(),
                component="dynamic_edi_builder",
                operation="_clear_dynamic_edi",
                context={"error_type": type(e).__name__},
                exc_info=True,
            )
        self._restore_upc_override_as_plain_values()

    def _prune_stale_plugin_generator_keys(self, removed_keys: list[str]) -> None:
        """Remove plugin form-generator entries tied to removed plugin form widgets.

        Plugin config forms store two field entries:
        - ``plugin_config_<identifier>`` -> form widget
        - ``plugin_config_<identifier>_generator`` -> FormGenerator instance

        When the form widget is cleared, we must also remove the paired generator
        entry; otherwise later extraction can call ``get_values()`` on generator
        widgets that have already been deleted by Qt.
        """
        for key in removed_keys:
            if not key.startswith("plugin_config_") or key.endswith("_generator"):
                continue

            generator_key = f"{key}_generator"
            if generator_key in self.fields:
                del self.fields[generator_key]

    def _find_and_track_widget_keys(self, widget, keys_to_remove) -> None:
        """Recursively find all descendant widgets and track their field keys."""
        self._add_widget_key_if_found(widget, keys_to_remove)
        for child in widget.findChildren(QWidget):
            self._add_widget_key_if_found(child, keys_to_remove)

    def _find_and_track_layout_keys(self, layout, keys_to_remove) -> None:
        """Find all widgets in a layout and track their field keys."""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if widget:
                self._add_widget_key_if_found(widget, keys_to_remove)
                for child in widget.findChildren(QWidget):
                    self._add_widget_key_if_found(child, keys_to_remove)
            sub_layout = item.layout()
            if sub_layout:
                self._find_and_track_layout_keys(sub_layout, keys_to_remove)

    def _add_widget_key_if_found(self, widget: QWidget, keys_to_remove: list) -> None:
        """Add widget's field key to keys_to_remove if found in fields."""
        for key, value in list(self.fields.items()):
            if value is widget:
                if key not in keys_to_remove:
                    keys_to_remove.append(key)
                break

    def _on_edi_check_toggled(self, checked: bool) -> None:
        """Handle Convert EDI checkbox toggle."""
        if self._edi_option_processing:
            return

        self._edi_option_processing = True
        log_with_context(
            logger,
            logging.DEBUG,  # DEBUG
            f"EDI option toggled to: {'Convert EDI' if checked else 'Do Nothing'}",
            correlation_id=get_correlation_id(),
            component="dynamic_edi_builder",
            operation="_on_edi_check_toggled",
            context={"convert_edi": checked},
        )
        try:
            self._clear_dynamic_edi()
            if checked:
                self._build_convert_edi_area()
            else:
                self._build_do_nothing_area()
            if self.on_dynamic_form_changed:
                self.on_dynamic_form_changed()
        finally:
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(100, self._clear_edi_processing_flag)

    def _clear_edi_processing_flag(self) -> None:
        """Clear the EDI processing flag after a delay."""
        self._edi_option_processing = False

    def _build_do_nothing_area(self) -> None:
        """Build the 'Do Nothing' EDI configuration section."""
        self.fields["process_edi"] = False
        # Explicitly clear convert_formats_var so the extractor saves
        # convert_to_format as "" rather than retaining a stale format value.
        self.fields["convert_formats_var"] = ""
        label = QLabel("Send As Is")
        self.dynamic_layout.addWidget(label)

    def _build_convert_edi_area(self) -> None:
        """Build the 'Convert EDI' configuration section."""
        self.fields["process_edi"] = True

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Convert To:"))
        self.convert_format_combo = QComboBox()
        self.convert_format_combo.addItems(self._get_convert_formats())
        self.convert_format_combo.setAccessibleName("Convert format")
        self.convert_format_combo.setAccessibleDescription(
            "Select output format when Convert EDI is enabled"
        )
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

        current_fmt = self._resolve_format_display_name(
            self.folder_config.get("convert_to_format") or ""
        )
        idx = self._find_combo_index_case_insensitive(
            self.convert_format_combo, current_fmt
        )
        if idx >= 0:
            self.convert_format_combo.setCurrentIndex(idx)
        self.handle_convert_format_changed(self.convert_format_combo.currentText())

        self.dynamic_layout.addWidget(wrapper)

    def handle_convert_format_changed(self, fmt: str) -> None:
        """Handle convert format selection changes."""
        log_with_context(
            logger,
            logging.DEBUG,  # DEBUG
            f"Convert format changed to: {fmt}",
            correlation_id=get_correlation_id(),
            component="dynamic_edi_builder",
            operation="handle_convert_format_changed",
            context={"format": fmt},
        )
        self._clear_convert_sub()
        fmt_lower = (fmt or "").lower()
        self._build_format_specific_options(fmt_lower, fmt)

        if self.on_convert_format_changed:
            self.on_convert_format_changed(fmt)
        if self.on_dynamic_form_changed:
            self.on_dynamic_form_changed()

    def _build_format_specific_options(self, fmt_lower: str, fmt: str) -> None:
        """Build format-specific sub-options based on the selected format."""
        if fmt_lower == "csv":
            self._build_csv_sub()
        elif fmt_lower == "scannerware":
            self._build_scannerware_sub()
        elif fmt_lower in ("simplified csv", "simplified_csv"):
            self._build_simplified_csv_sub()
        elif fmt_lower in ("estore einvoice", "estore einvoice generic"):
            self._build_estore_sub(fmt)
        elif fmt_lower == "fintech":
            self._build_fintech_sub()
        elif fmt_lower in ("scansheet type a", "scansheet-type-a"):
            pass
        elif fmt_lower in (
            "jolley custom",
            "jolley_custom",
            "stewarts custom",
            "stewarts_custom",
            "yellowdog csv",
        ):
            self._build_basic_options_sub()
        else:
            plugin = self.plugin_manager.get_configuration_plugin_by_format_name(fmt)
            if plugin:
                self._build_plugin_config_sub(plugin)

    def _clear_convert_sub(self) -> None:
        """Clear convert sub-widgets and clean up field references."""
        if not self.convert_sub_layout:
            return

        log_with_context(
            logger,
            logging.DEBUG,  # DEBUG
            "Clearing convert sub widgets",
            correlation_id=get_correlation_id(),
            component="dynamic_edi_builder",
            operation="_clear_convert_sub",
        )
        self._snapshot_upc_override()
        try:
            keys_to_remove = self._extract_and_cleanup_items()
            for key in keys_to_remove:
                if key in self.fields:
                    del self.fields[key]
            self._prune_stale_plugin_generator_keys(keys_to_remove)

        except Exception as e:
            log_with_context(
                logger,
                40,  # ERROR
                f"Error in _clear_convert_sub: {e}",
                correlation_id=get_correlation_id(),
                component="dynamic_edi_builder",
                operation="_clear_convert_sub",
                context={"error_type": type(e).__name__},
                exc_info=True,
            )
        self._restore_upc_override_as_plain_values()

    def _extract_and_cleanup_items(self) -> list:
        """Extract items from convert_sub_layout and cleanup widgets/layouts.

        Returns:
            List of field keys to remove

        """
        keys_to_remove = []
        items_to_remove = []
        layout = self.convert_sub_layout
        if layout is None:
            return keys_to_remove

        while layout.count():
            items_to_remove.append(layout.takeAt(0))

        for item in items_to_remove:
            if item:
                self._cleanup_layout_item(item, keys_to_remove)

        return keys_to_remove

    def _cleanup_layout_item(self, item, keys_to_remove: list) -> None:
        """Cleanup a single layout item and track its field keys."""
        widget = item.widget()
        if widget:
            self._find_and_track_widget_keys(widget, keys_to_remove)
            if not widget.testAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose):
                widget.setParent(None)
                widget.deleteLater()
        sub_layout = item.layout()
        if sub_layout:
            self._find_and_track_layout_keys(sub_layout, keys_to_remove)
            sub_layout.deleteLater()

    # Mapping from legacy flat DB column names to TweaksConfigurationPlugin field names.
    _TWEAKS_LEGACY_FIELD_MAP = {
        "pad_a_records": "pad_arec",
        "a_record_padding": "arec_padding",
        "a_record_padding_length": "arec_padding_len",
        "append_a_records": "append_arec",
        "a_record_append_text": "append_arec_text",
        "calculate_upc_check_digit": "calc_upc",
        "retail_uom": "retail_uom",
        "override_upc_bool": "override_upc",
        "override_upc_level": "override_upc_level",
        "override_upc_category_filter": "override_upc_category_filter",
        "upc_target_length": "upc_target_length",
        "upc_padding_pattern": "upc_padding_pattern",
        "split_prepaid_sales_tax_crec": "split_prepaid_sales_tax_crec",
        "invoice_date_custom_format": "invoice_date_custom_format",
        "invoice_date_custom_format_string": "invoice_date_custom_format_string",
        "invoice_date_offset": "invoice_date_offset",
        "force_txt_file_ext": "force_txt_file_ext",
    }

    def _build_legacy_plugin_config(self, plugin: ConfigurationPlugin) -> dict:
        """Build a plugin config dict from legacy flat DB columns.

        Used as a fallback when a folder was saved before the plugin
        configuration system existed (i.e. plugin_configurations is absent
        or does not contain an entry for this plugin).

        Only the Tweaks plugin has a known legacy column mapping; for any
        other plugin an empty dict is returned.
        """
        from interface.plugins.tweaks_configuration_plugin import (
            TweaksConfigurationPlugin,
        )

        if not isinstance(plugin, TweaksConfigurationPlugin):
            return {}

        cfg = self.folder_config
        result = {}
        for legacy_key, plugin_key in self._TWEAKS_LEGACY_FIELD_MAP.items():
            if legacy_key in cfg and cfg[legacy_key] is not None:
                result[plugin_key] = cfg[legacy_key]
        return result

    def _build_plugin_config_sub(self, plugin: ConfigurationPlugin) -> None:
        """Build plugin configuration sub-section."""
        schema = plugin.get_configuration_schema()
        if schema:
            form_generator = FormGeneratorFactory.create_form_generator(schema, "qt")
            plugin_config = self.folder_config.get("plugin_configurations", {}).get(
                plugin.get_format_name().lower(), {}
            )
            # Fall back to legacy flat DB columns when no plugin config is stored yet.
            # This handles folders created before the plugin configuration system.
            if not plugin_config:
                plugin_config = self._build_legacy_plugin_config(plugin)
            form_widget = form_generator.build_form(
                plugin_config, self.convert_sub_container
            )

            plugin_key = f"plugin_config_{plugin.get_identifier()}"
            self.fields[plugin_key] = form_widget
            self.fields[f"{plugin_key}_generator"] = form_generator
            if self.convert_sub_layout is not None:
                self.convert_sub_layout.addWidget(form_widget)

    def _build_csv_sub(self) -> None:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        upc_check = QCheckBox("Calculate UPC Check Digit")
        upc_check.setAccessibleName("Calculate UPC check digit")
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
        column_sort_field.setAccessibleName("CSV column sort")
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
        if self.convert_sub_layout is not None:
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
    ) -> None:
        cfg = self.folder_config
        upc_check.setChecked(
            normalize_bool(cfg.get("calculate_upc_check_digit", False))
        )
        a_rec_check.setChecked(normalize_bool(cfg.get("include_a_records", False)))
        c_rec_check.setChecked(normalize_bool(cfg.get("include_c_records", False)))
        headers_check.setChecked(normalize_bool(cfg.get("include_headers", False)))
        ampersand_check.setChecked(normalize_bool(cfg.get("filter_ampersand", False)))
        pad_arec_check.setChecked(normalize_bool(cfg.get("pad_a_records", False)))
        arec_padding_field.setText(str(cfg.get("a_record_padding", "")))

        pad_len = str(
            cfg.get("a_record_padding_length")
            if cfg.get("a_record_padding_length") is not None
            else 6
        )
        idx = arec_padding_length.findText(pad_len)
        if idx >= 0:
            arec_padding_length.setCurrentIndex(idx)

        override_upc_check.setChecked(
            normalize_bool(cfg.get("override_upc_bool", False))
        )

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
        each_uom_check.setChecked(normalize_bool(cfg.get("retail_uom", False)))
        split_sales_tax_check.setChecked(
            normalize_bool(cfg.get("split_prepaid_sales_tax_crec", False))
        )
        include_item_numbers_check.setChecked(
            normalize_bool(cfg.get("include_item_numbers", False))
        )
        include_item_desc_check.setChecked(
            normalize_bool(cfg.get("include_item_description", False))
        )
        column_sort_field.setText(str(cfg.get("simple_csv_sort_order", "")))

    def _build_scannerware_sub(self) -> None:
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
        pad_arec_check.setChecked(normalize_bool(cfg.get("pad_a_records", False)))
        arec_padding_field.setText(str(cfg.get("a_record_padding", "")))
        pad_len = str(
            cfg.get("a_record_padding_length")
            if cfg.get("a_record_padding_length") is not None
            else 6
        )
        idx = arec_padding_length.findText(pad_len)
        if idx >= 0:
            arec_padding_length.setCurrentIndex(idx)
        append_arec_check.setChecked(normalize_bool(cfg.get("append_a_records", False)))
        arec_append_field.setText(str(cfg.get("a_record_append_text", "")))

        if self.convert_sub_layout is not None:
            self.convert_sub_layout.addWidget(wrapper)

    def _build_simplified_csv_sub(self) -> None:
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
        headers_check.setChecked(normalize_bool(cfg.get("include_headers", False)))
        include_item_numbers_check.setChecked(
            normalize_bool(cfg.get("include_item_numbers", False))
        )
        include_item_desc_check.setChecked(
            normalize_bool(cfg.get("include_item_description", False))
        )
        each_uom_check.setChecked(normalize_bool(cfg.get("retail_uom", False)))
        column_sort_field.setText(str(cfg.get("simple_csv_sort_order", "")))

        if self.convert_sub_layout is not None:
            self.convert_sub_layout.addWidget(wrapper)

    def _build_estore_sub(self, fmt: str) -> None:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        form_widget = QWidget()
        layout = QFormLayout(form_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(form_widget)

        estore_store_number_field = QLineEdit()
        self.fields["estore_store_number_field"] = estore_store_number_field
        layout.addRow("Estore Store Number:", estore_store_number_field)

        estore_vendor_oid_field = QLineEdit()
        self.fields["estore_Vendor_OId_field"] = estore_vendor_oid_field
        layout.addRow("Estore Vendor OId:", estore_vendor_oid_field)

        estore_vendor_name_field = QLineEdit()
        self.fields["estore_vendor_namevendoroid_field"] = estore_vendor_name_field
        layout.addRow("Estore Vendor Name OId:", estore_vendor_name_field)

        estore_c_record_oid_field = None
        if fmt == "eStore eInvoice Generic":
            estore_c_record_oid_field = QLineEdit()
            self.fields["estore_c_record_oid_field"] = estore_c_record_oid_field
            layout.addRow("Estore C Record OId:", estore_c_record_oid_field)

        cfg = self.folder_config
        estore_store_number_field.setText(str(cfg.get("estore_store_number", "")))
        estore_vendor_oid_field.setText(str(cfg.get("estore_Vendor_OId", "")))
        estore_vendor_name_field.setText(
            str(cfg.get("estore_vendor_NameVendorOID", ""))
        )
        if fmt == "eStore eInvoice Generic" and estore_c_record_oid_field is not None:
            estore_c_record_oid_field.setText(str(cfg.get("estore_c_record_OID", "")))

        if self.convert_sub_layout is not None:
            self.convert_sub_layout.addWidget(wrapper)

    def _build_fintech_sub(self) -> None:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        form_widget = QWidget()
        layout = QFormLayout(form_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(form_widget)

        fintech_division_field = QLineEdit()
        self.fields["fintech_divisionid_field"] = fintech_division_field
        layout.addRow("Fintech Division ID:", fintech_division_field)

        fintech_division_field.setText(
            str(self.folder_config.get("fintech_division_id", ""))
        )
        if self.convert_sub_layout is not None:
            self.convert_sub_layout.addWidget(wrapper)

    def _build_basic_options_sub(self) -> None:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("No additional options for this format."))
        if self.convert_sub_layout is not None:
            self.convert_sub_layout.addWidget(wrapper)

    def _build_tweak_edi_area(self) -> None:
        """Compatibility shim for legacy callers.

        The dedicated tweak mode has been retired. Route legacy invocations to
        Convert EDI mode with the "Tweaks" conversion target selected when
        available.
        """
        self._build_convert_edi_area()
        if self.convert_format_combo is None:
            return

        idx = self.convert_format_combo.findText("Tweaks")
        if idx >= 0:
            self.convert_format_combo.setCurrentIndex(idx)
