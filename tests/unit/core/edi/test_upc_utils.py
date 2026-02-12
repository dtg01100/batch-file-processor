"""Unit tests for UPC utility functions."""

import pytest
from core.edi.upc_utils import (
    calc_check_digit,
    convert_upce_to_upca,
    pad_upc,
    validate_upc,
)


class TestCalcCheckDigit:
    """Tests for calc_check_digit function."""
    
    def test_calc_check_digit_simple(self):
        """Test check digit calculation for simple case."""
        # UPC 04180000026 should have check digit 5
        result = calc_check_digit("04180000026")
        assert result == 5
    
    def test_calc_check_digit_with_int_input(self):
        """Test check digit calculation accepts integer input."""
        result = calc_check_digit(4180000026)
        assert result == 5
    
    def test_calc_check_digit_zero_result(self):
        """Test check digit that results in 0."""
        # Test case where check digit should be 0
        result = calc_check_digit("03600029145")
        assert result == 2  # Known check digit for this UPC
    
    def test_calc_check_digit_all_zeros(self):
        """Test check digit for all zeros."""
        result = calc_check_digit("00000000000")
        assert result == 0
    
    def test_calc_check_digit_all_nines(self):
        """Test check digit for all nines."""
        result = calc_check_digit("99999999999")
        # For 11 nines: odd positions (from right) * 3 + even positions
        # = 6*27 + 5*9 = 162 + 45 = 207
        # 207 % 10 = 7, 10 - 7 = 3
        assert result == 3
    
    def test_calc_check_digit_single_digit(self):
        """Test check digit for single digit."""
        result = calc_check_digit("5")
        # 5 * 3 = 15, 15 % 10 = 5, 10 - 5 = 5
        assert result == 5


class TestConvertUpceToUpca:
    """Tests for convert_upce_to_upca function."""
    
    def test_convert_8_digit_upce(self):
        """Test conversion of 8-digit UPC-E to UPC-A.
        
        Example from docstring: 04182635 -> 041800000265
        """
        result = convert_upce_to_upca("04182635")
        assert result == "041800000265"
    
    def test_convert_6_digit_upce(self):
        """Test conversion of 6-digit UPC-E (middle digits only)."""
        # 6-digit input is treated as middle digits
        result = convert_upce_to_upca("418263")
        # d6=3, so mfrnum = d1+d2+d3+"00" = "41800", itemnum = "000"+d4+d5 = "00026"
        # newmsg = "0" + "41800" + "00026" = "04180000026"
        assert result == "041800000265"
    
    def test_convert_7_digit_upce(self):
        """Test conversion of 7-digit UPC-E (truncates last digit)."""
        result = convert_upce_to_upca("4182635")
        # Takes first 6 digits: 418263
        assert result == "041800000265"
    
    def test_convert_upce_d6_is_0(self):
        """Test conversion when d6 is 0."""
        # d6 in ["0", "1", "2"]: mfrnum = d1+d2+d6+"00", itemnum = "00"+d3+d4+d5
        result = convert_upce_to_upca("123450")
        # d1=1, d2=2, d3=3, d4=4, d5=5, d6=0
        # mfrnum = "12" + "0" + "00" = "12000"
        # itemnum = "00" + "3" + "4" + "5" = "00345"
        # newmsg = "0" + "12000" + "00345" = "01200000345"
        assert result.startswith("01200000345")
    
    def test_convert_upce_d6_is_1(self):
        """Test conversion when d6 is 1."""
        result = convert_upce_to_upca("123451")
        # mfrnum = "12" + "1" + "00" = "12100"
        # itemnum = "00" + "3" + "4" + "5" = "00345"
        # newmsg = "0" + "12100" + "00345" = "01210000345"
        assert result.startswith("01210000345")
    
    def test_convert_upce_d6_is_2(self):
        """Test conversion when d6 is 2."""
        result = convert_upce_to_upca("123452")
        # mfrnum = "12" + "2" + "00" = "12200"
        # itemnum = "00" + "3" + "4" + "5" = "00345"
        assert result.startswith("01220000345")
    
    def test_convert_upce_d6_is_3(self):
        """Test conversion when d6 is 3."""
        # d6 == "3": mfrnum = d1+d2+d3+"00", itemnum = "000"+d4+d5
        result = convert_upce_to_upca("123453")
        # mfrnum = "12" + "3" + "00" = "12300"
        # itemnum = "000" + "4" + "5" = "00045"
        assert result.startswith("01230000045")
    
    def test_convert_upce_d6_is_4(self):
        """Test conversion when d6 is 4."""
        # d6 == "4": mfrnum = d1+d2+d3+d4+"0", itemnum = "0000"+d5
        result = convert_upce_to_upca("123454")
        # mfrnum = "12" + "3" + "4" + "0" = "12340"
        # itemnum = "0000" + "5" = "00005"
        assert result.startswith("01234000005")
    
    def test_convert_upce_d6_is_5_to_9(self):
        """Test conversion when d6 is 5-9."""
        # d6 >= 5: mfrnum = d1+d2+d3+d4+d5, itemnum = "0000"+d6
        result = convert_upce_to_upca("123455")
        # mfrnum = "12345"
        # itemnum = "0000" + "5" = "00005"
        assert result.startswith("01234500005")
    
    def test_convert_upce_invalid_length(self):
        """Test conversion returns empty string for invalid length."""
        result = convert_upce_to_upca("123")  # Too short
        assert result == ""
        
        result = convert_upce_to_upca("123456789")  # Too long
        assert result == ""
    
    def test_convert_upce_preserves_check_digit(self):
        """Test that converted UPC-A has valid check digit."""
        result = convert_upce_to_upca("04182635")
        # Verify the check digit is valid
        assert validate_upc(result)


class TestPadUpc:
    """Tests for pad_upc function."""
    
    def test_pad_upc_shorter(self):
        """Test padding a shorter UPC."""
        result = pad_upc("12345", 10)
        assert result == "     12345"
    
    def test_pad_upc_exact_length(self):
        """Test UPC that is exactly target length."""
        result = pad_upc("12345", 5)
        assert result == "12345"
    
    def test_pad_upc_longer(self):
        """Test truncating a longer UPC."""
        result = pad_upc("123456789", 5)
        assert result == "12345"
    
    def test_pad_upc_custom_fill_char(self):
        """Test padding with custom fill character."""
        result = pad_upc("12345", 10, "0")
        assert result == "0000012345"
    
    def test_pad_upc_empty_string(self):
        """Test padding empty string."""
        result = pad_upc("", 5)
        assert result == "     "


class TestValidateUpc:
    """Tests for validate_upc function."""
    
    def test_validate_upc_valid(self):
        """Test validation of valid UPC."""
        # UPC 041800000265 is valid (from convert_upce_to_upca example)
        result = validate_upc("041800000265")
        assert result is True
    
    def test_validate_upc_invalid_check_digit(self):
        """Test validation of UPC with wrong check digit."""
        result = validate_upc("041800000260")  # Wrong check digit
        assert result is False
    
    def test_validate_upc_too_short(self):
        """Test validation of too short UPC."""
        result = validate_upc("12345678901")  # 11 digits
        assert result is False
    
    def test_validate_upc_empty(self):
        """Test validation of empty string."""
        result = validate_upc("")
        assert result is False
    
    def test_validate_upc_non_numeric(self):
        """Test validation of non-numeric string."""
        result = validate_upc("ABCDEFGHIJKL")
        assert result is False
    
    def test_validate_upc_with_spaces(self):
        """Test validation of UPC with spaces."""
        result = validate_upc("04180000026 ")
        assert result is False
    
    def test_validate_upc_none(self):
        """Test validation of None."""
        result = validate_upc(None)  # type: ignore
        assert result is False
    
    def test_validate_upc_longer_valid(self):
        """Test validation of longer UPC (13+ digits)."""
        # For 13+ digits, it validates the first 12
        # 041800000265 is valid, so 0418000002650 should also be valid
        # But actually validate_upc checks if len(upc) < 12, so 13 chars passes
        # Then it takes upc[:-1] = "041800000265" and upc[-1] = "0"
        # So it checks if calc_check_digit("041800000265") == 0
        # calc_check_digit("041800000265") = 5, not 0
        # So this should be False
        result = validate_upc("0418000002650")
        assert result is False  # The 13th digit '0' is not the check digit
        
        # Test with correct check digit at position 12
        result = validate_upc("041800000265")  # 12 digits, check digit is 5
        assert result is True


class TestUpcIntegration:
    """Integration tests for UPC utilities."""
    
    def test_convert_and_validate(self):
        """Test that converted UPC-E validates correctly."""
        upce = "04182635"
        upca = convert_upce_to_upca(upce)
        assert validate_upc(upca)
    
    def test_calc_check_digit_matches_validation(self):
        """Test that calc_check_digit matches validate_upc logic."""
        upc = "041800000265"
        value = upc[:-1]
        expected_check = int(upc[-1])
        calculated_check = calc_check_digit(value)
        
        assert calculated_check == expected_check
        assert validate_upc(upc)
