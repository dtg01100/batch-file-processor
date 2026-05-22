"""Converter Registry - Single Source of Truth for EDI Convert Formats.

This module provides a central registry for all EDI converter formats.
Each converter module declares its metadata via the CONVERTER_METADATA dict,
and this registry provides functions to query available formats.

Design Principles:
1. Each converter module owns its metadata declaration
2. No duplication - metadata lives in exactly one place (converter module)
3. All consumers (UI, validation, pipeline) query this registry
4. The registry auto-discovers converters via pkgutil

Usage in Converter Module:
    # In dispatch/converters/convert_to_csv.py
    CONVERTER_METADATA = {
        "format_name": "csv",
        "display_name": "CSV",
        "description": "Convert EDI to standard CSV format",
    }

Usage by Consumers:
    from dispatch.converters.registry import get_all_converters
    formats = get_all_converters()
"""

from __future__ import annotations

import os
import pkgutil
from dataclasses import dataclass
from typing import Any, cast

# Registry storage - populated on first access
_CONVERTER_REGISTRY: dict[str, dict[str, Any]] = {}
_REGISTRY_INITIALIZED = False


@dataclass
class ConverterMetadata:
    """Metadata for a single converter format.

    Attributes:
        format_name: Internal name (matches module suffix, e.g., "csv")
        display_name: Human-readable name for UI (e.g., "CSV")
        module_name: Full module path (e.g., "dispatch.converters.convert_to_csv")
        description: Optional description of the format

    """

    format_name: str
    display_name: str
    module_name: str
    description: str = ""


def _register_converter(metadata: dict[str, Any]) -> None:
    """Register a converter in the global registry.

    Args:
        metadata: Dictionary with required keys: format_name, display_name, module_name

    """
    global _CONVERTER_REGISTRY

    format_name = metadata["format_name"]
    _CONVERTER_REGISTRY[format_name] = {
        "format_name": format_name,
        "display_name": metadata["display_name"],
        "module_name": metadata["module_name"],
        "description": metadata.get("description", ""),
    }


def _discover_converters() -> None:
    """Auto-discover converters from dispatch/converters package.

    Scans the converters package for convert_to_*.py modules and imports
    their CONVERTER_METADATA dict to build the registry.

    Note: Some converters (like scansheet_type_a) may fail to import due to
    missing optional dependencies (e.g., pkg_resources). The registry falls
    back to using hardcoded metadata for these converters.
    """
    global _REGISTRY_INITIALIZED, _CONVERTER_REGISTRY

    if _REGISTRY_INITIALIZED:
        return

    _CONVERTER_REGISTRY.clear()

    # Default display name mappings for converters without explicit metadata
    DISPLAY_NAME_OVERRIDES = {
        "scannerware": "ScannerWare",
        "scansheet_type_a": "ScanSheet_Type_A",
        "jolley_custom": "jolley_custom",
        "estore_einvoice": "eStore_eInvoice",
        "estore_einvoice_generic": "eStore_eInvoice_Generic",
    }

    # Hardcoded metadata for converters that may fail to import due to
    # optional dependencies (e.g., pkg_resources, barcode)
    FALLBACK_METADATA = {
        "scansheet_type_a": {
            "format_name": "scansheet_type_a",
            "display_name": "ScanSheet_Type_A",
            "module_name": "dispatch.converters.convert_to_scansheet_type_a",
            "description": "Convert EDI to ScanSheet Type A Excel format",
        },
    }

    converter_path = os.path.join(os.path.dirname(__file__))
    if not os.path.isdir(converter_path):
        _REGISTRY_INITIALIZED = True
        return

    for _, module_name, is_pkg in pkgutil.iter_modules([converter_path]):
        if module_name.startswith("convert_to_") and not is_pkg:
            format_name = module_name.replace("convert_to_", "")

            # Try to import the module and get CONVERTER_METADATA
            try:
                full_module_name = f"dispatch.converters.{module_name}"
                import importlib

                mod = importlib.import_module(full_module_name)
                metadata = getattr(mod, "CONVERTER_METADATA", None)

                if metadata:
                    # Module has explicit metadata
                    _register_converter(metadata)
                else:
                    # Auto-generate metadata from module name
                    display_name = DISPLAY_NAME_OVERRIDES.get(format_name, format_name)
                    _register_converter(
                        {
                            "format_name": format_name,
                            "display_name": display_name,
                            "module_name": full_module_name,
                            "description": "",
                        }
                    )
            except ImportError:
                # Module failed to import (likely due to optional dependency).
                # Use fallback metadata if available, otherwise skip.
                if format_name in FALLBACK_METADATA:
                    _register_converter(FALLBACK_METADATA[format_name])
                # else: skip this converter silently

    _REGISTRY_INITIALIZED = True


def get_all_converters() -> list[ConverterMetadata]:
    """Get all registered converter formats.

    Returns:
        List of ConverterMetadata for all available formats, sorted by display_name

    """
    _discover_converters()

    result = []
    for fmt_data in _CONVERTER_REGISTRY.values():
        result.append(ConverterMetadata(**fmt_data))

    result.sort(key=lambda x: x.display_name)
    return result


def get_converter_by_name(format_name: str) -> ConverterMetadata | None:
    """Get converter metadata by format name.

    Args:
        format_name: The internal format name (e.g., "csv")

    Returns:
        ConverterMetadata if found, None otherwise

    """
    _discover_converters()

    fmt_data = _CONVERTER_REGISTRY.get(format_name)
    if fmt_data:
        return ConverterMetadata(**fmt_data)
    return None


def get_format_names() -> list[str]:
    """Get all format names (internal names).

    Returns:
        List of format names sorted alphabetically

    """
    _discover_converters()
    return sorted(_CONVERTER_REGISTRY.keys())


def get_display_name(format_name: str) -> str:
    """Get the display name for a format.

    Args:
        format_name: The internal format name

    Returns:
        Display name for the format, or the format_name if not found

    """
    _discover_converters()

    fmt_data = _CONVERTER_REGISTRY.get(format_name)
    if fmt_data:
        return cast(str, fmt_data["display_name"])
    return format_name


def get_module_name(format_name: str) -> str | None:
    """Get the module name for a format.

    Args:
        format_name: The internal format name

    Returns:
        Full module path if found, None otherwise

    """
    _discover_converters()

    fmt_data = _CONVERTER_REGISTRY.get(format_name)
    if fmt_data:
        return cast(str, fmt_data["module_name"])
    return None


def format_exists(format_name: str) -> bool:
    """Check if a format exists in the registry.

    Args:
        format_name: The internal format name to check

    Returns:
        True if format exists, False otherwise

    """
    _discover_converters()
    return format_name in _CONVERTER_REGISTRY


def get_converter_module(format_name: str) -> Any:
    """Import and return the converter module.

    Args:
        format_name: The internal format name

    Returns:
        The imported module

    Raises:
        ImportError: If the module cannot be imported

    """
    module_name = get_module_name(format_name)
    if not module_name:
        raise ImportError(f"No module found for format: {format_name}")

    import importlib

    return importlib.import_module(module_name)
