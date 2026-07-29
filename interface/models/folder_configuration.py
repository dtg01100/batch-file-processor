"""ConvertFormat enum (the dispatch-coupled part).

This module contains :class:`ConvertFormat` -- a metaclass-driven
enum-like class auto-populated from dispatch.converters.registry at
import time. It is the only part of the folder configuration model
that depends on dispatch.

All other folder configuration classes (FolderConfiguration, the
nested configs, FolderConfigurationPydantic) live in
:mod:`core.domain.models.folder` and can be imported without pulling
in dispatch.

Import ConvertFormat via::

    from interface.models.folder_configuration import ConvertFormat
"""

from typing import ClassVar


def _discover_format_values() -> list[tuple[str, str]]:
    """Auto-discover convert formats from dispatch.converters.registry.

    Returns tuples of (internal_name, display_name).
    Pulls from the central converter registry - the single source of truth.
    """
    from dispatch.converters.registry import get_all_converters

    values = [("do_nothing", "do_nothing")]
    for converter in get_all_converters():
        values.append((converter.format_name, converter.display_name))
    return values


class _ConvertFormatMeta(type):
    """Metaclass to enable ConvertFormat class iteration."""

    _discovered: list[str]
    _display_values: dict[str, str]

    def _ensure_discovered(cls) -> None: ...

    def __iter__(cls):
        cls._ensure_discovered()
        for v in cls._discovered:
            yield cls(cls._display_values[v])

    def __len__(cls):
        cls._ensure_discovered()
        return len(cls._discovered)

    def __getattr__(cls, name: str) -> "ConvertFormat":
        cls._ensure_discovered()
        if name.startswith("_"):
            raise AttributeError(name)
        key = name.upper().replace("-", "_").replace(" ", "_")
        if hasattr(cls, key):
            return getattr(cls, key)  # type: ignore[no-any-return]
        raise AttributeError(name)


class ConvertFormat(metaclass=_ConvertFormatMeta):
    """Enum-like class for EDI convert formats.

    Auto-populated from dispatch/converters/convert_to_*.py modules.
    """

    _discovered: ClassVar[list[str]] = []

    def __init__(self, value: str):
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    @property
    def name(self) -> str:
        return self._value.upper().replace("-", "_").replace(" ", "_")

    @classmethod
    def _ensure_discovered(cls):
        if not cls._discovered:
            discovered = _discover_format_values()
            cls._discovered = [v[0] for v in discovered]
            cls._display_values = {v[0]: v[1] for v in discovered}
            for v in discovered:
                key = v[0].upper().replace("-", "_").replace(" ", "_")
                setattr(cls, key, cls(v[1]))

    @classmethod
    def values(cls) -> list[str]:
        """Get all available format values."""
        cls._ensure_discovered()
        return list(cls._discovered)

    @classmethod
    def from_string(cls, s: str) -> "ConvertFormat | None":
        """Create a ConvertFormat from a string value."""
        if not s:
            return None
        cls._ensure_discovered()
        s_normalized = s.lower().replace(" ", "_").replace("-", "_")
        for v in cls._discovered:
            if v.lower() == s_normalized:
                return cls(cls._display_values.get(v, v))
        return None

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ConvertFormat.{self.name}"

    def __eq__(self, other) -> bool:
        if isinstance(other, ConvertFormat):
            return self._value == other._value
        if isinstance(other, str):
            return self._value.lower() == other.lower()
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)


# Initialize - this populates the class attributes for all formats
ConvertFormat._ensure_discovered()
