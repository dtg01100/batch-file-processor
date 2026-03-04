"""Tests for EDI tweak option combinations.

This module tests that arbitrary combinations of EDI tweak options
work correctly and produce expected behavior.

Tests cover:
- All boolean tweaks enabled simultaneously
- All boolean tweaks disabled simultaneously
- Mixed boolean combinations
- Cross-field interactions
- Edge cases and boundary conditions
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path
import tempfile

from dispatch.pipeline.tweaker import EDITweakerStep


class TestEDITweakBooleanCombinations:
    """Test EDI tweak with various boolean option combinations."""

    @pytest.fixture
    def base_parameters(self):
        """Create base parameters dictionary with all EDI tweak fields."""
        return {
            'pad_a_records': "False",
            'a_record_padding': "",
            'a_record_padding_length': 0,
            'append_a_records': "False",
            'a_record_append_text': "APPEND",
            'invoice_date_custom_format': False,
            'invoice_date_custom_format_string': "%Y-%m-%d",
            'force_txt_file_ext': "False",
            'calculate_upc_check_digit': "False",
            'invoice_date_offset': 0,
            'retail_uom': False,
            'override_upc_bool': False,
            'override_upc_level': 1,
            'override_upc_category_filter': "ALL",
            'split_prepaid_sales_tax_crec': "False",
            'upc_target_length': 11,
            'upc_padding_pattern': "           ",
            'tweak_edi': True,
        }

    @pytest.fixture
    def base_settings(self):
        """Create base settings dictionary."""
        return MagicMock()

    @pytest.mark.parametrize("pad_arec,append_arec,force_txt,calc_upc,retail_uom,override_upc,split_tax,tweak_edi", [
        (True, True, True, True, True, True, True, True),  # All enabled
        (False, False, False, False, False, False, False, False),  # All disabled
        (True, False, True, False, True, False, True, False),  # Mixed 1
        (False, True, False, True, False, True, False, True),  # Mixed 2
        (True, True, False, False, True, True, False, False),  # Mixed 3
        (False, False, True, True, False, False, True, True),  # Mixed 4
    ])
    def test_boolean_combinations(self, base_parameters, base_settings, pad_arec, append_arec, force_txt, calc_upc, retail_uom, override_upc, split_tax, tweak_edi):
        """Test various combinations of boolean EDI tweak flags."""
        params = base_parameters.copy()
        params['pad_a_records'] = "True" if pad_arec else "False"
        params['append_a_records'] = "True" if append_arec else "False"
        params['force_txt_file_ext'] = "True" if force_txt else "False"
        params['calculate_upc_check_digit'] = "True" if calc_upc else "False"
        params['retail_uom'] = retail_uom
        params['override_upc_bool'] = override_upc
        params['split_prepaid_sales_tax_crec'] = "True" if split_tax else "False"
        params['tweak_edi'] = tweak_edi

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            # Should not crash with any boolean combination
            assert result is not None

    def test_all_options_enabled_simultaneously(self, base_parameters, base_settings):
        """Test all EDI tweak options enabled at once."""
        params = base_parameters.copy()
        params['pad_a_records'] = "True"
        params['a_record_padding'] = "X"
        params['a_record_padding_length'] = 10
        params['append_a_records'] = "True"
        params['a_record_append_text'] = "CUSTOM_APPEND"
        params['invoice_date_custom_format'] = True
        params['invoice_date_custom_format_string'] = "%Y%m%d"
        params['force_txt_file_ext'] = "True"
        params['calculate_upc_check_digit'] = "True"
        params['invoice_date_offset'] = 7
        params['retail_uom'] = True
        params['override_upc_bool'] = True
        params['override_upc_level'] = 2
        params['override_upc_category_filter'] = "CAT1,CAT2"
        params['split_prepaid_sales_tax_crec'] = "True"
        params['upc_target_length'] = 12
        params['upc_padding_pattern'] = "123456789012"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    def test_all_options_disabled(self, base_parameters, base_settings):
        """Test all EDI tweak options disabled."""
        params = base_parameters.copy()
        params['tweak_edi'] = False

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            # String 'False' should skip tweaking
            mock_tweak_func.assert_not_called()
            assert result.output_path == str(input_file)
            assert not result.was_tweaked

    @pytest.mark.parametrize("date_offset", [-365, -30, -14, -7, -1, 0, 1, 7, 14, 30, 365])
    def test_invoice_date_offset_variations(self, base_parameters, base_settings, date_offset):
        """Test invoice_date_offset with various values."""
        params = base_parameters.copy()
        params['invoice_date_offset'] = date_offset

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    @pytest.mark.parametrize("upc_length", [0, 1, 5, 11, 12, 15, 20])
    def test_upc_target_length_variations(self, base_parameters, base_settings, upc_length):
        """Test upc_target_length with various values."""
        params = base_parameters.copy()
        params['upc_target_length'] = upc_length
        params['calculate_upc_check_digit'] = "True"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    @pytest.mark.parametrize("padding_pattern", ["", "0", "X", "12345", "0123456789", "ABCDEFGHIJ", "           "])
    def test_upc_padding_pattern_variations(self, base_parameters, base_settings, padding_pattern):
        """Test upc_padding_pattern with various patterns."""
        params = base_parameters.copy()
        params['upc_padding_pattern'] = padding_pattern
        params['calculate_upc_check_digit'] = "True"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    @pytest.mark.parametrize("date_format", [
        "%Y-%m-%d",
        "%Y%m%d",
        "%m/%d/%Y",
        "%d-%b-%Y",
        "%Y/%m/%d",
    ])
    def test_custom_date_format_variations(self, base_parameters, base_settings, date_format):
        """Test invoice_date_custom_format_string with various formats."""
        params = base_parameters.copy()
        params['invoice_date_custom_format'] = True
        params['invoice_date_custom_format_string'] = date_format

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    @pytest.mark.parametrize("override_level", [0, 1, 2, 3, 5, 10])
    def test_override_upc_level_variations(self, base_parameters, base_settings, override_level):
        """Test override_upc_level with various values."""
        params = base_parameters.copy()
        params['override_upc_bool'] = True
        params['override_upc_level'] = override_level

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            upc_dict = {"UPC1": "NEWUPC1"}
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                upc_dict
            )
            
            assert result is not None

    @pytest.mark.parametrize("category_filter", ["ALL", "CAT1", "CAT1,CAT2", "CAT1,CAT2,CAT3,CAT4"])
    def test_override_upc_category_filter_variations(self, base_parameters, base_settings, category_filter):
        """Test override_upc_category_filter with various filters."""
        params = base_parameters.copy()
        params['override_upc_bool'] = True
        params['override_upc_category_filter'] = category_filter

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            upc_dict = {"CAT1:ITEM1": "NEWUPC1"}
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                upc_dict
            )
            
            assert result is not None

    @pytest.mark.parametrize("padding_length", [0, 1, 5, 10, 20, 50, 100])
    def test_a_record_padding_length_variations(self, base_parameters, base_settings, padding_length):
        """Test a_record_padding_length with various values."""
        params = base_parameters.copy()
        params['pad_a_records'] = "True"
        params['a_record_padding'] = "X"
        params['a_record_padding_length'] = padding_length

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    def test_a_record_options_combination(self, base_parameters, base_settings):
        """Test A-record options combined: pad, append, and custom text."""
        params = base_parameters.copy()
        params['pad_a_records'] = "True"
        params['a_record_padding'] = "0"
        params['a_record_padding_length'] = 15
        params['append_a_records'] = "True"
        params['a_record_append_text'] = "CUSTOM_SUFFIX"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    def test_upc_options_combination(self, base_parameters, base_settings):
        """Test UPC options combined: calculate check digit, override, and padding."""
        params = base_parameters.copy()
        params['calculate_upc_check_digit'] = "True"
        params['upc_target_length'] = 12
        params['upc_padding_pattern'] = "0"
        params['override_upc_bool'] = True
        params['override_upc_level'] = 1

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            upc_dict = {"ITEM1": "NEWUPC"}
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                upc_dict
            )
            
            assert result is not None

    def test_date_options_combination(self, base_parameters, base_settings):
        """Test date options combined: custom format and offset."""
        params = base_parameters.copy()
        params['invoice_date_custom_format'] = True
        params['invoice_date_custom_format_string'] = "%Y%m%d"
        params['invoice_date_offset'] = 7

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            assert result is not None

    def test_tweak_edi_false_skips_all_tweaks(self, base_parameters, base_settings):
        """Test that tweak_edi=False skips all tweaking operations."""
        params = base_parameters.copy()
        params['tweak_edi'] = False
        # Enable various tweaks, but they should be skipped
        params['pad_a_records'] = "True"
        params['calculate_upc_check_digit'] = "True"
        params['invoice_date_offset'] = 5

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            # String 'False' should skip tweaking
            mock_tweak_func.assert_not_called()
            assert result.output_path == str(input_file)
            assert not result.was_tweaked

    def test_empty_upc_dict_with_override_enabled(self, base_parameters, base_settings):
        """Test override_upc_bool=True with empty upc_dict."""
        params = base_parameters.copy()
        params['override_upc_bool'] = True
        params['override_upc_level'] = 1
        params['override_upc_category_filter'] = "CAT1"

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            upc_dict = {}  # Empty UPC dict
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                upc_dict
            )
            
            # Should not crash with empty UPC dict
            assert result is not None

    def test_zero_padding_length_with_padding_enabled(self, base_parameters, base_settings):
        """Test pad_a_records=True with zero padding_length."""
        params = base_parameters.copy()
        params['pad_a_records'] = "True"
        params['a_record_padding'] = ""
        params['a_record_padding_length'] = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000010101250000100000\\n")
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            # Should not crash with zero padding length
            assert result is not None

    def test_custom_date_format_with_invalid_date(self, base_parameters, base_settings):
        """Test custom date format with invalid date (000000)."""
        params = base_parameters.copy()
        params['invoice_date_custom_format'] = True
        params['invoice_date_custom_format_string'] = "%Y-%m-%d"

        # Use EDI with invalid date (000000)
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.edi"
            input_file.write_text("AVENDOR00000000000000000000100000\\n")  # Date is 000000
            
            mock_tweak_func = Mock(return_value=str(Path(tmpdir) / "output.edi"))
            tweaker = EDITweakerStep(tweak_function=mock_tweak_func)
            
            result = tweaker.tweak(
                str(input_file),
                tmpdir,
                params,
                base_settings(),
                {}
            )
            
            # Should handle invalid date gracefully
            assert result is not None
