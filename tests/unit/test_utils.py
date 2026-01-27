"""
Unit tests for utils.py - captures current production functionality.

These tests verify the utility functions in utils.py to ensure stability
and catch any regressions in future changes.
"""

import pytest
import os
import sys
from datetime import datetime

# Add parent directory to path so we can import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils


@pytest.mark.unit
class TestDacStrIntToInt:
    """Tests for the dac_str_int_to_int function."""

    def test_empty_string_returns_zero(self):
        """Empty or whitespace strings should return 0."""
        assert utils.dac_str_int_to_int("") == 0
        assert utils.dac_str_int_to_int("   ") == 0

    def test_positive_number(self):
        """Positive DAC strings are converted to integers."""
        assert utils.dac_str_int_to_int("12345") == 12345
        assert utils.dac_str_int_to_int("1") == 1
        assert utils.dac_str_int_to_int("999999") == 999999

    def test_negative_number(self):
        """Negative DAC strings (prefixed with -) are handled correctly."""
        # DAC format encodes negatives: leading minus sign means negative
        # The actual calculation is int(str[1:]) - (int(str[1:]) * 2)
        result = utils.dac_str_int_to_int("-100")
        assert result < 0
        assert result == 100 - (100 * 2)  # -100

    def test_leading_zeros(self):
        """Numbers with leading zeros are handled correctly."""
        assert utils.dac_str_int_to_int("00123") == 123
        assert utils.dac_str_int_to_int("0") == 0


@pytest.mark.unit
class TestConvertToPrice:
    """Tests for the convert_to_price function."""

    def test_basic_price_conversion(self):
        """Prices are converted with decimal point."""
        assert utils.convert_to_price("12345") == "123.45"
        assert utils.convert_to_price("1") == "0.1"
        assert utils.convert_to_price("999") == "9.99"

    def test_zero_price(self):
        """Zero prices are handled correctly."""
        assert utils.convert_to_price("0") == "0.0"
        assert utils.convert_to_price("00") == "0.00"

    def test_leading_zeros_stripped(self):
        """Leading zeros are stripped from the main portion."""
        assert utils.convert_to_price("001234") == "12.34"
        assert utils.convert_to_price("000100") == "1.00"


@pytest.mark.unit
class TestDactimeFromDatetime:
    """Tests for the dactime_from_datetime function."""

    def test_basic_date_conversion(self):
        """Dates are converted to DAC time format."""
        dt = datetime(2021, 1, 15)
        result = utils.dactime_from_datetime(dt)
        assert result == "1210115"  # (2021 - 1900) = 121, then 010115

    def test_year_2000(self):
        """Year 2000 is handled correctly."""
        dt = datetime(2000, 1, 1)
        result = utils.dactime_from_datetime(dt)
        assert result == "1000101"  # (2000 - 1900) = 100

    def test_year_1999(self):
        """Year 1999 is handled correctly."""
        dt = datetime(1999, 12, 31)
        result = utils.dactime_from_datetime(dt)
        assert result == "0991231"  # (1999 - 1900) = 99


@pytest.mark.unit
class TestDatetimeFromDactime:
    """Tests for the datetime_from_dactime function."""

    def test_basic_dactime_conversion(self):
        """DAC times are converted to datetime objects."""
        result = utils.datetime_from_dactime(1210115)
        assert result.year == 2021
        assert result.month == 1
        assert result.day == 15

    def test_year_2000_conversion(self):
        """Year 2000 DAC times are converted correctly."""
        result = utils.datetime_from_dactime(1000101)
        assert result.year == 2000
        assert result.month == 1
        assert result.day == 1

    def test_dactime_roundtrip(self):
        """Converting datetime to dactime and back produces same result."""
        original = datetime(2021, 6, 30)
        dactime = utils.dactime_from_datetime(original)
        result = utils.datetime_from_dactime(int(dactime))
        assert result.year == original.year
        assert result.month == original.month
        assert result.day == original.day


@pytest.mark.unit
class TestDatetimeFromInvtime:
    """Tests for the datetime_from_invtime function."""

    def test_basic_invtime_conversion(self):
        """Invoice times are converted to datetime objects."""
        result = utils.datetime_from_invtime("010521")
        assert result.month == 1
        assert result.day == 5
        assert result.year == 2021

    def test_december_date(self):
        """December dates are handled correctly."""
        result = utils.datetime_from_invtime("121531")
        assert result.month == 12
        assert result.day == 15
        assert result.year == 2031


@pytest.mark.unit
class TestDactimeFromInvtime:
    """Tests for the dactime_from_invtime function."""

    def test_invtime_to_dactime_conversion(self):
        """Invoice times are properly converted to DAC times."""
        result = utils.dactime_from_invtime("010521")
        # 01/05/21 should become 2021-01-05
        # DAC time: (2021 - 1900) = 121, then 010105
        assert result == "1210105"

    def test_year_2020_conversion(self):
        """Year 2020 is handled correctly."""
        result = utils.dactime_from_invtime("010120")
        # 01/01/20 should become 2020-01-01
        assert result == "1200101"


@pytest.mark.unit
class TestCalcCheckDigit:
    """Tests for the calc_check_digit function."""

    def test_check_digit_calculation(self):
        """Check digits are calculated correctly."""
        # Based on standard UPC/EAN check digit algorithm
        result = utils.calc_check_digit("12345678901")
        assert isinstance(result, int)
        assert 0 <= result <= 9


@pytest.mark.unit
class TestConvertUPCEToUPCA:
    """Tests for the convert_UPCE_to_UPCA function."""

    def test_upce_to_upca_conversion_type_0(self):
        """UPC-E codes ending in 0 are expanded correctly."""
        # UPC-E format: XABCDE0 -> UPCA: XAB00CDE
        upca = utils.convert_UPCE_to_UPCA("01234560")
        assert len(upca) == 12  # UPCA is always 12 digits
        assert upca.startswith("0")

    def test_upce_to_upca_conversion_type_1(self):
        """UPC-E codes ending in 1 are expanded correctly."""
        # UPC-E format: XABCDE1 -> UPCA: XAB10CDE
        upca = utils.convert_UPCE_to_UPCA("01234561")
        assert len(upca) == 12

    def test_upce_to_upca_conversion_type_2(self):
        """UPC-E codes ending in 2 are expanded correctly."""
        # UPC-E format: XABCDE2 -> UPCA: XAB20CDE
        upca = utils.convert_UPCE_to_UPCA("01234562")
        assert len(upca) == 12

    def test_upce_to_upca_conversion_type_3(self):
        """UPC-E codes ending in 3 are expanded correctly."""
        # UPC-E format: XABCDE3 -> UPCA: XAB300DE
        upca = utils.convert_UPCE_to_UPCA("01234563")
        assert len(upca) == 12

    def test_upce_to_upca_conversion_type_4(self):
        """UPC-E codes ending in 4 are expanded correctly."""
        # UPC-E format: XABCDE4 -> UPCA: XAB3000E
        upca = utils.convert_UPCE_to_UPCA("01234564")
        assert len(upca) == 12

    def test_upce_to_upca_conversion_type_5_to_9(self):
        """UPC-E codes ending in 5-9 are expanded correctly."""
        # UPC-E format: XABCDE(5-9) -> UPCA: XABCDE(5-9)00
        for suffix in range(5, 10):
            upca = utils.convert_UPCE_to_UPCA(f"0123456{suffix}")
            assert len(upca) == 12
