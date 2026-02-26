"""
UI Widget Abstraction Layer

Provides a framework-agnostic abstraction layer for creating UI widgets,
supporting Qt to ensure compatibility with the application's
dual UI framework architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .config_schemas import ConfigurationSchema, FieldType


class WidgetBase(ABC):
    """
    Base interface for all UI widgets.

    Provides a framework-agnostic interface for widget creation,
    configuration, and interaction.
    """

    @abstractmethod
    def get_widget(self) -> Any:
        """
        Get the native widget instance.

        Returns the actual widget object from the UI framework.

        Returns:
            Any: Native widget instance (Qt)
        """
        pass

    @abstractmethod
    def set_value(self, value: Any) -> None:
        """
        Set the widget's value.

        Args:
            value: Value to set
        """
        pass

    @abstractmethod
    def get_value(self) -> Any:
        """
        Get the widget's current value.

        Returns:
            Any: Current widget value
        """
        pass

    @abstractmethod
    def set_label(self, label: str) -> None:
        """
        Set the widget's label.

        Args:
            label: Label text
        """
        pass

    @abstractmethod
    def set_description(self, description: str) -> None:
        """
        Set the widget's description.

        Args:
            description: Description text
        """
        pass

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None:
        """
        Set whether the widget is enabled.

        Args:
            enabled: True if widget should be enabled, False otherwise
        """
        pass

    @abstractmethod
    def set_visible(self, visible: bool) -> None:
        """
        Set whether the widget is visible.

        Args:
            visible: True if widget should be visible, False otherwise
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate the widget's current value.

        Returns:
            bool: True if value is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_validation_errors(self) -> list:
        """
        Get validation errors for the widget's current value.

        Returns:
            list: List of validation error messages
        """
        pass


class WidgetFactory(ABC):
    """
    Factory for creating UI widgets based on field types.

    Implements the abstract factory pattern to create compatible
    widgets for different UI frameworks.
    """

    @abstractmethod
    def create_widget(self, field_type: FieldType,
                     field_definition: dict, parent: Any = None) -> WidgetBase:
        """
        Create a widget for a specific field type.

        Args:
            field_type: Type of field to create widget for
            field_definition: Field definition metadata
            parent: Optional parent widget

        Returns:
            WidgetBase: Created widget instance
        """
        pass


class WidgetFactoryRegistry:
    """
    Registry for widget factories.

    Manages widget factories for different UI frameworks and allows
    dynamic lookup based on framework type.
    """

    _factories = {}

    @classmethod
    def register_factory(cls, framework: str, factory: WidgetFactory):
        """
        Register a widget factory for a specific UI framework.

        Args:
            framework: UI framework identifier (e.g., 'qt')
            factory: Widget factory to register
        """
        cls._factories[framework] = factory

    @classmethod
    def get_factory(cls, framework: str) -> Optional[WidgetFactory]:
        """
        Get the widget factory for a specific UI framework.

        Args:
            framework: UI framework identifier

        Returns:
            Optional[WidgetFactory]: Widget factory or None if not found
        """
        return cls._factories.get(framework)

    @classmethod
    def has_factory(cls, framework: str) -> bool:
        """
        Check if a widget factory exists for a specific UI framework.

        Args:
            framework: UI framework identifier

        Returns:
            bool: True if factory exists, False otherwise
        """
        return framework in cls._factories


class ConfigurationWidgetBuilder:
    """
    Builder for creating configuration widgets from schemas.

    Provides a fluent interface for constructing widget layouts
    from configuration schemas.
    """

    def __init__(self, framework: str = 'qt'):
        """
        Initialize the widget builder.

        Args:
            framework: UI framework to use ('qt')
        """
        self.framework = framework
        self.factory = WidgetFactoryRegistry.get_factory(framework)
        if self.factory is None:
            raise ValueError(f"No widget factory registered for framework: {framework}")

    def build_widgets_from_schema(self, schema: ConfigurationSchema,
                                 parent: Any = None) -> Dict[str, WidgetBase]:
        """
        Build widgets from a configuration schema.

        Args:
            schema: Configuration schema to build widgets from
            parent: Optional parent widget

        Returns:
            Dict[str, WidgetBase]: Dictionary of field names to widget instances
        """
        widgets = {}
        for field in schema.fields:
            widget = self.factory.create_widget(
                field.field_type,
                field,
                parent
            )
            widgets[field.name] = widget

        return widgets

    def build_configuration_panel(self, schema: ConfigurationSchema,
                                config: dict = None,
                                parent: Any = None) -> Any:
        """
        Build a complete configuration panel from a schema.

        Args:
            schema: Configuration schema
            config: Optional initial configuration values
            parent: Optional parent widget

        Returns:
            Any: Container widget with all configuration fields
        """
        widgets = self.build_widgets_from_schema(schema, parent)

        # Set initial values if provided
        if config:
            for field_name, widget in widgets.items():
                if field_name in config:
                    widget.set_value(config[field_name])

        return self._layout_widgets(widgets, schema, parent)

    @abstractmethod
    def _layout_widgets(self, widgets: Dict[str, WidgetBase],
                      schema: ConfigurationSchema,
                      parent: Any = None) -> Any:
        """
        Layout widgets in a container.

        Args:
            widgets: Dictionary of widgets
            schema: Configuration schema
            parent: Optional parent widget

        Returns:
            Any: Container widget with layout
        """
        pass


class QtWidgetFactory(WidgetFactory):
    """
    Widget factory for Qt UI framework.

    Creates Qt-compatible widgets for each field type.
    """

    def create_widget(self, field_type: FieldType,
                     field_definition: dict, parent: Any = None) -> WidgetBase:
        """
        Create a Qt widget for a specific field type.

        Args:
            field_type: Type of field to create widget for
            field_definition: Field definition metadata
            parent: Optional parent widget

        Returns:
            WidgetBase: Created widget instance
        """
        from PyQt5.QtWidgets import (
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
            QListWidget, QTextEdit
        )

        if field_type == FieldType.STRING:
            return QtLineEditWidget(field_definition, parent)
        elif field_type == FieldType.INTEGER:
            return QtSpinBoxWidget(field_definition, parent)
        elif field_type == FieldType.FLOAT:
            return QtDoubleSpinBoxWidget(field_definition, parent)
        elif field_type == FieldType.BOOLEAN:
            return QtCheckBoxWidget(field_definition, parent)
        elif field_type == FieldType.SELECT:
            return QtComboBoxWidget(field_definition, parent)
        elif field_type == FieldType.MULTI_SELECT:
            return QtListWidgetWidget(field_definition, parent)
        elif field_type == FieldType.LIST:
            return QtTextEditWidget(field_definition, parent)
        elif field_type == FieldType.DICT:
            return QtTextEditWidget(field_definition, parent)
        else:
            raise ValueError(f"Unsupported field type: {field_type}")


class QtWidgetBase(WidgetBase):
    """
    Base class for Qt widgets.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        """
        Initialize the Qt widget base class.

        Args:
            field_definition: Field definition metadata
            parent: Optional parent widget
        """
        self.field_definition = field_definition
        self.widget = None
        self.parent = parent

    def get_widget(self) -> Any:
        """
        Get the native Qt widget instance.

        Returns:
            Any: Qt widget instance
        """
        return self.widget

    def set_label(self, label: str) -> None:
        """
        Set the widget's label.

        Args:
            label: Label text
        """
        # For Qt, the label is typically managed separately in the layout
        pass

    def set_description(self, description: str) -> None:
        """
        Set the widget's description.

        Args:
            description: Description text
        """
        pass

    def validate(self) -> bool:
        """
        Validate the widget's current value against the field definition.

        Returns:
            bool: True if value is valid, False otherwise
        """
        from .validation_framework import ValidationResult

        value = self.get_value()
        validation = self.field_definition.validate(value)
        return validation.success

    def get_validation_errors(self) -> list:
        """
        Get validation errors for the widget's current value.

        Returns:
            list: List of validation error messages
        """
        from .validation_framework import ValidationResult

        value = self.get_value()
        validation = self.field_definition.validate(value)
        return validation.errors


class QtLineEditWidget(QtWidgetBase):
    """
    Qt line edit widget for string fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QLineEdit

        self.widget = QLineEdit(parent)
        if field_definition.default:
            self.widget.setText(field_definition.default)

    def set_value(self, value: Any) -> None:
        if value is not None:
            self.widget.setText(str(value))

    def get_value(self) -> Any:
        return self.widget.text()

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


class QtSpinBoxWidget(QtWidgetBase):
    """
    Qt spin box widget for integer fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QSpinBox

        self.widget = QSpinBox(parent)
        if field_definition.min_value is not None:
            self.widget.setMinimum(field_definition.min_value)
        if field_definition.max_value is not None:
            self.widget.setMaximum(field_definition.max_value)
        if field_definition.default is not None:
            self.widget.setValue(field_definition.default)

    def set_value(self, value: Any) -> None:
        if value is not None:
            self.widget.setValue(value)

    def get_value(self) -> Any:
        return self.widget.value()

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


class QtDoubleSpinBoxWidget(QtWidgetBase):
    """
    Qt double spin box widget for float fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QDoubleSpinBox

        self.widget = QDoubleSpinBox(parent)
        if field_definition.min_value is not None:
            self.widget.setMinimum(field_definition.min_value)
        if field_definition.max_value is not None:
            self.widget.setMaximum(field_definition.max_value)
        self.widget.setDecimals(2)
        if field_definition.default is not None:
            self.widget.setValue(field_definition.default)

    def set_value(self, value: Any) -> None:
        if value is not None:
            self.widget.setValue(value)

    def get_value(self) -> Any:
        return self.widget.value()

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


class QtComboBoxWidget(QtWidgetBase):
    """
    Qt combo box widget for select fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QComboBox

        self.widget = QComboBox(parent)
        for choice in field_definition.choices:
            self.widget.addItem(choice["label"], choice["value"])
        if field_definition.default is not None:
            index = self.widget.findData(field_definition.default)
            if index >= 0:
                self.widget.setCurrentIndex(index)

    def set_value(self, value: Any) -> None:
        if value is not None:
            index = self.widget.findData(value)
            if index >= 0:
                self.widget.setCurrentIndex(index)

    def get_value(self) -> Any:
        return self.widget.currentData()

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


class QtCheckBoxWidget(QtWidgetBase):
    """
    Qt check box widget for boolean fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QCheckBox

        self.widget = QCheckBox(field_definition.label, parent)
        if field_definition.default:
            self.widget.setChecked(field_definition.default)

    def set_value(self, value: Any) -> None:
        if value is not None:
            self.widget.setChecked(bool(value))

    def get_value(self) -> Any:
        return self.widget.isChecked()

    def set_label(self, label: str) -> None:
        self.widget.setText(label)

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


class QtListWidgetWidget(QtWidgetBase):
    """
    Qt list widget for multi-select fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QListWidget

        self.widget = QListWidget(parent)
        self.widget.setSelectionMode(QListWidget.MultiSelection)
        for choice in field_definition.choices:
            self.widget.addItem(choice["label"], choice["value"])
        if field_definition.default:
            for i in range(self.widget.count()):
                item = self.widget.item(i)
                if item.data(0) in field_definition.default:
                    item.setSelected(True)

    def set_value(self, value: Any) -> None:
        if value is not None:
            for i in range(self.widget.count()):
                item = self.widget.item(i)
                item.setSelected(item.data(0) in value)

    def get_value(self) -> Any:
        selected = []
        for item in self.widget.selectedItems():
            selected.append(item.data(0))
        return selected

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


class QtTextEditWidget(QtWidgetBase):
    """
    Qt text edit widget for list and dict fields.
    """

    def __init__(self, field_definition: dict, parent: Any = None):
        super().__init__(field_definition, parent)
        from PyQt5.QtWidgets import QTextEdit

        self.widget = QTextEdit(parent)
        if field_definition.default:
            import json
            self.widget.setText(json.dumps(field_definition.default, indent=2))

    def set_value(self, value: Any) -> None:
        if value is not None:
            import json
            self.widget.setText(json.dumps(value, indent=2))

    def get_value(self) -> Any:
        try:
            import json
            return json.loads(self.widget.toPlainText())
        except Exception:
            return {}

    def set_enabled(self, enabled: bool) -> None:
        self.widget.setEnabled(enabled)

    def set_visible(self, visible: bool) -> None:
        self.widget.setVisible(visible)


# Register widget factories
WidgetFactoryRegistry.register_factory('qt', QtWidgetFactory())
