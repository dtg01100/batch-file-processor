import decimal
import pytest
from dispatch.services.item_processing import ItemProcessor


class TestItemProcessor:
    def test_convert_to_item_total_positive(self):
        processor = ItemProcessor()
        total, qty = processor.convert_to_item_total("1999", "5")
        assert total == decimal.Decimal("99.95")
        assert qty == 5

    def test_convert_to_item_total_negative_qty(self):
        processor = ItemProcessor()
        total, qty = processor.convert_to_item_total("1999", "-2")
        assert total == decimal.Decimal("-39.98")
        assert qty == -2

    def test_generate_full_upc_11_digits(self):
        processor = ItemProcessor()
        result = processor.generate_full_upc("01234567890")  # 11 digits
        assert len(result) == 12
        assert result[-1] == str(processor._calc_check_digit(result[:-1]))

    def test_generate_full_upc_upce_to_upca(self):
        processor = ItemProcessor()
        result = processor.generate_full_upc("00123457")  # UPC-E
        assert len(result) == 12

    def test_generate_full_upc_empty(self):
        processor = ItemProcessor()
        assert processor.generate_full_upc("") == ""
        assert processor.generate_full_upc("   ") == ""
