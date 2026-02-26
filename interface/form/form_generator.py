"""
Dynamic Form Generator

Provides a framework-agnostic form generator that can dynamically render UI
from ConfigurationSchema definitions. Supports the Qt framework
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
            framework: UI framework to use ('qt')
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
        self._plugin_sections: List[WidgetBase] = []
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}

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

    def add_plugin_section(
        self,
        section_id: str,
        schema: ConfigurationSchema,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a plugin configuration section to the form.

        Args:
            section_id: Unique identifier for the section
            schema: Configuration schema for the section
            config: Optional initial configuration values
        """
        self._plugin_configs[section_id] = config or {}
        # This will be rendered in build_form when _render_plugin_sections is called

    def add_plugin_sections(
        self,
        sections: List[Dict[str, Any]]
    ) -> None:
        """
        Add multiple plugin configuration sections to the form.

        Args:
            sections: List of section definitions with 'id', 'schema', and optional 'config'
        """
        for section in sections:
            self.add_plugin_section(
                section.get('id', f'section_{len(self._plugin_sections)}'),
                section.get('schema'),
                section.get('config')
            )

    def get_plugin_section_values(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration values from all plugin sections.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping section IDs to their values
        """
        values = {}
        for section in self._plugin_sections:
            if hasattr(section, 'get_values'):
                section_id = getattr(section, 'section_id', 'unknown')
                values[section_id] = section.get_values()
        return values

    def set_plugin_section_values(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Set configuration values for plugin sections.

        Args:
            configs: Dictionary mapping section IDs to their configuration values
        """
        for section in self._plugin_sections:
            section_id = getattr(section, 'section_id', None)
            if section_id and section_id in configs:
                section.set_values(configs[section_id])

    def validate_plugin_sections(self) -> ValidationResult:
        """
        Validate all plugin sections.

        Returns:
            ValidationResult: Combined validation result for all sections
        """
        all_errors = []
        for section in self._plugin_sections:
            if hasattr(section, 'validate'):
                result = section.validate()
                if not result.success:
                    all_errors.extend(result.errors)
            elif hasattr(section, 'get_validation_errors'):
                all_errors.extend(section.get_validation_errors())
        
        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)


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

        # Render plugin sections
        self._render_plugin_sections(parent)

        return self.form_container

    def _render_plugin_sections(self, parent: Any = None) -> None:
        """
        Render plugin sections added to the form.

        Args:
            parent: Optional parent widget
        """
        if not self._plugin_configs:
            return

        from interface.form.section_factory import SectionFactoryRegistry

        try:
            section_layout = self.form_container.layout()
            
            for section_id, schema in self._plugin_configs.items():
                if schema is None:
                    continue
                    
                config = self._plugin_configs.get(section_id)
                section_widget = SectionFactoryRegistry.create_section(
                    'default',
                    schema,
                    self.framework,
                    config,
                    self.form_container
                )
                
                if section_widget:
                    section_widget.section_id = section_id
                    self._plugin_sections.append(section_widget)
                    native_widget = section_widget.render(config)
                    section_layout.addWidget(native_widget)
                    
        except Exception as e:
            print(f"Error rendering plugin sections: {e}")

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
            framework: UI framework ('qt')

        Returns:
            FormGenerator: Form generator instance

        Raises:
            ValueError: If framework is not supported
        """
        if framework == 'qt':
            return QtFormGenerator(schema, framework)
        else:
            raise ValueError(f"Unsupported UI framework: {framework}")
