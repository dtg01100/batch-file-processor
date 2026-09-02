"""Tests for the typed record proxy (Phase 11.1)."""

import pytest

from core.edi.edi_parser import ARecord, BRecord, CRecord
from webapp.pipeline.converters.typed_records import (
    TypedRecordProxy,
    parse_typed_record,
)


class TestTypedRecordProxy:
    def test_attribute_access(self):
        record = ARecord(
            record_type="A",
            cust_vendor="VENDOR",
            invoice_number="INV001",
            invoice_date="010125",
            invoice_total="0000010000",
        )
        proxy = TypedRecordProxy(record=record)
        assert proxy.invoice_number == "INV001"
        assert proxy.invoice_date == "010125"
        assert proxy.invoice_total == "0000010000"

    def test_dict_style_access(self):
        record = ARecord(
            record_type="A",
            cust_vendor="VENDOR",
            invoice_number="INV001",
            invoice_date="010125",
            invoice_total="0000010000",
        )
        proxy = TypedRecordProxy(record=record)
        assert proxy["invoice_number"] == "INV001"
        assert proxy["invoice_date"] == "010125"

    def test_get_method(self):
        record = ARecord(
            record_type="A",
            cust_vendor="VENDOR",
            invoice_number="",
            invoice_date="",
            invoice_total="",
        )
        proxy = TypedRecordProxy(record=record)
        assert proxy.get("invoice_number", "DEFAULT") == ""
        assert proxy.get("missing", "DEFAULT") == "DEFAULT"

    def test_contains(self):
        record = ARecord(
            record_type="A",
            cust_vendor="VENDOR",
            invoice_number="INV001",
            invoice_date="010125",
            invoice_total="0",
        )
        proxy = TypedRecordProxy(record=record)
        assert "invoice_number" in proxy
        assert "nonexistent" not in proxy


class TestParseTypedRecord:
    def test_a_record(self):
        d = {
            "record_type": "A",
            "cust_vendor": "VENDOR",
            "invoice_number": "INV001",
            "invoice_date": "010125",
            "invoice_total": "0000010000",
        }
        proxy = parse_typed_record(d)
        assert isinstance(proxy.record, ARecord)
        assert proxy.invoice_number == "INV001"

    def test_b_record(self):
        d = {
            "record_type": "B",
            "upc_number": "01234567890",
            "description": "Test",
            "vendor_item": "123456",
            "unit_cost": "000100",
            "combo_code": "01",
            "unit_multiplier": "000001",
            "qty_of_units": "00010",
            "suggested_retail_price": "00199",
            "price_multi_pack": "001",
            "parent_item_number": "000000",
        }
        proxy = parse_typed_record(d)
        assert isinstance(proxy.record, BRecord)
        assert proxy.upc_number == "01234567890"
        assert proxy.unit_cost == "000100"

    def test_c_record(self):
        d = {
            "record_type": "C",
            "charge_type": "TAB",
            "description": "Sales Tax",
            "amount": "000010000",
        }
        proxy = parse_typed_record(d)
        assert isinstance(proxy.record, CRecord)
        assert proxy.charge_type == "TAB"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown record_type"):
            parse_typed_record({"record_type": "X"})

    def test_missing_fields_default_empty(self):
        """Defensive: a partial dict yields a typed record with empty fields."""
        proxy = parse_typed_record({"record_type": "A"})
        assert isinstance(proxy.record, ARecord)
        assert proxy.invoice_number == ""
        assert proxy.cust_vendor == ""
