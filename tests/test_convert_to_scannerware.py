import os
import tempfile
import pytest
import convert_to_scannerware
# Patch utils.capture_records for controlled input parsing
class DummyUtils:
    @staticmethod
    def capture_records(line):
        # Simulate parsing for A, B, C records
        if line.startswith("A"):
            return {
                'record_type': 'A',
                'invoice_number': 'INV1234567',
                'invoice_date': '010124',
                'invoice_total': '00012345'
            }
        elif line.startswith("B"):
            return {
                'record_type': 'B',
                'upc_number': '123456789012',
                'description': 'Test Product Description',
                'vendor_item': 'VEND123',
                'unit_cost': '000100',
                'unit_multiplier': '01',
                'qty_of_units': '10',
                'suggested_retail_price': '000150'
            }
        elif line.startswith("C"):
            return {
                'record_type': 'C',
                'description': 'Charge Description',
                'amount': '00050'
            }
        return {}

@pytest.fixture(autouse=True)
def patch_utils(monkeypatch):
    monkeypatch.setattr(convert_to_scannerware, "utils", DummyUtils)

@pytest.fixture
def parameters_dict():
    return {
        'a_record_padding': 'PAD',
        'append_a_records': "True",
        'a_record_append_text': 'APPEND',
        'force_txt_file_ext': "True",
        'invoice_date_offset': 0
    }

def test_edi_convert_a_record(parameters_dict):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        output_path = os.path.join(tmpdir, "output")
        # Write a single A record
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("A|dummy|data\n")
        result_file = convert_to_scannerware.edi_convert(
            input_path, output_path, {}, parameters_dict, None
        )
        assert result_file.endswith(".txt")
        with open(result_file, "rb") as f:
            content = f.read().decode()
        # Check for expected fields in output
        assert content.startswith("A")
        assert "PAD" in content
        assert "1234567" in content
        assert "010124" in content
        assert "00012345" in content
        assert "APPEND" in content

def test_edi_convert_b_record(parameters_dict):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        output_path = os.path.join(tmpdir, "output")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("B|dummy|data\n")
        result_file = convert_to_scannerware.edi_convert(
            input_path, output_path, {}, parameters_dict, None
        )
        with open(result_file, "rb") as f:
            content = f.read().decode()
        assert content.startswith("B")
        assert "123456789012" in content
        assert "Test Product Description"[:25] in content
        assert "VEND123" in content
        assert "000100" in content
        assert "01" in content
        assert "10" in content
        assert "000150" in content

def test_edi_convert_c_record(parameters_dict):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        output_path = os.path.join(tmpdir, "output")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("C|dummy|data\n")
        result_file = convert_to_scannerware.edi_convert(
            input_path, output_path, {}, parameters_dict, None
        )
        with open(result_file, "rb") as f:
            content = f.read().decode()
        assert content.startswith("C")
        assert "Charge Description" in content
        assert "00050" in content

def test_edi_convert_invoice_date_offset(parameters_dict):
    params = parameters_dict.copy()
    params['invoice_date_offset'] = 1  # Add one day
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        output_path = os.path.join(tmpdir, "output")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("A|dummy|data\n")
        result_file = convert_to_scannerware.edi_convert(
            input_path, output_path, {}, params, None
        )
        with open(result_file, "rb") as f:
            content = f.read().decode()
        # 010124 + 1 day = 010224
        assert "010224" in content

def test_edi_convert_force_txt_file_ext_false(parameters_dict):
    params = parameters_dict.copy()
    params['force_txt_file_ext'] = "False"
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.txt")
        output_path = os.path.join(tmpdir, "output")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("A|dummy|data\n")
        result_file = convert_to_scannerware.edi_convert(
            input_path, output_path, {}, params, None
        )
        assert result_file == output_path