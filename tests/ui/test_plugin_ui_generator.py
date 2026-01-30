"""
Unit tests for interface.ui.plugin_ui_generator module.

Tests dynamic UI generation from ConfigField descriptors.
Note: Requires PyQt6 to be installed.
"""

import pytest

# Try to import PyQt6, skip tests if not available
try:
    from PyQt6.QtWidgets import (
        QApplication,
        QWidget,
        QLineEdit,
        QCheckBox,
        QSpinBox,
        QDoubleSpinBox,
        QComboBox,
        QTextEdit,
    )
    from plugin_config import ConfigField
    from interface.ui.plugin_ui_generator import PluginUIGenerator

    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


pytestmark = pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    import sys

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestCreateWidgetForField:
    """Tests for PluginUIGenerator.create_widget_for_field method."""

    def test_boolean_field_creates_checkbox(self, qapp):
        """Boolean field should create QCheckBox."""
        field = ConfigField(
            key="enabled", label="Enabled", type="boolean", default=True
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QCheckBox)
        assert widget.isChecked() is True
        assert getter() is True

    def test_boolean_field_default_false(self, qapp):
        """Boolean field with default False should be unchecked."""
        field = ConfigField(
            key="disabled", label="Disabled", type="boolean", default=False
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert widget.isChecked() is False
        assert getter() is False

    def test_string_field_creates_lineedit(self, qapp):
        """String field should create QLineEdit."""
        field = ConfigField(
            key="name", label="Name", type="string", default="default_value"
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QLineEdit)
        assert widget.text() == "default_value"
        assert getter() == "default_value"

    def test_string_field_with_placeholder(self, qapp):
        """String field with placeholder should set placeholder text."""
        field = ConfigField(
            key="username",
            label="Username",
            type="string",
            default="",
            placeholder="Enter username",
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert widget.placeholderText() == "Enter username"

    def test_string_field_with_help(self, qapp):
        """String field with help should set tooltip."""
        field = ConfigField(
            key="api_key",
            label="API Key",
            type="string",
            default="",
            help="Your API key from the dashboard",
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert widget.toolTip() == "Your API key from the dashboard"

    def test_integer_field_creates_spinbox(self, qapp):
        """Integer field should create QSpinBox."""
        field = ConfigField(key="count", label="Count", type="integer", default=10)
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QSpinBox)
        assert widget.value() == 10
        assert getter() == 10

    def test_integer_field_with_range(self, qapp):
        """Integer field with min/max should set spinbox range."""
        field = ConfigField(
            key="port",
            label="Port",
            type="integer",
            default=8080,
            min_value=1,
            max_value=65535,
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert widget.minimum() == 1
        assert widget.maximum() == 65535

    def test_float_field_creates_doublespinbox(self, qapp):
        """Float field should create QDoubleSpinBox."""
        field = ConfigField(key="rate", label="Rate", type="float", default=1.5)
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QDoubleSpinBox)
        assert widget.value() == 1.5
        assert getter() == 1.5

    def test_float_field_with_range(self, qapp):
        """Float field with min/max should set spinbox range."""
        field = ConfigField(
            key="percentage",
            label="Percentage",
            type="float",
            default=50.0,
            min_value=0.0,
            max_value=100.0,
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert widget.minimum() == 0.0
        assert widget.maximum() == 100.0

    def test_select_field_creates_combobox(self, qapp):
        """Select field should create QComboBox."""
        field = ConfigField(
            key="format",
            label="Format",
            type="select",
            options=["csv", "json", "xml"],
            default="csv",
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QComboBox)
        assert widget.count() == 3
        assert widget.currentText() == "csv"
        assert getter() == "csv"

    def test_select_field_with_tuple_options(self, qapp):
        """Select field with tuple options should use value/label pairs."""
        field = ConfigField(
            key="level",
            label="Level",
            type="select",
            options=[("debug", "Debug"), ("info", "Info"), ("error", "Error")],
            default="info",
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert widget.count() == 3
        # Should display "Info" but return "info"
        assert widget.currentText() == "Info"
        assert getter() == "info"

    def test_text_field_creates_textedit(self, qapp):
        """Text field should create QTextEdit."""
        field = ConfigField(
            key="description", label="Description", type="text", default="Default text"
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QTextEdit)
        assert widget.toPlainText() == "Default text"
        assert getter() == "Default text"

    def test_unknown_type_creates_lineedit(self, qapp):
        """Unknown field type should create QLineEdit as fallback."""
        field = ConfigField(
            key="unknown", label="Unknown", type="unknown_type", default="fallback"
        )
        widget, getter = PluginUIGenerator.create_widget_for_field(field)

        assert isinstance(widget, QLineEdit)
        assert widget.text() == "fallback"


class TestCreatePluginConfigWidget:
    """Tests for PluginUIGenerator.create_plugin_config_widget method."""

    def test_creates_widget_with_all_fields(self, qapp):
        """Should create widget containing all fields."""
        fields = [
            ConfigField(key="name", label="Name", type="string", default="test"),
            ConfigField(key="count", label="Count", type="integer", default=5),
            ConfigField(key="enabled", label="Enabled", type="boolean", default=True),
        ]

        widget, value_getters = PluginUIGenerator.create_plugin_config_widget(fields)

        assert isinstance(widget, QWidget)
        assert "name" in value_getters
        assert "count" in value_getters
        assert "enabled" in value_getters

    def test_skips_conditional_fields(self, qapp):
        """Should skip fields with visible_if condition."""
        fields = [
            ConfigField(key="name", label="Name", type="string", default=""),
            ConfigField(
                key="advanced",
                label="Advanced",
                type="string",
                default="",
                visible_if={"enabled": True},
            ),
        ]

        widget, value_getters = PluginUIGenerator.create_plugin_config_widget(fields)

        assert "name" in value_getters
        assert "advanced" not in value_getters

    def test_applies_current_values(self, qapp):
        """Should apply current_values when provided."""
        fields = [
            ConfigField(key="name", label="Name", type="string", default="default"),
            ConfigField(key="count", label="Count", type="integer", default=0),
        ]
        current_values = {"name": "custom_name", "count": 42}

        widget, value_getters = PluginUIGenerator.create_plugin_config_widget(
            fields, current_values=current_values
        )

        assert value_getters["name"]() == "custom_name"
        assert value_getters["count"]() == 42


class TestSetWidgetValue:
    """Tests for PluginUIGenerator._set_widget_value method."""

    def test_sets_checkbox_value(self, qapp):
        """Should set checkbox value correctly."""
        widget = QCheckBox()
        PluginUIGenerator._set_widget_value(widget, True)
        assert widget.isChecked() is True

        PluginUIGenerator._set_widget_value(widget, False)
        assert widget.isChecked() is False

    def test_sets_lineedit_value(self, qapp):
        """Should set line edit value correctly."""
        widget = QLineEdit()
        PluginUIGenerator._set_widget_value(widget, "test value")
        assert widget.text() == "test value"

    def test_sets_lineedit_none_to_empty(self, qapp):
        """Should convert None to empty string for line edit."""
        widget = QLineEdit()
        PluginUIGenerator._set_widget_value(widget, None)
        assert widget.text() == ""

    def test_sets_spinbox_value(self, qapp):
        """Should set spinbox value correctly."""
        widget = QSpinBox()
        widget.setRange(0, 1000)
        PluginUIGenerator._set_widget_value(widget, 42)
        assert widget.value() == 42

    def test_sets_doublespinbox_value(self, qapp):
        """Should set double spinbox value correctly."""
        widget = QDoubleSpinBox()
        widget.setRange(0, 1000)
        PluginUIGenerator._set_widget_value(widget, 3.14)
        assert abs(widget.value() - 3.14) < 0.001

    def test_sets_combobox_by_data(self, qapp):
        """Should set combobox by data value."""
        widget = QComboBox()
        widget.addItem("Option 1", "opt1")
        widget.addItem("Option 2", "opt2")

        PluginUIGenerator._set_widget_value(widget, "opt2")
        assert widget.currentData() == "opt2"

    def test_sets_combobox_by_text(self, qapp):
        """Should set combobox by text if data not found."""
        widget = QComboBox()
        widget.addItem("Option 1")
        widget.addItem("Option 2")

        PluginUIGenerator._set_widget_value(widget, "Option 2")
        assert widget.currentText() == "Option 2"

    def test_sets_textedit_value(self, qapp):
        """Should set text edit value correctly."""
        widget = QTextEdit()
        PluginUIGenerator._set_widget_value(widget, "multi\nline\ntext")
        assert widget.toPlainText() == "multi\nline\ntext"


class TestGetConfigValues:
    """Tests for PluginUIGenerator.get_config_values method."""

    def test_extracts_all_values(self, qapp):
        """Should extract values from all getters."""
        value_getters = {
            "name": lambda: "test_name",
            "count": lambda: 42,
            "enabled": lambda: True,
        }

        values = PluginUIGenerator.get_config_values(value_getters)

        assert values == {"name": "test_name", "count": 42, "enabled": True}

    def test_handles_empty_getters(self, qapp):
        """Should handle empty getters dict."""
        values = PluginUIGenerator.get_config_values({})
        assert values == {}


class TestPluginUIGeneratorIntegration:
    """Integration tests for PluginUIGenerator."""

    def test_full_workflow(self, qapp):
        """Test complete workflow: create, modify, extract."""
        fields = [
            ConfigField(key="host", label="Host", type="string", default="localhost"),
            ConfigField(key="port", label="Port", type="integer", default=8080),
            ConfigField(key="secure", label="Secure", type="boolean", default=False),
            ConfigField(
                key="protocol",
                label="Protocol",
                type="select",
                options=["http", "https"],
                default="http",
            ),
        ]

        # Create widget
        widget, value_getters = PluginUIGenerator.create_plugin_config_widget(fields)

        # Extract initial values
        initial = PluginUIGenerator.get_config_values(value_getters)
        assert initial["host"] == "localhost"
        assert initial["port"] == 8080
        assert initial["secure"] is False
        assert initial["protocol"] == "http"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
