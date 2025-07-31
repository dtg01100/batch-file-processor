import pytest

@pytest.fixture
def sample_edi_lines():
    return [
        "B|123456|00010|000250|000001|Widget|000002|SomeDesc\n",
        "B|654321|00005|000500|000001|Gadget|000001|OtherDesc\n",
        "C|not_b_record|should_skip\n",
    ]

@pytest.fixture
def sample_edi_lines_bad():
    return [
        "B|bad|bad|bad|bad|bad|bad\n",
        "C|not_b_record|should_skip\n",
    ]

@pytest.fixture
def upc_lookup():
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
