import os
import csv
import tempfile
import pytest
import convert_to_stewarts_custom

@pytest.fixture
def mock_utils(monkeypatch):
    class DummyUtils:
        @staticmethod
        def capture_records(line):
            # Simulate header and two item lines
            if "HEADER" in line:
                return {
                    "record_type": "A",
                    "invoice_number": "000123",
                    "invoice_total": "00001234"
                }
            elif "ITEM" in line:
                return {
                    "record_type": "B",
                    "vendor_item": "1001",
                    "description": "Test Item",
                    "upc_number": "12345678901",
                    "qty_of_units": "2",
                    "unit_cost": "0000123",
                    "unit_multiplier": "1"
                }
            elif "CHARGE" in line:
                return {
                    "record_type": "C",
                    "description": "Shipping",
                    "amount": "0000050"
                }
            return None

        @staticmethod
        def calc_check_digit(upc):
            return "5"

        @staticmethod
        def convert_UPCE_to_UPCA(upce):
            return "000000000000"

    monkeypatch.setattr(convert_to_stewarts_custom, "utils", DummyUtils)

@pytest.fixture
def mock_query_runner(monkeypatch):
    class DummyQueryObject:
        def run_arbitrary_query(self, query):
            if "select distinct" in query:
                # UOM lookup
                return [
                    ("1001", "1", "EA"),
                ]
            else:
                # Header fields
                return [(
                    "Salesperson", "20240101", "NET30", "30", "Active", "123", "Test Customer", "1",
                    "123 Main St", "Townsville", "TS", "12345", "5551234567", "cust@email.com", "cust2@email.com",
                    None, None, None, None, None, None, None, None, None, None
                )]
    monkeypatch.setattr(convert_to_stewarts_custom, "query_runner", lambda *a, **kw: DummyQueryObject())

@pytest.fixture
def edi_file(tmp_path):
    edi_content = [
        "HEADER\n",
        "ITEM\n",
        "CHARGE\n"
    ]
    edi_path = tmp_path / "test.edi"
    with open(edi_path, "w") as f:
        f.writelines(edi_content)
    return str(edi_path)

def test_edi_convert_creates_csv(tmp_path, mock_utils, mock_query_runner, edi_file):
    output_filename = str(tmp_path / "output")
    settings_dict = {
        "as400_username": "user",
        "as400_password": "pass",
        "as400_address": "address",
        "odbc_driver": "driver"
    }
    parameters_dict = {}
    upc_dict = {}

    result_csv = convert_to_stewarts_custom.edi_convert(
        edi_file, output_filename, settings_dict, parameters_dict, upc_dict
    )

    assert os.path.exists(result_csv)
    with open(result_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        # Check header and some data rows
        assert rows[0][0] == "Invoice Details"
        assert any("Test Item" in row for row in rows)
        assert any("Shipping" in row for row in rows)
        assert any("Total:" in row for row in rows)

def test_edi_convert_raises_on_missing_header(monkeypatch, tmp_path, mock_utils, mock_query_runner):
    # Patch utils.capture_records to return header with missing invoice_number
    class DummyUtils:
        @staticmethod
        def capture_records(line):
            return {"record_type": "A", "invoice_number": "", "invoice_total": "00001234"}
        @staticmethod
        def calc_check_digit(upc): return "5"
        @staticmethod
        def convert_UPCE_to_UPCA(upce): return "000000000000"
    monkeypatch.setattr(convert_to_stewarts_custom, "utils", DummyUtils)

    edi_path = tmp_path / "test.edi"
    with open(edi_path, "w") as f:
        f.write("HEADER\n")

    output_filename = str(tmp_path / "output")
    settings_dict = {
        "as400_username": "user",
        "as400_password": "pass",
        "as400_address": "address",
        "odbc_driver": "driver"
    }
    parameters_dict = {}
    upc_dict = {}

    # Patch query_runner to return empty header_fields
    class DummyQueryObject:
        def run_arbitrary_query(self, query):
            return []
    monkeypatch.setattr(convert_to_stewarts_custom, "query_runner", lambda *a, **kw: DummyQueryObject())

    with pytest.raises(convert_to_stewarts_custom.CustomerLookupError):
        convert_to_stewarts_custom.edi_convert(
            str(edi_path), output_filename, settings_dict, parameters_dict, upc_dict
        )