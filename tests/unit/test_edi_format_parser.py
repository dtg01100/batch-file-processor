"""Tests for EDI format parser and abstraction layer."""

import json
import os
import pytest
from pathlib import Path

from edi_format_parser import EDIFormatParser, EDIFormatError
import utils


class TestEDIFormatParser:
    """Test EDI format parser functionality."""

    def test_load_default_format(self):
        """Default format can be loaded."""
        parser = EDIFormatParser.get_default_parser()

        assert parser is not None
        assert parser.format_id == "default"
        assert "A" in parser.record_types
        assert "B" in parser.record_types
        assert "C" in parser.record_types

    def test_parse_a_record(self):
        """A records are parsed correctly."""
        parser = EDIFormatParser.get_default_parser()
        line = "A000001INV00001011221251000012345"

        result = parser.parse_line(line)

        assert result is not None
        assert result["record_type"] == "A"
        assert result["cust_vendor"] == "000001"
        assert result["invoice_number"] == "INV0000101"
        assert result["invoice_date"] == "122125"
        assert result["invoice_total"] == "1000012345"

    def test_parse_b_record(self):
        """B records are parsed correctly."""
        parser = EDIFormatParser.get_default_parser()
        line = "B012345678901Product Description 1234561234567890100001000100050000"

        result = parser.parse_line(line)

        assert result is not None
        assert result["record_type"] == "B"
        assert result["upc_number"] == "01234567890"
        assert result["description"] == "1Product Description 1234"
        assert result["vendor_item"] == "561234"
        assert result["unit_cost"] == "567890"
        assert result["combo_code"] == "10"
        assert result["unit_multiplier"] == "000100"
        assert result["qty_of_units"] == "01000"
        assert result["suggested_retail_price"] == "50000"

    def test_parse_c_record(self):
        """C records are parsed correctly."""
        parser = EDIFormatParser.get_default_parser()
        line = "C00100000123"

        result = parser.parse_line(line)

        assert result is not None
        assert result["record_type"] == "C"
        assert result["charge_type"] == "001"

    def test_parse_empty_line(self):
        """Empty lines return None."""
        parser = EDIFormatParser.get_default_parser()

        assert parser.parse_line("") is None
        assert parser.parse_line("   ") is None

    def test_identify_record_type(self):
        """Record types are identified correctly."""
        parser = EDIFormatParser.get_default_parser()

        assert parser.identify_record_type("A000001INV00001011221251000012345") == "A"
        assert parser.identify_record_type("B012345678901Product...") == "B"
        assert parser.identify_record_type("C001...") == "C"
        assert parser.identify_record_type("") is None

    def test_get_record_type_config(self):
        """Record type configurations are accessible."""
        parser = EDIFormatParser.get_default_parser()

        a_config = parser.get_record_type_config("A")
        assert a_config is not None
        assert a_config["name"] == "Invoice Header"
        assert "fields" in a_config

        assert parser.get_record_type_config("Z") is None

    def test_get_field_definition(self):
        """Field definitions are accessible."""
        parser = EDIFormatParser.get_default_parser()

        field = parser.get_field_definition("A", "invoice_number")
        assert field is not None
        assert field["position"] == 7
        assert field["length"] == 10

        assert parser.get_field_definition("A", "nonexistent") is None
        assert parser.get_field_definition("Z", "invoice_number") is None

    def test_validate_file_start(self):
        """File start validation works."""
        parser = EDIFormatParser.get_default_parser()

        assert parser.validate_file_start("A000001...") is True
        assert parser.validate_file_start("B012345...") is False
        assert parser.validate_file_start("") is False

    def test_get_allowed_record_types(self):
        """Allowed record types are returned."""
        parser = EDIFormatParser.get_default_parser()

        allowed = parser.get_allowed_record_types()
        assert "A" in allowed
        assert "B" in allowed
        assert "C" in allowed


class TestUtilsCaptureRecordsWithParser:
    """Test backward compatibility of utils.capture_records."""

    def test_capture_records_still_works(self):
        """Original capture_records function still works."""
        line = "A000001INV00001011221251000012345"

        result = utils.capture_records(line)

        assert result is not None
        assert result["record_type"] == "A"
        assert result["cust_vendor"] == "000001"

    def test_capture_records_b_record(self):
        """B records work with capture_records."""
        line = "B012345678901Product Description 1234561234567890100001000100050000"

        result = utils.capture_records(line)

        assert result is not None
        assert result["record_type"] == "B"
        assert result["upc_number"] == "01234567890"

    def test_capture_records_c_record(self):
        """C records work with capture_records."""
        line = "C00100000123"

        result = utils.capture_records(line)

        assert result is not None
        assert result["record_type"] == "C"

    def test_capture_records_empty_line(self):
        """Empty lines return None."""
        assert utils.capture_records("") is None

    def test_capture_records_with_explicit_parser(self):
        """capture_records accepts explicit parser."""
        parser = EDIFormatParser.get_default_parser()
        line = "A000001INV00001011221251000012345"

        result = utils.capture_records(line, parser)

        assert result is not None
        assert result["record_type"] == "A"


class TestEDIFormatParserRegistry:
    """Test format registry functionality."""

    def test_list_available_formats(self):
        """Available formats can be listed."""
        formats = EDIFormatParser.list_available_formats()

        assert len(formats) >= 1

        default_format = next((f for f in formats if f["id"] == "default"), None)
        assert default_format is not None
        assert "name" in default_format
        assert "version" in default_format

    def test_load_format_by_id(self):
        """Formats can be loaded by ID."""
        parser = EDIFormatParser.load_format("default")

        assert parser is not None
        assert parser.format_id == "default"

    def test_load_nonexistent_format_raises_error(self):
        """Loading nonexistent format raises error."""
        with pytest.raises(EDIFormatError):
            EDIFormatParser.load_format("nonexistent_format")

    def test_format_caching(self):
        """Formats are cached in registry."""
        parser1 = EDIFormatParser.load_format("default")
        parser2 = EDIFormatParser.load_format("default")

        assert parser1 is parser2


class TestEDIFormatConfiguration:
    """Test format configuration validation."""

    def test_invalid_config_missing_field_raises_error(self):
        """Invalid configuration raises error."""
        invalid_config = {"format_id": "test"}

        with pytest.raises(EDIFormatError):
            EDIFormatParser(invalid_config)

    def test_invalid_config_empty_record_types_raises_error(self):
        """Empty record types raises error."""
        invalid_config = {
            "format_id": "test",
            "format_name": "Test",
            "format_version": "1.0",
            "record_types": {},
        }

        with pytest.raises(EDIFormatError):
            EDIFormatParser(invalid_config)


class TestCustomFormatExample:
    """Example test for custom format (demonstrates extensibility)."""

    def test_custom_format_can_be_created(self, tmp_path):
        """Custom formats can be defined and used."""
        custom_format = {
            "format_id": "custom_test",
            "format_name": "Custom Test Format",
            "format_version": "1.0",
            "description": "Test custom format",
            "record_types": {
                "H": {
                    "name": "Header",
                    "identifier": {"position": 0, "length": 1, "value": "H"},
                    "fields": [
                        {
                            "name": "record_type",
                            "position": 0,
                            "length": 1,
                            "type": "string",
                        },
                        {
                            "name": "invoice_id",
                            "position": 1,
                            "length": 8,
                            "type": "string",
                        },
                    ],
                }
            },
            "validation_rules": {
                "file_must_start_with": "H",
                "allowed_record_types": ["H"],
            },
        }

        format_file = tmp_path / "custom_test_format.json"
        with open(format_file, "w") as f:
            json.dump(custom_format, f)

        parser = EDIFormatParser.from_file(str(format_file))

        assert parser.format_id == "custom_test"

        result = parser.parse_line("H12345678")
        assert result is not None
        assert result["record_type"] == "H"
        assert result["invoice_id"] == "12345678"
