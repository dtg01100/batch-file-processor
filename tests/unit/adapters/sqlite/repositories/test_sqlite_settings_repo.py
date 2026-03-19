"""
Unit tests for SqliteSettingsRepository.
"""

from unittest.mock import MagicMock

from adapters.sqlite.repositories import SqliteSettingsRepository
from core.ports.repositories import ISettingsRepository


def _make_db():
    db = MagicMock()
    return db


class TestISettingsRepositoryConformance:
    def test_is_instance_of_interface(self):
        repo = SqliteSettingsRepository(_make_db())
        assert isinstance(repo, ISettingsRepository)


class TestGetDefaults:
    def test_delegates_to_get_oversight_or_default(self):
        db = _make_db()
        defaults = {"id": 1, "logs_directory": "/logs"}
        db.get_oversight_or_default.return_value = defaults
        repo = SqliteSettingsRepository(db)

        result = repo.get_defaults()

        db.get_oversight_or_default.assert_called_once()
        assert result == defaults


class TestUpdateDefaults:
    def test_delegates_to_update_default_settings(self):
        db = _make_db()
        repo = SqliteSettingsRepository(db)
        settings = {"logs_directory": "/new/logs"}

        repo.update_defaults(settings)

        db.update_default_settings.assert_called_once_with(settings)


class TestGetSetting:
    def test_delegates_to_db_get_setting(self):
        db = _make_db()
        db.get_setting.return_value = "value123"
        repo = SqliteSettingsRepository(db)

        result = repo.get_setting("some_key")

        db.get_setting.assert_called_once_with("some_key")
        assert result == "value123"

    def test_returns_none_when_not_found(self):
        db = _make_db()
        db.get_setting.return_value = None
        repo = SqliteSettingsRepository(db)

        result = repo.get_setting("missing_key")

        assert result is None


class TestSetSetting:
    def test_delegates_to_db_set_setting(self):
        db = _make_db()
        repo = SqliteSettingsRepository(db)

        repo.set_setting("my_key", "my_value")

        db.set_setting.assert_called_once_with("my_key", "my_value")
