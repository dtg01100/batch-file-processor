import io
import csv
import pytest
from unittest.mock import MagicMock, patch
import convert_to_yellowdog_csv

@pytest.fixture
def mock_utils(monkeypatch):
    import datetime
    # Mock all utils functions/classes used in the module
    monkeypatch.setattr("convert_to_yellowdog_csv.utils.invFetcher", MagicMock())
    monkeypatch.setattr("convert_to_yellowdog_csv.utils.datetime_from_invtime", lambda x: datetime.date(2024, 6, 1))
    monkeypatch.setattr("convert_to_yellowdog_csv.utils.convert_to_price", lambda x: f"${x}")
    monkeypatch.setattr("convert_to_yellowdog_csv.utils.dac_str_int_to_int", lambda x: int(x))
    monkeypatch.setattr("convert_to_yellowdog_csv.utils.capture_records", lambda x: eval(x.strip()))
    return convert_to_yellowdog_csv.utils

@pytest.fixture
def fake_inv_fetcher():
    fetcher = MagicMock()
    fetcher.fetch_uom_desc.return_value = "EA"
    fetcher.fetch_cust_name.return_value = "Test Customer"
    fetcher.fetch_po.return_value = "PO123"
    return fetcher

def test_yellowdog_writer_add_and_flush(monkeypatch, mock_utils, fake_inv_fetcher):
    # Patch invFetcher to return our fake_inv_fetcher
    mock_utils.invFetcher.return_value = fake_inv_fetcher

    output = io.StringIO()
    settings_dict = {}

    writer = convert_to_yellowdog_csv.YDogWriter(output, settings_dict)

    # Add an A record (invoice header)
    a_line = {
        "record_type": "A",
        "invoice_date": "20240601",
        "invoice_total": "1000",
        "invoice_number": "12345"
    }
    writer.add_line(a_line)

    # Add a B record (line item)
    b_line = {
        "record_type": "B",
        "description": "Widget",
        "vendor_item": "W123",
        "unit_cost": "500",
        "qty_of_units": "2",
        "unit_multiplier": "1",
        "upc_number": "000111222333"
    }
    writer.add_line(b_line)

    # Add a C record (charge)
    c_line = {
        "record_type": "C",
        "description": "Shipping",
        "amount": "50"
    }
    writer.add_line(c_line)

    # Flush to CSV
    writer.flush_to_csv()

    output.seek(0)
    reader = csv.reader(output)
    rows = list(reader)

    # Header + 2 data rows expected
    assert rows[0][0] == "Invoice Total"
    assert any("Widget" in row for row in rows)
    assert any("Shipping" in row for row in rows)

def test_edi_convert(monkeypatch, mock_utils, fake_inv_fetcher, tmp_path):
    # Patch invFetcher to return our fake_inv_fetcher
    mock_utils.invFetcher.return_value = fake_inv_fetcher

    # Prepare a fake EDI file
    edi_lines = [
        "{'record_type': 'A', 'invoice_date': '20240601', 'invoice_total': '1000', 'invoice_number': '12345'}\n",
        "{'record_type': 'B', 'description': 'Widget', 'vendor_item': 'W123', 'unit_cost': '500', 'qty_of_units': '2', 'unit_multiplier': '1', 'upc_number': '000111222333'}\n",
        "{'record_type': 'C', 'description': 'Shipping', 'amount': '50'}\n"
    ]
    edi_file = tmp_path / "input.edi"
    edi_file.write_text("".join(edi_lines))

    output_filename = str(tmp_path / "output")
    settings_dict = {}
    parameters_dict = {}
    upc_lookup = {}

    result_csv = convert_to_yellowdog_csv.edi_convert(
        str(edi_file), output_filename, settings_dict, parameters_dict, upc_lookup
    )

    with open(result_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows[0][0] == "Invoice Total"
    assert any("Widget" in row for row in rows)
    assert any("Shipping" in row for row in rows)