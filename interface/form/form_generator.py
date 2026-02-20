"""
Dynamic Form Generator

Provides a framework-agnostic form generator that can dynamically render UI
from ConfigurationSchema definitions. Supports both Qt and Tkinter frameworks
through the existing UI abstraction layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition
from interface.plugins.ui_abstraction import (
    WidgetBase,
    WidgetFactoryRegistry,
    ConfigurationWidgetBuilder
)
from interface.plugins.validation_framework import ValidationResult


class FormGenerator(ABC):
    """
    Base interface for form generators.

    Provides a framework-agnostic interface for creating and managing dynamic forms
    from ConfigurationSchema definitions.
    """

    def __init__(self, schema: ConfigurationSchema, framework: str = 'qt'):
        """
        Initialize the form generator.

        Args:
            schema: Configuration schema to generate form from
            framework: UI framework to use ('qt' or 'tkinter')
        """
        self.schema = schema
        self.framework = framework
        self.factory = WidgetFactoryRegistry.get_factory(framework)
        if self.factory is None:
            raise ValueError(f"No widget factory registered for framework: {framework}")
        
        self.widgets: Dict[str, WidgetBase] = {}
        self.form_container: Any = None
        self._field_dependencies: Dict[str, List[str]] = {}
        self._visibility_callbacks: Dict[str, List] = {}

    @abstractmethod
    def build_form(self, config: dict = None, parent: Any = None) -> Any:
        """
        Build the complete form from the schema.

        Args:
            config: Optional initial configuration values
            parent: Optional parent widget

        Returns:
            Any: Form container widget
        """
        pass

    @abstractmethod
    def get_values(self) -> Dict[str, Any]:
        """
        Get current values from all form fields.

        Returns:
            Dict[str, Any]: Current field values
        """
        pass

    @abstractmethod
    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set values for all form fields.

        Args:
            config: Configuration values to set
        """
        pass

    @abstractmethod
    def validate(self) -> ValidationResult:
        """
        Validate the entire form.

        Returns:
            ValidationResult: Validation result
        """
        pass

    @abstractmethod
    def get_validation_errors(self) -> List[str]:
        """
        Get all validation errors from the form.

        Returns:
            List[str]: List of validation error messages
        """
        pass

    def set_field_visibility(self, field_name: str, visible: bool) -> None:
        """
        Set visibility of a specific field.

        Args:
            field_name: Field name to set visibility for
            visible: True if field should be visible, False otherwise
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_visible(visible)

    def set_field_enabled(self, field_name: str, enabled: bool) -> None:
        """
        Set enabled state of a specific field.

        Args:
            field_name: Field name to set enabled state for
            enabled: True if field should be enabled, False otherwise
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_enabled(enabled)

    def get_field_value(self, field_name: str) -> Any:
        """
        Get current value of a specific field.

        Args:
            field_name: Field name to get value for

        Returns:
            Any: Current field value
        """
        if field_name in self.widgets:
            return self.widgets[field_name].get_value()
        return None

    def set_field_value(self, field_name: str, value: Any) -> None:
        """
        Set value of a specific field.

        Args:
            field_name: Field name to set value for
            value: Value to set
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_value(value)

    def set_field_label(self, field_name: str, label: str) -> None:
        """
        Set label of a specific field.

        Args:
            field_name: Field name to set label for
            label: Label text
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_label(label)

    def set_field_description(self, field_name: str, description: str) -> None:
        """
        Set description of a specific field.

        Args:
            field_name: Field name to set description for
            description: Description text
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_description(description)

    def register_field_dependency(self, dependent_field: str, trigger_field: str, 
                                 condition: Optional[callable] = None):
        """
        Register a field dependency where the visibility of a field depends on
        the value of another field.

        Args:
            dependent_field: Field that depends on another field
            trigger_field: Field that triggers the dependency
            condition: Optional condition function that takes trigger field value
                and returns True if dependent field should be visible
        """
        if trigger_field not in self._field_dependencies:
            self._field_dependencies[trigger_field] = []
        self._field_dependencies[trigger_field].append(dependent_field)

        if condition is not None:
            if trigger_field not in self._visibility_callbacks:
                self._visibility_callbacks[trigger_field] = []
            self._visibility_callbacks[trigger_field].append(
                (dependent_field, condition)
            )

    @abstractmethod
    def _setup_field_dependencies(self):
        """
        Setup field dependencies and dynamic visibility callbacks.
        """
        pass

    def _update_dependent_fields(self, trigger_field: str):
        """
        Update the visibility of fields dependent on a trigger field.

        Args:
            trigger_field: Field that triggered the change
        """
        if trigger_field not in self._field_dependencies:
            return

        trigger_value = self.get_field_value(trigger_field)

        for dependent_field in self._field_dependencies[trigger_field]:
            # Determine if field should be visible
            visible = True
            if trigger_field in self._visibility_callbacks:
                for (dep_field, condition) in self._visibility_callbacks[trigger_field]:
                    if dep_field == dependent_field:
                        visible = condition(trigger_value)
                        break

            self.set_field_visibility(dependent_field, visible)


class QtFormGenerator(FormGenerator):
    """
    Qt implementation of the form generator.
    """

    def build_form(self, config: dict = None, parent: Any = None) -> Any:
        """
        Build the Qt form from the schema.

        Args:
            config: Optional initial configuration values
            parent: Optional parent widget

        Returns:
            Any: Qt form container widget
        """
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel

        # Create main container widget
        self.form_container = QWidget(parent)
        layout = QVBoxLayout(self.form_container)

        # Create widget builder
        from interface.plugins.ui_abstraction import ConfigurationWidgetBuilder
        
        class QtWidgetBuilder(ConfigurationWidgetBuilder):
            def _layout_widgets(self, widgets, schema, parent):
                container = QWidget(parent)
                form_layout = QFormLayout(container)
                
                for field in schema.fields:
                    widget = widgets[field.name]
                    native_widget = widget.get_widget()
                    
                    # For checkboxes, we don't need a separate label
                    if field.field_type == 'boolean':
                        form_layout.addRow(native_widget)
                    else:
                        # Create label with optional tooltip
                        label = QLabel(field.label)
                        if field.description:
                            label.setToolTip(field.description)
                        form_layout.addRow(label, native_widget)
                
                return container

        builder = QtWidgetBuilder('qt')
        widget_container = builder.build_configuration_panel(self.schema, config, parent)
        layout.addWidget(widget_container)

        # Store widget references
        for field in self.schema.fields:
            # We need to manually create widgets to store references
            widget = self.factory.create_widget(field.field_type, field, parent)
            self.widgets[field.name] = widget

        # Set initial values if provided
        if config:
            self.set_values(config)

        # Setup field dependencies
        self._setup_field_dependencies()

        return self.form_container

    def get_values(self) -> Dict[str, Any]:
        """
        Get current values from all Qt form fields.

        Returns:
            Dict[str, Any]: Current field values
        """
        values = {}
        for field_name, widget in self.widgets.items():
            values[field_name] = widget.get_value()
        return values

    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set values for all Qt form fields.

        Args:
            config: Configuration values to set
        """
        for field_name, value in config.items():
            if field_name in self.widgets:
                self.widgets[field_name].set_value(value)

    def validate(self) -> ValidationResult:
        """
        Validate the entire Qt form.

        Returns:
            ValidationResult: Validation result
        """
        all_errors = []
        for field_name, widget in self.widgets.items():
            if not widget.validate():
                all_errors.extend(widget.get_validation_errors())
        
        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)

    def get_validation_errors(self) -> List[str]:
        """
        Get all validation errors from the Qt form.

        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        for widget in self.widgets.values():
            errors.extend(widget.get_validation_errors())
        return errors

    def _setup_field_dependencies(self):
        """
        Setup field dependencies and dynamic visibility callbacks for Qt.
        """
        from PyQt6.QtCore import pyqtSignal, QObject

        # For each field, check if it has dependencies
        for trigger_field in self._field_dependencies:
            if trigger_field in self.widgets:
                widget = self.widgets[trigger_field]
                native_widget = widget.get_widget()
                
                # Connect value change signals
                if hasattr(native_widget, 'textChanged'):
                    native_widget.textChanged.connect(
                        lambda: self._update_dependent_fields(trigger_field)
                    )
                elif hasattr(native_widget, 'valueChanged'):
                    native_widget.valueChanged.connect(
                        lambda: self._update_dependent_fields(trigger_field)
                    )
                elif hasattr(native_widget, 'stateChanged'):
                    native_widget.stateChanged.connect(
                        lambda: self._update_dependent_fields(trigger_field)
                    )


class TkinterFormGenerator(FormGenerator):
    """
    Tkinter implementation of the form generator.
    """

    def build_form(self, config: dict = None, parent: Any = None) -> Any:
        """
        Build the Tkinter form from the schema.

        Args:
            config: Optional initial configuration values
            parent: Optional parent widget

        Returns:
            Any: Tkinter form container widget
        """
        import tkinter as tk
        from tkinter import ttk

        # Create main container widget
        self.form_container = ttk.Frame(parent)
        self.form_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create widget builder
        from interface.plugins.ui_abstraction import ConfigurationWidgetBuilder
        
        class TkinterWidgetBuilder(ConfigurationWidgetBuilder):
            def _layout_widgets(self, widgets, schema, parent):
                container = ttk.Frame(parent)
                
                row = 0
                for field in schema.fields:
                    widget = widgets[field.name]
                    native_widget = widget.get_widget()
                    
                    # Create label
                    label = ttk.Label(container, text=field.label)
                    label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
                    
                    # Place widget
                    if field.field_type == 'boolean':
                        native_widget.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
                    elif field.field_type in ['list', 'dict']:
                        native_widget.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
                        container.grid_columnconfigure(1, weight=1)
                    else:
                        native_widget.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
                        container.grid_columnconfigure(1, weight=1)
                    
                    # Add description as tooltip if available
                    if field.description:
                        label.bind("<Enter>", lambda e, d=field.description: self._show_tooltip(e, d))
                        native_widget.bind("<Enter>", lambda e, d=field.description: self._show_tooltip(e, d))
                    
                    row += 1
                
                return container

        builder = TkinterWidgetBuilder('tkinter')
        widget_container = builder.build_configuration_panel(self.schema, config, self.form_container)
        widget_container.pack(fill=tk.BOTH, expand=True)

        # Store widget references
        for field in self.schema.fields:
            widget = self.factory.create_widget(field.field_type, field, self.form_container)
            self.widgets[field.name] = widget

        # Set initial values if provided
        if config:
            self.set_values(config)

        # Setup field dependencies
        self._setup_field_dependencies()

        return self.form_container

    def get_values(self) -> Dict[str, Any]:
        """
        Get current values from all Tkinter form fields.

        Returns:
            Dict[str, Any]: Current field values
        """
        values = {}
        for field_name, widget in self.widgets.items():
            values[field_name] = widget.get_value()
        return values

    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set values for all Tkinter form fields.

        Args:
            config: Configuration values to set
        """
        for field_name, value in config.items():
            if field_name in self.widgets:
                self.widgets[field_name].set_value(value)

    def validate(self) -> ValidationResult:
        """
        Validate the entire Tkinter form.

        Returns:
            ValidationResult: Validation result
        """
        all_errors = []
        for field_name, widget in self.widgets.items():
            if not widget.validate():
                all_errors.extend(widget.get_validation_errors())
        
        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)

    def get_validation_errors(self) -> List[str]:
        """
        Get all validation errors from the Tkinter form.

        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        for widget in self.widgets.values():
            errors.extend(widget.get_validation_errors())
        return errors

    def _setup_field_dependencies(self):
        """
        Setup field dependencies and dynamic visibility callbacks for Tkinter.
        """
        # For each field, check if it has dependencies
        for trigger_field in self._field_dependencies:
            if trigger_field in self.widgets:
                widget = self.widgets[trigger_field]
                native_widget = widget.get_widget()
                
                # Bind value change events
                native_widget.bind('<FocusOut>', 
                    lambda e, tf=trigger_field: self._update_dependent_fields(tf))
                native_widget.bind('<KeyRelease>',
                    lambda e, tf=trigger_field: self._update_dependent_fields(tf))


class FormGeneratorFactory:
    """
    Factory for creating form generator instances.
    """

    @staticmethod
    def create_form_generator(schema: ConfigurationSchema, 
                             framework: str = 'qt') -> FormGenerator:
        """
        Create a form generator instance for the specified framework.

        Args:
            schema: Configuration schema
            framework: UI framework ('qt' or 'tkinter')

        Returns:
            FormGenerator: Form generator instance

        Raises:
            ValueError: If framework is not supported
        """
        if framework == 'qt':
            return QtFormGenerator(schema, framework)
        elif framework == 'tkinter':
            return TkinterFormGenerator(schema, framework)
        else:
            raise ValueError(f"Unsupported UI framework: {framework}")
