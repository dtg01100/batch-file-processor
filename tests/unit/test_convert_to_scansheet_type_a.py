"""Unit tests for ScanSheet Type A barcode parsing robustness."""

import pytest

from convert_to_scansheet_type_a import ScanSheetTypeAConverter


class TestScanSheetBarcodeParsing:
    """Validate barcode parsing against real-world UPC formatting."""

    def test_interpret_barcode_string_strips_non_digits(self):
        converter = ScanSheetTypeAConverter()

        # Real-world values can include separators, spaces, and text.
        result = converter._interpret_barcode_string("  0-12345 67890A  ")

        assert result == "01234567890"

    def test_interpret_barcode_string_zero_pads_short_values(self):
        converter = ScanSheetTypeAConverter()

        result = converter._interpret_barcode_string("12345")

        assert result == "00000012345"

    def test_interpret_barcode_string_uses_last_11_digits_when_long(self):
        converter = ScanSheetTypeAConverter()

        result = converter._interpret_barcode_string("99123456789012")

        assert result == "23456789012"

    def test_interpret_barcode_string_rejects_empty(self):
        converter = ScanSheetTypeAConverter()

        with pytest.raises(ValueError, match="Input contents are not an integer"):
            converter._interpret_barcode_string("   ---   ")
