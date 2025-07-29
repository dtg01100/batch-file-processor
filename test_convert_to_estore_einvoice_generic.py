import os
import tempfile
import csv
from unittest import mock
from decimal import Decimal
import pytest
import convert_to_estore_einvoice_generic as cte

@pytest.fixture
def settings_dict():
    return {
        "as400_username": "user",
        "as400_password": "pass",
        "as400_address": "address",
        "odbc_driver": "driver"
    }

@pytest.fixture
def parameters_dict():
    return {
        "estore_store_number": "123",
        "estore_Vendor_OId": "456",
        "estore_vendor_NameVendorOID": "TestVendor",
        "estore_c_record_OID": "789"
    }

@pytest.fixture
def upc_lookup():
    return {
        111111: ("desc", "012345678905"),
        222222: ("desc2", "098765432109")
    }

@pytest.fixture
def edi_lines():
    # Simulate EDI lines for record types A, B, C
    return [
        "A|invoice_number=1001|invoice_date=010122|invoice_total=0000012345|\n",
        "B|vendor_item=111111|unit_multiplier=1|description=Test Item|upc_number=012345678905|qty_of_units=10|unit_cost=00000100|suggested_retail_price=00000200|parent_item_number=111111|\n",
        "C|description=Service Fee|amount=00000050|\n"
    ]

@pytest.fixture
def mock_utils(monkeypatch):
    class MockUtils:
        @staticmethod
        def capture_records(line):
            if line.startswith("A"):
                return {
                    "record_type": "A",
                    "invoice_number": "1001",
                    "invoice_date": "010122",
                    "invoice_total": "0000012345"
                }
            elif line.startswith("B"):
                if "vendor_item=999999" in line:
                    return {
                        "record_type": "B",
                        "vendor_item": "999999",
                        "unit_multiplier": "1",
                        "description": "Unknown Item",
                        "upc_number": "000000000000",
                        "qty_of_units": "5",
                        "unit_cost": "00000100",
                        "suggested_retail_price": "00000200",
                        "parent_item_number": "999999"
                    }
                else:
                    return {
                        "record_type": "B",
                        "vendor_item": "111111",
                        "unit_multiplier": "1",
                        "description": "Test Item",
                        "upc_number": "012345678905",
                        "qty_of_units": "10",
                        "unit_cost": "00000100",
                        "suggested_retail_price": "00000200",
                        "parent_item_number": "111111"
                    }
            elif line.startswith("C"):
                return {
                    "record_type": "C",
                    "description": "Service Fee",
                    "amount": "00000050"
                }
            return None

        @staticmethod
        def convert_to_price(val):
            return Decimal(val)

        @staticmethod
        def dac_str_int_to_int(val):
            return int(val)

    monkeypatch.setattr(cte, "utils", MockUtils)

@pytest.fixture
def mock_query_runner(monkeypatch):
    class MockQueryRunner:
        def __init__(self, *args, **kwargs):
            pass
        def run_arbitrary_query(self, qry):
            if "ohhst" in qry:
                return [("PO123", "CUST456")]
            elif "odhst" in qry:
                return [(1, "Each"), (2, "Case")]
            elif "dsanrep" in qry:
                return [("HI",)]
            return []
    monkeypatch.setattr(cte, "query_runner", MockQueryRunner)

def test_invfetcher_fetch_po_and_cust(settings_dict, mock_query_runner):
    fetcher = cte.invFetcher(settings_dict)
    po = fetcher.fetch_po("1001")
    cust = fetcher.fetch_cust("1001")
    assert po == "PO123"
    assert cust == "CUST456"

def test_invfetcher_fetch_uom_desc(settings_dict, mock_query_runner):
    fetcher = cte.invFetcher(settings_dict)
    desc = fetcher.fetch_uom_desc(111111, 1, 0, 1001)
    assert desc == "Case" or desc == "Each"

def test_edi_convert_creates_csv(tmp_path, settings_dict, parameters_dict, upc_lookup, edi_lines, mock_utils, mock_query_runner):
    edi_file = tmp_path / "edi.txt"
    with open(edi_file, "w") as f:
        for line in edi_lines:
            f.write(line)
    output_filename_initial = tmp_path / "output.csv"
    output_file = cte.edi_convert(
        str(edi_file),
        str(output_filename_initial),
        settings_dict,
        parameters_dict,
        upc_lookup
    )
    assert os.path.exists(output_file)
    with open(output_file, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        # Header + 2 data rows expected
        assert rows[0][0] == "Store #"
        assert any("Test Item" in row for row in rows[1:])
        assert any("Service Fee" in row for row in rows[1:])

def test_edi_convert_handles_missing_upc(tmp_path, settings_dict, parameters_dict, mock_utils, mock_query_runner):
    edi_file = tmp_path / "edi_missing_upc.txt"
    # B record with unknown vendor_item
    edi_lines = [
        "A|invoice_number=1001|invoice_date=010122|invoice_total=0000012345|\n",
        "B|vendor_item=999999|unit_multiplier=1|description=Unknown Item|upc_number=000000000000|qty_of_units=5|unit_cost=00000100|suggested_retail_price=00000200|parent_item_number=999999|\n"
    ]
    with open(edi_file, "w") as f:
        for line in edi_lines:
            f.write(line)
    output_filename_initial = tmp_path / "output_missing_upc.csv"
    upc_lookup = {}
    output_file = cte.edi_convert(
        str(edi_file),
        str(output_filename_initial),
        settings_dict,
        parameters_dict,
        upc_lookup
    )
    assert os.path.exists(output_file)
    with open(output_file, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        print(rows)
        assert any("Unknown Item" in row for row in rows[1:])