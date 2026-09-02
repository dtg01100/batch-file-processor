"""Typed folder configuration (Phase 11.4).

The flat ``folders`` table stores 50+ columns. Code that reads them
via ``row["folder_name"]`` or ``row.get("folder_name")`` is correct
but easy to get wrong (typos become silent ``KeyError`` or
``None`` at runtime). This module provides:

1. ``FolderConfig`` — a typed dataclass that mirrors the flat
   row's fields. ``FolderConfigAdapter.from_row(row)`` produces
   one.
2. ``FolderConfigAdapter`` — the constructor + factory. Reads a
   flat row, normalizes booleans, and exposes a typed config.

The flat schema is unchanged (Phase 8 DECISION 1). The adapter is
read-only: the webapp folder editor continues to write the flat
row directly; the pipeline reads through the adapter.

Phase 11.2+ will add per-converter config dataclasses
(``CSVConverterConfig`` etc.) loaded from the adapter's
``parameters`` dict by the registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_TRUE_STRINGS = frozenset(("True", "true", "1", "yes", "on"))
_FALSE_STRINGS = frozenset(("False", "false", "0", "no", "off"))


def _to_bool(value: Any, default: bool = False) -> bool:
    """Normalize a string-ish bool to a real bool.

    Empty / missing values use ``default``. Unknown strings are
    treated as ``False`` (the legacy behaviour of the
    ``normalize_parameter`` helper).
    """
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return False
    return default


def _to_int(value: Any, default: int = 0) -> int:
    """Parse an integer; on failure, return ``default``."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class FolderConfig:
    """Typed view of a flat ``folders`` table row.

    The flat row dict is the source of truth (the webapp editor
    writes it). ``FolderConfigAdapter.from_row`` produces this
    dataclass for the pipeline to read.

    The dataclass exposes dict-style access (``config["folder_name"]``)
    so existing pipeline code that uses ``row[...]`` keeps working
    during the migration window.
    """

    # Identity
    folder_id: int
    folder_name: str
    alias: str
    is_active: bool

    # What to do
    convert_to_format: str = ""
    process_backends: list[str] = field(default_factory=list)

    # Watcher state
    watch_enabled: bool = False
    watch_interval_seconds: int = 30

    # Per-converter parameters (flat dict, read by the matching
    # converter's config dataclass in Phase 11.2+)
    parameters: dict[str, Any] = field(default_factory=dict)

    # Plugin configurations (per-format UI overrides merged at
    # read time by ``webapp.converters_api.merge_plugin_config``)
    plugin_configurations: dict[str, Any] = field(default_factory=dict)

    # Health (populated by the watcher / runner)
    last_tick_at: str = ""
    last_run_id: str = ""
    last_error: str = ""

    # Thresholds (0/empty = no limit)
    max_duration_seconds: int = 0
    max_failure_rate_percent: int = 0

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for backward compatibility.

        Lets pipeline code that reads ``folder["folder_name"]``
        keep working with a ``FolderConfig`` instance.
        """
        if not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style ``.get`` for backward compatibility."""
        return getattr(self, key, default)


class FolderConfigAdapter:
    """Construct a ``FolderConfig`` from a flat ``folders`` row dict.

    Usage:
        row = db.folders_table.find_one(id=42)
        config = FolderConfigAdapter.from_row(row)
        print(config.folder_name)  # typed access
        print(config["folder_name"])  # dict-style, legacy

    The adapter is read-only; the webapp editor continues to write
    flat rows.
    """

    @staticmethod
    def from_row(row: dict[str, Any]) -> FolderConfig:
        """Build a ``FolderConfig`` from a flat row dict.

        Args:
            row: A flat ``folders`` row dict (raw from
                ``db.folders_table.find_one``).

        Returns:
            A typed ``FolderConfig`` instance.
        """
        backends: list[str] = []
        for backend_name in ("copy", "ftp", "email", "http"):
            if _to_bool(row.get(f"process_backend_{backend_name}", False)):
                backends.append(backend_name)

        return FolderConfig(
            folder_id=_to_int(row.get("id"), default=0),
            folder_name=str(row.get("folder_name", "") or ""),
            alias=str(row.get("alias", "") or ""),
            is_active=_to_bool(row.get("folder_is_active"), default=False),
            convert_to_format=str(
                row.get("convert_to_format", "") or ""
            ).strip().lower(),
            process_backends=backends,
            watch_enabled=_to_bool(row.get("watch_enabled"), default=False),
            watch_interval_seconds=_to_int(
                row.get("watch_interval_seconds"), default=30
            ),
            parameters=dict(row),
            plugin_configurations=_parse_plugin_configurations(
                row.get("plugin_configurations")
            ),
            last_tick_at=str(row.get("last_tick_at", "") or ""),
            last_run_id=str(row.get("last_run_id", "") or ""),
            last_error=str(row.get("last_error", "") or ""),
            max_duration_seconds=_to_int(row.get("max_duration_seconds"), default=0),
            max_failure_rate_percent=_to_int(
                row.get("max_failure_rate_percent"), default=0
            ),
        )


def _parse_plugin_configurations(value: Any) -> dict[str, Any]:
    """Parse the ``plugin_configurations`` JSON-ish column.

    Stored as ``"{}"`` by default; older rows may have it as JSON
    text. Tolerate both shapes.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        import contextlib
        import json

        with contextlib.suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
    return {}
