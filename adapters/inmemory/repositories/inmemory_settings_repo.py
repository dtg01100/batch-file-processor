"""
In-memory settings repository.

Pure-Python implementation of :class:`ISettingsRepository` for tests
and ephemeral contexts. The oversight/defaults singleton is a single
dict; the key/value table is a dict.
"""

from typing import Any

from core.ports.repositories import ISettingsRepository

_DEFAULTS: dict[str, Any] = {
    "id": 1,
    "folder_name": "template",
    "folder_is_active": False,
    "alias": "template",
    "process_backend_copy": False,
    "process_backend_ftp": False,
    "process_backend_email": False,
    "process_backend_http": False,
    "process_edi": False,
    "split_edi": False,
    "convert_to_format": "",
    "copy_to_directory": "",
    "ftp_server": "",
    "ftp_port": 21,
    "ftp_username": "",
    "ftp_password": "",
    "ftp_folder": "",
    "email_to": "",
    "email_subject_line": "",
    "alert_on_failure": True,
}


class InMemorySettingsRepository(ISettingsRepository):
    """Settings repository backed by in-process dicts."""

    def __init__(self, defaults: dict[str, Any] | None = None) -> None:
        # The defaults singleton is mutable so tests can pre-seed.
        self._defaults: dict[str, Any] = (
            dict(defaults) if defaults is not None else dict(_DEFAULTS)
        )
        self._kv: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # ISettingsRepository
    # ------------------------------------------------------------------

    def get_defaults(self) -> dict[str, Any]:
        return dict(self._defaults)

    def update_defaults(self, settings: dict[str, Any]) -> None:
        # Mirror the SQLite behaviour: 'id' is forced to 1.
        merged = {**self._defaults, **settings, "id": 1}
        self._defaults = merged

    def get_setting(self, key: str) -> Any | None:
        return self._kv.get(key)

    def set_setting(self, key: str, value: Any) -> None:
        self._kv[key] = value
