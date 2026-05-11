"""Pipeline Factory for creating configured dispatch pipelines.

This module provides factory functions to create and configure
dispatch pipelines without requiring callers to know about
concrete pipeline step implementations.

Example:
    >>> from dispatch.pipeline import create_standard_pipeline
    >>> config = create_standard_pipeline(
    ...     settings=settings_dict,
    ...     progress_reporter=progress_service,
    ... )
"""

from typing import Any

from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.splitter import EDISplitterStep
from dispatch.pipeline.validator import EDIValidationStep
from dispatch.results import DispatchConfig


def create_standard_pipeline(
    *,
    database: Any = None,
    settings: dict | None = None,
    version: str = "1.0.0",
    progress_reporter: Any = None,
    file_system: Any = None,
    backends: dict[str, Any] | None = None,
    error_handler: Any = None,
    upc_service: Any = None,
    file_processor: Any = None,
    upc_dict: dict | None = None,
) -> DispatchConfig:
    """Create a standard EDI processing pipeline configuration.

    Creates a DispatchConfig with all standard pipeline steps
    (validator, splitter, converter) pre-configured.

    Args:
        database: Database interface for persistence
        settings: Application settings dictionary
        version: Application version string
        progress_reporter: Progress reporter for UI updates
        file_system: File system interface for file operations
        backends: Dictionary of backend name to backend instance
        error_handler: Error handler instance
        upc_service: UPC service for dictionary fetching
        file_processor: File processor service
        upc_dict: Cached UPC dictionary

    Returns:
        Configured DispatchConfig ready for use with DispatchOrchestrator

    """
    return DispatchConfig(
        database=database,
        file_system=file_system,
        backends=backends or {},
        error_handler=error_handler,
        settings=settings or {},
        version=version,
        upc_service=upc_service,
        progress_reporter=progress_reporter,
        validator_step=EDIValidationStep(),
        splitter_step=EDISplitterStep(),
        converter_step=EDIConverterStep(),
        file_processor=file_processor,
        upc_dict=upc_dict or {},
    )
