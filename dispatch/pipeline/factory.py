"""Pipeline Factory for creating configured dispatch pipelines.

This module provides factory functions to create and configure
dispatch pipelines without requiring callers to know about
concrete pipeline step implementations.

This decouples the UI layer from dispatch implementation details
and enables easy pipeline configuration for different scenarios.

Example:
    >>> from dispatch.pipeline.factory import create_standard_pipeline
    >>> config = create_standard_pipeline(
    ...     settings=settings_dict,
    ...     progress_reporter=progress_service,
    ... )
    >>> orchestrator = DispatchOrchestrator(config)
"""

from typing import Any

from dispatch import DispatchConfig
from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.splitter import EDISplitterStep
from dispatch.pipeline.validator import EDIValidationStep


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


def create_minimal_pipeline(
    *,
    database: Any = None,
    settings: dict | None = None,
    version: str = "1.0.0",
) -> DispatchConfig:
    """Create a minimal pipeline configuration for testing or simple scenarios.

    Creates a DispatchConfig without pipeline steps. Useful for
    testing, migration scenarios, or when pipeline processing
    is not needed.

    Args:
        database: Database interface for persistence
        settings: Application settings dictionary
        version: Application version string

    Returns:
        Minimal DispatchConfig without pipeline steps

    """
    return DispatchConfig(
        database=database,
        settings=settings or {},
        version=version,
        backends={},
    )


def create_pipeline_with_custom_steps(
    *,
    validator_step: Any = None,
    splitter_step: Any = None,
    converter_step: Any = None,
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
    """Create a pipeline with custom step implementations.

    Allows injection of custom pipeline step implementations
    for testing, alternative processing logic, or specialized
    scenarios.

    Args:
        validator_step: Custom validator step (or None to skip validation)
        splitter_step: Custom splitter step (or None to skip splitting)
        converter_step: Custom converter step (or None to skip conversion)
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
        DispatchConfig with custom pipeline steps

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
        validator_step=validator_step,
        splitter_step=splitter_step,
        converter_step=converter_step,
        file_processor=file_processor,
        upc_dict=upc_dict or {},
    )
