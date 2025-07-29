import os
import tempfile
import pytest
import edi_tweaks
import sys
from unittest.mock import MagicMock, patch

# Patch utils and query_runner dependencies

@pytest.fixture
def mock_utils(monkeypatch):
    mock_utils = MagicMock()
    mock_utils.capture_records.side_effect = [
        {
            'record_type': 'A',
            'cust_vendor': 'VEND',
            'invoice_number': '123456',
            'invoice_date': '010124',
            'invoice_total': '000100'
        },
        {
            'record_type': 'B',
            'upc_number': '12345678901',
            'description': 'ITEMDESC',
            'vendor_item': '1001',
            'unit_cost': '000100',
            'combo_code': 'C',
            'unit_multiplier': '000002',
            'qty_of_units': '00003',
            'suggested_retail_price': '000200',
            'price_multi_pack': '000000',
            'parent_item_number': ''
        },
        {
            'record_type': 'C',
            'other': 'data'
        }
    ]
    mock_utils.calc_check_digit.return_value = 5
    mock_utils.convert_UPCE_to_UPCA.return_value = '123456789012'
    sys.modules['utils'] = mock_utils
    return mock_utils

@pytest.fixture
def mock_query_runner(monkeypatch):
    mock_query = MagicMock()
    mock_query.run_arbitrary_query.side_effect = [
        [('PO123',)],  # For poFetcher
        [(100, 50)]    # For cRecGenerator
    ]
    mock_query_runner = MagicMock(return_value=mock_query)
    sys.modules['query_runner'] = mock_query_runner
    return mock_query_runner

@pytest.fixture
def minimal_settings():
    return {
        "as400_username": "user",
        "as400_password": "pass",
        "as400_address": "address",
        "odbc_driver": "driver"
    }

@pytest.fixture
def minimal_parameters():
    return {
        'pad_a_records': "False",
        'a_record_padding': "",
        'a_record_padding_length': 0,
        'append_a_records': "False",
        'a_record_append_text': "",
        'invoice_date_custom_format': False,
        'invoice_date_custom_format_string': "",
        'force_txt_file_ext': "False",
        'calculate_upc_check_digit': "False",
        'invoice_date_offset': 0,
        'retail_uom': False,
        'override_upc_bool': False,
        'override_upc_level': 1,
        'override_upc_category_filter': "ALL",
        'split_prepaid_sales_tax_crec': False
    }

@pytest.fixture
def upc_dict():
    return {
        1001: ["CAT1", "12345678901", "ALTUPC"]
    }

def test_edi_tweak_basic(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    # Prepare a fake EDI input file
    edi_lines = [
        "AVEND1234567890120101240000010000\n",
        "B12345678901ITEMDESC1001000002 00003 000200000000\n",
        "CTABSales Tax000000100\n"
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        with open(edi_input, "w") as f:
            f.writelines(edi_lines)

        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            minimal_parameters,
            upc_dict
        )

        assert os.path.exists(result)
        with open(result, "r") as f:
            output_lines = f.readlines()
        # Should have 3 lines (A, B, C)
        assert len(output_lines) == 3
        assert output_lines[0].startswith("A")
        assert output_lines[1].startswith("B")
        assert output_lines[2].startswith("C")

def test_edi_tweak_force_txt(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['force_txt_file_ext'] = "True"
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output")
        with open(edi_input, "w") as f:
            f.write("AVEND1234567890120101240000010000\n")
        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            params,
            upc_dict
        )
        assert result.endswith(".txt")
        assert os.path.exists(result)

def test_edi_tweak_append_arec(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['append_a_records'] = "True"
    params['a_record_append_text'] = "PO:%po_str%"
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        with open(edi_input, "w") as f:
            f.write("AVEND1234567890120101240000010000")
        # Patch query_runner.query_runner to use the mock
        with patch("query_runner.query_runner", mock_query_runner):
            result = edi_tweaks.edi_tweak(
                edi_input,
                edi_output,
                minimal_settings,
                params,
                upc_dict
            )
        with open(result, "r") as f:
            line = f.readline()
        assert "PO:PO123" in line

def test_edi_tweak_pad_arec(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['pad_a_records'] = "True"
    params['a_record_padding'] = "PAD"
    params['a_record_padding_length'] = 8
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        with open(edi_input, "w") as f:
            f.write("AVEND1234567890120101240000010000\n")
        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            params,
            upc_dict
        )
        with open(result, "r") as f:
            line = f.readline()
        assert "PAD     " in line

def test_edi_tweak_invoice_date_offset(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['invoice_date_offset'] = 1
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        with open(edi_input, "w") as f:
            f.write("AVEND1234567890120101240000010000\n")
        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            params,
            upc_dict
        )
        with open(result, "r") as f:
            line = f.readline()
        # The date should be offset by 1 day (010124 -> 010224)
        assert "010224" in line

def test_edi_tweak_invoice_date_custom_format(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['invoice_date_custom_format'] = True
    params['invoice_date_custom_format_string'] = "%Y-%m-%d"
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        with open(edi_input, "w") as f:
            f.write("AVEND1234567890120101240000010000\n")
        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            params,
            upc_dict
        )
        with open(result, "r") as f:
            line = f.readline()
        assert "2024-01-01" in line

def test_edi_tweak_override_upc(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['override_upc_bool'] = True
    params['override_upc_level'] = 1
    params['override_upc_category_filter'] = "ALL"
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        b_record = (
            "B" +
            "12345678901" +                # upc_number (11)
            "ITEMDESC".ljust(25) +         # description (25)
            "1001  " +                     # vendor_item (6, padded)
            "000100" +                     # unit_cost (6)
            "C " +                         # combo_code (2, padded)
            "000002" +                     # unit_multiplier (6)
            "00003" +                      # qty_of_units (5)
            "00020" +                      # suggested_retail_price (5)
            "000" +                        # price_multi_pack (3)
            "000000"                       # parent_item_number (6)
            + "\n"
        )
        with open(edi_input, "w") as f:
            f.write(b_record)
        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            params,
            upc_dict
        )
        with open(result, "r") as f:
            line = f.readline()
        assert upc_dict[1001][1] in line

def test_edi_tweak_calc_upc(monkeypatch, mock_utils, mock_query_runner, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['calculate_upc_check_digit'] = "True"
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        b_record = (
            "B" +
            "12345678901" +                # upc_number (11)
            "ITEMDESC".ljust(25) +         # description (25)
            "1001  " +                     # vendor_item (6, padded)
            "000100" +                     # unit_cost (6)
            "C " +                         # combo_code (2, padded)
            "000002" +                     # unit_multiplier (6)
            "00003" +                      # qty_of_units (5)
            "00020" +                      # suggested_retail_price (5)
            "000" +                        # price_multi_pack (3)
            "000000"                       # parent_item_number (6)
            + "\n"
        )
        with open(edi_input, "w") as f:
            f.write(b_record)
        result = edi_tweaks.edi_tweak(
            edi_input,
            edi_output,
            minimal_settings,
            params,
            upc_dict
        )
        with open(result, "r") as f:
            line = f.readline()
        # Should append check digit (mocked as 5)
        assert "123456789012" in line

def test_edi_tweak_split_prepaid_sales_tax_crec(monkeypatch, mock_utils, minimal_settings, minimal_parameters, upc_dict):
    params = minimal_parameters.copy()
    params['split_prepaid_sales_tax_crec'] = True
    edi_lines = [
        "AVEND1234567890120101240000010000\n",
        "B12345678901ITEMDESC1001000002 00003 000200000000\n",
        "CTABSales Tax000000100\n"
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        edi_input = os.path.join(tmpdir, "input.edi")
        edi_output = os.path.join(tmpdir, "output.edi")
        with open(edi_input, "w") as f:
            f.writelines(edi_lines)
        # Custom mock query runner for this test
        class CustomMockQuery:
            def run_arbitrary_query(self, query):
                return [
                    (60, 40),
                ]
        class CustomMockQueryRunner:
            def __init__(self, *a, **kw):
                pass
            def __call__(self, *a, **kw):
                return CustomMockQuery()
        with patch("edi_tweaks.query_runner", CustomMockQueryRunner()):
            result = edi_tweaks.edi_tweak(
                edi_input,
                edi_output,
                minimal_settings,
                params,
                upc_dict
            )
        with open(result, "r") as f:
            lines = f.readlines()
        # Should write two CTAB lines for split tax (queried)
        ctab_lines = [l for l in lines if l.startswith("C")]
        print(ctab_lines)
        assert any("Prepaid Sales Tax" in l for l in ctab_lines)
        assert any("Sales Tax" in l and "Prepaid" not in l for l in ctab_lines)
        assert len(ctab_lines) == 2