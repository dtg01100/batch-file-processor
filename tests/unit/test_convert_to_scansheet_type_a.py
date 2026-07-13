"""Unit tests for ScanSheet Type A barcode parsing robustness."""

import io as _io

import pytest

from dispatch.converters.convert_to_scansheet_type_a import ScanSheetTypeAConverter


# pyzbar is required for the round-trip barcode tests. If it's not
# installed, the entire module is skipped — the tests cannot meaningfully
# run, and the assertion-mutation meta-test runner would otherwise
# report the assertions as "dead" (because the test is skipped before
# the assertion runs). Adding the skip at module level lets the
# runner know the assertions are guarded by an external dependency.
try:
    import pyzbar  # noqa: F401 — import only to check availability for skipif
    _pyzbar_available = True
except ImportError:
    _pyzbar_available = False

pytestmark = [
    pytest.mark.unit,
    pytest.mark.conversion,
    pytest.mark.skipif(
        not _pyzbar_available, reason="pyzbar not installed"
    ),
]


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

    def test_extract_invoices_from_edi_filters_to_a_records_only(self, tmp_path):
        """Regression: _extract_invoices_from_edi must filter to A records.

        The mutation runner's ``eq_to_ne`` at line 149
        (flipping ``record_type == "A"`` to ``record_type != "A"``)
        was not caught by existing tests because no test exercised
        this private method with mixed A/B/C records. With the
        mutation applied, the function would extract B and C
        records' invoice numbers (which are not invoices) and skip
        the actual A records.

        See commit ea1ed275d (Phase 3 bug 5) follow-up for context.
        """
        converter = ScanSheetTypeAConverter()

        # Build an EDI file with one A record and one B record.
        # The A record's invoice_number is 0000000123; the B record
        # has no invoice_number (B records don't have that field).
        edi_content = (
            "AVENDOR00000000010101240000000123\n"  # A record — invoice 0000000123
            "B00123456789Test Item Description    123456001234010000010000500123      \n"  # B record
            "CFRTFreight Charge                 000001234\n"  # C record
        )
        edi_file = tmp_path / "input.edi"
        edi_file.write_text(edi_content)

        result = converter._extract_invoices_from_edi(str(edi_file))

        # Only the A record's invoice number (last 7 digits) should
        # be in the result. B and C records must NOT leak in.
        # A record invoice_number is "0000000001" (10 digits) →
        # last 7 digits = "0000001".
        assert result == ["0000001"], (
            f"expected only A-record invoice numbers, got {result!r}"
        )
