"""Plugin Configuration Data Mapping Layer.

This module provides a centralized data mapping layer for handling plugin configurations
between the UI dialogs and the FolderConfiguration model. It supports both Qt and Tkinter
widget systems, providing methods to extract, populate, and validate plugin configurations.

Key components:
- PluginConfigurationMapper: Core class for handling plugin configuration mapping
- ExtractedPluginConfig: Container for extracted plugin configuration data
- PluginConfigPopulationResult: Result object for widget population operations
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from interface.models.folder_configuration import FolderConfiguration
from interface.plugins.plugin_manager import PluginManager
from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.plugins.ui_abstraction import WidgetBase
from interface.plugins.validation_framework import ValidationResult


@dataclass
class ExtractedPluginConfig:
    """Container for extracted plugin configuration data."""
    format_name: str
    config: Dict[str, Any]
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class PluginConfigPopulationResult:
    """Result object for widget population operations."""
    success: bool
    widget_count: int = 0
    errors: List[str] = field(default_factory=list)


class PluginConfigurationMapper:
    """
    Data mapping layer for plugin configurations between dialogs and FolderConfiguration model.
    
    Handles the extraction, population, and validation of plugin configurations from both
    Qt and Tkinter widget systems, providing a unified interface for working with plugin data.
    """
    
    def __init__(self):
        """Initialize the plugin configuration mapper."""
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
    
    def extract_plugin_configurations(self, dialog_fields: Dict[str, Any],
                                     framework: str = 'qt') -> List[ExtractedPluginConfig]:
        """
        Extract plugin configurations from the edit folders dialog.
        
        Args:
            dialog_fields: Dictionary mapping field names to widget references
            framework: UI framework to use ('qt' or 'tkinter')
            
        Returns:
            List[ExtractedPluginConfig]: Extracted plugin configurations with validation errors
        """
        extracted_configs = []
        
        # Get all available configuration plugins
        config_plugins = self.plugin_manager.get_configuration_plugins()
        
        for plugin in config_plugins:
            try:
                # Extract configuration from widgets
                config = self._extract_plugin_config(plugin, dialog_fields, framework)
                
                # Validate the extracted configuration
                validation = plugin.validate_config(config)
                
                extracted_configs.append(
                    ExtractedPluginConfig(
                        format_name=plugin.get_format_name(),
                        config=config,
                        validation_errors=validation.errors
                    )
                )
            except Exception as e:
                extracted_configs.append(
                    ExtractedPluginConfig(
                        format_name=plugin.get_format_name(),
                        config={},
                        validation_errors=[f"Error extracting configuration: {str(e)}"]
                    )
                )
        
        return extracted_configs
    
    def _extract_plugin_config(self, plugin: ConfigurationPlugin,
                              dialog_fields: Dict[str, Any],
                              framework: str) -> Dict[str, Any]:
        """
        Extract configuration for a specific plugin.
        
        Args:
            plugin: Configuration plugin to extract data for
            dialog_fields: Dictionary mapping field names to widget references
            framework: UI framework to use ('qt' or 'tkinter')
            
        Returns:
            Dict[str, Any]: Extracted plugin configuration
        """
        config = {}
        
        # Get the configuration schema for the plugin
        schema = plugin.get_configuration_schema()
        
        if schema:
            # Extract values from widgets based on schema fields
            for field in schema.fields:
                field_name = field.name
                widget = dialog_fields.get(field_name)
                
                if widget:
                    try:
                        if isinstance(widget, WidgetBase):
                            # If widget is already using the UI abstraction layer
                            config[field_name] = widget.get_value()
                        else:
                            # Direct widget access based on framework
                            config[field_name] = self._get_widget_value(widget, field_name, framework)
                    except Exception as e:
                        config[field_name] = field.default
        
        return config
    
    def _get_widget_value(self, widget: Any, field_name: str, framework: str) -> Any:
        """
        Get widget value based on UI framework.
        
        Args:
            widget: Native widget instance
            field_name: Field name for context
            framework: UI framework identifier
            
        Returns:
            Any: Widget value
        """
        if framework == 'qt':
            return self._get_qt_widget_value(widget)
        elif framework == 'tkinter':
            return self._get_tkinter_widget_value(widget)
        else:
            raise ValueError(f"Unsupported UI framework: {framework}")
    
    def _get_qt_widget_value(self, widget: Any) -> Any:
        """
        Get value from a Qt widget.
        
        Args:
            widget: Qt widget instance
            
        Returns:
            Any: Widget value
        """
        # Import Qt modules dynamically to avoid circular dependencies
        from PyQt5.QtWidgets import (
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
            QListWidget, QTextEdit
        )
        
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QComboBox):
            return widget.currentData()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QListWidget):
            selected = []
            for item in widget.selectedItems():
                selected.append(item.data(0))
            return selected
        elif isinstance(widget, QTextEdit):
            try:
                import json
                return json.loads(widget.toPlainText())
            except Exception:
                return {}
        else:
            return ""
    
    def _get_tkinter_widget_value(self, widget: Any) -> Any:
        """
        Get value from a Tkinter widget.
        
        Args:
            widget: Tkinter widget instance
            
        Returns:
            Any: Widget value
        """
        import tkinter as tk
        from tkinter import ttk
        
        if hasattr(widget, 'get'):
            try:
                return widget.get()
            except Exception:
                return ""
        elif isinstance(widget, tk.Listbox):
            selected_indices = widget.curselection()
            return [widget.get(index) for index in selected_indices]
        elif isinstance(widget, tk.Text):
            try:
                import json
                return json.loads(widget.get("1.0", tk.END))
            except Exception:
                return {}
        else:
            return ""
    
    def populate_plugin_widgets(self, folder_config: FolderConfiguration,
                              dialog_fields: Dict[str, Any],
                              framework: str = 'qt') -> PluginConfigPopulationResult:
        """
        Populate plugin widgets with data from FolderConfiguration.
        
        Args:
            folder_config: Folder configuration to populate widgets with
            dialog_fields: Dictionary mapping field names to widget references
            framework: UI framework to use ('qt' or 'tkinter')
            
        Returns:
            PluginConfigPopulationResult: Result of the population operation
        """
        result = PluginConfigPopulationResult(success=True)
        
        # Get all available configuration plugins
        config_plugins = self.plugin_manager.get_configuration_plugins()
        
        for plugin in config_plugins:
            try:
                # Get the configuration for this plugin's format
                config = folder_config.get_plugin_configuration(plugin.get_format_name())
                
                if config:
                    # Get the schema and populate widgets
                    schema = plugin.get_configuration_schema()
                    if schema:
                        for field in schema.fields:
                            field_name = field.name
                            widget = dialog_fields.get(field_name)
                            
                            if widget and field_name in config:
                                try:
                                    if isinstance(widget, WidgetBase):
                                        widget.set_value(config[field_name])
                                    else:
                                        self._set_widget_value(widget, config[field_name], framework)
                                    result.widget_count += 1
                                except Exception as e:
                                    result.errors.append(
                                        f"Error setting '{field_name}' for {plugin.get_format_name()}: {str(e)}"
                                    )
            except Exception as e:
                result.errors.append(
                    f"Error populating plugin {plugin.get_format_name()}: {str(e)}"
                )
        
        result.success = len(result.errors) == 0
        return result
    
    def _set_widget_value(self, widget: Any, value: Any, framework: str) -> None:
        """
        Set widget value based on UI framework.
        
        Args:
            widget: Native widget instance
            value: Value to set
            framework: UI framework identifier
        """
        if framework == 'qt':
            self._set_qt_widget_value(widget, value)
        elif framework == 'tkinter':
            self._set_tkinter_widget_value(widget, value)
        else:
            raise ValueError(f"Unsupported UI framework: {framework}")
    
    def _set_qt_widget_value(self, widget: Any, value: Any) -> None:
        """
        Set value for a Qt widget.
        
        Args:
            widget: Qt widget instance
            value: Value to set
        """
        from PyQt5.QtWidgets import (
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
            QListWidget, QTextEdit
        )
        
        if isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QListWidget):
            for i in range(widget.count()):
                item = widget.item(i)
                item.setSelected(item.data(0) in value)
        elif isinstance(widget, QTextEdit):
            import json
            widget.setText(json.dumps(value, indent=2))
    
    def _set_tkinter_widget_value(self, widget: Any, value: Any) -> None:
        """
        Set value for a Tkinter widget.
        
        Args:
            widget: Tkinter widget instance
            value: Value to set
        """
        import tkinter as tk
        from tkinter import ttk
        
        if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
        elif hasattr(widget, 'set'):
            widget.set(value)
        elif isinstance(widget, tk.Listbox):
            widget.selection_clear(0, tk.END)
            if isinstance(value, list):
                for item in value:
                    try:
                        index = widget.get(0, tk.END).index(item)
                        widget.selection_set(index)
                    except ValueError:
                        pass
        elif isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            import json
            widget.insert("1.0", json.dumps(value, indent=2))
    
    def update_folder_configuration(self, folder_config: FolderConfiguration,
                                   extracted_configs: List[ExtractedPluginConfig]) -> None:
        """
        Update FolderConfiguration with extracted plugin configurations.
        
        Args:
            folder_config: Folder configuration to update
            extracted_configs: Extracted plugin configurations to apply
        """
        for config_data in extracted_configs:
            if not config_data.validation_errors:
                folder_config.set_plugin_configuration(
                    config_data.format_name,
                    config_data.config
                )
            else:
                folder_config.remove_plugin_configuration(config_data.format_name)
    
    def validate_plugin_configurations(self, folder_config: FolderConfiguration) -> List[str]:
        """
        Validate all plugin configurations in FolderConfiguration.
        
        Args:
            folder_config: Folder configuration to validate
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        for format_name, config in folder_config.plugin_configurations.items():
            try:
                plugin = self.plugin_manager.get_configuration_plugin_by_format_name(format_name)
                
                if plugin:
                    validation: ValidationResult = plugin.validate_config(config)
                    if not validation.success:
                        for error in validation.errors:
                            errors.append(f"Plugin config for {format_name}: {error}")
                else:
                    errors.append(f"No configuration plugin found for format: {format_name}")
            except Exception as e:
                errors.append(f"Error validating plugin config for {format_name}: {str(e)}")
        
        return errors
    
    def get_plugin_configuration_fields(self, format_name: str) -> List[Dict[str, Any]]:
        """
        Get the configuration fields for a specific plugin format.
        
        Args:
            format_name: The convert format name (e.g., "csv", "ScannerWare")
            
        Returns:
            List[Dict[str, Any]]: List of field definitions with metadata
        """
        plugin = self.plugin_manager.get_configuration_plugin_by_format_name(format_name)
        
        if plugin:
            schema = plugin.get_configuration_schema()
            if schema:
                fields = []
                for field in schema.fields:
                    fields.append({
                        'name': field.name,
                        'type': field.field_type,
                        'label': field.label,
                        'description': field.description,
                        'default': field.default,
                        'required': field.required,
                        'choices': field.choices,
                        'min_value': field.min_value,
                        'max_value': field.max_value,
                        'min_length': field.min_length,
                        'max_length': field.max_length
                    })
                return fields
        
        return []
    
    def get_supported_plugin_formats(self) -> List[str]:
        """
        Get all supported plugin formats.
        
        Returns:
            List[str]: List of supported plugin format names
        """
        config_plugins = self.plugin_manager.get_configuration_plugins()
        return [plugin.get_format_name() for plugin in config_plugins]


class BasePluginConfigExtractor(ABC):
    """
    Base abstract class for plugin configuration extractors.
    
    Provides a template for implementing framework-specific extractors.
    """
    
    @abstractmethod
    def extract(self, dialog_fields: Dict[str, Any]) -> List[ExtractedPluginConfig]:
        """
        Extract plugin configurations from dialog fields.
        
        Args:
            dialog_fields: Dictionary mapping field names to widget references
            
        Returns:
            List[ExtractedPluginConfig]: Extracted plugin configurations
        """
        pass


class QtPluginConfigExtractor(BasePluginConfigExtractor):
    """
    Qt-specific plugin configuration extractor.
    """
    
    def __init__(self):
        """Initialize the Qt plugin config extractor."""
        self.mapper = PluginConfigurationMapper()
    
    def extract(self, dialog_fields: Dict[str, Any]) -> List[ExtractedPluginConfig]:
        """
        Extract plugin configurations from Qt dialog fields.
        
        Args:
            dialog_fields: Dictionary mapping field names to Qt widget references
            
        Returns:
            List[ExtractedPluginConfig]: Extracted plugin configurations
        """
        return self.mapper.extract_plugin_configurations(dialog_fields, framework='qt')


class TkinterPluginConfigExtractor(BasePluginConfigExtractor):
    """
    Tkinter-specific plugin configuration extractor.
    """
    
    def __init__(self):
        """Initialize the Tkinter plugin config extractor."""
        self.mapper = PluginConfigurationMapper()
    
    def extract(self, dialog_fields: Dict[str, Any]) -> List[ExtractedPluginConfig]:
        """
        Extract plugin configurations from Tkinter dialog fields.
        
        Args:
            dialog_fields: Dictionary mapping field names to Tkinter widget references
            
        Returns:
            List[ExtractedPluginConfig]: Extracted plugin configurations
        """
        return self.mapper.extract_plugin_configurations(dialog_fields, framework='tkinter')


class BasePluginWidgetPopulator(ABC):
    """
    Base abstract class for plugin widget populators.
    
    Provides a template for implementing framework-specific widget population.
    """
    
    @abstractmethod
    def populate(self, folder_config: FolderConfiguration,
                dialog_fields: Dict[str, Any]) -> PluginConfigPopulationResult:
        """
        Populate plugin widgets with data from FolderConfiguration.
        
        Args:
            folder_config: Folder configuration to populate widgets with
            dialog_fields: Dictionary mapping field names to widget references
            
        Returns:
            PluginConfigPopulationResult: Result of the population operation
        """
        pass


class QtPluginWidgetPopulator(BasePluginWidgetPopulator):
    """
    Qt-specific plugin widget populator.
    """
    
    def __init__(self):
        """Initialize the Qt plugin widget populator."""
        self.mapper = PluginConfigurationMapper()
    
    def populate(self, folder_config: FolderConfiguration,
                dialog_fields: Dict[str, Any]) -> PluginConfigPopulationResult:
        """
        Populate Qt plugin widgets with data from FolderConfiguration.
        
        Args:
            folder_config: Folder configuration to populate widgets with
            dialog_fields: Dictionary mapping field names to Qt widget references
            
        Returns:
            PluginConfigPopulationResult: Result of the population operation
        """
        return self.mapper.populate_plugin_widgets(folder_config, dialog_fields, framework='qt')


class TkinterPluginWidgetPopulator(BasePluginWidgetPopulator):
    """
    Tkinter-specific plugin widget populator.
    """
    
    def __init__(self):
        """Initialize the Tkinter plugin widget populator."""
        self.mapper = PluginConfigurationMapper()
    
    def populate(self, folder_config: FolderConfiguration,
                dialog_fields: Dict[str, Any]) -> PluginConfigPopulationResult:
        """
        Populate Tkinter plugin widgets with data from FolderConfiguration.
        
        Args:
            folder_config: Folder configuration to populate widgets with
            dialog_fields: Dictionary mapping field names to Tkinter widget references
            
        Returns:
            PluginConfigPopulationResult: Result of the population operation
        """
        return self.mapper.populate_plugin_widgets(folder_config, dialog_fields, framework='tkinter')
