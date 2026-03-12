"""
Form Generator Unit Tests

Tests for the dynamic form generator system.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.gui]

from interface.form import FormGenerator, FormGeneratorFactory
from interface.plugins.config_schemas import (
    ConfigurationSchema,
    FieldDefinition,
    FieldType,
)


class TestFormGenerator:
    """Tests for the form generator base functionality."""

    def setup_method(self):
        """Create a basic configuration schema for testing."""
        self.basic_schema = ConfigurationSchema(
            [
                FieldDefinition("name", FieldType.STRING, label="Name", required=True),
                FieldDefinition(
                    "age", FieldType.INTEGER, label="Age", min_value=18, max_value=100
                ),
                FieldDefinition(
                    "email", FieldType.STRING, label="Email", required=True
                ),
            ]
        )

    def test_factory_creation_qt(self):
        """Test creating a Qt form generator instance."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, "qt")
        assert generator is not None
        assert isinstance(generator, FormGenerator)

    def test_factory_invalid_framework(self):
        """Test factory with invalid framework."""
        with pytest.raises(ValueError):
            FormGeneratorFactory.create_form_generator(self.basic_schema, "invalid")

    def test_register_field_dependency(self):
        """Test registering field dependencies."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, "qt")

        # Register a dependency
        generator.register_field_dependency(
            dependent_field="email",
            trigger_field="age",
            condition=lambda value: value > 21,
        )

        assert "age" in generator._field_dependencies
        assert "email" in generator._field_dependencies["age"]
        assert len(generator._visibility_callbacks["age"]) == 1

    def test_get_default_values(self):
        """Test getting default values from schema."""
        schema = ConfigurationSchema(
            [
                FieldDefinition("field1", FieldType.STRING, default="test"),
                FieldDefinition("field2", FieldType.INTEGER, default=42),
                FieldDefinition("field3", FieldType.BOOLEAN, default=True),
            ]
        )

        defaults = schema.get_defaults()
        assert defaults["field1"] == "test"
        assert defaults["field2"] == 42
        assert defaults["field3"] is True

    @pytest.mark.qt
    def test_set_values(self, qtbot):
        """Test setting values."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, "qt")
        form = generator.build_form()
        qtbot.addWidget(form)

        test_values = {"name": "Test User", "age": 30, "email": "test@example.com"}

        generator.set_values(test_values)
        values = generator.get_values()

        assert values["name"] == "Test User"
        assert values["age"] == 30
        assert values["email"] == "test@example.com"

    @pytest.mark.qt
    def test_field_visibility(self, qtbot):
        """Test field visibility control."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, "qt")
        form = generator.build_form()
        qtbot.addWidget(form)

        widget = generator.widgets["age"]
        mock1 = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        widget.set_visible = mock1
        generator.set_field_visibility("age", False)
        mock1.assert_called_once_with(False)

        mock2 = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        widget.set_visible = mock2
        generator.set_field_visibility("age", True)
        mock2.assert_called_once_with(True)

    @pytest.mark.qt
    def test_field_enabled(self, qtbot):
        """Test field enabled/disabled state."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, "qt")
        form = generator.build_form()
        qtbot.addWidget(form)

        # Initially, all fields should be enabled
        assert generator.widgets["name"].get_widget().isEnabled()
        assert generator.widgets["age"].get_widget().isEnabled()
        assert generator.widgets["email"].get_widget().isEnabled()

        # Disable a field
        generator.set_field_enabled("age", False)
        assert not generator.widgets["age"].get_widget().isEnabled()

        # Enable it again
        generator.set_field_enabled("age", True)
        assert generator.widgets["age"].get_widget().isEnabled()

    def test_validation_empty_form(self):
        """Test validation of an empty form using schema directly."""
        validation = self.basic_schema.validate({})
        assert not validation.success
        assert len(validation.errors) > 0

    def test_validation_valid_form(self):
        """Test validation of a valid form using schema directly."""
        validation = self.basic_schema.validate(
            {"name": "Valid User", "age": 30, "email": "valid@example.com"}
        )
        assert validation.success
        assert len(validation.errors) == 0

    def test_validation_invalid_age(self):
        """Test validation with invalid age using schema directly."""
        validation = self.basic_schema.validate(
            {
                "name": "Invalid User",
                "age": 17,  # Below minimum
                "email": "invalid@example.com",
            }
        )
        assert not validation.success
        assert any("must be at least" in error for error in validation.errors)


class TestComplexFormGenerator:
    """Tests for more complex form scenarios."""

    @pytest.mark.qt
    def test_multi_select_field(self, qtbot):
        """Test multi-select field functionality."""
        schema = ConfigurationSchema(
            [
                FieldDefinition(
                    "interests",
                    FieldType.MULTI_SELECT,
                    label="Interests",
                    choices=[
                        {"label": "Programming", "value": "programming"},
                        {"label": "Reading", "value": "reading"},
                        {"label": "Music", "value": "music"},
                    ],
                    default=["programming", "reading"],
                )
            ]
        )

        generator = FormGeneratorFactory.create_form_generator(schema, "qt")
        form = generator.build_form()
        qtbot.addWidget(form)

        values = generator.get_values()
        assert set(values["interests"]) == {"programming", "reading"}

    @pytest.mark.qt
    def test_dynamic_visibility(self, qtbot):
        """Test dynamic field visibility based on dependencies."""
        schema = ConfigurationSchema(
            [
                FieldDefinition(
                    "employed", FieldType.BOOLEAN, label="Employed", default=True
                ),
                FieldDefinition("salary", FieldType.FLOAT, label="Salary", min_value=0),
            ]
        )

        generator = FormGeneratorFactory.create_form_generator(schema, "qt")
        generator.register_field_dependency(
            "salary", "employed", lambda value: value is True
        )
        form = generator.build_form()
        qtbot.addWidget(form)

        salary_widget = generator.widgets["salary"]
        mock_set_visible = __import__(
            "unittest.mock", fromlist=["MagicMock"]
        ).MagicMock()
        salary_widget.set_visible = mock_set_visible

        generator.set_field_value("employed", False)
        generator._update_dependent_fields("employed")
        assert mock_set_visible.call_args_list[-1] == __import__(
            "unittest.mock", fromlist=["call"]
        ).call(False)


class TestPluginSectionCommunication:
    """Communication tests for FormGenerator <-> plugin section factory/widgets."""

    @pytest.mark.qt
    def test_render_plugin_sections_passes_schema_and_config_to_factory(
        self, qtbot, monkeypatch
    ):
        base_schema = ConfigurationSchema(
            [
                FieldDefinition("name", FieldType.STRING, label="Name"),
            ]
        )
        plugin_schema = ConfigurationSchema(
            [
                FieldDefinition(
                    "include_headers", FieldType.BOOLEAN, label="Include Headers"
                ),
            ]
        )

        generator = FormGeneratorFactory.create_form_generator(base_schema, "qt")
        generator.add_plugin_section(
            section_id="csv_section",
            schema=plugin_schema,
            config={"include_headers": True},
        )

        captured = {}

        class FakeSection:
            def render(self, config):
                from PyQt6.QtWidgets import QWidget

                captured["render_config"] = config
                return QWidget()

            def get_values(self):
                return {"include_headers": True}

        def fake_create_section(section_type, schema, framework, config, parent):
            captured["section_type"] = section_type
            captured["schema"] = schema
            captured["framework"] = framework
            captured["config"] = config
            captured["parent"] = parent
            return FakeSection()

        monkeypatch.setattr(
            "interface.form.section_factory.SectionFactoryRegistry.create_section",
            fake_create_section,
        )

        form = generator.build_form(parent=None)
        qtbot.addWidget(form)

        assert captured["section_type"] == "default"
        assert captured["schema"] is plugin_schema
        assert captured["framework"] == "qt"
        assert captured["config"] == {"include_headers": True}
        assert captured["render_config"] == {"include_headers": True}

    def test_plugin_section_values_roundtrip_and_validation_aggregation(self):
        schema = ConfigurationSchema(
            [
                FieldDefinition("name", FieldType.STRING, label="Name"),
            ]
        )
        generator = FormGeneratorFactory.create_form_generator(schema, "qt")

        section_ok = MagicMock()
        section_ok.section_id = "ok_section"
        section_ok.get_values.return_value = {"enabled": True}
        section_ok.validate.return_value = __import__(
            "interface.plugins.validation_framework", fromlist=["ValidationResult"]
        ).ValidationResult(success=True, errors=[])

        section_bad = MagicMock()
        section_bad.section_id = "bad_section"
        section_bad.get_values.return_value = {"enabled": False}
        section_bad.validate.return_value = __import__(
            "interface.plugins.validation_framework", fromlist=["ValidationResult"]
        ).ValidationResult(success=False, errors=["bad field"])

        section_fallback = MagicMock()
        section_fallback.section_id = "fallback_section"
        # No validate() method branch: use get_validation_errors fallback
        del section_fallback.validate
        section_fallback.get_values.return_value = {"x": 1}
        section_fallback.get_validation_errors.return_value = ["fallback error"]

        generator._plugin_sections = [section_ok, section_bad, section_fallback]

        values = generator.get_plugin_section_values()
        assert values["ok_section"] == {"enabled": True}
        assert values["bad_section"] == {"enabled": False}
        assert values["fallback_section"] == {"x": 1}

        generator.set_plugin_section_values(
            {
                "ok_section": {"enabled": False},
                "bad_section": {"enabled": True},
            }
        )
        section_ok.set_values.assert_called_once_with({"enabled": False})
        section_bad.set_values.assert_called_once_with({"enabled": True})

        result = generator.validate_plugin_sections()
        assert result.success is False
        assert "bad field" in result.errors
        assert "fallback error" in result.errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
