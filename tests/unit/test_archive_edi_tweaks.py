from pathlib import Path

from archive.edi_tweaks import _create_query_runner_adapter, edi_tweak


def _base_settings():
    return {
        "as400_username": "user",
        "as400_password": "pass",
        "as400_address": "host",
        "odbc_driver": "driver",
    }


def _base_parameters():
    return {
        "pad_a_records": "False",
        "a_record_padding": "",
        "a_record_padding_length": 0,
        "append_a_records": "False",
        "a_record_append_text": "",
        "invoice_date_custom_format": False,
        "invoice_date_custom_format_string": "%Y-%m-%d",
        "force_txt_file_ext": "False",
        "calculate_upc_check_digit": "False",
        "invoice_date_offset": 0,
        "retail_uom": False,
        "override_upc_bool": False,
        "override_upc_level": 1,
        "override_upc_category_filter": "ALL",
        "split_prepaid_sales_tax_crec": "False",
        "upc_target_length": 11,
        "upc_padding_pattern": "           ",
        "tweak_edi": True,
    }


def _a_record(invoice_number: int, vendor: str = "VENDOR") -> str:
    return f"A{vendor:<6}{invoice_number:010d}0101250000100000\n"


class RecordingLegacyRunner:
    def __init__(self, *_args):
        self.calls = []

    def run_arbitrary_query(self, query, params=None):
        self.calls.append((query, params))
        return [("PO-0001",)]


class PONumberRunner:
    def __init__(self, *_args):
        self.calls = []

    def run_arbitrary_query(self, query, params=None):
        self.calls.append((query, params))
        invoice_number = params[0]
        return [(f"PO-{invoice_number:04d}",)]


def test_query_runner_adapter_forwards_params(monkeypatch):
    created_runners = []

    def fake_query_runner(*args):
        runner = RecordingLegacyRunner(*args)
        created_runners.append(runner)
        return runner

    monkeypatch.setattr("archive.edi_tweaks.query_runner", fake_query_runner)

    adapter = _create_query_runner_adapter(_base_settings())

    result = adapter.run_query("SELECT 1 WHERE id = ?", (123,))

    assert result == [("PO-0001",)]
    assert created_runners[0].calls == [("SELECT 1 WHERE id = ?", (123,))]


def test_edi_tweak_replaces_po_placeholder_per_invoice(tmp_path, monkeypatch):
    created_runners = []

    def fake_query_runner(*args):
        runner = PONumberRunner(*args)
        created_runners.append(runner)
        return runner

    monkeypatch.setattr("archive.edi_tweaks.query_runner", fake_query_runner)

    input_file = tmp_path / "input.edi"
    output_file = tmp_path / "output.edi"
    input_file.write_text(_a_record(1) + _a_record(2))

    parameters = _base_parameters()
    parameters["append_a_records"] = "True"
    parameters["a_record_append_text"] = " PO:%po_str%"

    edi_tweak(
        str(input_file),
        str(output_file),
        _base_settings(),
        parameters,
        upc_dict={},
    )

    output_lines = output_file.read_text().splitlines()

    assert output_lines == [
        "AVENDOR00000000010101250000100000 PO:PO-0001",
        "AVENDOR00000000020101250000100000 PO:PO-0002",
    ]
    assert created_runners[0].calls == [
        (
            """
            SELECT ohhst.bte4cd
            FROM dacdata.ohhst ohhst
            WHERE ohhst.bthhnb = ?
            """,
            (1,),
        ),
        (
            """
            SELECT ohhst.bte4cd
            FROM dacdata.ohhst ohhst
            WHERE ohhst.bthhnb = ?
            """,
            (2,),
        ),
    ]
