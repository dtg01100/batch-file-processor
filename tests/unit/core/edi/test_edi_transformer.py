"""Unit tests for EDI transformer utility functions."""

from decimal import Decimal

import pytest

from core.edi.edi_transformer import (
    convert_to_price,
    convert_to_price_decimal,
    dac_str_int_to_int,
    detect_invoice_is_credit,
)


class TestDacStrIntToInt:
    """Tests for dac_str_int_to_int."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", 0),
            ("   ", 0),
            ("0", 0),
            ("123", 123),
            ("-123", -123),
            ("abc", 0),
        ],
    )
    def test_conversion(self, value, expected):
        """Converts numeric strings and safely handles invalid ones."""
        assert dac_str_int_to_int(value) == expected


class TestPriceConverters:
    """Tests for convert_to_price and convert_to_price_decimal."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("000123", "1.23"),
            ("000000", "0.00"),
            ("05", "0.05"),
            ("5", "0.5"),
        ],
    )
    def test_convert_to_price(self, value, expected):
        """Price string conversion inserts decimal and trims leading zeros."""
        assert convert_to_price(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("000123", Decimal("1.23")),
            ("000000", Decimal("0.00")),
            ("05", Decimal("0.05")),
        ],
    )
    def test_convert_to_price_decimal(self, value, expected):
        """Decimal conversion returns Decimal for valid input."""
        assert convert_to_price_decimal(value) == expected

    def test_convert_to_price_decimal_invalid_returns_zero(self):
        """Invalid decimal format returns 0 fallback."""
        assert convert_to_price_decimal("abcd") == 0


class TestDetectInvoiceIsCredit:
    """Tests for detect_invoice_is_credit."""

    def test_detects_regular_invoice(self, tmp_path):
        """Positive total is not a credit."""
        edi_path = tmp_path / "regular.inv"
        edi_path.write_text("AVENDOR00000000010101240000000123\n", encoding="utf-8")

        assert detect_invoice_is_credit(str(edi_path)) is False

    def test_detects_credit_invoice(self, tmp_path):
        """Negative total is identified as credit."""
        edi_path = tmp_path / "credit.inv"
        edi_path.write_text("AVENDOR0000000001010124-000000123\n", encoding="utf-8")

        assert detect_invoice_is_credit(str(edi_path)) is True

    def test_invalid_first_record_raises_value_error(self, tmp_path):
        """First record that is not A raises ValueError."""
        edi_path = tmp_path / "invalid_first_record.inv"
        edi_path.write_text(
            "B00123456789Test Item Description    123456001234010000010000500123      \n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Invoice Type Detection"):
            detect_invoice_is_credit(str(edi_path))
