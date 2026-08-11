"""Unit tests for webapp.paths (base-dir rebasing)."""

import pytest

from webapp.paths import (
    FOLDER_PATH_FIELDS,
    rebase_row,
    resolve,
    resolve_row,
    to_relative,
)

pytestmark = [pytest.mark.unit]


class TestToRelative:
    """Root stripping."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("C:\\Data\\Incoming\\X", "Data/Incoming/X"),
            ("C:/Data/Incoming/X", "Data/Incoming/X"),
            ("/home/user/incoming", "home/user/incoming"),
            ("/srv/batch/inbox", "srv/batch/inbox"),
            ("\\\\server\\share\\folder", "server/share/folder"),
            ("C:\\folder", "folder"),
            ("relative/path", "relative/path"),
            ("relative\\path", "relative/path"),
            ("", ""),
            (None, None),
        ],
    )
    def test_strips_root(self, path, expected):
        assert to_relative(path) == expected

    def test_platform_flag_is_accepted(self):
        assert to_relative("C:\\In\\Folder", _source_platform="Windows") == "In/Folder"
        assert to_relative("/var/data", _source_platform="Linux") == "var/data"


class TestResolve:
    """Relative -> absolute against the base-dir."""

    def test_joins_relative_path(self, tmp_path):
        assert resolve(tmp_path, "incoming/x") == str(tmp_path / "incoming" / "x")

    def test_normalises_backslashes(self, tmp_path):
        assert resolve(tmp_path, "incoming\\x") == str(tmp_path / "incoming" / "x")

    def test_absolute_passes_through(self, tmp_path):
        assert resolve(tmp_path, "/etc/hosts") == "/etc/hosts"

    def test_empty_returns_empty(self, tmp_path):
        assert resolve(tmp_path, "") == ""
        assert resolve(tmp_path, None) == ""


class TestRebaseRow:
    """Folder-row rebasing."""

    def test_folder_path_fields_become_relative(self):
        row = {
            "id": 1,
            "folder_name": "C:\\Data\\Incoming\\A",
            "copy_to_directory": "D:\\Out\\B",
            "ftp_server": "example.com",  # not a path — untouched
        }
        out = rebase_row(row, "Windows")
        assert out["folder_name"] == "Data/Incoming/A"
        assert out["copy_to_directory"] == "Out/B"
        assert out["ftp_server"] == "example.com"
        # input not mutated
        assert row["folder_name"] == "C:\\Data\\Incoming\\A"

    def test_path_fields_are_declared(self):
        assert "folder_name" in FOLDER_PATH_FIELDS
        assert "copy_to_directory" in FOLDER_PATH_FIELDS

    def test_empty_paths_survive(self):
        out = rebase_row(
            {"id": 1, "folder_name": "", "copy_to_directory": None}, "Windows"
        )
        assert out["folder_name"] == ""
        assert out["copy_to_directory"] is None


class TestResolveRow:
    """Runner-side resolution of relative rows."""

    def test_resolves_path_fields(self, tmp_path):
        row = {"id": 1, "folder_name": "incoming/a", "copy_to_directory": "out"}
        out = resolve_row(row, tmp_path)
        assert out["folder_name"] == str(tmp_path / "incoming" / "a")
        assert out["copy_to_directory"] == str(tmp_path / "out")
        # input not mutated
        assert row["folder_name"] == "incoming/a"

    def test_round_trip_to_relative_resolve(self, tmp_path):
        row = {"id": 1, "folder_name": "C:\\Data\\Incoming\\X"}
        relative = rebase_row(row, "Windows")
        resolved = resolve_row(relative, tmp_path)
        assert resolved["folder_name"] == str(tmp_path / "Data" / "Incoming" / "X")
