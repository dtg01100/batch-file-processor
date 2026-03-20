"""Tests for plugin configuration mapper integration and state management."""

import unittest
from unittest.mock import MagicMock

import pytest
from PyQt5.QtWidgets import QApplication, QTextEdit

from interface.models.folder_configuration import FolderConfiguration
from interface.operations.plugin_configuration_mapper import (
    ExtractedPluginConfig,
    PluginConfigPopulationResult,
    PluginConfigurationMapper,
    PluginSectionStateManager,
)
from interface.plugins.config_schemas import (
    ConfigurationSchema,
    FieldDefinition,
    FieldType,
)
from interface.plugins.ui_abstraction import WidgetBase
from interface.plugins.validation_framework import ValidationResult


class TestPluginSectionStateManager(unittest.TestCase):
    """Tests for PluginSectionStateManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.state_manager = PluginSectionStateManager()

    def test_initialize_state(self):
        """Test initializing state for a plugin section."""
        config = {"include_headers": True, "filter_ampersand": False}

        self.state_manager.initialize_state("csv", config, True, [])

        state = self.state_manager.get_state("csv")
        self.assertIsNotNone(state)
        self.assertEqual(state.config, config)
        self.assertTrue(state.is_valid)
        self.assertEqual(len(state.validation_errors), 0)

    def test_update_state(self):
        """Test updating state for a plugin section."""
        config = {"include_headers": True}
        new_config = {"include_headers": False}

        self.state_manager.initialize_state("csv", config, True, [])
        changed = self.state_manager.update_state("csv", new_config, True, [])

        self.assertTrue(changed)
        state = self.state_manager.get_state("csv")
        self.assertEqual(state.config, new_config)
        self.assertTrue(self.state_manager.is_dirty)

    def test_update_state_no_change(self):
        """Test updating state when config hasn't changed."""
        config = {"include_headers": True}

        self.state_manager.initialize_state("csv", config, True, [])
        changed = self.state_manager.update_state("csv", config, True, [])

        self.assertFalse(changed)

    def test_undo(self):
        """Test undo functionality."""
        config1 = {"include_headers": True}
        config2 = {"include_headers": False}

        self.state_manager.initialize_state("csv", config1, True, [])
        self.state_manager.update_state("csv", config2, True, [])

        result = self.state_manager.undo()

        self.assertTrue(result)
        state = self.state_manager.get_state("csv")
        self.assertEqual(state.config, config1)

    def test_redo(self):
        """Test redo functionality."""
        config1 = {"include_headers": True}
        config2 = {"include_headers": False}

        self.state_manager.initialize_state("csv", config1, True, [])
        self.state_manager.update_state("csv", config2, True, [])
        self.state_manager.undo()

        result = self.state_manager.redo()

        self.assertTrue(result)
        state = self.state_manager.get_state("csv")
        self.assertEqual(state.config, config2)

    def test_undo_empty_stack(self):
        """Test undo with empty stack."""
        result = self.state_manager.undo()
        self.assertFalse(result)

    def test_redo_empty_stack(self):
        """Test redo with empty stack."""
        result = self.state_manager.redo()
        self.assertFalse(result)

    def test_mark_saved(self):
        """Test marking state as saved."""
        config = {"include_headers": True}

        self.state_manager.initialize_state("csv", config, True, [])
        self.state_manager.update_state("csv", {"include_headers": False}, True, [])

        self.state_manager.mark_saved()

        self.assertFalse(self.state_manager.is_dirty)

    def test_reset_to_saved(self):
        """Test resetting to saved state."""
        config = {"include_headers": True}

        self.state_manager.initialize_state("csv", config, True, [])
        self.state_manager.update_state("csv", {"include_headers": False}, True, [])

        self.state_manager.reset_to_saved()

        state = self.state_manager.get_state("csv")
        self.assertEqual(state.config, config)
        self.assertFalse(self.state_manager.is_dirty)

    def test_get_all_configs(self):
        """Test getting all configurations."""
        config1 = {"include_headers": True}
        config2 = {"field1": "value1"}

        self.state_manager.initialize_state("csv", config1, True, [])
        self.state_manager.initialize_state("scannerware", config2, True, [])

        configs = self.state_manager.get_all_configs()

        self.assertEqual(len(configs), 2)
        self.assertIn("csv", configs)
        self.assertIn("scannerware", configs)

    def test_get_invalid_sections(self):
        """Test getting sections with validation errors."""
        self.state_manager.initialize_state("csv", {"include_headers": True}, True, [])
        self.state_manager.initialize_state(
            "invalid", {"field": "value"}, False, ["Error 1", "Error 2"]
        )

        invalid = self.state_manager.get_invalid_sections()

        self.assertIn("invalid", invalid)
        self.assertNotIn("csv", invalid)

    def test_get_all_validation_errors(self):
        """Test getting all validation errors."""
        self.state_manager.initialize_state(
            "csv", {"include_headers": True}, False, ["Error 1"]
        )
        self.state_manager.initialize_state(
            "invalid", {"field": "value"}, False, ["Error 2", "Error 3"]
        )

        errors = self.state_manager.get_all_validation_errors()

        self.assertEqual(len(errors), 3)
        self.assertIn("Error 1", errors)
        self.assertIn("Error 2", errors)
        self.assertIn("Error 3", errors)

    def test_can_undo_property(self):
        """Test can_undo property."""
        self.assertFalse(self.state_manager.can_undo)

        self.state_manager.initialize_state("csv", {"value": 1}, True, [])
        self.state_manager.update_state("csv", {"value": 2}, True, [])

        self.assertTrue(self.state_manager.can_undo)

    def test_can_redo_property(self):
        """Test can_redo property."""
        self.assertFalse(self.state_manager.can_redo)

        self.state_manager.initialize_state("csv", {"value": 1}, True, [])
        self.state_manager.update_state("csv", {"value": 2}, True, [])
        self.state_manager.undo()

        self.assertTrue(self.state_manager.can_redo)

    def test_clear(self):
        """Test clearing all state."""
        self.state_manager.initialize_state("csv", {"include_headers": True}, True, [])
        self.state_manager.update_state("csv", {"include_headers": False}, True, [])

        self.state_manager.clear()

        self.assertIsNone(self.state_manager.get_state("csv"))
        self.assertFalse(self.state_manager.is_dirty)


class TestPluginConfigurationMapper(unittest.TestCase):
    """Tests for PluginConfigurationMapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.mapper = PluginConfigurationMapper()

    def test_init(self):
        """Test initialization."""
        self.assertIsNotNone(self.mapper)
        self.assertIsNotNone(self.mapper.state_manager)
        self.assertIsNotNone(self.mapper.plugin_manager)

    def test_get_supported_plugin_formats(self):
        """Test getting supported plugin formats."""
        formats = self.mapper.get_supported_plugin_formats()

        self.assertIsInstance(formats, list)

    def test_get_plugin_configuration_fields(self):
        """Test getting plugin configuration fields."""
        fields = self.mapper.get_plugin_configuration_fields("csv")

        self.assertIsInstance(fields, list)

    def test_serialize_plugin_config(self):
        """Test serializing plugin config."""
        config = {"include_headers": True, "filter_ampersand": False}

        serialized = self.mapper.serialize_plugin_config("csv", config)

        self.assertIsInstance(serialized, str)
        self.assertIn("csv", serialized)

    def test_deserialize_plugin_config(self):
        """Test deserializing plugin config."""
        config = {"include_headers": True, "filter_ampersand": False}

        serialized = self.mapper.serialize_plugin_config("csv", config)
        format_name, deserialized_config = self.mapper.deserialize_plugin_config(
            serialized
        )

        self.assertEqual(format_name, "csv")
        self.assertEqual(deserialized_config, config)

    def test_roundtrip_serialization(self):
        """Test roundtrip serialization/deserialization."""
        config = {"include_headers": True, "filter_ampersand": False}

        serialized = self.mapper.serialize_plugin_config("csv", config)
        format_name, deserialized = self.mapper.deserialize_plugin_config(serialized)

        self.assertEqual(format_name, "csv")
        self.assertEqual(deserialized, config)

    def test_validate_plugin_configurations_from_dict(self):
        """Test validating plugin configurations from dict."""
        folder_config_dict = {
            "plugin_configurations": {"csv": {"include_headers": True}}
        }

        errors = self.mapper.validate_plugin_configurations_from_dict(
            folder_config_dict
        )

        self.assertIsInstance(errors, list)

    def test_state_manager_integration(self):
        """Test that state manager is properly integrated."""
        config = {"include_headers": True}

        self.mapper.state_manager.initialize_state("csv", config, True, [])

        # After initialization, state is saved so is_dirty should be False
        self.assertFalse(self.mapper.state_manager.is_dirty)

        # After update, it should be dirty
        self.mapper.state_manager.update_state(
            "csv", {"include_headers": False}, True, []
        )

        self.assertTrue(self.mapper.state_manager.is_dirty)

        self.mapper.state_manager.mark_saved()

        self.assertFalse(self.mapper.state_manager.is_dirty)

    def test_get_state_manager(self):
        """Test getting state manager."""
        state_manager = self.mapper.get_state_manager()

        self.assertIsNotNone(state_manager)
        self.assertIsInstance(state_manager, PluginSectionStateManager)


class TestPluginConfigurationMapperWithFolderConfig(unittest.TestCase):
    """Tests for PluginConfigurationMapper with FolderConfiguration."""

    def setUp(self):
        """Set up test fixtures."""
        self.mapper = PluginConfigurationMapper()
        self.folder_config = FolderConfiguration(
            folder_name="Test Folder", folder_is_active="True", alias="Test"
        )

    def test_populate_plugin_widgets_from_dict(self):
        """Test populating plugin widgets from dict."""
        folder_config_dict = {
            "folder_name": "Test Folder",
            "folder_is_active": "True",
            "alias": "Test",
            "plugin_configurations": {"csv": {"include_headers": True}},
        }

        dialog_fields = {}

        result = self.mapper.populate_plugin_widgets_from_dict(
            folder_config_dict, dialog_fields, framework="qt"
        )

        self.assertIsInstance(result, PluginConfigPopulationResult)

    def test_update_folder_configuration_from_dict(self):
        """Test updating folder configuration from dict."""
        folder_config_dict = {"folder_name": "Test Folder", "plugin_configurations": {}}

        extracted_configs = [
            ExtractedPluginConfig(
                format_name="csv",
                config={"include_headers": True},
                validation_errors=[],
            )
        ]

        updated = self.mapper.update_folder_configuration_from_dict(
            folder_config_dict, extracted_configs
        )

        self.assertIn("plugin_configurations", updated)
        self.assertIn("csv", updated["plugin_configurations"])


class TestExtractedPluginConfig(unittest.TestCase):
    """Tests for ExtractedPluginConfig dataclass."""

    def test_creation(self):
        """Test creating ExtractedPluginConfig."""
        config = ExtractedPluginConfig(
            format_name="csv",
            config={"include_headers": True},
            validation_errors=["Error 1"],
        )

        self.assertEqual(config.format_name, "csv")
        self.assertEqual(config.config, {"include_headers": True})
        self.assertEqual(config.validation_errors, ["Error 1"])

    def test_default_validation_errors(self):
        """Test default validation errors."""
        config = ExtractedPluginConfig(format_name="csv", config={})

        self.assertEqual(config.validation_errors, [])


class TestPluginConfigPopulationResult(unittest.TestCase):
    """Tests for PluginConfigPopulationResult dataclass."""

    def test_creation(self):
        """Test creating PluginConfigPopulationResult."""
        result = PluginConfigPopulationResult(
            success=True, widget_count=5, errors=["Error 1"]
        )

        self.assertTrue(result.success)
        self.assertEqual(result.widget_count, 5)
        self.assertEqual(result.errors, ["Error 1"])

    def test_default_values(self):
        """Test default values."""
        result = PluginConfigPopulationResult(success=True)

        self.assertEqual(result.widget_count, 0)
        self.assertEqual(result.errors, [])


@pytest.fixture
def qapp():
    """Provide a Qt application for widget-based tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class BrokenWidget(WidgetBase):
    """Widget abstraction that fails when read."""

    def get_widget(self):
        return None

    def set_value(self, value):
        return None

    def get_value(self):
        raise RuntimeError("widget exploded")

    def set_label(self, label):
        return None

    def set_description(self, description):
        return None

    def set_enabled(self, enabled):
        return None

    def set_visible(self, visible):
        return None

    def validate(self):
        return True

    def get_validation_errors(self):
        return []


def _build_test_plugin(field_name="test_field", default="fallback"):
    plugin = MagicMock()
    plugin.get_format_name.return_value = "csv"
    plugin.get_configuration_schema.return_value = ConfigurationSchema(
        [
            FieldDefinition(
                name=field_name,
                field_type=FieldType.STRING,
                label=field_name,
                default=default,
            )
        ]
    )
    plugin.validate_config.return_value = ValidationResult(success=True, errors=[])
    return plugin


def test_extract_plugin_configurations_uses_defaults_when_not_strict(monkeypatch):
    """Non-strict mode should keep legacy defaulting on widget access failures."""
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
    plugin = _build_test_plugin()
    plugin_manager = MagicMock()
    plugin_manager.get_configuration_plugins.return_value = [plugin]
    mapper = PluginConfigurationMapper(plugin_manager=plugin_manager)

    extracted = mapper.extract_plugin_configurations(
        {"test_field": BrokenWidget()}, framework="qt"
    )

    assert extracted[0].config == {"test_field": "fallback"}
    assert extracted[0].validation_errors == []


def test_extract_plugin_configurations_raise_in_strict_mode(monkeypatch):
    """Strict testing mode should surface widget read failures."""
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
    plugin = _build_test_plugin()
    plugin_manager = MagicMock()
    plugin_manager.get_configuration_plugins.return_value = [plugin]
    mapper = PluginConfigurationMapper(plugin_manager=plugin_manager)

    with pytest.raises(RuntimeError, match="Error extracting configuration for csv"):
        mapper.extract_plugin_configurations({"test_field": BrokenWidget()}, "qt")


@pytest.mark.qt
def test_get_qt_widget_value_returns_empty_dict_when_not_strict(monkeypatch, qapp):
    """Non-strict mode should keep legacy JSON fallback behavior."""
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
    widget = QTextEdit()
    widget.setPlainText("{not-json")
    mapper = PluginConfigurationMapper(plugin_manager=MagicMock())

    assert mapper._get_qt_widget_value(widget, "json_field") == {}


@pytest.mark.qt
def test_get_qt_widget_value_raises_on_invalid_json_in_strict_mode(monkeypatch, qapp):
    """Strict testing mode should surface invalid JSON in QTextEdit widgets."""
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
    widget = QTextEdit()
    widget.setPlainText("{not-json")
    mapper = PluginConfigurationMapper(plugin_manager=MagicMock())

    with pytest.raises(
        ValueError, match="Invalid JSON in QTextEdit for field 'json_field'"
    ):
        mapper._get_qt_widget_value(widget, "json_field")


def test_get_qt_widget_value_returns_empty_string_for_unsupported_widget_when_not_strict(
    monkeypatch,
):
    """Non-strict mode should keep legacy fallback for unknown widgets."""
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
    mapper = PluginConfigurationMapper(plugin_manager=MagicMock())

    assert mapper._get_qt_widget_value(object(), "unknown_field") == ""


def test_get_qt_widget_value_raises_for_unsupported_widget_in_strict_mode(
    monkeypatch,
):
    """Strict testing mode should surface unsupported widget types."""
    monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
    mapper = PluginConfigurationMapper(plugin_manager=MagicMock())

    with pytest.raises(
        TypeError,
        match="Unsupported Qt widget type for field 'unknown_field': object",
    ):
        mapper._get_qt_widget_value(object(), "unknown_field")


if __name__ == "__main__":
    unittest.main()
