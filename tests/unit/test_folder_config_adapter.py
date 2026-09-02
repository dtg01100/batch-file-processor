"""Unit tests for ``webapp.pipeline.config.FolderConfigAdapter``."""

import json

from tests.conftest import make_folder_row
from webapp.pipeline.config import FolderConfig, FolderConfigAdapter


class TestFolderConfigAdapter:
    def test_default_row_produces_typed_config(self):
        row = make_folder_row(id=42, alias="ACME", folder_name="acme/in")
        config = FolderConfigAdapter.from_row(row)
        assert isinstance(config, FolderConfig)
        assert config.folder_id == 42
        assert config.folder_name == "acme/in"
        assert config.alias == "ACME"
        assert config.is_active is True
        assert config.convert_to_format == "csv"
        assert config.process_backends == []
        assert config.watch_enabled is False

    def test_backends_parsed_into_list(self):
        row = make_folder_row(backends=("copy", "ftp"))
        config = FolderConfigAdapter.from_row(row)
        assert config.process_backends == ["copy", "ftp"]

    def test_dict_style_access_works(self):
        row = make_folder_row(alias="BACKWARD")
        config = FolderConfigAdapter.from_row(row)
        # New typed access
        assert config.alias == "BACKWARD"
        # Old dict-style access
        assert config["alias"] == "BACKWARD"
        assert config["folder_name"] == "/data/test-folder"
        # Old .get access
        assert config.get("alias") == "BACKWARD"
        assert config.get("missing", "fallback") == "fallback"

    def test_dict_style_unknown_key_raises(self):
        config = FolderConfigAdapter.from_row(make_folder_row())
        import pytest

        with pytest.raises(KeyError):
            config["nonexistent_field"]

    def test_watch_enabled_normalized(self):
        row = make_folder_row(watch_enabled="True")
        config = FolderConfigAdapter.from_row(row)
        assert config.watch_enabled is True

    def test_plugin_configurations_parsed_from_json(self):
        row = make_folder_row(
            plugin_configurations=json.dumps({"csv": {"include_headers": True}})
        )
        config = FolderConfigAdapter.from_row(row)
        assert config.plugin_configurations == {"csv": {"include_headers": True}}

    def test_plugin_configurations_default_empty_dict(self):
        row = make_folder_row()
        config = FolderConfigAdapter.from_row(row)
        assert config.plugin_configurations == {}

    def test_thresholds_parsed_as_int(self):
        row = make_folder_row(max_duration_seconds=300, max_failure_rate_percent=5)
        config = FolderConfigAdapter.from_row(row)
        assert config.max_duration_seconds == 300
        assert config.max_failure_rate_percent == 5

    def test_unknown_bool_string_treated_as_false(self):
        """Legacy behaviour: 'maybe' is not 'True' / 'False', so it's False.

        This matches ``normalize_parameter`` in the converter base.
        """
        row = make_folder_row()
        row["folder_is_active"] = "maybe"
        config = FolderConfigAdapter.from_row(row)
        assert config.is_active is False

    def test_id_zero_when_missing(self):
        row = make_folder_row()
        row.pop("id", None)
        config = FolderConfigAdapter.from_row(row)
        assert config.folder_id == 0
