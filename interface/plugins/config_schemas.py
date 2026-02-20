"""
Configuration Schema Framework

Defines the base classes for configuration schemas and validation.
Provides a declarative way to define plugin configuration fields
with built-in validation support.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable

from .validation_framework import ValidationResult, Validator


class FieldType(Enum):
    """
    Configuration field types supported by the system.
    """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    SELECT = "select"
    MULTI_SELECT = "multi_select"


class FieldDefinition:
    """
    Definition of a single configuration field.

    Contains metadata about the field, including type, validation rules,
    and default values.
    """

    def __init__(
        self,
        name: str,
        field_type: FieldType,
        label: str = "",
        description: str = "",
        default: Any = None,
        required: bool = False,
        validators: Optional[List[Validator]] = None,
        choices: Optional[List[Dict[str, Any]]] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
    ):
        """
        Initialize a field definition.

        Args:
            name: Field name (key in config dictionary)
            field_type: Type of the field
            label: Human-readable label for the field
            description: Detailed description of the field
            default: Default value
            required: Whether the field is required
            validators: Custom validators for the field
            choices: Available choices (for SELECT and MULTI_SELECT)
            min_value: Minimum value (for numeric fields)
            max_value: Maximum value (for numeric fields)
            min_length: Minimum length (for string fields)
            max_length: Maximum length (for string fields)
        """
        self.name = name
        self.field_type = field_type
        self.label = label or name
        self.description = description
        self.default = default
        self.required = required
        self.validators = validators or []
        self.choices = choices or []
        self.min_value = min_value
        self.max_value = max_value
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any) -> ValidationResult:
        """
        Validate a value against this field definition.

        Args:
            value: Value to validate

        Returns:
            ValidationResult: Validation result
        """
        # Check required field
        if self.required and value is None:
            return ValidationResult(
                success=False,
                errors=[f"Field '{self.name}' is required"]
            )

        if value is None:
            return ValidationResult(success=True, errors=[])

        # Type validation
        errors = []

        if self.field_type == FieldType.STRING:
            if not isinstance(value, str):
                errors.append(f"Field '{self.name}' must be a string")
            elif self.min_length is not None and len(value) < self.min_length:
                errors.append(
                    f"Field '{self.name}' must be at least {self.min_length} characters long"
                )
            elif self.max_length is not None and len(value) > self.max_length:
                errors.append(
                    f"Field '{self.name}' must be at most {self.max_length} characters long"
                )

        elif self.field_type == FieldType.INTEGER:
            if not isinstance(value, int):
                errors.append(f"Field '{self.name}' must be an integer")
            elif self.min_value is not None and value < self.min_value:
                errors.append(
                    f"Field '{self.name}' must be at least {self.min_value}"
                )
            elif self.max_value is not None and value > self.max_value:
                errors.append(
                    f"Field '{self.name}' must be at most {self.max_value}"
                )

        elif self.field_type == FieldType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"Field '{self.name}' must be a number")
            elif self.min_value is not None and value < self.min_value:
                errors.append(
                    f"Field '{self.name}' must be at least {self.min_value}"
                )
            elif self.max_value is not None and value > self.max_value:
                errors.append(
                    f"Field '{self.name}' must be at most {self.max_value}"
                )

        elif self.field_type == FieldType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"Field '{self.name}' must be a boolean")

        elif self.field_type == FieldType.LIST:
            if not isinstance(value, list):
                errors.append(f"Field '{self.name}' must be a list")

        elif self.field_type == FieldType.DICT:
            if not isinstance(value, dict):
                errors.append(f"Field '{self.name}' must be a dictionary")

        elif self.field_type == FieldType.SELECT:
            if not isinstance(value, str):
                errors.append(f"Field '{self.name}' must be a string")
            elif self.choices and value not in [c["value"] for c in self.choices]:
                valid_choices = ", ".join([c["value"] for c in self.choices])
                errors.append(
                    f"Field '{self.name}' must be one of: {valid_choices}"
                )

        elif self.field_type == FieldType.MULTI_SELECT:
            if not isinstance(value, list):
                errors.append(f"Field '{self.name}' must be a list")
            elif self.choices:
                valid_values = [c["value"] for c in self.choices]
                invalid_values = [v for v in value if v not in valid_values]
                if invalid_values:
                    valid_choices = ", ".join(valid_values)
                    errors.append(
                        f"Field '{self.name}' contains invalid values: {', '.join(invalid_values)}. "
                        f"Valid choices are: {valid_choices}"
                    )

        # Custom validators
        for validator in self.validators:
            validation = validator.validate(value)
            if not validation.success:
                errors.extend(validation.errors)

        return ValidationResult(success=len(errors) == 0, errors=errors)


class ConfigurationSchema:
    """
    Represents a complete configuration schema for a plugin.

    Contains all field definitions and provides validation methods.
    """

    def __init__(self, fields: List[FieldDefinition]):
        """
        Initialize a configuration schema.

        Args:
            fields: List of field definitions
        """
        self.fields = fields
        self._field_map = {field.name: field for field in fields}

    def get_field(self, name: str) -> Optional[FieldDefinition]:
        """
        Get a field definition by name.

        Args:
            name: Field name

        Returns:
            Optional[FieldDefinition]: Field definition or None if not found
        """
        return self._field_map.get(name)

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate a configuration dictionary against this schema.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult: Validation result
        """
        all_errors = []

        for field in self.fields:
            value = config.get(field.name)
            validation = field.validate(value)
            all_errors.extend(validation.errors)

        return ValidationResult(success=len(all_errors) == 0, errors=all_errors)

    def get_defaults(self) -> Dict[str, Any]:
        """
        Get the default configuration values.

        Returns:
            Dict[str, Any]: Dictionary of field names to default values
        """
        return {
            field.name: field.default
            for field in self.fields
            if field.default is not None
        }

    def get_required_fields(self) -> List[str]:
        """
        Get the list of required field names.

        Returns:
            List[str]: List of required field names
        """
        return [
            field.name
            for field in self.fields
            if field.required
        ]

    def get_field_types(self) -> Dict[str, FieldType]:
        """
        Get a dictionary mapping field names to their types.

        Returns:
            Dict[str, FieldType]: Field name to type mapping
        """
        return {
            field.name: field.field_type
            for field in self.fields
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the schema to a dictionary representation.

        Returns:
            Dict[str, Any]: Schema as a dictionary
        """
        return {
            "fields": [
                {
                    "name": field.name,
                    "type": field.field_type.value,
                    "label": field.label,
                    "description": field.description,
                    "default": field.default,
                    "required": field.required,
                    "choices": field.choices,
                    "min_value": field.min_value,
                    "max_value": field.max_value,
                    "min_length": field.min_length,
                    "max_length": field.max_length
                }
                for field in self.fields
            ]
        }
