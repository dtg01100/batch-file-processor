"""Integration tests for plugin mapper and form generator."""

import unittest
from unittest.mock import MagicMock, patch

from interface.models.folder_configuration import FolderConfiguration
from interface.operations.plugin_configuration_mapper import (
    PluginConfigurationMapper,
    PluginSectionStateManager,
)


class TestPluginMapperWithFormGenerator(unittest.TestCase):
    """Integration tests for plugin mapper with form generator."""

    def test_form_generator_integration(self):
        """Test that plugin mapper works with real Qt widgets."""
        from PyQt5.QtWidgets import QApplication, QCheckBox, QLineEdit, QSpinBox

        # Ensure QApplication exists for offscreen testing
        QApplication.instance() or QApplication(["test"])

        mapper = PluginConfigurationMapper()

        # Create real Qt widgets
        include_headers_checkbox = QCheckBox()
        include_headers_checkbox.setChecked(True)

        delimiter_edit = QLineEdit()
        delimiter_edit.setText(";")

        precision_spin = QSpinBox()
        precision_spin.setRange(0, 10)
        precision_spin.setValue(4)

        widget_fields = {
            "include_headers": include_headers_checkbox,
            "delimiter": delimiter_edit,
            "numeric_precision": precision_spin,
        }

        with patch(
            "interface.operations.plugin_configuration_mapper.PluginManager"
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.discover_plugins = MagicMock()
            mock_manager.initialize_plugins = MagicMock()
            mock_manager.get_configuration_plugins = MagicMock(return_value=[])

            extracted = mapper.extract_plugin_configurations(
                widget_fields, framework="qt"
            )

            self.assertIsInstance(extracted, list)

    def test_state_manager_with_multiple_formats(self):
        """Test state manager with multiple plugin formats."""
        state_manager = PluginSectionStateManager()

        csv_config = {"include_headers": True}
        scannerware_config = {"padding": "left"}
        estore_config = {"store_number": "12345"}

        state_manager.initialize_state("csv", csv_config, True, [])
        state_manager.initialize_state("scannerware", scannerware_config, True, [])
        state_manager.initialize_state("estore", estore_config, True, [])

        all_configs = state_manager.get_all_configs()

        self.assertEqual(len(all_configs), 3)
        self.assertIn("csv", all_configs)
        self.assertIn("scannerware", all_configs)
        self.assertIn("estore", all_configs)

    def test_undo_redo_with_multiple_formats(self):
        """Test undo/redo with multiple plugin formats."""
        state_manager = PluginSectionStateManager()

        state_manager.initialize_state("csv", {"v1": 1}, True, [])
        state_manager.update_state("csv", {"v1": 2}, True, [])
        state_manager.update_state("csv", {"v1": 3}, True, [])

        state_manager.undo()
        state_manager.undo()

        state = state_manager.get_state("csv")
        self.assertEqual(state.config, {"v1": 1})

        state_manager.redo()

        state = state_manager.get_state("csv")
        self.assertEqual(state.config, {"v1": 2})


class TestPluginMapperWithFolderConfig(unittest.TestCase):
    """Tests for plugin mapper with FolderConfiguration."""

    def test_update_folder_with_multiple_plugins(self):
        """Test updating folder config with multiple plugins."""
        mapper = PluginConfigurationMapper()

        folder_config = FolderConfiguration(
            folder_name="Test Folder", folder_is_active="True"
        )

        extracted_configs = [
            MagicMock(),
            MagicMock(),
        ]

        extracted_configs[0].format_name = "csv"
        extracted_configs[0].config = {"include_headers": True}
        extracted_configs[0].validation_errors = []

        extracted_configs[1].format_name = "scannerware"
        extracted_configs[1].config = {"padding": "left"}
        extracted_configs[1].validation_errors = []

        mapper.update_folder_configuration(folder_config, extracted_configs)

        csv_config = folder_config.get_plugin_configuration("csv")
        self.assertIsNotNone(csv_config)
        self.assertEqual(csv_config["include_headers"], True)

    def test_serialize_deserialize_roundtrip(self):
        """Test full serialize/deserialize roundtrip."""
        mapper = PluginConfigurationMapper()

        original_config = {
            "include_headers": True,
            "filter_ampersand": False,
            "numeric_precision": 4,
            "custom_fields": ["field1", "field2"],
        }

        serialized = mapper.serialize_plugin_config("csv", original_config)
        format_name, deserialized = mapper.deserialize_plugin_config(serialized)

        self.assertEqual(format_name, "csv")
        self.assertEqual(deserialized, original_config)

    def test_validation_state_tracking(self):
        """Test that validation state is properly tracked."""
        state_manager = PluginSectionStateManager()

        state_manager.initialize_state("csv", {"value": 1}, True, [])

        self.assertTrue(state_manager.get_state("csv").is_valid)

        state_manager.update_state("csv", {"value": 2}, False, ["Invalid value"])

        state = state_manager.get_state("csv")
        self.assertFalse(state.is_valid)
        self.assertIn("Invalid value", state.validation_errors)

        invalid_sections = state_manager.get_invalid_sections()
        self.assertIn("csv", invalid_sections)


class TestBackwardCompatibility(unittest.TestCase):
    """Tests for backward compatibility with existing folder settings."""

    def test_empty_plugin_configurations(self):
        """Test that empty plugin configurations work correctly."""
        folder_config = FolderConfiguration(
            folder_name="Test Folder", folder_is_active="True"
        )

        csv_config = folder_config.get_plugin_configuration("csv")
        self.assertIsNone(csv_config)

        has_csv = folder_config.has_plugin_configuration("csv")
        self.assertFalse(has_csv)

    def test_legacy_folder_config_dict(self):
        """Test that legacy folder config dict is handled correctly."""
        PluginConfigurationMapper()

        legacy_config = {
            "folder_name": "Test",
            "folder_is_active": "True",
            "convert_to_format": "csv",
            "include_headers": "True",
        }

        folder_config = FolderConfiguration.from_dict(legacy_config)

        self.assertEqual(folder_config.folder_name, "Test")
        self.assertEqual(folder_config.folder_is_active, True)

    def test_plugin_config_migration(self):
        """Test migrating legacy settings to plugin config."""
        PluginConfigurationMapper()

        legacy_settings = {
            "include_headers": "True",
            "filter_ampersand": "False",
            "calculate_upc_check_digit": "True",
        }

        plugin_config = {}

        for key, value in legacy_settings.items():
            if value == "True":
                plugin_config[key] = True
            elif value == "False":
                plugin_config[key] = False
            else:
                plugin_config[key] = value

        self.assertTrue(plugin_config["include_headers"])
        self.assertFalse(plugin_config["filter_ampersand"])
        self.assertTrue(plugin_config["calculate_upc_check_digit"])


if __name__ == "__main__":
    unittest.main()
