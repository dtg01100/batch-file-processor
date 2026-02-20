"""
Configuration Plugin Interface

Defines the ConfigurationPlugin interface that extends PluginBase for
handling configuration operations with specific format support. This interface
provides a structured way to implement configuration plugins that support
different data formats with validation, serialization, and deserialization
capabilities.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum

from .plugin_base import PluginBase
from .config_schemas import FieldDefinition
from .validation_framework import ValidationResult
from ..models.folder_configuration import ConvertFormat


class ConfigurationPlugin(PluginBase, ABC):
    """
    Configuration plugin interface for handling specific data formats.
    
    Extends PluginBase with format-specific configuration capabilities,
    providing methods for schema definition, validation, and serialization.
    """
    
    @classmethod
    @abstractmethod
    def get_format_name(cls) -> str:
        """
        Get the human-readable name of the configuration format.
        
        Returns:
            str: Format name for display purposes
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_format_enum(cls) -> ConvertFormat:
        """
        Get the ConvertFormat enum value associated with this format.
        
        Returns:
            ConvertFormat: The format enum from folder_configuration
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_config_fields(cls) -> List[FieldDefinition]:
        """
        Get the list of field definitions for this configuration format.
        
        Returns:
            List[FieldDefinition]: List of field definitions that define the
            configuration schema for this format.
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate configuration data against the format's schema.
        
        Args:
            config: Configuration data to validate
            
        Returns:
            ValidationResult: Result of the validation operation
        """
        pass
    
    @abstractmethod
    def create_config(self, data: Dict[str, Any]) -> Any:
        """
        Create a configuration instance from raw data.
        
        Args:
            data: Raw data to create the configuration from
            
        Returns:
            Any: Configuration instance specific to this format
        """
        pass
    
    @abstractmethod
    def serialize_config(self, config: Any) -> Dict[str, Any]:
        """
        Serialize a configuration instance to dictionary format.
        
        Args:
            config: Configuration instance to serialize
            
        Returns:
            Dict[str, Any]: Serialized configuration data
        """
        pass
    
    @abstractmethod
    def deserialize_config(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize stored data into a configuration instance.
        
        Args:
            data: Stored data to deserialize
            
        Returns:
            Any: Configuration instance specific to this format
        """
        pass
    
    @classmethod
    def get_configuration_schema(cls):
        """
        Get the configuration schema for the plugin.
        
        Overrides the default implementation to use the fields returned by
        get_config_fields() to create a ConfigurationSchema instance.
        
        Returns:
            Optional[ConfigurationSchema]: Configuration schema for the plugin
        """
        from .config_schemas import ConfigurationSchema
        
        fields = cls.get_config_fields()
        if fields:
            return ConfigurationSchema(fields)
        return None
