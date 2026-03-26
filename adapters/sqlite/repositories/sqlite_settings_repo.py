"""
SQLite settings repository implementation.

Wraps the DatabaseObj / Table API to implement ISettingsRepository.
Covers both the 'administrative' singleton (oversight/defaults) and
the key/value 'settings' table.
"""

from typing import Any

from core.ports.repositories import ISettingsRepository


class SqliteSettingsRepository(ISettingsRepository):
    """Settings repository backed by DatabaseObj.

    Args:
        database_obj: A ``DatabaseObj`` instance (or compatible mock).

    """

    def __init__(self, database_obj: Any) -> None:
        self._db = database_obj

    # ------------------------------------------------------------------
    # ISettingsRepository implementation
    # ------------------------------------------------------------------

    def get_defaults(self) -> dict[str, Any]:
        """Return the oversight/defaults singleton (id=1 in administrative).

        Delegates to DatabaseObj.get_oversight_or_default() which
        guarantees a non-None return value.
        """
        return self._db.get_oversight_or_default()

    def update_defaults(self, settings: dict[str, Any]) -> None:
        """Update the oversight/defaults singleton record."""
        self._db.update_default_settings(settings)

    def get_setting(self, key: str) -> Any | None:
        """Return a named setting from the key/value settings table."""
        return self._db.get_setting(key)

    def set_setting(self, key: str, value: Any) -> None:
        """Upsert a named setting into the key/value settings table."""
        self._db.set_setting(key, value)
