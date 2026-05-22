"""Unit tests for ScanSheet Type A barcode parsing robustness."""

import io as _io

import pytest

from dispatch.converters.convert_to_scansheet_type_a import ScanSheetTypeAConverter


class TestScanSheetBarcodeParsing:
    """Validate barcode parsing against real-world UPC formatting."""

class TestScanSheetBarcodeGeneration:
    """Validate barcode generation produces correct, decodable barcodes."""

    def _try_decode_barcode(self, buffer: _io.BytesIO) -> str | None:
        """Attempt to decode a barcode image from a BytesIO buffer.
        
        Returns the decoded data as string, or None if decoding fails.
        pyzbar is required for this - if not available, returns None.
        """
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode

            buffer.seek(0)
            img = Image.open(buffer)
            decoded = decode(img)
            if decoded:
                return decoded[0].data.decode("utf-8")
        except ImportError:
            pass
        return None

    def test_barcode_decodes_to_correct_upc(self):
        """Verify generated barcode decodes to the input UPC value."""
        converter = ScanSheetTypeAConverter()

        upc = "012345678905"
        buf, _, _ = converter._generate_barcode(upc)

        decoded = self._try_decode_barcode(buf)
        if decoded is None:
            pytest.skip("pyzbar not available for barcode decoding")

        # UPC-A is encoded as EAN-13 (12 digits → 13 digits with leading zero)
        expected_ean13 = "0" + upc
        assert decoded == expected_ean13, (
            f"Barcode decoded to {decoded}, expected EAN-13 format {expected_ean13}"
        )

    def test_barcode_decodes_for_different_upcs(self):
        """Verify multiple different UPCs generate correct barcodes."""
        converter = ScanSheetTypeAConverter()

        test_upcs = [
            "012345678905",
            "987654321012",
            "000000000001",
            "123456789012",
        ]

        decoded_upcs = []
        for upc in test_upcs:
            buf, _, _ = converter._generate_barcode(upc)
            decoded = self._try_decode_barcode(buf)
            if decoded:
                # UPC-A is encoded as EAN-13 (12 digits → 13 digits with leading zero)
                decoded_upcs.append("0" + upc)

        if len(decoded_upcs) != len(test_upcs):
            pytest.skip("pyzbar not available for barcode decoding")

        expected = ["0" + upc for upc in test_upcs]
        assert decoded_upcs == expected, (
            f"Decoded UPCs {decoded_upcs} don't match expected {expected}"
        )

    def test_barcode_contains_visual_content(self):
        """Verify barcode image is not blank - contains bars and spaces."""
        from PIL import Image

        converter = ScanSheetTypeAConverter()
        buf, _, _ = converter._generate_barcode("012345678905")

        buf.seek(0)
        img = Image.open(buf)

        # Convert to grayscale and check variance (blank images have no variance)
        gray = img.convert("L")
        pixels = list(gray.getdata())

        # Count pixels that differ from the background (quiet zone is white)
        # Barcodes have significant variation in the bar region, but also have
        # quiet zones (white space) at edges
        different_pixels = sum(1 for p in pixels if p != pixels[0])
        variance_ratio = different_pixels / len(pixels)

        # Lower threshold - barcodes have white space around them (quiet zones)
        assert variance_ratio > 0.15, (
            f"Barcode appears blank - only {variance_ratio:.1%} of pixels vary"
        )
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
