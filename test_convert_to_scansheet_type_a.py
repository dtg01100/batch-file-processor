import os
import tempfile
import pytest
from unittest import mock
import convert_to_scansheet_type_a as ctsa

@pytest.fixture
def fake_settings_dict():
    return {
        "as400_username": "user",
        "as400_password": "pass",
        "as400_address": "address",
        "odbc_driver": "driver"
    }

@pytest.fixture
def fake_parameters_dict():
    return {}

@pytest.fixture
def fake_upc_lookup():
    return {}

@pytest.fixture
def fake_edi_file(tmp_path):
    edi_content = (
        "record_type=A|invoice_number=INV0001234\n"
        "record_type=B|other_field=foo\n"
        "record_type=A|invoice_number=INV0005678\n"
    )
    edi_path = tmp_path / "test.edi"
    edi_path.write_text(edi_content)
    return str(edi_path)

@pytest.fixture
def fake_query_runner():
    class FakeQueryRunner:
        def run_arbitrary_query(self, query):
            # Return a list of tuples as fake DB rows
            return [
                ("012345678905", "Item1", "Desc1", "Pack1", "U/M1", 10, 1.23, 2.34),
                ("098765432109", "Item2", "Desc2", "Pack2", "U/M2", 5, 4.56, 7.89)
            ]
    return FakeQueryRunner()

@pytest.fixture(autouse=True)
def patch_utils_and_query_runner(monkeypatch, fake_query_runner):
    # Patch utils.capture_records to parse the test EDI lines
    def fake_capture_records(line):
        d = {}
        for part in line.strip().split("|"):
            if "=" in part:
                k, v = part.split("=")
                d[k] = v
        return d
    monkeypatch.setattr(ctsa.utils, "capture_records", fake_capture_records)
    monkeypatch.setattr(ctsa, "query_runner", lambda *a, **kw: fake_query_runner)

def test_edi_convert_creates_xlsx(tmp_path, fake_edi_file, fake_settings_dict, fake_parameters_dict, fake_upc_lookup):
    output_filename = str(tmp_path / "output")
    # Patch barcode and PIL image handling to avoid actual image generation
    with mock.patch.object(ctsa, "barcode"), \
         mock.patch.object(ctsa, "pil_ImageOps"), \
         mock.patch.object(ctsa, "pil_Image"), \
         mock.patch.object(ctsa, "OpenPyXlImage"):
        result = ctsa.edi_convert(
            fake_edi_file,
            output_filename,
            fake_settings_dict,
            fake_parameters_dict,
            fake_upc_lookup
        )
    assert result.endswith(".xlsx")
    assert os.path.exists(result)
