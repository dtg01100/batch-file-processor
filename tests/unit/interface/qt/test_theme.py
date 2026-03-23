"""Tests for Theme class asset URI generation."""

from pathlib import Path

from interface.qt.theme import Theme


class TestAssetUri:
    """Test suite for Theme._asset_uri method."""

    def test_asset_uri_returns_absolute_path(self):
        """Test that _asset_uri returns an absolute filesystem path."""
        result = Theme._asset_uri("checkbox_checked.svg")

        # Should be an absolute path starting with /
        assert Path(result).is_absolute(), f"Expected absolute path, got: {result}"

    def test_asset_uri_does_not_return_uri(self):
        """Test that _asset_uri returns a path string, not a URI with file:// scheme."""
        result = Theme._asset_uri("checkbox_checked.svg")

        # Should NOT contain file:// scheme - Qt stylesheets don't handle URIs correctly
        assert not result.startswith(
            "file://"
        ), f"Expected path string, got URI: {result}"
        assert "file:" not in result, f"Path should not contain file: scheme: {result}"

    def test_asset_uri_points_to_existing_file(self):
        """Test that the returned path points to an existing asset file."""
        result = Theme._asset_uri("checkbox_checked.svg")

        assert Path(result).exists(), f"Asset file does not exist: {result}"

    def test_asset_uri_all_assets_exist(self):
        """Test that all SVG assets referenced in stylesheets exist."""
        # These are the assets used in the theme stylesheet
        assets = [
            "checkbox_checked.svg",
            "spinbox_up.svg",
            "spinbox_down.svg",
            "spinbox_up_disabled.svg",
            "spinbox_down_disabled.svg",
            "dropdown_arrow.svg",
            "dropdown_arrow_disabled.svg",
        ]

        for asset in assets:
            result = Theme._asset_uri(asset)
            assert Path(result).exists(), f"Asset file does not exist: {result}"

    def test_asset_uri_path_contains_assets_directory(self):
        """Test that the returned path contains the assets directory."""
        result = Theme._asset_uri("checkbox_checked.svg")

        assert "assets" in result, f"Path should contain 'assets' directory: {result}"
        assert result.endswith(
            "checkbox_checked.svg"
        ), f"Path should end with filename: {result}"

    def test_asset_uri_uses_forward_slashes_for_qss(self):
        """Qt stylesheets expect URL paths with forward slashes for reliability."""
        result = Theme._asset_uri("checkbox_checked.svg")

        assert "\\" not in result, f"Path should not contain backslashes: {result}"
