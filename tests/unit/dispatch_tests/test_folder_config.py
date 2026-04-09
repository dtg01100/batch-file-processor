"""Tests for dispatch.config.folder_config - FolderProcessingConfig."""

from dispatch.config.folder_config import FolderProcessingConfig


class TestFolderProcessingConfig:
    """Tests for FolderProcessingConfig dataclass."""

    def test_default_values(self):
        """Test default values are sensible."""
        config = FolderProcessingConfig()

        assert config.folder_name == ""
        assert config.alias == ""
        assert config.process_edi is False
        assert config.convert_edi is False
        assert config.convert_to_format == ""
        assert config.tweak_edi is False
        assert config.split_edi is False
        assert config.validate_edi is False
        assert config.send_backend == ""
        assert config.is_active is True
        assert config.extra_params == {}

    def test_from_dict_with_booleans(self):
        """Test from_dict with proper boolean values."""
        data = {
            "folder_name": "/path/to/folder",
            "alias": "Test Folder",
            "process_edi": True,
            "convert_edi": True,
            "convert_to_format": "csv",
            "tweak_edi": False,
        }

        config = FolderProcessingConfig.from_dict(data)

        assert config.folder_name == "/path/to/folder"
        assert config.alias == "Test Folder"
        assert config.process_edi is True
        assert config.convert_edi is True
        assert config.convert_to_format == "csv"
        assert config.tweak_edi is False

    def test_from_dict_with_string_booleans(self):
        """Test from_dict normalizes string booleans."""
        data = {
            "folder_name": "/path/to/folder",
            "process_edi": "True",
            "convert_edi": "true",
            "tweak_edi": "1",
            "split_edi": "0",
        }

        config = FolderProcessingConfig.from_dict(data)

        assert config.process_edi is True
        assert config.convert_edi is True
        assert config.tweak_edi is True
        assert config.split_edi is False

    def test_from_dict_uses_folder_name_as_alias(self):
        """Test alias falls back to folder_name if not provided."""
        data = {"folder_name": "/path/to/folder"}

        config = FolderProcessingConfig.from_dict(data)

        assert config.alias == "/path/to/folder"

    def test_from_dict_extracts_extra_params(self):
        """Test extra parameters are captured in extra_params."""
        data = {
            "folder_name": "/path/to/folder",
            "custom_param_1": "value1",
            "custom_param_2": 42,
        }

        config = FolderProcessingConfig.from_dict(data)

        assert config.extra_params == {
            "custom_param_1": "value1",
            "custom_param_2": 42,
        }

    def test_to_dict_roundtrip(self):
        """Test to_dict produces usable dictionary."""
        original = FolderProcessingConfig(
            folder_name="/path/to/folder",
            alias="Test",
            process_edi=True,
            convert_edi=True,
            convert_to_format="csv",
        )

        data = original.to_dict()
        restored = FolderProcessingConfig.from_dict(data)

        assert restored.folder_name == original.folder_name
        assert restored.alias == original.alias
        assert restored.process_edi == original.process_edi
        assert restored.convert_edi == original.convert_edi
        assert restored.convert_to_format == original.convert_to_format

    def test_display_name_property(self):
        """Test display_name returns alias or folder_name."""
        config_with_alias = FolderProcessingConfig(
            folder_name="/path", alias="My Folder"
        )
        assert config_with_alias.display_name == "My Folder"

        config_without_alias = FolderProcessingConfig(folder_name="/path")
        assert config_without_alias.display_name == "/path"

    def test_has_conversion_property(self):
        """Test has_conversion checks both flag and format."""
        config = FolderProcessingConfig(convert_edi=True, convert_to_format="csv")
        assert config.has_conversion is True

        config_no_format = FolderProcessingConfig(convert_edi=True, convert_to_format="")
        assert config_no_format.has_conversion is False

        config_disabled = FolderProcessingConfig(
            convert_edi=False, convert_to_format="csv"
        )
        assert config_disabled.has_conversion is False

    def test_has_tweaks_property_legacy(self):
        """Test has_tweaks checks legacy flag and format."""
        config_legacy = FolderProcessingConfig(tweak_edi=True)
        assert config_legacy.has_tweaks is True

        config_new = FolderProcessingConfig(convert_to_format="tweaks")
        assert config_new.has_tweaks is True

        config_no_tweaks = FolderProcessingConfig()
        assert config_no_tweaks.has_tweaks is False

    def test_from_dict_with_empty_data(self):
        """Test from_dict with empty dict uses all defaults."""
        config = FolderProcessingConfig.from_dict({})

        assert config.folder_name == ""
        assert config.alias == ""
        assert config.is_active is True

    def test_from_dict_with_none_values(self):
        """Test from_dict handles None values gracefully."""
        data = {
            "folder_name": None,
            "process_edi": None,
            "convert_to_format": None,
        }

        # Should not raise
        config = FolderProcessingConfig.from_dict(data)

        assert config.folder_name is None or config.folder_name == ""
        assert config.process_edi is False  # normalize_bool(None) -> False
