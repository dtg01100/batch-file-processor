import os
import csv
import pytest
from decimal import Decimal
from unittest import mock
import convert_to_simplified_csv

@pytest.fixture
def sample_edi_lines():
    # Simulate EDI file lines
    return [
        "B|123456|00010|000250|000001|Widget|000002|SomeDesc\n",  # valid
        "B|654321|00005|000500|000001|Gadget|000001|OtherDesc\n",  # valid
        "C|not_b_record|should_skip\n",  # not B record
    ]

@pytest.fixture
def sample_edi_lines_bad():
    # Simulate EDI file lines with a bad B record
    return [
        "B|bad|bad|bad|bad|bad|bad\n",  # invalid B record
        "C|not_b_record|should_skip\n",  # not B record
    ]

@pytest.fixture
def upc_lookup():
    # vendor_item: (unused, upc)
    return {
        123456: (None, "01234567890"),
        654321: (None, "09876543210"),
    }

@pytest.fixture
def settings_dict():
    return {}

@pytest.fixture
def parameters_dict():
    return {
        "retail_uom": True,
        "include_headers": "True",
        "include_item_numbers": True,
        "include_item_description": True,
        "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,description,vendor_item"
    }

@pytest.fixture
def mock_capture_records():
    # Patch utils.capture_records to parse our fake EDI lines
    def _capture_records(line):
        if line.startswith("B|"):
            parts = line.strip().split("|")
            if len(parts) < 7:
                return None
            try:
                return {
                    "record_type": "B",
                    "vendor_item": parts[1],
                    "qty_of_units": parts[2],
                    "unit_cost": parts[3],
                    "description": parts[5],
                    "unit_multiplier": parts[4],
                    "upc_number": "",
                }
            except Exception:
                return None
        return None
    return _capture_records

def test_edi_convert_creates_csv(tmp_path, sample_edi_lines, upc_lookup, settings_dict, parameters_dict, mock_capture_records):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"

    # Write sample EDI lines to file
    with open(edi_file, "w", encoding="utf-8") as f:
        f.writelines(sample_edi_lines)

    # Patch utils.capture_records
    with mock.patch("convert_to_simplified_csv.utils.capture_records", side_effect=mock_capture_records):
        result_csv = convert_to_simplified_csv.edi_convert(
            str(edi_file),
            str(output_file),
            settings_dict,
            parameters_dict,
            upc_lookup
        )

    # Check output file exists
    assert os.path.exists(result_csv)

    # Read and check CSV content
    with open(result_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)


    # Should include header + 2 valid B records
    assert rows[0] == ["UPC", "Quantity", "Cost", "Item Description", "Item Number"]
    # Check that UPC and Item Number are correct for first record
    assert rows[1][0].strip() == "01234567890"
    assert rows[1][4] == "123456"
    # Check that UPC and Item Number are correct for second record
    assert rows[2][0].strip() == "09876543210"
    assert rows[2][4] == "654321"
    # Should only have 3 rows (header + 2 valid)
    assert len(rows) == 3

def test_edi_convert_no_headers(tmp_path, sample_edi_lines, upc_lookup, settings_dict, parameters_dict, mock_capture_records):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"

    parameters_dict_no_headers = parameters_dict.copy()
    parameters_dict_no_headers["include_headers"] = "False"

    with open(edi_file, "w", encoding="utf-8") as f:
        f.writelines(sample_edi_lines)

    with mock.patch("convert_to_simplified_csv.utils.capture_records", side_effect=mock_capture_records):
        result_csv = convert_to_simplified_csv.edi_convert(
            str(edi_file),
            str(output_file),
            settings_dict,
            parameters_dict_no_headers,
            upc_lookup
        )

    with open(result_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Should not include header, only 2 valid B records
    assert len(rows) == 2
    assert rows[0][4] == "123456"
    assert rows[1][4] == "654321"

def test_edi_convert_missing_upc(tmp_path, sample_edi_lines, settings_dict, parameters_dict, mock_capture_records):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"

    # Remove upc_lookup for one item to test missing UPC
    upc_lookup = {654321: (None, "09876543210")}

    with open(edi_file, "w", encoding="utf-8") as f:
        f.writelines(sample_edi_lines)

    with mock.patch("convert_to_simplified_csv.utils.capture_records", side_effect=mock_capture_records):
        result_csv = convert_to_simplified_csv.edi_convert(
            str(edi_file),
            str(output_file),
            settings_dict,
            parameters_dict,
            upc_lookup
        )

    with open(result_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # First record should have blank UPC
    assert rows[1][0] == "           "
    # Second record should have correct UPC
    assert rows[2][0].strip() == "09876543210"

def test_edi_convert_bad_b_record(tmp_path, sample_edi_lines_bad, upc_lookup, settings_dict, parameters_dict, mock_capture_records):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"

    # Write sample EDI lines with a bad B record
    with open(edi_file, "w", encoding="utf-8") as f:
        f.writelines(sample_edi_lines_bad)
    try:
        with mock.patch("convert_to_simplified_csv.utils.capture_records", side_effect=mock_capture_records):
            result_csv = convert_to_simplified_csv.edi_convert(
                str(edi_file),
                str(output_file),
                settings_dict,
                parameters_dict,
                upc_lookup
            )
        assert False, "Expected ValueError due to bad B record"
    except ValueError as e:
        assert str(e) == "invalid literal for int() with base 10: 'bad'"
