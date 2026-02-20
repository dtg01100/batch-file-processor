"""
Form Generator Unit Tests

Tests for the dynamic form generator system.
"""

import pytest

from interface.form import FormGeneratorFactory, FormGenerator
from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition, FieldType
from interface.plugins.validation_framework import Validator


class TestFormGenerator:
    """Tests for the form generator base functionality."""

    def setup_method(self):
        """Create a basic configuration schema for testing."""
        self.basic_schema = ConfigurationSchema([
            FieldDefinition('name', FieldType.STRING, label='Name', required=True),
            FieldDefinition('age', FieldType.INTEGER, label='Age', min_value=18, max_value=100),
            FieldDefinition('email', FieldType.STRING, label='Email', required=True),
        ])

    def test_factory_creation_qt(self):
        """Test creating a Qt form generator instance."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, 'qt')
        assert generator is not None
        assert isinstance(generator, FormGenerator)

    def test_factory_creation_tkinter(self):
        """Test creating a Tkinter form generator instance."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, 'tkinter')
        assert generator is not None
        assert isinstance(generator, FormGenerator)

    def test_factory_invalid_framework(self):
        """Test factory with invalid framework."""
        with pytest.raises(ValueError):
            FormGeneratorFactory.create_form_generator(self.basic_schema, 'invalid')

    def test_register_field_dependency(self):
        """Test registering field dependencies."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, 'qt')
        
        # Register a dependency
        generator.register_field_dependency(
            dependent_field='email',
            trigger_field='age',
            condition=lambda value: value > 21
        )
        
        assert 'age' in generator._field_dependencies
        assert 'email' in generator._field_dependencies['age']
        assert len(generator._visibility_callbacks['age']) == 1

    def test_get_default_values(self):
        """Test getting default values from schema."""
        schema = ConfigurationSchema([
            FieldDefinition('field1', FieldType.STRING, default='test'),
            FieldDefinition('field2', FieldType.INTEGER, default=42),
            FieldDefinition('field3', FieldType.BOOLEAN, default=True),
        ])
        
        defaults = schema.get_defaults()
        assert defaults['field1'] == 'test'
        assert defaults['field2'] == 42
        assert defaults['field3'] is True

    @pytest.mark.skip(reason="UI thread required for widget creation")
    def test_set_values(self):
        """Test setting values."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, 'qt')
        generator.build_form()
        
        test_values = {
            'name': 'Test User',
            'age': 30,
            'email': 'test@example.com'
        }
        
        generator.set_values(test_values)
        values = generator.get_values()
        
        assert values['name'] == 'Test User'
        assert values['age'] == 30
        assert values['email'] == 'test@example.com'

    @pytest.mark.skip(reason="UI thread required for widget creation")
    def test_field_visibility(self):
        """Test field visibility control."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, 'qt')
        generator.build_form()
        
        # Initially, all fields should be visible
        assert generator.widgets['name'].get_widget().isVisible()
        assert generator.widgets['age'].get_widget().isVisible()
        assert generator.widgets['email'].get_widget().isVisible()
        
        # Hide a field
        generator.set_field_visibility('age', False)
        assert not generator.widgets['age'].get_widget().isVisible()
        
        # Show it again
        generator.set_field_visibility('age', True)
        assert generator.widgets['age'].get_widget().isVisible()

    @pytest.mark.skip(reason="UI thread required for widget creation")
    def test_field_enabled(self):
        """Test field enabled/disabled state."""
        generator = FormGeneratorFactory.create_form_generator(self.basic_schema, 'qt')
        generator.build_form()
        
        # Initially, all fields should be enabled
        assert generator.widgets['name'].get_widget().isEnabled()
        assert generator.widgets['age'].get_widget().isEnabled()
        assert generator.widgets['email'].get_widget().isEnabled()
        
        # Disable a field
        generator.set_field_enabled('age', False)
        assert not generator.widgets['age'].get_widget().isEnabled()
        
        # Enable it again
        generator.set_field_enabled('age', True)
        assert generator.widgets['age'].get_widget().isEnabled()

    def test_validation_empty_form(self):
        """Test validation of an empty form using schema directly."""
        validation = self.basic_schema.validate({})
        assert not validation.success
        assert len(validation.errors) > 0

    def test_validation_valid_form(self):
        """Test validation of a valid form using schema directly."""
        validation = self.basic_schema.validate({
            'name': 'Valid User',
            'age': 30,
            'email': 'valid@example.com'
        })
        assert validation.success
        assert len(validation.errors) == 0

    def test_validation_invalid_age(self):
        """Test validation with invalid age using schema directly."""
        validation = self.basic_schema.validate({
            'name': 'Invalid User',
            'age': 17,  # Below minimum
            'email': 'invalid@example.com'
        })
        assert not validation.success
        assert any('must be at least' in error for error in validation.errors)


class TestComplexFormGenerator:
    """Tests for more complex form scenarios."""

    @pytest.mark.skip(reason="UI thread required for widget creation")
    def test_multi_select_field(self):
        """Test multi-select field functionality."""
        schema = ConfigurationSchema([
            FieldDefinition(
                'interests',
                FieldType.MULTI_SELECT,
                label='Interests',
                choices=[
                    {'label': 'Programming', 'value': 'programming'},
                    {'label': 'Reading', 'value': 'reading'},
                    {'label': 'Music', 'value': 'music'}
                ],
                default=['programming', 'reading']
            )
        ])
        
        generator = FormGeneratorFactory.create_form_generator(schema, 'qt')
        generator.build_form()
        
        values = generator.get_values()
        assert set(values['interests']) == {'programming', 'reading'}

    @pytest.mark.skip(reason="UI thread required for widget creation")
    def test_dynamic_visibility(self):
        """Test dynamic field visibility based on dependencies."""
        schema = ConfigurationSchema([
            FieldDefinition('employed', FieldType.BOOLEAN, label='Employed', default=True),
            FieldDefinition('salary', FieldType.FLOAT, label='Salary', min_value=0)
        ])
        
        generator = FormGeneratorFactory.create_form_generator(schema, 'qt')
        generator.register_field_dependency(
            'salary',
            'employed',
            lambda value: value is True
        )
        generator.build_form()
        
        # Initially, salary should be visible
        assert generator.widgets['salary'].get_widget().isVisible()
        
        # When employed is False, salary should hide
        generator.set_field_value('employed', False)
        # We need to manually trigger the update since we're setting programmatically
        generator._update_dependent_fields('employed')
        
        assert not generator.widgets['salary'].get_widget().isVisible()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
