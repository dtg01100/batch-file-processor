"""
Config Section Widgets

Provides reusable configuration section widgets for the Qt framework.
These widgets enable plugins to create common UI sections that
can be reused across different configuration interfaces.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable

from ..plugins.config_schemas import ConfigurationSchema, FieldDefinition, FieldType
from ..plugins.ui_abstraction import WidgetBase, WidgetFactoryRegistry
from ..plugins.validation_framework import ValidationResult


class ConfigSectionWidget(ABC):
    """
    Base class for configuration section widgets.
    
    Provides common functionality for rendering and managing
    configuration sections with form fields.
    """

    def __init__(
        self,
        schema: ConfigurationSchema,
        framework: str = 'qt',
        parent: Any = None
    ):
        """
        Initialize the config section widget.
        
        Args:
            schema: Configuration schema for this section
            framework: UI framework ('qt')
            parent: Optional parent widget
        """
        self.schema = schema
        self.framework = framework
        self.parent = parent
        self.widgets: Dict[str, WidgetBase] = {}
        self.container: Any = None
        self._value_changed_callbacks: List[Callable] = []

    @abstractmethod
    def render(self, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Render the section widget.
        
        Args:
            config: Optional initial configuration values
            
        Returns:
            Any: Rendered widget container
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
        Validate the section's configuration.
        
        Returns:
            ValidationResult: Validation result
        """
        pass

    def get_validation_errors(self) -> List[str]:
        """
        Get all validation errors from the section.
        
        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        for widget in self.widgets.values():
            errors.extend(widget.get_validation_errors())
        return errors

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

    def set_field_visibility(self, field_name: str, visible: bool) -> None:
        """
        Set visibility of a specific field.
        
        Args:
            field_name: Field name to set visibility for
            visible: True if field should be visible
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_visible(visible)

    def set_field_enabled(self, field_name: str, enabled: bool) -> None:
        """
        Set enabled state of a specific field.
        
        Args:
            field_name: Field name to set enabled state for
            enabled: True if field should be enabled
        """
        if field_name in self.widgets:
            self.widgets[field_name].set_enabled(enabled)

    def register_value_changed_callback(self, callback: Callable) -> None:
        """
        Register a callback for value changes.
        
        Args:
            callback: Callback function to register
        """
        self._value_changed_callbacks.append(callback)

    def _notify_value_changed(self) -> None:
        """
        Notify all registered callbacks of value changes.
        """
        for callback in self._value_changed_callbacks:
            callback(self.get_values())


class QtConfigSectionWidget(ConfigSectionWidget):
    """
    Qt implementation of the config section widget.
    """

    def render(self, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Render the Qt section widget.
        
        Args:
            config: Optional initial configuration values
            
        Returns:
            Any: Qt widget container
        """
        from PyQt6.QtWidgets import (
            QWidget, QVBoxLayout, QFormLayout, QGroupBox, QLabel
        )

        self.container = QGroupBox(self.schema.title if hasattr(self.schema, 'title') else 'Configuration')
        layout = QVBoxLayout(self.container)

        form_layout = QFormLayout()
        
        factory = WidgetFactoryRegistry.get_factory(self.framework)
        if factory is None:
            raise ValueError(f"No widget factory registered for framework: {self.framework}")

        for field in self.schema.fields:
            widget = factory.create_widget(field.field_type, field, self.container)
            self.widgets[field.name] = widget
            
            if field.field_type == FieldType.BOOLEAN:
                form_layout.addRow(widget.get_widget())
            else:
                label = QLabel(field.label)
                if field.description:
                    label.setToolTip(field.description)
                form_layout.addRow(label, widget.get_widget())

        layout.addLayout(form_layout)

        if config:
            self.set_values(config)

        return self.container

    def get_values(self) -> Dict[str, Any]:
        """
        Get current values from all form fields.
        
        Returns:
            Dict[str, Any]: Current field values
        """
        values = {}
        for field_name, widget in self.widgets.items():
            values[field_name] = widget.get_value()
        return values

    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set values for all form fields.
        
        Args:
            config: Configuration values to set
        """
        for field_name, value in config.items():
            if field_name in self.widgets:
                self.widgets[field_name].set_value(value)

    def validate(self) -> ValidationResult:
        """
        Validate the section's configuration.
        
        Returns:
            ValidationResult: Validation result
        """
        all_errors = self.get_validation_errors()
        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)


class CollapsibleSectionWidget(ConfigSectionWidget):
    """
    Config section widget with collapsible functionality.
    
    Provides a section that can be expanded or collapsed by the user.
    """

    def __init__(
        self,
        schema: ConfigurationSchema,
        framework: str = 'qt',
        parent: Any = None,
        expanded: bool = True
    ):
        """
        Initialize the collapsible section widget.
        
        Args:
            schema: Configuration schema for this section
            framework: UI framework ('qt')
            parent: Optional parent widget
            expanded: Whether section is expanded by default
        """
        super().__init__(schema, framework, parent)
        self.expanded = expanded

    @abstractmethod
    def toggle(self) -> None:
        """
        Toggle the collapsed/expanded state.
        """
        pass


class QtCollapsibleSectionWidget(CollapsibleSectionWidget):
    """
    Qt implementation of the collapsible config section widget.
    """

    def render(self, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Render the Qt collapsible section widget.
        
        Args:
            config: Optional initial configuration values
            
        Returns:
            Any: Qt widget container
        """
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox

        self.container = QGroupBox(
            self.schema.title if hasattr(self.schema, 'title') else 'Configuration'
        )
        self.container.setCheckable(True)
        self.container.setChecked(self.expanded)
        
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)

        factory = WidgetFactoryRegistry.get_factory(self.framework)
        if factory is None:
            raise ValueError(f"No widget factory registered for framework: {self.framework}")

        for field in self.schema.fields:
            widget = factory.create_widget(field.field_type, field, self._content_widget)
            self.widgets[field.name] = widget
            
            if field.field_type == FieldType.BOOLEAN:
                self._content_layout.addWidget(widget.get_widget())
            else:
                from PyQt6.QtWidgets import QFormLayout
                form_layout = QFormLayout()
                form_layout.addRow(field.label, widget.get_widget())
                self._content_layout.addLayout(form_layout)

        layout = QVBoxLayout(self.container)
        layout.addWidget(self._content_widget)

        if config:
            self.set_values(config)

        return self.container

    def get_values(self) -> Dict[str, Any]:
        """
        Get current values from all form fields.
        
        Returns:
            Dict[str, Any]: Current field values
        """
        values = {}
        for field_name, widget in self.widgets.items():
            values[field_name] = widget.get_value()
        return values

    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set values for all form fields.
        
        Args:
            config: Configuration values to set
        """
        for field_name, value in config.items():
            if field_name in self.widgets:
                self.widgets[field_name].set_value(value)

    def validate(self) -> ValidationResult:
        """
        Validate the section's configuration.
        
        Returns:
            ValidationResult: Validation result
        """
        all_errors = self.get_validation_errors()
        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)

    def toggle(self) -> None:
        """
        Toggle the collapsed/expanded state.
        """
        self.expanded = not self.expanded
        self.container.setChecked(self.expanded)
        self._content_widget.setVisible(self.expanded)


class TabbedSectionWidget(ConfigSectionWidget):
    """
    Config section widget with tabs for organizing multiple sections.
    
    Provides a tabbed interface where each tab contains a different
    configuration section.
    """

    def __init__(
        self,
        sections: List[ConfigurationSchema],
        framework: str = 'qt',
        parent: Any = None
    ):
        """
        Initialize the tabbed section widget.
        
        Args:
            sections: List of configuration schemas for each tab
            framework: UI framework ('qt')
            parent: Optional parent widget
        """
        self.sections = sections
        self.section_widgets: List[ConfigSectionWidget] = []
        super().__init__(sections[0] if sections else ConfigurationSchema([]), framework, parent)

    def render(self, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Render the tabbed section widget.
        
        Args:
            config: Optional initial configuration values
            
        Returns:
            Any: Qt tab widget container
        """
        if self.framework == 'qt':
            return self._render_qt(config)
        else:
            return self._render_qt(config)

    def _render_qt(self, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Render Qt tabbed section widget.
        """
        from PyQt6.QtWidgets import QTabWidget, QWidget

        self.container = QTabWidget(self.parent)
        
        for schema in self.sections:
            section_widget = QtConfigSectionWidget(schema, self.framework, self.container)
            tab = section_widget.render(config)
            self.container.addTab(tab, schema.title if hasattr(schema, 'title') else 'Tab')
            self.section_widgets.append(section_widget)

        return self.container

    def get_values(self) -> Dict[str, Any]:
        """
        Get current values from all tabs.
        
        Returns:
            Dict[str, Any]: Current field values from all sections
        """
        values = {}
        for section_widget in self.section_widgets:
            values.update(section_widget.get_values())
        return values

    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set values for all tabs.
        
        Args:
            config: Configuration values to set
        """
        for section_widget in self.section_widgets:
            section_widget.set_values(config)

    def validate(self) -> ValidationResult:
        """
        Validate all tabs.
        
        Returns:
            ValidationResult: Combined validation result
        """
        all_errors = []
        for section_widget in self.section_widgets:
            all_errors.extend(section_widget.get_validation_errors())
        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)
