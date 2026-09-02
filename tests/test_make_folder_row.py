"""Smoke tests for the Phase 9.7 ``make_folder_row`` factory."""

from tests.conftest import make_folder_row


class TestMakeFolderRow:
    def test_defaults_produce_active_csv_row(self):
        row = make_folder_row()
        assert row["convert_to_format"] == "csv"
        assert row["folder_is_active"] == "True"
        assert row["process_backend_copy"] == "False"
        assert row["process_backend_ftp"] == "False"
        assert "plugin_configurations" in row
        assert "id" in row

    def test_backends_set_their_columns(self):
        row = make_folder_row(backends=("copy", "ftp"))
        assert row["process_backend_copy"] == "True"
        assert row["process_backend_ftp"] == "True"
        assert row["process_backend_email"] == "False"
        assert row["process_backend_http"] == "False"

    def test_overrides_win(self):
        row = make_folder_row(convert_to_format="x810", include_headers="False")
        assert row["convert_to_format"] == "x810"
        assert row["include_headers"] == "False"

    def test_id_and_alias_customizable(self):
        row = make_folder_row(id=42, alias="ACME")
        assert row["id"] == 42
        assert row["alias"] == "ACME"

    def test_watch_enabled_default_false(self):
        row = make_folder_row()
        assert row["watch_enabled"] == "False"
        row2 = make_folder_row(watch_enabled="True")
        assert row2["watch_enabled"] == "True"
