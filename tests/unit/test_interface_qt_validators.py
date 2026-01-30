"""
Unit tests for interface.utils.qt_validators module.

Tests Qt validators for email, port, IP address, and other patterns.
Note: Requires PyQt6 to be installed.
"""

import pytest

# Try to import PyQt6, skip tests if not available
try:
    from PyQt6.QtGui import QValidator
    from interface.utils.qt_validators import (
        PORT_VALIDATOR,
        POSITIVE_INT_VALIDATOR,
        NON_NEGATIVE_INT_VALIDATOR,
        EMAIL_VALIDATOR,
        IP_ADDRESS_VALIDATOR,
        FTP_HOST_VALIDATOR,
        HEX_COLOR_VALIDATOR,
        POSITIVE_DOUBLE_VALIDATOR,
        create_range_validator,
        create_regex_validator,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


pytestmark = pytest.mark.skipif(not PYQT6_AVAILABLE, reason="PyQt6 not available")


class TestPortValidator:
    """Tests for PORT_VALIDATOR."""

    def test_valid_port_min(self):
        """Port 1 should be acceptable."""
        state, _, _ = PORT_VALIDATOR.validate("1", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_port_max(self):
        """Port 65535 should be acceptable."""
        state, _, _ = PORT_VALIDATOR.validate("65535", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_port_common(self):
        """Port 8080 should be acceptable."""
        state, _, _ = PORT_VALIDATOR.validate("8080", 0)
        assert state == QValidator.State.Acceptable

    def test_invalid_port_zero(self):
        """Port 0 should be invalid."""
        state, _, _ = PORT_VALIDATOR.validate("0", 0)
        assert state != QValidator.State.Acceptable

    def test_invalid_port_too_high(self):
        """Port 65536 should not be acceptable (may be Intermediate as user edits)."""
        state, _, _ = PORT_VALIDATOR.validate("65536", 0)
        assert state != QValidator.State.Acceptable


class TestPositiveIntValidator:
    """Tests for POSITIVE_INT_VALIDATOR."""

    def test_valid_positive(self):
        """Positive integer should be acceptable."""
        state, _, _ = POSITIVE_INT_VALIDATOR.validate("42", 0)
        assert state == QValidator.State.Acceptable

    def test_invalid_zero(self):
        """Zero should be invalid."""
        state, _, _ = POSITIVE_INT_VALIDATOR.validate("0", 0)
        assert state != QValidator.State.Acceptable


class TestNonNegativeIntValidator:
    """Tests for NON_NEGATIVE_INT_VALIDATOR."""

    def test_valid_zero(self):
        """Zero should be acceptable."""
        state, _, _ = NON_NEGATIVE_INT_VALIDATOR.validate("0", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_positive(self):
        """Positive integer should be acceptable."""
        state, _, _ = NON_NEGATIVE_INT_VALIDATOR.validate("100", 0)
        assert state == QValidator.State.Acceptable


class TestEmailValidator:
    """Tests for EMAIL_VALIDATOR."""

    def test_valid_email_simple(self):
        """Simple email should be acceptable."""
        state, _, _ = EMAIL_VALIDATOR.validate("user@example.com", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_email_with_plus(self):
        """Email with plus sign should be acceptable."""
        state, _, _ = EMAIL_VALIDATOR.validate("user+tag@example.com", 0)
        assert state == QValidator.State.Acceptable

    def test_invalid_email_no_at(self):
        """Email without @ should not be acceptable (may be Intermediate as user edits)."""
        state, _, _ = EMAIL_VALIDATOR.validate("userexample.com", 0)
        assert state != QValidator.State.Acceptable

    def test_invalid_email_no_domain(self):
        """Email without domain should be invalid."""
        state, _, _ = EMAIL_VALIDATOR.validate("user@", 0)
        assert state != QValidator.State.Acceptable


class TestIpAddressValidator:
    """Tests for IP_ADDRESS_VALIDATOR."""

    def test_valid_ip(self):
        """Valid IP should be acceptable."""
        state, _, _ = IP_ADDRESS_VALIDATOR.validate("192.168.1.1", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_ip_zeros(self):
        """IP with zeros should be acceptable."""
        state, _, _ = IP_ADDRESS_VALIDATOR.validate("0.0.0.0", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_ip_max(self):
        """Max IP should be acceptable."""
        state, _, _ = IP_ADDRESS_VALIDATOR.validate("255.255.255.255", 0)
        assert state == QValidator.State.Acceptable

    def test_invalid_ip_octet_too_high(self):
        """IP with octet > 255 should be invalid."""
        state, _, _ = IP_ADDRESS_VALIDATOR.validate("256.1.1.1", 0)
        assert state == QValidator.State.Invalid


class TestFtpHostValidator:
    """Tests for FTP_HOST_VALIDATOR."""

    def test_valid_hostname(self):
        """Valid hostname should be acceptable."""
        state, _, _ = FTP_HOST_VALIDATOR.validate("ftp.example.com", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_ip(self):
        """Valid IP should be acceptable."""
        state, _, _ = FTP_HOST_VALIDATOR.validate("192.168.1.1", 0)
        assert state == QValidator.State.Acceptable


class TestHexColorValidator:
    """Tests for HEX_COLOR_VALIDATOR."""

    def test_valid_color(self):
        """Valid hex color should be acceptable."""
        state, _, _ = HEX_COLOR_VALIDATOR.validate("#FF0000", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_color_lowercase(self):
        """Lowercase hex color should be acceptable."""
        state, _, _ = HEX_COLOR_VALIDATOR.validate("#ff00ff", 0)
        assert state == QValidator.State.Acceptable

    def test_invalid_color_no_hash(self):
        """Color without hash should be invalid."""
        state, _, _ = HEX_COLOR_VALIDATOR.validate("FF0000", 0)
        assert state == QValidator.State.Invalid

    def test_invalid_color_short(self):
        """Short color code should not be acceptable (may be Intermediate as user types)."""
        state, _, _ = HEX_COLOR_VALIDATOR.validate("#FFF", 0)
        assert state != QValidator.State.Acceptable


class TestPositiveDoubleValidator:
    """Tests for POSITIVE_DOUBLE_VALIDATOR."""

    def test_valid_positive_float(self):
        """Positive float should be acceptable."""
        state, _, _ = POSITIVE_DOUBLE_VALIDATOR.validate("123.45", 0)
        assert state == QValidator.State.Acceptable

    def test_valid_zero(self):
        """Zero should be acceptable."""
        state, _, _ = POSITIVE_DOUBLE_VALIDATOR.validate("0", 0)
        assert state == QValidator.State.Acceptable


class TestCreateRangeValidator:
    """Tests for create_range_validator function."""

    def test_creates_valid_range(self):
        """Should create validator with specified range."""
        validator = create_range_validator(10, 100)
        state, _, _ = validator.validate("50", 0)
        assert state == QValidator.State.Acceptable

    def test_rejects_below_range(self):
        """Should reject values below range."""
        validator = create_range_validator(10, 100)
        state, _, _ = validator.validate("5", 0)
        assert state != QValidator.State.Acceptable

    def test_rejects_above_range(self):
        """Should reject values above range (may be Intermediate as user edits)."""
        validator = create_range_validator(10, 100)
        state, _, _ = validator.validate("200", 0)
        assert state != QValidator.State.Acceptable


class TestCreateRegexValidator:
    """Tests for create_regex_validator function."""

    def test_creates_valid_pattern(self):
        """Should create validator with specified pattern."""
        validator = create_regex_validator(r"^[A-Z]{3}$")
        state, _, _ = validator.validate("ABC", 0)
        assert state == QValidator.State.Acceptable

    def test_rejects_non_matching(self):
        """Should reject non-matching strings."""
        validator = create_regex_validator(r"^[A-Z]{3}$")
        state, _, _ = validator.validate("abc", 0)
        assert state == QValidator.State.Invalid

    def test_rejects_wrong_length(self):
        """Should reject strings of wrong length."""
        validator = create_regex_validator(r"^[A-Z]{3}$")
        state, _, _ = validator.validate("ABCD", 0)
        assert state == QValidator.State.Invalid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
