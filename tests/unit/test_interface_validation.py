"""
Unit tests for interface.utils.validation module.

Tests pure validation functions for email, folder paths, FTP hosts,
ports, and other input validation.
"""

import os
import tempfile
import pytest
from unittest.mock import patch

from interface.utils.validation import (
    validate_email,
    validate_folder_path,
    validate_ftp_host,
    validate_port,
    validate_positive_integer,
    validate_non_negative_integer,
    validate_folder_exists,
    sanitize_input,
    validate_numeric,
    validate_boolean,
    validate_url,
    validate_ip_address,
)


class TestValidateEmail:
    """Tests for validate_email function."""

    def test_valid_email_simple(self):
        """Valid simple email should return True."""
        assert validate_email("user@example.com") is True

    def test_valid_email_with_plus(self):
        """Valid email with plus sign should return True."""
        assert validate_email("user+tag@example.com") is True

    def test_valid_email_with_subdomain(self):
        """Valid email with subdomain should return True."""
        assert validate_email("user@mail.example.com") is True

    def test_valid_email_with_dots(self):
        """Valid email with dots in local part should return True."""
        assert validate_email("first.last@example.com") is True

    def test_invalid_email_no_at(self):
        """Email without @ should return False."""
        assert validate_email("userexample.com") is False

    def test_invalid_email_no_domain(self):
        """Email without domain should return False."""
        assert validate_email("user@") is False

    def test_invalid_email_no_tld(self):
        """Email without TLD should return False."""
        assert validate_email("user@example") is False

    def test_invalid_email_empty(self):
        """Empty string should return False."""
        assert validate_email("") is False

    def test_invalid_email_none(self):
        """None should return False."""
        assert validate_email(None) is False

    def test_invalid_email_spaces(self):
        """Email with spaces should return False."""
        assert validate_email("user @example.com") is False


class TestValidateFolderPath:
    """Tests for validate_folder_path function."""

    def test_valid_path_exists(self):
        """Existing accessible path should return (True, None)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, error = validate_folder_path(tmpdir)
            assert is_valid is True
            assert error is None

    def test_invalid_path_empty(self):
        """Empty path should return (False, error)."""
        is_valid, error = validate_folder_path("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_invalid_path_nonexistent(self):
        """Non-existent path should return (False, error)."""
        is_valid, error = validate_folder_path("/nonexistent/path/that/does/not/exist")
        assert is_valid is False
        assert "does not exist" in error.lower()

    @pytest.mark.skipif(os.name == "nt", reason="Permission tests differ on Windows")
    def test_invalid_path_not_accessible(self):
        """Non-accessible path should return (False, error)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory and remove all permissions
            restricted_dir = os.path.join(tmpdir, "restricted")
            os.mkdir(restricted_dir)
            os.chmod(restricted_dir, 0o000)
            try:
                is_valid, error = validate_folder_path(restricted_dir)
                assert is_valid is False
                assert "not accessible" in error.lower()
            finally:
                os.chmod(restricted_dir, 0o755)


class TestValidateFtpHost:
    """Tests for validate_ftp_host function."""

    def test_valid_hostname(self):
        """Valid hostname should return True."""
        assert validate_ftp_host("ftp.example.com") is True

    def test_valid_hostname_simple(self):
        """Simple hostname should return True."""
        assert validate_ftp_host("localhost") is True

    def test_valid_ip_address(self):
        """Valid IP address should return True."""
        assert validate_ftp_host("192.168.1.1") is True

    def test_invalid_empty(self):
        """Empty string should return False."""
        assert validate_ftp_host("") is False

    def test_invalid_none(self):
        """None should return False."""
        assert validate_ftp_host(None) is False

    def test_invalid_starts_with_dot(self):
        """Hostname starting with dot should return False."""
        assert validate_ftp_host(".example.com") is False


class TestValidatePort:
    """Tests for validate_port function."""

    def test_valid_port_min(self):
        """Port 1 should be valid."""
        assert validate_port(1) is True

    def test_valid_port_max(self):
        """Port 65535 should be valid."""
        assert validate_port(65535) is True

    def test_valid_port_common(self):
        """Common port 80 should be valid."""
        assert validate_port(80) is True

    def test_valid_port_ftp(self):
        """FTP port 21 should be valid."""
        assert validate_port(21) is True

    def test_invalid_port_zero(self):
        """Port 0 should be invalid."""
        assert validate_port(0) is False

    def test_invalid_port_negative(self):
        """Negative port should be invalid."""
        assert validate_port(-1) is False

    def test_invalid_port_too_high(self):
        """Port above 65535 should be invalid."""
        assert validate_port(65536) is False

    def test_invalid_port_string(self):
        """String port should be invalid."""
        assert validate_port("80") is False

    def test_invalid_port_float(self):
        """Float port should be invalid."""
        assert validate_port(80.5) is False


class TestValidatePositiveInteger:
    """Tests for validate_positive_integer function."""

    def test_valid_positive(self):
        """Positive integer should return True."""
        assert validate_positive_integer(1) is True
        assert validate_positive_integer(100) is True

    def test_invalid_zero(self):
        """Zero should return False."""
        assert validate_positive_integer(0) is False

    def test_invalid_negative(self):
        """Negative should return False."""
        assert validate_positive_integer(-1) is False

    def test_invalid_float(self):
        """Float should return False."""
        assert validate_positive_integer(1.5) is False

    def test_invalid_string(self):
        """String should return False."""
        assert validate_positive_integer("1") is False


class TestValidateNonNegativeInteger:
    """Tests for validate_non_negative_integer function."""

    def test_valid_zero(self):
        """Zero should return True."""
        assert validate_non_negative_integer(0) is True

    def test_valid_positive(self):
        """Positive integer should return True."""
        assert validate_non_negative_integer(1) is True

    def test_invalid_negative(self):
        """Negative should return False."""
        assert validate_non_negative_integer(-1) is False

    def test_invalid_float(self):
        """Float should return False."""
        assert validate_non_negative_integer(0.5) is False


class TestValidateFolderExists:
    """Tests for validate_folder_exists function."""

    def test_valid_folder_exists(self):
        """Existing folder should return True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert validate_folder_exists(tmpdir) is True

    def test_invalid_folder_not_exists(self):
        """Non-existent folder should return False."""
        assert validate_folder_exists("/nonexistent/path") is False

    def test_invalid_folder_is_file(self):
        """File (not folder) should return False."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            assert validate_folder_exists(tmpfile.name) is False

    def test_invalid_folder_empty(self):
        """Empty string should return False."""
        assert validate_folder_exists("") is False


class TestSanitizeInput:
    """Tests for sanitize_input function."""

    def test_normal_input(self):
        """Normal input should pass through."""
        assert sanitize_input("hello world") == "hello world"

    def test_removes_control_characters(self):
        """Control characters should be removed."""
        assert sanitize_input("hello\x00world") == "helloworld"
        assert sanitize_input("test\x1fvalue") == "testvalue"

    def test_truncates_long_input(self):
        """Long input should be truncated."""
        long_input = "a" * 300
        result = sanitize_input(long_input)
        assert len(result) == 255

    def test_custom_max_length(self):
        """Custom max length should be respected."""
        result = sanitize_input("hello world", max_length=5)
        assert result == "hello"

    def test_none_input(self):
        """None input should return empty string."""
        assert sanitize_input(None) == ""

    def test_preserves_unicode(self):
        """Unicode characters should be preserved."""
        assert sanitize_input("héllo wörld") == "héllo wörld"


class TestValidateNumeric:
    """Tests for validate_numeric function."""

    def test_valid_integer_string(self):
        """Integer string should return True."""
        assert validate_numeric("123") is True

    def test_valid_negative_integer(self):
        """Negative integer string should return True."""
        assert validate_numeric("-123") is True

    def test_invalid_float_without_flag(self):
        """Float string without allow_decimal should return False."""
        assert validate_numeric("123.45") is False

    def test_valid_float_with_flag(self):
        """Float string with allow_decimal should return True."""
        assert validate_numeric("123.45", allow_decimal=True) is True

    def test_invalid_non_numeric(self):
        """Non-numeric string should return False."""
        assert validate_numeric("abc") is False

    def test_invalid_empty(self):
        """Empty string should return False."""
        assert validate_numeric("") is False


class TestValidateBoolean:
    """Tests for validate_boolean function."""

    def test_true_values(self):
        """True string values should return True."""
        assert validate_boolean("true") is True
        assert validate_boolean("True") is True
        assert validate_boolean("TRUE") is True
        assert validate_boolean("1") is True
        assert validate_boolean("yes") is True
        assert validate_boolean("on") is True

    def test_false_values(self):
        """False string values should return False."""
        assert validate_boolean("false") is False
        assert validate_boolean("False") is False
        assert validate_boolean("FALSE") is False
        assert validate_boolean("0") is False
        assert validate_boolean("no") is False
        assert validate_boolean("off") is False

    def test_invalid_values(self):
        """Invalid values should return None."""
        assert validate_boolean("maybe") is None
        assert validate_boolean("") is None
        assert validate_boolean("2") is None


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_http_url(self):
        """HTTP URL should return True."""
        assert validate_url("http://example.com") is True

    def test_valid_https_url(self):
        """HTTPS URL should return True."""
        assert validate_url("https://example.com") is True

    def test_valid_url_with_path(self):
        """URL with path should return True."""
        assert validate_url("https://example.com/path/to/page") is True

    def test_invalid_no_protocol(self):
        """URL without protocol should return False."""
        assert validate_url("example.com") is False

    def test_invalid_ftp_protocol(self):
        """FTP URL should return False."""
        assert validate_url("ftp://example.com") is False

    def test_invalid_empty(self):
        """Empty string should return False."""
        assert validate_url("") is False


class TestValidateIpAddress:
    """Tests for validate_ip_address function."""

    def test_valid_ip(self):
        """Valid IP address should return True."""
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("10.0.0.1") is True
        assert validate_ip_address("255.255.255.255") is True
        assert validate_ip_address("0.0.0.0") is True

    def test_invalid_ip_octet_too_high(self):
        """IP with octet > 255 should return False."""
        assert validate_ip_address("256.1.1.1") is False

    def test_invalid_ip_too_few_octets(self):
        """IP with too few octets should return False."""
        assert validate_ip_address("192.168.1") is False

    def test_invalid_ip_too_many_octets(self):
        """IP with too many octets should return False."""
        assert validate_ip_address("192.168.1.1.1") is False

    def test_invalid_ip_non_numeric(self):
        """IP with non-numeric parts should return False."""
        assert validate_ip_address("192.168.a.1") is False

    def test_invalid_ip_empty(self):
        """Empty string should return False."""
        assert validate_ip_address("") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
