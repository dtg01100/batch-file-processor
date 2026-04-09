"""Folder Processing Configuration.

This module provides a typed configuration class for folder processing,
replacing the use of raw dictionaries with proper type hints and validation.

Example:
    >>> config = FolderProcessingConfig.from_dict(folder_dict)
    >>> if config.convert_edi:
    ...     print(f"Converting to {config.convert_to_format}")
"""

from dataclasses import dataclass, field
from typing import Any

from core.utils.bool_utils import normalize_bool


@dataclass
class FolderProcessingConfig:
    """Typed configuration for folder processing settings.

    This dataclass replaces raw dictionary access for folder configuration,
    providing type safety, IDE support, and validation.

    Attributes:
        folder_name: Path to the folder to process
        alias: Display name for the folder
        process_edi: Whether to process EDI files
        convert_edi: Whether to convert EDI files
        convert_to_format: Target format for conversion (e.g., 'csv', 'fintech')
        tweak_edi: Whether to apply EDI tweaks (legacy, use convert_to_format='tweaks')
        split_edi: Whether to split multi-invoice EDI files
        validate_edi: Whether to validate EDI format
        send_backend: Backend type for sending files ('copy', 'ftp', 'email', 'http')
        is_active: Whether this folder is enabled for processing
        extra_params: Additional custom parameters

    """

    folder_name: str = ""
    alias: str = ""
    process_edi: bool = False
    convert_edi: bool = False
    convert_to_format: str = ""
    tweak_edi: bool = False
    split_edi: bool = False
    validate_edi: bool = False
    send_backend: str = ""
    is_active: bool = True
    extra_params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FolderProcessingConfig":
        """Create a FolderProcessingConfig from a dictionary.

        Handles normalization of boolean values from string representations
        (e.g., "True", "False", "1", "0") to proper Python booleans.

        Args:
            data: Dictionary containing folder configuration

        Returns:
            FolderProcessingConfig instance with normalized values

        """
        return cls(
            folder_name=data.get("folder_name", ""),
            alias=data.get("alias", data.get("folder_name", "")),
            process_edi=normalize_bool(data.get("process_edi", False)),
            convert_edi=normalize_bool(data.get("convert_edi", False)),
            convert_to_format=data.get("convert_to_format", ""),
            tweak_edi=normalize_bool(data.get("tweak_edi", False)),
            split_edi=normalize_bool(data.get("split_edi", False)),
            validate_edi=normalize_bool(data.get("validate_edi", False)),
            send_backend=data.get("send_backend", ""),
            is_active=normalize_bool(data.get("is_active", True)),
            extra_params={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "folder_name",
                    "alias",
                    "process_edi",
                    "convert_edi",
                    "convert_to_format",
                    "tweak_edi",
                    "split_edi",
                    "validate_edi",
                    "send_backend",
                    "is_active",
                }
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration back to a dictionary.

        Useful for serialization or interfacing with legacy code.

        Returns:
            Dictionary representation of the configuration

        """
        return {
            "folder_name": self.folder_name,
            "alias": self.alias,
            "process_edi": self.process_edi,
            "convert_edi": self.convert_edi,
            "convert_to_format": self.convert_to_format,
            "tweak_edi": self.tweak_edi,
            "split_edi": self.split_edi,
            "validate_edi": self.validate_edi,
            "send_backend": self.send_backend,
            "is_active": self.is_active,
            **self.extra_params,
        }

    @property
    def display_name(self) -> str:
        """Get the display name for this folder.

        Returns:
            Alias if set, otherwise folder_name

        """
        return self.alias if self.alias else self.folder_name

    @property
    def has_conversion(self) -> bool:
        """Check if conversion is configured.

        Returns:
            True if conversion is enabled and a format is specified

        """
        return self.convert_edi and bool(self.convert_to_format)

    @property
    def has_tweaks(self) -> bool:
        """Check if tweaks are configured.

        Returns:
            True if tweaks are enabled (legacy check)

        """
        return self.tweak_edi or self.convert_to_format == "tweaks"
