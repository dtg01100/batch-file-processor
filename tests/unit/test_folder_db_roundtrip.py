import ast
import contextlib
import json
import unittest

from backend.database import sqlite_wrapper
from core.database import schema
from core.domain.models.folder import FolderConfiguration


def _normalize_plugin_configs(value):
    """Normalize stored plugin_configurations (may be dict, JSON string, or Python dict repr)."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        # Try JSON first
        try:
            return json.loads(value)
        except Exception:
            try:
                # Fallback to Python literal eval for dict repr
                return ast.literal_eval(value)
            except Exception:
                # Last-resort: empty dict
                return {}
    return {}


class TestFolderDatabaseRoundTrip(unittest.TestCase):
    """Folder rows round-trip through the DB, including plugin_configurations.

    The plugin *configuration mapper* (form/widget layer) was removed in the
    webapp pivot; the plugin_configurations JSON column and its DB round-trip
    remain load-bearing because the dispatch converters read them at run time.
    """

    def setUp(self):
        # in-memory DB
        self.db = sqlite_wrapper.Database.connect(":memory:")
        schema.ensure_schema(self.db)

    def tearDown(self):
        with contextlib.suppress(Exception):
            self.db.close()

    def test_insert_and_read_folder_with_plugin_configs(self):
        fc = FolderConfiguration(folder_name="rt-test", folder_is_active="True")
        fc.set_plugin_configuration(
            "csv", {"include_headers": True, "filter_ampersand": False}
        )

        folders = self.db["folders"]
        new_id = folders.insert(fc.to_dict())

        row = folders.find_one(id=new_id)
        self.assertIsNotNone(row)

        stored = _normalize_plugin_configs(row.get("plugin_configurations"))
        self.assertIn("csv", stored)
        self.assertEqual(stored["csv"]["include_headers"], True)

    def test_insert_and_read_folder_plugin_configs_roundtrip_via_from_dict(self):
        """to_dict() -> DB -> find_one -> from_dict() preserves plugin configs."""
        fc = FolderConfiguration(folder_name="rt-roundtrip")
        fc.set_plugin_configuration("tweaks", {"foo": "bar", "n": 3})

        folders = self.db["folders"]
        new_id = folders.insert(fc.to_dict())

        row = folders.find_one(id=new_id)
        self.assertIsNotNone(row)
        row["plugin_configurations"] = _normalize_plugin_configs(
            row.get("plugin_configurations")
        )

        restored = FolderConfiguration.from_dict(dict(row))
        self.assertEqual(
            restored.get_plugin_configuration("tweaks"), {"foo": "bar", "n": 3}
        )


if __name__ == "__main__":
    unittest.main()
