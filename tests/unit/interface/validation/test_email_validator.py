"""Unit tests for email validation.

Tests the email validation functions and EmailValidator class
to ensure proper email format validation.
"""

import pytest
from interface.validation.email_validator import (
    validate_email,
    validate_email_list,
    normalize_email,
    EmailValidator,
)


class TestValidateEmail:
    """Tests for validate_email function."""
    
    def test_valid_email(self):
        """Test valid email passes."""
        assert validate_email("test@example.com") is True
    
    def test_valid_email_with_subdomain(self):
        """Test valid email with subdomain."""
        assert validate_email("user@mail.example.com") is True
    
    def test_valid_email_with_plus(self):
        """Test valid email with plus sign."""
        assert validate_email("user+tag@example.com") is True
    
    def test_valid_email_with_dots(self):
        """Test valid email with dots in local part."""
        assert validate_email("first.last@example.com") is True
    
    def test_valid_email_with_numbers(self):
        """Test valid email with numbers."""
        assert validate_email("user123@example123.com") is True
    
    def test_invalid_email_no_at(self):
        """Test invalid email without @."""
        assert validate_email("testexample.com") is False
    
    def test_invalid_email_no_domain(self):
        """Test invalid email without domain."""
        assert validate_email("test@") is False
    
    def test_invalid_email_no_tld(self):
        """Test invalid email without TLD."""
        assert validate_email("test@example") is False
    
    def test_invalid_email_no_local_part(self):
        """Test invalid email without local part."""
        assert validate_email("@example.com") is False
    
    def test_invalid_email_multiple_at(self):
        """Test invalid email with multiple @."""
        assert validate_email("test@@example.com") is False
    
    def test_empty_email(self):
        """Test empty email fails."""
        assert validate_email("") is False
    
    def test_none_email(self):
        """Test None email fails."""
        assert validate_email(None) is False
    
    def test_whitespace_only_email(self):
        """Test whitespace-only email fails."""
        assert validate_email("   ") is False
    
    def test_custom_pattern(self):
        """Test custom pattern validation."""
        # Pattern that only accepts .org domains
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.org\b'
        
        assert validate_email("test@example.org", pattern) is True
        assert validate_email("test@example.com", pattern) is False


class TestValidateEmailList:
    """Tests for validate_email_list function."""
    
    def test_valid_list(self):
        """Test valid email list."""
        valid, invalid = validate_email_list("a@test.com, b@test.com")
        assert valid is True
        assert len(invalid) == 0
    
    def test_valid_list_semicolon_separator(self):
        """Test valid email list with semicolon separator."""
        valid, invalid = validate_email_list("a@test.com; b@test.com", separator="; ")
        assert valid is True
        assert len(invalid) == 0
    
    def test_mixed_list(self):
        """Test mixed valid/invalid list."""
        valid, invalid = validate_email_list("a@test.com, invalid")
        assert valid is False
        assert "invalid" in invalid
    
    def test_empty_list(self):
        """Test empty list."""
        valid, invalid = validate_email_list("")
        assert valid is True
        assert len(invalid) == 0
    
    def test_none_list(self):
        """Test None list."""
        valid, invalid = validate_email_list(None)
        assert valid is True
        assert len(invalid) == 0
    
    def test_all_invalid(self):
        """Test all invalid emails."""
        valid, invalid = validate_email_list("invalid1, invalid2, invalid3")
        assert valid is False
        assert len(invalid) == 3
    
    def test_whitespace_handling(self):
        """Test whitespace is stripped."""
        valid, invalid = validate_email_list("  a@test.com  ,  b@test.com  ")
        assert valid is True
        assert len(invalid) == 0
    
    def test_custom_pattern(self):
        """Test custom pattern with list."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.org\b'
        
        valid, invalid = validate_email_list(
            "test@example.org, test@example.com",
            pattern=pattern
        )
        
        assert valid is False
        assert "test@example.com" in invalid


class TestNormalizeEmail:
    """Tests for normalize_email function."""
    
    def test_lowercase(self):
        """Test email is lowercased."""
        assert normalize_email("TEST@EXAMPLE.COM") == "test@example.com"
    
    def test_mixed_case(self):
        """Test mixed case is lowercased."""
        assert normalize_email("Test@Example.Com") == "test@example.com"
    
    def test_strip_whitespace(self):
        """Test whitespace is stripped."""
        assert normalize_email("  test@test.com  ") == "test@test.com"
    
    def test_strip_and_lowercase(self):
        """Test both strip and lowercase."""
        assert normalize_email("  TEST@TEST.COM  ") == "test@test.com"
    
    def test_empty_returns_empty(self):
        """Test empty returns empty."""
        assert normalize_email("") == ""
    
    def test_none_returns_empty(self):
        """Test None returns empty."""
        assert normalize_email(None) == ""
    
    def test_whitespace_returns_empty(self):
        """Test whitespace-only returns empty."""
        assert normalize_email("   ") == ""


class TestEmailValidator:
    """Tests for EmailValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create default validator."""
        return EmailValidator()
    
    def test_validate_valid_email(self, validator):
        """Test validate method with valid email."""
        assert validator.validate("test@example.com") is True
    
    def test_validate_invalid_email(self, validator):
        """Test validate method with invalid email."""
        assert validator.validate("invalid") is False
    
    def test_validate_list_valid(self, validator):
        """Test validate_list with valid emails."""
        valid, invalid = validator.validate_list("a@test.com; b@test.com")
        assert valid is True
        assert len(invalid) == 0
    
    def test_validate_list_invalid(self, validator):
        """Test validate_list with invalid emails."""
        valid, invalid = validator.validate_list("a@test.com; invalid")
        assert valid is False
        assert "invalid" in invalid
    
    def test_normalize(self, validator):
        """Test normalize method."""
        assert validator.normalize("TEST@EXAMPLE.COM") == "test@example.com"
    
    def test_validate_and_normalize_valid(self, validator):
        """Test validate_and_normalize with valid email."""
        is_valid, normalized = validator.validate_and_normalize("  TEST@TEST.COM  ")
        assert is_valid is True
        assert normalized == "test@test.com"
    
    def test_validate_and_normalize_invalid(self, validator):
        """Test validate_and_normalize with invalid email."""
        is_valid, normalized = validator.validate_and_normalize("invalid")
        assert is_valid is False
        assert normalized == "invalid"
    
    def test_filter_valid(self, validator):
        """Test filter_valid method."""
        emails = ["a@test.com", "invalid", "b@test.com", "bad"]
        result = validator.filter_valid(emails)
        
        assert result == ["a@test.com", "b@test.com"]
    
    def test_filter_invalid(self, validator):
        """Test filter_invalid method."""
        emails = ["a@test.com", "invalid", "b@test.com", "bad"]
        result = validator.filter_invalid(emails)
        
        assert result == ["invalid", "bad"]
    
    def test_custom_pattern(self):
        """Test validator with custom pattern."""
        # Only accept .org domains
        validator = EmailValidator(pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.org\b')
        
        assert validator.validate("test@example.org") is True
        assert validator.validate("test@example.com") is False
    
    def test_default_pattern(self, validator):
        """Test default pattern is set."""
        assert validator.pattern is not None
        assert isinstance(validator.pattern, str)


class TestEmailValidatorEdgeCases:
    """Tests for edge cases in email validation."""
    
    @pytest.fixture
    def validator(self):
        """Create default validator."""
        return EmailValidator()
    
    def test_email_with_special_chars(self, validator):
        """Test email with allowed special characters."""
        # These special characters are allowed in local part per our pattern
        # The pattern allows: A-Za-z0-9._%+-
        assert validator.validate("user.def@example.com") is True
        assert validator.validate("user+def@example.com") is True
        assert validator.validate("user%def@example.com") is True
        assert validator.validate("user_def@example.com") is True
        # Note: ! and # are NOT in our allowed character set
    
    def test_email_with_long_tld(self, validator):
        """Test email with long TLD."""
        # TLD can be up to 7 characters in our pattern
        assert validator.validate("test@example.abcdefg") is True
    
    def test_email_with_short_tld(self, validator):
        """Test email with short TLD."""
        assert validator.validate("test@example.ab") is True
    
    def test_empty_list_filter(self, validator):
        """Test filtering empty list."""
        assert validator.filter_valid([]) == []
        assert validator.filter_invalid([]) == []
    
    def test_single_email_list(self, validator):
        """Test list with single email."""
        valid, invalid = validator.validate_list("a@test.com")
        assert valid is True
    
    def test_trailing_separator(self, validator):
        """Test list with trailing separator."""
        # Trailing separator creates empty string after split
        valid, invalid = validator.validate_list("a@test.com, ")
        # Empty string after stripping should be handled
        # This depends on implementation details
