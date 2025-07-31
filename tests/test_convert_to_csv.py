import os
import csv
import tempfile
import pytest
from unittest import mock
import convert_to_csv
@pytest.fixture
def sample_parameters():
    return {
        'calculate_upc_check_digit': "True",
        'include_a_records': "True",
        'include_c_records': "True",
        'include_headers': "True",
        'filter_ampersand': "True",
        'pad_a_records': "False",
        'a_record_padding': "PADDED",
        'override_upc_bool': True,
        'override_upc_level': 1,
        'override_upc_category_filter': "ALL",
        'retail_uom': False,
    }

@pytest.fixture
def sample_upc_lut():
    # vendor_item: (category, upc1, upc2)
    return {
        123: ("FOOD", "00000000001", "000000000012"),
        456: ("DRINK", "00000000002", "000000000022"),
    }

@pytest.fixture
def sample_edi_lines():
    # A, B, and C records
    return [
        "A|VENDOR1|INV123|20240101|10000\n",
        "B|123|000123|000100|000500|000200|000001|Test & Product|000100|000200\n",
        "C|CHG|Some charge|00500\n"
    ]

@pytest.fixture
def sample_utils():
    # Patch utils functions used in convert_to_csv
    utils = mock.Mock()
    # A record
    utils.capture_records.side_effect = [
        {'record_type': 'A', 'cust_vendor': 'VENDOR1', 'invoice_number': 'INV123', 'invoice_date': '20240101', 'invoice_total': '10000'},
        # B record
        {
            'record_type': 'B',
            'vendor_item': '123',
            'upc_number': '00000000001',
            'qty_of_units': '00010',
            'unit_cost': '000500',
            'suggested_retail_price': '000700',
            'description': 'Test & Product ',
            'unit_multiplier': '000001'
        },
        # C record
        {'record_type': 'C', 'charge_type': 'CHG', 'description': 'Some charge', 'amount': '00500'}
    ]
    utils.calc_check_digit.return_value = 5
    utils.convert_UPCE_to_UPCA.return_value = "000000000000"
    return utils

def test_edi_convert_creates_csv(tmp_path, sample_parameters, sample_upc_lut, sample_edi_lines, sample_utils):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"
    edi_file.write_text("".join(sample_edi_lines))

    with mock.patch("convert_to_csv.utils", sample_utils):
        result_csv = convert_to_csv.edi_convert(
            str(edi_file),
            str(output_file),
            {},
            sample_parameters,
            sample_upc_lut
        )

    # Check file exists
    assert os.path.exists(result_csv)

    # Read CSV and check contents
    with open(result_csv, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Header
    assert rows[0] == ["UPC", "Qty. Shipped", "Cost", "Suggested Retail", "Description", "Case Pack", "Item Number"]
    # "A" record
    assert rows[1][0] == "A"
    # "B" record
    assert rows[2][0].startswith("\t") or rows[2][0] == "00000000001"
    assert "Test AND Product" in rows[2]
    # "C" record
    assert rows[3][0] == "C"

def test_edi_convert_handles_no_headers(tmp_path, sample_parameters, sample_upc_lut, sample_edi_lines, sample_utils):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"
    edi_file.write_text("".join(sample_edi_lines))
    params = dict(sample_parameters)
    params['include_headers'] = "False"

    with mock.patch("convert_to_csv.utils", sample_utils):
        result_csv = convert_to_csv.edi_convert(
            str(edi_file),
            str(output_file),
            {},
            params,
            sample_upc_lut
        )

    with open(result_csv, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # No header row
    assert rows[0][0] == "A"

def test_edi_convert_filters_ampersand(tmp_path, sample_parameters, sample_upc_lut, sample_edi_lines, sample_utils):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"
    edi_file.write_text("".join(sample_edi_lines))
    params = dict(sample_parameters)
    params['filter_ampersand'] = "True"

    with mock.patch("convert_to_csv.utils", sample_utils):
        result_csv = convert_to_csv.edi_convert(
            str(edi_file),
            str(output_file),
            {},
            params,
            sample_upc_lut
        )

    with open(result_csv, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # "AND" should replace "&"
    assert any("AND" in cell for row in rows for cell in row)

def test_edi_convert_pad_arec(tmp_path, sample_parameters, sample_upc_lut, sample_edi_lines, sample_utils):
    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"
    edi_file.write_text("".join(sample_edi_lines))
    params = dict(sample_parameters)
    params['pad_a_records'] = "True"
    params['a_record_padding'] = "PADDED"

    with mock.patch("convert_to_csv.utils", sample_utils):
        result_csv = convert_to_csv.edi_convert(
            str(edi_file),
            str(output_file),
            {},
            params,
            sample_upc_lut
        )

    with open(result_csv, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # "A" record should have padded value
    assert "PADDED" in rows[1]

def test_edi_convert_handles_blank_upc(tmp_path, sample_parameters, sample_upc_lut, sample_edi_lines, sample_utils):
    # Patch utils.capture_records to return a B record with blank upc_number
    blank_upc_utils = mock.Mock()
    blank_upc_utils.capture_records.side_effect = [
        {'record_type': 'B',
         'vendor_item': '999',
         'upc_number': '',
         'qty_of_units': '00010',
         'unit_cost': '000500',
         'suggested_retail_price': '000700',
         'description': 'Test Product ',
         'unit_multiplier': '000001'}
    ]
    blank_upc_utils.calc_check_digit.return_value = 5
    blank_upc_utils.convert_UPCE_to_UPCA.return_value = "000000000000"

    edi_file = tmp_path / "input.edi"
    output_file = tmp_path / "output"
    edi_file.write_text("B|999|000999|000100|000500|000200|000001|Test Product|000100|000200\n")

    with mock.patch("convert_to_csv.utils", blank_upc_utils):
        result_csv = convert_to_csv.edi_convert(
            str(edi_file),
            str(output_file),
            {},
            sample_parameters,
            sample_upc_lut
        )

    with open(result_csv, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Should not crash, upc_number should be blank or as per logic
    assert rows[1][0] == ""
