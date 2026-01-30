from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QTextEdit,
    QGroupBox,
)
from PyQt6.QtCore import Qt

from plugin_config import ConfigField


class PluginUIGenerator:
    @staticmethod
    def create_widget_for_field(
        field: ConfigField, parent: Optional[QWidget] = None
    ) -> tuple[QWidget, Any]:
        """Create a Qt widget for a configuration field.

        Args:
            field: ConfigField definition.
            parent: Parent widget.

        Returns:
            Tuple of (widget, value_getter) where value_getter is a callable
            that returns the current widget value.
        """
        if field.type == "boolean":
            widget = QCheckBox(field.label, parent)
            widget.setChecked(
                field.default if isinstance(field.default, bool) else False
            )
            if field.help:
                widget.setToolTip(field.help)
            return widget, lambda: widget.isChecked()

        elif field.type == "string":
            widget = QLineEdit(parent)
            widget.setText(str(field.default) if field.default else "")
            if field.placeholder:
                widget.setPlaceholderText(field.placeholder)
            if field.help:
                widget.setToolTip(field.help)
            return widget, lambda: widget.text()

        elif field.type == "integer":
            widget = QSpinBox(parent)
            default_val = field.default if isinstance(field.default, int) else 0
            min_val = int(field.min_value) if field.min_value is not None else 0
            max_val = (
                int(field.max_value)
                if field.max_value is not None
                else max(99, default_val)
            )
            widget.setMinimum(min_val)
            widget.setMaximum(max_val)
            widget.setValue(default_val)
            if field.help:
                widget.setToolTip(field.help)
            return widget, lambda: widget.value()

        elif field.type == "float":
            widget = QDoubleSpinBox(parent)
            default_val = (
                field.default if isinstance(field.default, (int, float)) else 0.0
            )
            min_val = float(field.min_value) if field.min_value is not None else 0.0
            max_val = (
                float(field.max_value)
                if field.max_value is not None
                else max(99.0, default_val)
            )
            widget.setMinimum(min_val)
            widget.setMaximum(max_val)
            widget.setValue(default_val)
            if field.help:
                widget.setToolTip(field.help)
            return widget, lambda: widget.value()

        elif field.type == "select":
            widget = QComboBox(parent)
            for option in field.options:
                if isinstance(option, tuple):
                    widget.addItem(option[1], option[0])
                else:
                    widget.addItem(option, option)

            if field.default:
                index = (
                    widget.findData(field.default)
                    if isinstance(field.options[0], tuple)
                    else widget.findText(field.default)
                )
                if index >= 0:
                    widget.setCurrentIndex(index)

            if field.help:
                widget.setToolTip(field.help)
            return widget, lambda: widget.currentData() if isinstance(
                field.options[0], tuple
            ) else widget.currentText()

        elif field.type == "text":
            widget = QTextEdit(parent)
            widget.setPlainText(str(field.default) if field.default else "")
            if field.placeholder:
                widget.setPlaceholderText(field.placeholder)
            if field.help:
                widget.setToolTip(field.help)
            widget.setMaximumHeight(100)
            return widget, lambda: widget.toPlainText()

        else:
            widget = QLineEdit(parent)
            widget.setText(str(field.default) if field.default else "")
            return widget, lambda: widget.text()

    @staticmethod
    def create_plugin_config_widget(
        fields: List[ConfigField],
        parent: Optional[QWidget] = None,
        current_values: Optional[Dict[str, Any]] = None,
    ) -> tuple[QWidget, Dict[str, Any]]:
        """Create a widget containing all configuration fields for a plugin.

        Args:
            fields: List of ConfigField definitions.
            parent: Parent widget.
            current_values: Current configuration values to populate.

        Returns:
            Tuple of (widget, value_getters) where value_getters is a dict
            mapping field keys to callables that return current values.
        """
        current_values = current_values or {}
        widget = QWidget(parent)
        layout = QGridLayout(widget)

        value_getters = {}
        row = 0

        for field in fields:
            if field.visible_if:
                continue

            field_widget, getter = PluginUIGenerator.create_widget_for_field(
                field, widget
            )

            if current_values and field.key in current_values:
                PluginUIGenerator._set_widget_value(
                    field_widget, current_values[field.key]
                )

            if field.type == "boolean":
                layout.addWidget(field_widget, row, 0, 1, 2)
            else:
                label = QLabel(
                    field.label + ("*" if field.required else "") + ":", widget
                )
                layout.addWidget(label, row, 0)
                layout.addWidget(field_widget, row, 1)

            value_getters[field.key] = getter
            row += 1

        layout.setRowStretch(row, 1)
        return widget, value_getters

    @staticmethod
    def _set_widget_value(widget: QWidget, value: Any) -> None:
        """Set the value of a widget."""
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value) if value is not None else "")
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setValue(value if value is not None else 0)
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index < 0:
                index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QTextEdit):
            widget.setPlainText(str(value) if value is not None else "")

    @staticmethod
    def get_config_values(value_getters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract current values from all widgets.

        Args:
            value_getters: Dict of field keys to value getter callables.

        Returns:
            Dict of field keys to current values.
        """
        return {key: getter() for key, getter in value_getters.items()}
