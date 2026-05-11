"""Operations package for interface module.

This package contains operation classes that handle business logic
for folder and data management.

Available operations:
- FolderManager: CRUD operations for folder configurations
- FolderDataExtractor: Extract folder data for display
- PluginConfigurationMapper: Data mapping layer for plugin configurations
- QtPluginConfigExtractor: Qt-specific plugin configuration extractor
- QtPluginWidgetPopulator: Qt-specific plugin widget populator
"""

from interface.operations.folder_data_extractor import FolderDataExtractor
from interface.operations.folder_manager import FolderManager
from interface.operations.plugin_configuration_mapper import (
    ExtractedPluginConfig,
    PluginConfigPopulationResult,
    PluginConfigurationMapper,
    QtPluginConfigExtractor,
    QtPluginWidgetPopulator,
)

__all__ = [
    "ExtractedPluginConfig",
    "FolderDataExtractor",
    "FolderManager",
    "PluginConfigPopulationResult",
    "PluginConfigurationMapper",
    "QtPluginConfigExtractor",
    "QtPluginWidgetPopulator",
]
