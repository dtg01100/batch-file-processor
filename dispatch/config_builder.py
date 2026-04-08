"""Dispatch configuration builder for simplified pipeline setup.

This module provides a fluent builder pattern for constructing DispatchConfig
instances with sensible defaults, reducing boilerplate in orchestration setup.

Example:
    >>> from dispatch.config_builder import DispatchConfigBuilder
    >>> from dispatch.edi_validator import EDIValidator
    >>> config = (
    ...     DispatchConfigBuilder()
    ...     .with_validator(EDIValidator())
    ...     .with_settings({"email_host": "smtp.example.com"})
    ...     .with_version("2.0.0")
    ...     .build()
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from dispatch.interfaces import (
    BackendInterface,
    DatabaseInterface,
    ErrorHandlerInterface,
    FileSystemInterface,
)

if TYPE_CHECKING:
    from dispatch.orchestrator import DispatchConfig


@dataclass
class DispatchConfigBuilder:
    """Fluent builder for DispatchConfig with sensible defaults.

    Attributes:
        _validator_step: Optional validator pipeline step
        _splitter_step: Optional splitter pipeline step
        _converter_step: Optional converter pipeline step
        _backends: Dictionary of backend name to backend instance
        _database: Optional database interface
        _file_system: Optional file system interface
        _error_handler: Optional error handler
        _settings: Application settings dictionary
        _version: Application version string
        _upc_service: Optional UPC lookup service
        _progress_reporter: Optional progress reporter
        _upc_dict: Optional UPC dictionary

    Example:
        >>> config = DispatchConfigBuilder().build()
        >>> config.version
        '1.0.0'
    """

    _validator_step: Any | None = None
    _splitter_step: Any | None = None
    _converter_step: Any | None = None
    _backends: dict[str, BackendInterface] = field(default_factory=dict)
    _database: DatabaseInterface | None = None
    _file_system: FileSystemInterface | None = None
    _error_handler: ErrorHandlerInterface | None = None
    _settings: dict = field(default_factory=dict)
    _version: str = "1.0.0"
    _upc_service: Any | None = None
    _progress_reporter: Any | None = None
    _upc_dict: dict = field(default_factory=dict)

    def with_validator(self, validator: Any) -> DispatchConfigBuilder:
        """Set the validator pipeline step.

        Args:
            validator: A validator pipeline step implementation

        Returns:
            Self for chaining
        """
        self._validator_step = validator
        return self

    def with_splitter(self, splitter: Any) -> DispatchConfigBuilder:
        """Set the splitter pipeline step.

        Args:
            splitter: Splitter pipeline step

        Returns:
            Self for chaining
        """
        self._splitter_step = splitter
        return self

    def with_converter(self, converter: Any) -> DispatchConfigBuilder:
        """Set the converter pipeline step.

        Args:
            converter: Converter pipeline step

        Returns:
            Self for chaining
        """
        self._converter_step = converter
        return self

    def with_backends(
        self, backends: dict[str, BackendInterface]
    ) -> DispatchConfigBuilder:
        """Set the backend instances.

        Args:
            backends: Dictionary mapping backend names to instances

        Returns:
            Self for chaining
        """
        self._backends = backends
        return self

    def add_backend(
        self, name: str, backend: BackendInterface
    ) -> DispatchConfigBuilder:
        """Add a single backend instance.

        Args:
            name: Backend name identifier
            backend: Backend instance

        Returns:
            Self for chaining
        """
        self._backends[name] = backend
        return self

    def with_database(self, database: DatabaseInterface) -> DispatchConfigBuilder:
        """Set the database interface.

        Args:
            database: DatabaseInterface implementation

        Returns:
            Self for chaining
        """
        self._database = database
        return self

    def with_file_system(
        self, file_system: FileSystemInterface
    ) -> DispatchConfigBuilder:
        """Set the file system interface.

        Args:
            file_system: FileSystemInterface implementation

        Returns:
            Self for chaining
        """
        self._file_system = file_system
        return self

    def with_error_handler(
        self, handler: ErrorHandlerInterface
    ) -> DispatchConfigBuilder:
        """Set the error handler.

        Args:
            handler: ErrorHandlerInterface implementation

        Returns:
            Self for chaining
        """
        self._error_handler = handler
        return self

    def with_settings(self, settings: dict) -> DispatchConfigBuilder:
        """Set the application settings.

        Args:
            settings: Dictionary of application settings

        Returns:
            Self for chaining
        """
        self._settings = settings
        return self

    def with_version(self, version: str) -> DispatchConfigBuilder:
        """Set the application version.

        Args:
            version: Version string

        Returns:
            Self for chaining
        """
        self._version = version
        return self

    def with_upc_service(self, service: Any) -> DispatchConfigBuilder:
        """Set the UPC lookup service.

        Args:
            service: UPC service instance

        Returns:
            Self for chaining
        """
        self._upc_service = service
        return self

    def with_progress_reporter(self, reporter: Any) -> DispatchConfigBuilder:
        """Set the progress reporter.

        Args:
            reporter: Progress reporter instance

        Returns:
            Self for chaining
        """
        self._progress_reporter = reporter
        return self

    def with_upc_dict(self, upc_dict: dict) -> DispatchConfigBuilder:
        """Set the UPC dictionary.

        Args:
            upc_dict: UPC lookup dictionary

        Returns:
            Self for chaining
        """
        self._upc_dict = upc_dict
        return self

    def build(self) -> DispatchConfig:
        """Build the DispatchConfig with current values.

        Returns:
            Configured DispatchConfig instance
        """
        from dispatch.orchestrator import DispatchConfig

        return DispatchConfig(
            validator_step=self._validator_step,
            splitter_step=self._splitter_step,
            converter_step=self._converter_step,
            backends=self._backends,
            database=self._database,
            file_system=self._file_system,
            error_handler=self._error_handler,
            settings=self._settings,
            version=self._version,
            upc_service=self._upc_service,
            progress_reporter=self._progress_reporter,
            upc_dict=self._upc_dict,
        )


def create_default_config() -> DispatchConfig:
    """Create a DispatchConfig with sensible defaults.

    Returns:
        DispatchConfig with default values
    """
    return DispatchConfigBuilder().build()
