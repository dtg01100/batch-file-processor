"""Edit Folders Dialog Components.

This package contains modular components for the Qt edit folders dialog,
following a decomposition strategy to improve maintainability and testability.

Components:
- data_extractor: Extracts dialog field data from Qt widgets
- column_builders: Builds individual dialog columns (others, folder, backend, EDI)
- dynamic_edi_builder: Handles dynamic EDI configuration sections
- event_handlers: Manages user interaction event handling
- layout_builder: Constructs the complete dialog UI layout
"""

from .data_extractor import QtFolderDataExtractor
from .column_builders import ColumnBuilders
from .dynamic_edi_builder import DynamicEDIBuilder
from .event_handlers import EventHandlers
from .layout_builder import UILayoutBuilder

__all__ = [
    'QtFolderDataExtractor',
    'ColumnBuilders',
    'DynamicEDIBuilder',
    'EventHandlers',
    'UILayoutBuilder'
]
