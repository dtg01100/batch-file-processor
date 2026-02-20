"""
Dynamic Form Generator Package

Provides a framework-agnostic form generator system that can dynamically render
UI from ConfigurationSchema definitions. Supports both Qt and Tkinter frameworks
through the existing UI abstraction layer.

Key Components:
- FormGenerator: Base interface for all form generators
- QtFormGenerator: Qt framework implementation
- TkinterFormGenerator: Tkinter framework implementation
- FormGeneratorFactory: Factory for creating form generator instances

Usage Example:
    from interface.form import FormGeneratorFactory
    from interface.plugins.config_schemas import ConfigurationSchema, FieldDefinition, FieldType

    # Create schema
    schema = ConfigurationSchema([
        FieldDefinition('name', FieldType.STRING, label='Name', required=True),
        FieldDefinition('age', FieldType.INTEGER, label='Age', min_value=18, max_value=100),
        FieldDefinition('email', FieldType.STRING, label='Email', required=True),
    ])

    # Create form generator (Qt or Tkinter)
    generator = FormGeneratorFactory.create_form_generator(schema, 'qt')

    # Build form
    form = generator.build_form()

    # Get values
    values = generator.get_values()

    # Validate
    result = generator.validate()
    if result.success:
        print("Form is valid")
    else:
        print(f"Errors: {result.errors}")
"""

from .form_generator import (
    FormGenerator,
    QtFormGenerator,
    TkinterFormGenerator,
    FormGeneratorFactory
)

__all__ = [
    'FormGenerator',
    'QtFormGenerator',
    'TkinterFormGenerator',
    'FormGeneratorFactory'
]
