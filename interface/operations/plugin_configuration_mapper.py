"""Plugin Configuration Data Mapping Layer.

This module provides a centralized data mapping layer for handling plugin configurations
between the UI dialogs and the FolderConfiguration model. It supports the Qt
widget system, providing methods to extract, populate, and validate plugin configurations.

Key components:
- PluginConfigurationMapper: Core class for handling plugin configuration mapping
- ExtractedPluginConfig: Container for extracted plugin configuration data
- PluginConfigPopulationResult: Result object for widget population operations
- PluginSectionStateManager: State management for plugin sections with undo/redo support
"""

import json
import copy
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from interface.models.folder_configuration import FolderConfiguration
from interface.plugins.plugin_manager import PluginManager
from interface.plugins.configuration_plugin import ConfigurationPlugin
from interface.plugins.ui_abstraction import WidgetBase
from interface.plugins.validation_framework import ValidationResult
from interface.plugins.config_schemas import ConfigurationSchema


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


@dataclass
class PluginSectionState:
    """Represents a snapshot of plugin section state."""
    format_name: str
    config: Dict[str, Any]
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    timestamp: float = 0.0


class PluginSectionStateManager:
    """
    State manager for tracking changes in plugin sections.
    
    Provides:
    - Dirty state tracking
    - Validation state management
    - Undo/redo functionality
    """
    
    def __init__(self):
        """Initialize the state manager."""
        self._current_states: Dict[str, PluginSectionState] = {}
        self._undo_stack: List[Dict[str, PluginSectionState]] = []
        self._redo_stack: List[Dict[str, PluginSectionState]] = []
        self._max_undo_levels = 50
        self._is_dirty = False
        self._last_saved_state: Optional[Dict[str, PluginSectionState]] = None
    
    def initialize_state(self, format_name: str, config: Dict[str, Any], 
                        is_valid: bool = True, validation_errors: List[str] = None) -> None:
        """
        Initialize state for a plugin section.
        
        Args:
            format_name: Plugin format name
            config: Configuration dictionary
            is_valid: Whether the configuration is valid
            validation_errors: List of validation errors
        """
        state = PluginSectionState(
            format_name=format_name,
            config=copy.deepcopy(config),
            is_valid=is_valid,
            validation_errors=validation_errors or [],
            timestamp=0.0
        )
        self._current_states[format_name.lower()] = state
        self._last_saved_state = copy.deepcopy(self._current_states)
        self._is_dirty = False
    
    def update_state(self, format_name: str, config: Dict[str, Any],
                    is_valid: bool = True, validation_errors: List[str] = None) -> bool:
        """
        Update state for a plugin section.
        
        Args:
            format_name: Plugin format name
            config: Configuration dictionary
            is_valid: Whether the configuration is valid
            validation_errors: List of validation errors
            
        Returns:
            bool: True if state was changed, False if unchanged
        """
        format_lower = format_name.lower()
        current_config = self._current_states.get(format_lower)
        
        if current_config:
            if current_config.config == config:
                return False
            
            self._save_to_undo_stack()
        
        import time
        state = PluginSectionState(
            format_name=format_name,
            config=copy.deepcopy(config),
            is_valid=is_valid,
            validation_errors=validation_errors or [],
            timestamp=time.time()
        )
        self._current_states[format_lower] = state
        self._is_dirty = True
        self._redo_stack.clear()
        
        return True
    
    def _save_to_undo_stack(self) -> None:
        """Save current state to undo stack."""
        state_copy = copy.deepcopy(self._current_states)
        self._undo_stack.append(state_copy)
        
        if len(self._undo_stack) > self._max_undo_levels:
            self._undo_stack.pop(0)
    
    def undo(self) -> bool:
        """
        Undo the last state change.
        
        Returns:
            bool: True if undo was successful
        """
        if not self._undo_stack:
            return False
        
        self._redo_stack.append(copy.deepcopy(self._current_states))
        self._current_states = self._undo_stack.pop()
        self._check_dirty_state()
        
        return True
    
    def redo(self) -> bool:
        """
        Redo the last undone state change.
        
        Returns:
            bool: True if redo was successful
        """
        if not self._redo_stack:
            return False
        
        self._undo_stack.append(copy.deepcopy(self._current_states))
        self._current_states = self._redo_stack.pop()
        self._check_dirty_state()
        
        return True
    
    def _check_dirty_state(self) -> None:
        """Check if current state is dirty compared to last saved state."""
        if self._last_saved_state is None:
            self._is_dirty = True
            return
        
        self._is_dirty = (
            self._current_states != self._last_saved_state
        )
    
    def mark_saved(self) -> None:
        """Mark current state as saved."""
        self._last_saved_state = copy.deepcopy(self._current_states)
        self._is_dirty = False
    
    def reset_to_saved(self) -> None:
        """Reset to the last saved state."""
        if self._last_saved_state:
            self._current_states = copy.deepcopy(self._last_saved_state)
            self._is_dirty = False
            self._undo_stack.clear()
            self._redo_stack.clear()
    
    def get_state(self, format_name: str) -> Optional[PluginSectionState]:
        """
        Get the current state for a plugin format.
        
        Args:
            format_name: Plugin format name
            
        Returns:
            Optional[PluginSectionState]: Current state or None
        """
        return self._current_states.get(format_name.lower())
    
    def get_all_states(self) -> Dict[str, PluginSectionState]:
        """
        Get all current states.
        
        Returns:
            Dict[str, PluginSectionState]: All current states
        """
        return copy.deepcopy(self._current_states)
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all current configurations.
        
        Returns:
            Dict[str, Dict[str, Any]]: All configurations
        """
        return {
            name: state.config 
            for name, state in self._current_states.items()
        }
    
    @property
    def is_dirty(self) -> bool:
        """Check if there are unsaved changes."""
        return self._is_dirty
    
    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0
    
    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    def get_invalid_sections(self) -> List[str]:
        """
        Get list of sections with validation errors.
        
        Returns:
            List[str]: List of format names with validation errors
        """
        return [
            name for name, state in self._current_states.items()
            if not state.is_valid
        ]
    
    def get_all_validation_errors(self) -> List[str]:
        """
        Get all validation errors from all sections.
        
        Returns:
            List[str]: All validation errors
        """
        errors = []
        for state in self._current_states.values():
            errors.extend(state.validation_errors)
        return errors
    
    def clear(self) -> None:
        """Clear all state."""
        self._current_states.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._last_saved_state = None
        self._is_dirty = False


class PluginConfigurationMapper:
    """
    Data mapping layer for plugin configurations between dialogs and FolderConfiguration model.
    
    Handles the extraction, population, and validation of plugin configurations from the
    Qt widget system, providing a unified interface for working with plugin data.
    """
    
    def __init__(self):
        """Initialize the plugin configuration mapper."""
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.plugin_manager.initialize_plugins()
        self.state_manager = PluginSectionStateManager()
    
    def extract_plugin_configurations(self, dialog_fields: Dict[str, Any],
                                     framework: str = 'qt') -> List[ExtractedPluginConfig]:
        """
        Extract plugin configurations from the edit folders dialog.
        
        Args:
            dialog_fields: Dictionary mapping field names to widget references
            framework: UI framework to use ('qt')
            
        Returns:
            List[ExtractedPluginConfig]: Extracted plugin configurations with validation errors
        """
        extracted_configs = []
        
        config_plugins = self.plugin_manager.get_configuration_plugins()
        
        for plugin in config_plugins:
            try:
                config = self._extract_plugin_config(plugin, dialog_fields, framework)
                
                validation = plugin.validate_config(config)
                
                extracted_configs.append(
                    ExtractedPluginConfig(
                        format_name=plugin.get_format_name(),
                        config=config,
                        validation_errors=validation.errors
                    )
                )
                
                self.state_manager.update_state(
                    plugin.get_format_name(),
                    config,
                    validation.success,
                    validation.errors
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
            framework: UI framework to use ('qt')
            
        Returns:
            Dict[str, Any]: Extracted plugin configuration
        """
        config = {}
        
        schema = plugin.get_configuration_schema()
        
        if schema:
            for field in schema.fields:
                field_name = field.name
                widget = dialog_fields.get(field_name)
                
                if widget:
                    try:
                        if isinstance(widget, WidgetBase):
                            config[field_name] = widget.get_value()
                        else:
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
        from PyQt5.QtWidgets import (
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
            QListWidget, QTextEdit
        )
        
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
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
                return json.loads(widget.toPlainText())
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
            framework: UI framework to use ('qt')
            
        Returns:
            PluginConfigPopulationResult: Result of the population operation
        """
        result = PluginConfigPopulationResult(success=True)
        
        config_plugins = self.plugin_manager.get_configuration_plugins()
        
        for plugin in config_plugins:
            try:
                config = folder_config.get_plugin_configuration(plugin.get_format_name())
                
                if config:
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
                    
                    self.state_manager.initialize_state(
                        plugin.get_format_name(),
                        config,
                        True,
                        []
                    )
            except Exception as e:
                result.errors.append(
                    f"Error populating plugin {plugin.get_format_name()}: {str(e)}"
                )
        
        result.success = len(result.errors) == 0
        return result
    
    def populate_plugin_widgets_from_dict(self, folder_config_dict: Dict[str, Any],
                                         dialog_fields: Dict[str, Any],
                                         framework: str = 'qt') -> PluginConfigPopulationResult:
        """
        Populate plugin widgets with data from folder config dict.
        
        Args:
            folder_config_dict: Folder configuration dictionary
            dialog_fields: Dictionary mapping field names to widget references
            framework: UI framework to use ('qt')
            
        Returns:
            PluginConfigPopulationResult: Result of the population operation
        """
        folder_config = FolderConfiguration.from_dict(folder_config_dict)
        return self.populate_plugin_widgets(folder_config, dialog_fields, framework)
    
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
            widget.setText(json.dumps(value, indent=2))
    
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
    
    def update_folder_configuration_from_dict(self, folder_config_dict: Dict[str, Any],
                                              extracted_configs: List[ExtractedPluginConfig]) -> Dict[str, Any]:
        """
        Update folder config dict with extracted plugin configurations.
        
        Args:
            folder_config_dict: Folder configuration dictionary to update
            extracted_configs: Extracted plugin configurations to apply
            
        Returns:
            Dict[str, Any]: Updated folder configuration dictionary
        """
        plugin_configs = {}
        
        for config_data in extracted_configs:
            if not config_data.validation_errors:
                plugin_configs[config_data.format_name.lower()] = config_data.config
        
        folder_config_dict['plugin_configurations'] = plugin_configs
        return folder_config_dict
    
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
    
    def validate_plugin_configurations_from_dict(self, folder_config_dict: Dict[str, Any]) -> List[str]:
        """
        Validate all plugin configurations in folder config dict.
        
        Args:
            folder_config_dict: Folder configuration dictionary
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        plugin_configs = folder_config_dict.get('plugin_configurations', {})
        
        for format_name, config in plugin_configs.items():
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
    
    def serialize_plugin_config(self, format_name: str, config: Dict[str, Any]) -> str:
        """
        Serialize plugin configuration to JSON string.
        
        Args:
            format_name: Plugin format name
            config: Configuration dictionary
            
        Returns:
            str: JSON serialized configuration
        """
        data = {
            'format_name': format_name,
            'config': config
        }
        return json.dumps(data)
    
    def deserialize_plugin_config(self, serialized: str) -> Tuple[str, Dict[str, Any]]:
        """
        Deserialize plugin configuration from JSON string.
        
        Args:
            serialized: JSON serialized configuration
            
        Returns:
            Tuple[str, Dict[str, Any]]: Format name and configuration
        """
        data = json.loads(serialized)
        return data.get('format_name', ''), data.get('config', {})
    
    def get_state_manager(self) -> PluginSectionStateManager:
        """
        Get the state manager instance.
        
        Returns:
            PluginSectionStateManager: State manager
        """
        return self.state_manager


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
