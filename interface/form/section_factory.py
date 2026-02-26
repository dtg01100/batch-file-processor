"""
Section Factory

Factory for creating form sections dynamically based on configuration.
Provides a centralized way to create different types of configuration
sections for plugins and the core system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from ..plugins.config_schemas import ConfigurationSchema
from ..plugins.section_registry import ConfigSectionBase, SectionRegistry
from .config_section_widgets import (
    ConfigSectionWidget,
    QtConfigSectionWidget,
    CollapsibleSectionWidget,
    QtCollapsibleSectionWidget,
    TabbedSectionWidget
)


class SectionFactory(ABC):
    """
    Abstract base class for section factories.
    
    Defines the interface for creating configuration sections.
    """

    @abstractmethod
    def create_section(
        self,
        section_type: str,
        schema: ConfigurationSchema,
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> ConfigSectionWidget:
        """
        Create a configuration section widget.
        
        Args:
            section_type: Type of section to create
            schema: Configuration schema for the section
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            ConfigSectionWidget: Created section widget
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        Get list of supported section types.
        
        Returns:
            List[str]: List of supported section type identifiers
        """
        pass


class QtSectionFactory(SectionFactory):
    """
    Qt implementation of the section factory.
    
    Creates Qt-specific configuration section widgets.
    """

    _section_type_map = {
        'default': QtConfigSectionWidget,
        'collapsible': QtCollapsibleSectionWidget,
        'tabbed': TabbedSectionWidget,
    }

    def create_section(
        self,
        section_type: str,
        schema: ConfigurationSchema,
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> ConfigSectionWidget:
        """
        Create a Qt configuration section widget.
        
        Args:
            section_type: Type of section to create
            schema: Configuration schema for the section
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            ConfigSectionWidget: Created section widget
        """
        if section_type == 'tabbed':
            if not isinstance(schema, list):
                raise ValueError("Tabbed section requires a list of schemas")
            widget = TabbedSectionWidget(schema, 'qt', parent)
        elif section_type == 'collapsible':
            widget = QtCollapsibleSectionWidget(schema, 'qt', parent)
        else:
            widget_class = self._section_type_map.get(section_type, QtConfigSectionWidget)
            widget = widget_class(schema, 'qt', parent)
        
        widget.render(config)
        return widget

    def get_supported_types(self) -> List[str]:
        """
        Get list of supported section types.
        
        Returns:
            List[str]: List of supported section type identifiers
        """
        return list(self._section_type_map.keys())


class SectionFactoryRegistry:
    """
    Registry for section factories.
    
    Manages section factories for different UI frameworks
    and provides a centralized way to create sections.
    """

    _factories: Dict[str, SectionFactory] = {}

    @classmethod
    def register_factory(cls, framework: str, factory: SectionFactory) -> None:
        """
        Register a section factory for a framework.
        
        Args:
            framework: Framework identifier ('qt')
            factory: Section factory to register
        """
        cls._factories[framework] = factory

    @classmethod
    def get_factory(cls, framework: str) -> Optional[SectionFactory]:
        """
        Get the section factory for a framework.
        
        Args:
            framework: Framework identifier
            
        Returns:
            Optional[SectionFactory]: Section factory or None if not found
        """
        return cls._factories.get(framework)

    @classmethod
    def create_section(
        cls,
        section_type: str,
        schema: ConfigurationSchema,
        framework: str = 'qt',
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> ConfigSectionWidget:
        """
        Create a configuration section widget.
        
        Args:
            section_type: Type of section to create
            schema: Configuration schema for the section
            framework: UI framework ('qt')
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            ConfigSectionWidget: Created section widget
            
        Raises:
            ValueError: If framework is not supported
        """
        factory = cls.get_factory(framework)
        if factory is None:
            raise ValueError(f"No section factory registered for framework: {framework}")
        
        return factory.create_section(section_type, schema, config, parent)

    @classmethod
    def create_section_from_registry(
        cls,
        section_id: str,
        framework: str = 'qt',
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> Optional[ConfigSectionWidget]:
        """
        Create a section from the section registry.
        
        Args:
            section_id: Section identifier from registry
            framework: UI framework ('qt')
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            Optional[ConfigSectionWidget]: Created section widget or None if not found
        """
        section_class = SectionRegistry.get_section(section_id)
        if section_class is None:
            return None
        
        schema = section_class.get_schema()
        section_type = 'default'
        
        if not section_class.is_expanded_by_default():
            section_type = 'collapsible'
        
        return cls.create_section(section_type, schema, framework, config, parent)

    @classmethod
    def create_all_registered_sections(
        cls,
        framework: str = 'qt',
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> List[ConfigSectionWidget]:
        """
        Create all sections registered in the section registry.
        
        Args:
            framework: UI framework ('qt')
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            List[ConfigSectionWidget]: List of created section widgets
        """
        sections = []
        for section_class in SectionRegistry.get_all_sections():
            schema = section_class.get_schema()
            section_type = 'default'
            
            if not section_class.is_expanded_by_default():
                section_type = 'collapsible'
            
            widget = cls.create_section(section_type, schema, framework, config, parent)
            sections.append(widget)
        
        return sections


class PluginSectionFactory:
    """
    Factory for creating sections from plugins.
    
    Provides integration between the plugin system and the
    section factory for dynamic section creation.
    """

    @classmethod
    def create_plugin_section(
        cls,
        plugin_id: str,
        section_id: str,
        framework: str = 'qt',
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> Optional[ConfigSectionWidget]:
        """
        Create a section from a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            section_id: Section identifier within the plugin
            framework: UI framework ('qt')
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            Optional[ConfigSectionWidget]: Created section widget or None if not found
        """
        full_section_id = f"{plugin_id}.{section_id}"
        return SectionFactoryRegistry.create_section_from_registry(
            full_section_id, framework, config, parent
        )

    @classmethod
    def create_all_plugin_sections(
        cls,
        plugin_id: str,
        framework: str = 'qt',
        config: Optional[Dict[str, Any]] = None,
        parent: Any = None
    ) -> List[ConfigSectionWidget]:
        """
        Create all sections for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            framework: UI framework ('qt')
            config: Optional initial configuration values
            parent: Optional parent widget
            
        Returns:
            List[ConfigSectionWidget]: List of created section widgets
        """
        sections = []
        
        for section_class in SectionRegistry.get_sections_by_plugin(plugin_id):
            schema = section_class.get_schema()
            section_type = 'default'
            
            if not section_class.is_expanded_by_default():
                section_type = 'collapsible'
            
            widget = SectionFactoryRegistry.create_section(
                section_type, schema, framework, config, parent
            )
            sections.append(widget)
        
        return sections

    @classmethod
    def get_plugin_section_ids(cls, plugin_id: str) -> List[str]:
        """
        Get all section IDs for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            List[str]: List of section IDs
        """
        return [
            section_class.get_section_id()
            for section_class in SectionRegistry.get_sections_by_plugin(plugin_id)
        ]


# Register default factories
SectionFactoryRegistry.register_factory('qt', QtSectionFactory())
