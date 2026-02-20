#!/usr/bin/env python3
"""
Form Generator Test

Demonstrates how to use the dynamic form generator with various field types
and features.
"""

import sys

from interface.form import FormGeneratorFactory
from interface.plugins.config_schemas import (
    ConfigurationSchema,
    FieldDefinition,
    FieldType
)
from interface.plugins.validation_framework import Validator


class EmailValidator(Validator):
    """Custom validator for email fields."""

    def validate(self, value: str) -> 'ValidationResult':
        if value and '@' not in value:
            return self.error("Email must contain '@'")
        return self.success()


def create_sample_schema() -> ConfigurationSchema:
    """Create a sample configuration schema for testing."""
    return ConfigurationSchema([
        FieldDefinition(
            name='name',
            field_type=FieldType.STRING,
            label='Full Name',
            description='Your complete name',
            required=True,
            min_length=2,
            max_length=100
        ),
        FieldDefinition(
            name='age',
            field_type=FieldType.INTEGER,
            label='Age',
            description='Your age in years',
            required=True,
            min_value=18,
            max_value=100,
            default=30
        ),
        FieldDefinition(
            name='email',
            field_type=FieldType.STRING,
            label='Email',
            description='Your email address',
            required=True,
            validators=[EmailValidator()]
        ),
        FieldDefinition(
            name='phone',
            field_type=FieldType.STRING,
            label='Phone Number',
            description='Your contact phone number',
            default='(555) 123-4567'
        ),
        FieldDefinition(
            name='gender',
            field_type=FieldType.SELECT,
            label='Gender',
            description='Your gender',
            choices=[
                {'label': 'Male', 'value': 'male'},
                {'label': 'Female', 'value': 'female'},
                {'label': 'Other', 'value': 'other'}
            ],
            default='other'
        ),
        FieldDefinition(
            name='interests',
            field_type=FieldType.MULTI_SELECT,
            label='Interests',
            description='Select your interests',
            choices=[
                {'label': 'Programming', 'value': 'programming'},
                {'label': 'Reading', 'value': 'reading'},
                {'label': 'Music', 'value': 'music'},
                {'label': 'Sports', 'value': 'sports'},
                {'label': 'Art', 'value': 'art'}
            ],
            default=['programming', 'reading']
        ),
        FieldDefinition(
            name='employed',
            field_type=FieldType.BOOLEAN,
            label='Employed',
            description='Are you currently employed?',
            default=True
        ),
        FieldDefinition(
            name='salary',
            field_type=FieldType.FLOAT,
            label='Salary',
            description='Your annual salary',
            min_value=0,
            max_value=1000000,
            default=50000.00
        ),
        FieldDefinition(
            name='bio',
            field_type=FieldType.LIST,
            label='Biography',
            description='Short description about yourself',
            default=['Software developer', 'Loves coding', 'Coffee enthusiast']
        ),
        FieldDefinition(
            name='settings',
            field_type=FieldType.DICT,
            label='Settings',
            description='Additional settings',
            default={
                'notifications': True,
                'theme': 'dark',
                'language': 'en'
            }
        )
    ])


def test_form_generator(framework: str = 'qt'):
    """Test the form generator with the sample schema."""
    print(f"Testing {framework.upper()} Form Generator...")

    # Create schema
    schema = create_sample_schema()

    try:
        # Create form generator
        generator = FormGeneratorFactory.create_form_generator(schema, framework)

        # Register field dependencies (salary field only visible if employed)
        generator.register_field_dependency(
            dependent_field='salary',
            trigger_field='employed',
            condition=lambda value: value is True
        )

        # Build the form
        if framework == 'qt':
            import sys
            from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton, QMessageBox

            app = QApplication(sys.argv)
            dialog = QDialog()
            dialog.setWindowTitle('Form Generator Test')
            dialog.setGeometry(100, 100, 600, 800)

            layout = QVBoxLayout(dialog)

            # Build form
            form = generator.build_form({
                'name': 'John Doe',
                'email': 'john@example.com'
            }, dialog)
            layout.addWidget(form)

            # Add test buttons
            btn_get_values = QPushButton('Get Values')
            btn_get_values.clicked.connect(lambda: print("Values:", generator.get_values()))
            layout.addWidget(btn_get_values)

            btn_validate = QPushButton('Validate')
            btn_validate.clicked.connect(lambda: print("Validation:", generator.validate()))
            layout.addWidget(btn_validate)

            btn_errors = QPushButton('Show Errors')
            btn_errors.clicked.connect(lambda: QMessageBox.warning(dialog, "Errors", str(generator.get_validation_errors())))
            layout.addWidget(btn_errors)

            dialog.show()
            sys.exit(app.exec_())

        elif framework == 'tkinter':
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.title('Form Generator Test')
            root.geometry('600x800')

            # Build form
            form = generator.build_form({
                'name': 'John Doe',
                'email': 'john@example.com'
            }, root)
            form.pack(fill=tk.BOTH, expand=True)

            # Add test buttons
            btn_frame = tk.Frame(root)
            btn_frame.pack(fill=tk.X, padx=10, pady=5)

            btn_get_values = tk.Button(btn_frame, text='Get Values', 
                                      command=lambda: print("Values:", generator.get_values()))
            btn_get_values.pack(side=tk.LEFT, padx=5)

            btn_validate = tk.Button(btn_frame, text='Validate',
                                     command=lambda: print("Validation:", generator.validate()))
            btn_validate.pack(side=tk.LEFT, padx=5)

            btn_errors = tk.Button(btn_frame, text='Show Errors',
                                    command=lambda: messagebox.showwarning("Errors", str(generator.get_validation_errors())))
            btn_errors.pack(side=tk.LEFT, padx=5)

            root.mainloop()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    framework = 'qt'
    if len(sys.argv) > 1:
        framework = sys.argv[1].lower()
    
    if framework not in ['qt', 'tkinter']:
        print("Usage: python test_form_generator.py [qt|tkinter]")
        sys.exit(1)
    
    test_form_generator(framework)
