"""Integration tests that validate real production data shapes from the fixture database.

Uses the shared conftest fixtures (legacy_v32_db, migrated_v42_db, real_folder_row,
real_folder_rows, real_settings_row, real_admin_row) to ensure that
FolderConfiguration.from_dict() and related models handle ALL real-world data
shapes present in the 530-row production database.
"""

import pytest

from interface.models.folder_configuration import FolderConfiguration


pytestmark = [pytest.mark.integration]


class TestRealFolderConfigFromDict:
    """Tests that FolderConfiguration.from_dict() works with real production data."""

    def test_from_dict_with_real_folder_row(self, real_folder_row):
        """Constructing from a known real row (id=21) succeeds with expected values."""
        fc = FolderConfiguration.from_dict(real_folder_row)
        assert fc.folder_name, "folder_name should not be empty"
        assert fc.alias == "012258"

    def test_from_dict_roundtrip_with_real_data(self, real_folder_row):
        """Round-tripping through from_dict -> to_dict preserves key fields."""
        fc = FolderConfiguration.from_dict(real_folder_row)
        result = fc.to_dict()
        assert result["alias"] == real_folder_row["alias"]
        assert result["convert_to_format"] == real_folder_row["convert_to_format"]

    def test_from_dict_with_multiple_real_rows(self, real_folder_rows):
        """All 5 diverse fixture rows parse without error and have folder names."""
        assert len(real_folder_rows) == 5, "Expected 5 diverse folder rows"
        for row in real_folder_rows:
            fc = FolderConfiguration.from_dict(row)
            assert fc.folder_name, (
                f"folder_name should not be empty for row id={row.get('id')}"
            )

    def test_edi_config_populated_from_real_data(self, real_folder_row):
        """EDI sub-configuration is populated and convert_to_format is a string."""
        fc = FolderConfiguration.from_dict(real_folder_row)
        assert fc.edi is not None, "edi should be populated from real data"
        assert isinstance(fc.edi.convert_to_format, str)

    def test_csv_config_populated_from_real_data(self, real_folder_row):
        """CSV sub-configuration is populated from real data."""
        fc = FolderConfiguration.from_dict(real_folder_row)
        assert fc.csv is not None, "csv should be populated from real data"


class TestRealFolderConfigAtScale:
    """Tests FolderConfiguration against ALL 530 folders in the fixture database."""

    def test_all_530_folders_parse_as_folder_config(self, migrated_v42_db):
        """Every one of the 530 production rows parses via from_dict without error."""
        failures = []
        count = 0
        for row in migrated_v42_db["folders"].all():
            count += 1
            try:
                FolderConfiguration.from_dict(row)
            except Exception as exc:
                failures.append(
                    f"Row id={row.get('id')} alias={row.get('alias')!r}: {exc}"
                )
        assert count == 530, f"Expected 530 folder rows, got {count}"
        assert failures == [], (
            f"{len(failures)} folder(s) failed to parse:\n"
            + "\n".join(failures)
        )

    def test_all_folders_roundtrip(self, migrated_v42_db):
        """First 50 folders survive a from_dict -> to_dict round-trip."""
        for row in migrated_v42_db["folders"].find(_limit=50):
            fc = FolderConfiguration.from_dict(row)
            result = fc.to_dict()
            assert isinstance(result, dict)
            assert "folder_name" in result, (
                f"Round-tripped dict missing 'folder_name' for row id={row.get('id')}"
            )


class TestRealSettingsIntegrity:
    """Validates that the migrated settings row contains expected keys and types."""

    def test_settings_have_expected_keys(self, real_settings_row):
        """Core settings keys exist and have non-None values."""
        for key in ("smtp_port", "email_smtp_server", "odbc_driver"):
            assert key in real_settings_row, f"Missing key: {key}"
            assert real_settings_row[key] is not None, f"{key} should not be None"

    def test_settings_smtp_port_is_numeric(self, real_settings_row):
        """smtp_port can be converted to int without error."""
        port = int(real_settings_row["smtp_port"])
        assert port > 0, "smtp_port should be a positive integer"


class TestRealAdminIntegrity:
    """Validates that the migrated administrative row has expected structure."""

    def test_admin_has_logs_directory(self, real_admin_row):
        """logs_directory exists and is a non-empty string."""
        assert "logs_directory" in real_admin_row
        assert isinstance(real_admin_row["logs_directory"], str)
        assert real_admin_row["logs_directory"], "logs_directory should not be empty"

    def test_admin_has_expected_keys(self, real_admin_row):
        """Administrative row contains logs_directory and enable_reporting."""
        for key in ("logs_directory", "enable_reporting"):
            assert key in real_admin_row, f"Missing key: {key}"
