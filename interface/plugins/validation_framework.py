"""
Validation Framework

Provides a strategy pattern for validation, allowing plugins to define
custom validation logic for their configuration fields.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Callable, Union

from dataclasses import dataclass


@dataclass
class ValidationResult:
    """
    Result of a validation operation.
    """
    success: bool
    errors: List[str]

    def __init__(self, success: bool = True, errors: List[str] = None):
        """
        Initialize a validation result.

        Args:
            success: Whether the validation succeeded
            errors: List of error messages if validation failed
        """
        self.success = success
        self.errors = errors or []

    def add_error(self, error: str) -> None:
        """
        Add an error message to the validation result.

        Args:
            error: Error message to add
        """
        self.success = False
        self.errors.append(error)

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """
        Merge this validation result with another one.

        Args:
            other: Validation result to merge

        Returns:
            ValidationResult: Merged validation result
        """
        return ValidationResult(
            success=self.success and other.success,
            errors=self.errors + other.errors
        )


class Validator(ABC):
    """
    Base class for all validators.

    Validators implement the strategy pattern, providing custom validation
    logic for configuration fields.
    """

    @abstractmethod
    def validate(self, value: Any) -> ValidationResult:
        """
        Validate a value.

        Args:
            value: Value to validate

        Returns:
            ValidationResult: Validation result
        """
        pass


class RegexValidator(Validator):
    """
    Validator that checks if a string matches a regular expression.
    """

    def __init__(self, regex: str, message: str = "Value does not match expected format"):
        """
        Initialize a regex validator.

        Args:
            regex: Regular expression to match
            message: Error message if validation fails
        """
        self.regex = regex
        self.message = message

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(success=False, errors=[self.message])

        import re
        if not re.match(self.regex, value):
            return ValidationResult(success=False, errors=[self.message])

        return ValidationResult(success=True)


class EmailValidator(Validator):
    """
    Validator that checks if a string is a valid email address.
    """

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(success=False, errors=["Email must be a string"])

        import re
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, value):
            return ValidationResult(success=False, errors=["Invalid email address format"])

        return ValidationResult(success=True)


class URLValidator(Validator):
    """
    Validator that checks if a string is a valid URL.
    """

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(success=False, errors=["URL must be a string"])

        import re
        url_pattern = r'^(https?|ftp)://[^\s]+$'
        if not re.match(url_pattern, value):
            return ValidationResult(success=False, errors=["Invalid URL format"])

        return ValidationResult(success=True)


class FilePathValidator(Validator):
    """
    Validator that checks if a string is a valid file path.
    """

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(success=False, errors=["File path must be a string"])

        import os
        if not os.path.exists(value):
            return ValidationResult(success=False, errors=["File or directory does not exist"])

        return ValidationResult(success=True)


class RangeValidator(Validator):
    """
    Validator that checks if a numeric value falls within a specific range.
    """

    def __init__(self, min_value: Union[int, float], max_value: Union[int, float],
                 message: str = "Value must be between {min} and {max}"):
        """
        Initialize a range validator.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            message: Error message if validation fails
        """
        self.min_value = min_value
        self.max_value = max_value
        self.message = message

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float)):
            return ValidationResult(success=False, errors=["Value must be a number"])

        if value < self.min_value or value > self.max_value:
            return ValidationResult(success=False, errors=[
                self.message.format(min=self.min_value, max=self.max_value)
            ])

        return ValidationResult(success=True)


class LengthValidator(Validator):
    """
    Validator that checks if a string or list has a specific length.
    """

    def __init__(self, min_length: int = 0, max_length: int = None,
                 message: str = "Value must be between {min} and {max} characters long"):
        """
        Initialize a length validator.

        Args:
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            message: Error message if validation fails
        """
        self.min_length = min_length
        self.max_length = max_length
        self.message = message

    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (str, list)):
            return ValidationResult(success=False, errors=["Value must be a string or list"])

        length = len(value)

        if self.max_length is None:
            if length < self.min_length:
                return ValidationResult(success=False, errors=[
                    self.message.format(min=self.min_length, max="infinite")
                ])
        else:
            if length < self.min_length or length > self.max_length:
                return ValidationResult(success=False, errors=[
                    self.message.format(min=self.min_length, max=self.max_length)
                ])

        return ValidationResult(success=True)


class CustomValidator(Validator):
    """
    Validator that uses a custom validation function.
    """

    def __init__(self, validation_func: Callable[[Any], ValidationResult],
                 message: str = "Validation failed"):
        """
        Initialize a custom validator.

        Args:
            validation_func: Custom validation function that returns a ValidationResult
            message: Default error message if validation fails
        """
        self.validation_func = validation_func
        self.message = message

    def validate(self, value: Any) -> ValidationResult:
        return self.validation_func(value)
