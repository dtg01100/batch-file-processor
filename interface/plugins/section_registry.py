"""
Section Registry

Provides a registry system for managing configuration UI sections that plugins
can use to register their custom configuration sections. This enables a modular
system where each plugin can provide its own UI sections while reusing common
components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable


class ConfigSectionBase(ABC):
    """
    Base class for all configuration sections.
    
    Defines the interface that all config sections must implement,
    including metadata and rendering capabilities.
    """

    @classmethod
    @abstractmethod
    def get_section_id(cls) -> str:
        """
        Get the unique identifier for this section.
        
        Returns:
            str: Unique section identifier
        """
        pass

    @classmethod
    @abstractmethod
    def get_section_title(cls) -> str:
        """
        Get the human-readable title for this section.
        
        Returns:
            str: Section title for display
        """
        pass

    @classmethod
    @abstractmethod
    def get_section_description(cls) -> str:
        """
        Get the description of this section.
        
        Returns:
            str: Section description
        """
        pass

    @classmethod
    @abstractmethod
    def get_schema(cls):
        """
        Get the configuration schema for this section.
        
        Returns:
            ConfigurationSchema: Schema for this section's configuration
        """
        pass

    @classmethod
    def get_priority(cls) -> int:
        """
        Get the display priority of this section.
        
        Lower values are displayed first.
        
        Returns:
            int: Priority value (default: 100)
        """
        return 100

    @classmethod
    def is_expanded_by_default(cls) -> bool:
        """
        Check if this section should be expanded by default.
        
        Returns:
            bool: True if expanded by default
        """
        return True


class SectionRenderer(ABC):
    """
    Abstract base class for rendering configuration sections.
    
    Provides framework-specific rendering capabilities for config sections.
    """

    @abstractmethod
    def render(self, parent: Any, config: Optional[Dict[str, Any]] = None) -> Any:
        """
        Render the section in the parent widget.
        
        Args:
            parent: Parent widget to render in
            config: Optional initial configuration values
            
        Returns:
            Any: Rendered section widget
        """
        pass

    @abstractmethod
    def get_values(self) -> Dict[str, Any]:
        """
        Get current configuration values from the rendered section.
        
        Returns:
            Dict[str, Any]: Current configuration values
        """
        pass

    @abstractmethod
    def set_values(self, config: Dict[str, Any]) -> None:
        """
        Set configuration values in the rendered section.
        
        Args:
            config: Configuration values to set
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate the current configuration values.
        
        Returns:
            bool: True if valid, False otherwise
        """
        pass

    @abstractmethod
    def get_validation_errors(self) -> List[str]:
        """
        Get validation errors from the section.
        
        Returns:
            List[str]: List of validation error messages
        """
        pass


class SectionRegistry:
    """
    Registry for managing configuration sections.
    
    Provides methods to register, retrieve, and manage configuration
    sections from plugins and the core system.
    """

    _sections: Dict[str, Type[ConfigSectionBase]] = {}
    _renderers: Dict[str, Callable] = {}
    _plugin_sections: Dict[str, List[str]] = {}

    @classmethod
    def register_section(cls, section_class: Type[ConfigSectionBase]) -> None:
        """
        Register a configuration section.
        
        Args:
            section_class: Section class to register
        """
        section_id = section_class.get_section_id()
        if section_id in cls._sections:
            raise ValueError(f"Section '{section_id}' is already registered")
        cls._sections[section_id] = section_class

    @classmethod
    def unregister_section(cls, section_id: str) -> None:
        """
        Unregister a configuration section.
        
        Args:
            section_id: ID of section to unregister
        """
        cls._sections.pop(section_id, None)
        cls._renderers.pop(section_id, None)

    @classmethod
    def get_section(cls, section_id: str) -> Optional[Type[ConfigSectionBase]]:
        """
        Get a registered section by ID.
        
        Args:
            section_id: Section identifier
            
        Returns:
            Optional[Type[ConfigSectionBase]]: Section class or None if not found
        """
        return cls._sections.get(section_id)

    @classmethod
    def get_all_sections(cls) -> List[Type[ConfigSectionBase]]:
        """
        Get all registered sections sorted by priority.
        
        Returns:
            List[Type[ConfigSectionBase]]: List of section classes sorted by priority
        """
        sections = list(cls._sections.values())
        sections.sort(key=lambda s: s.get_priority())
        return sections

    @classmethod
    def get_sections_by_plugin(cls, plugin_id: str) -> List[Type[ConfigSectionBase]]:
        """
        Get all sections registered by a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            List[Type[ConfigSectionBase]]: List of section classes for the plugin
        """
        section_ids = cls._plugin_sections.get(plugin_id, [])
        return [cls._sections[sid] for sid in section_ids if sid in cls._sections]

    @classmethod
    def register_plugin_section(cls, plugin_id: str, section_class: Type[ConfigSectionBase]) -> None:
        """
        Register a section as belonging to a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            section_class: Section class to register for the plugin
        """
        section_id = section_class.get_section_id()
        cls.register_section(section_class)
        
        if plugin_id not in cls._plugin_sections:
            cls._plugin_sections[plugin_id] = []
        if section_id not in cls._plugin_sections[plugin_id]:
            cls._plugin_sections[plugin_id].append(section_id)

    @classmethod
    def register_renderer(cls, section_id: str, renderer_factory: Callable) -> None:
        """
        Register a renderer factory for a section.
        
        Args:
            section_id: Section identifier
            renderer_factory: Callable that creates a SectionRenderer
        """
        cls._renderers[section_id] = renderer_factory

    @classmethod
    def get_renderer(cls, section_id: str) -> Optional[Callable]:
        """
        Get the renderer factory for a section.
        
        Args:
            section_id: Section identifier
            
        Returns:
            Optional[Callable]: Renderer factory or None if not found
        """
        return cls._renderers.get(section_id)

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered sections and renderers.
        """
        cls._sections.clear()
        cls._renderers.clear()
        cls._plugin_sections.clear()

    @classmethod
    def get_section_count(cls) -> int:
        """
        Get the total number of registered sections.
        
        Returns:
            int: Number of registered sections
        """
        return len(cls._sections)


class PluginSection(ConfigSectionBase):
    """
    Base class for plugin-provided configuration sections.
    
    Provides a convenient way for plugins to define their own
    configuration sections that integrate with the section registry.
    """

    @classmethod
    def get_plugin_id(cls) -> str:
        """
        Get the plugin identifier this section belongs to.
        
        Returns:
            str: Plugin identifier
        """
        raise NotImplementedError("Subclasses must implement get_plugin_id")

    @classmethod
    def get_priority(cls) -> int:
        """
        Get the display priority of this section.
        
        Returns:
            int: Priority value (default: 100)
        """
        return 100
