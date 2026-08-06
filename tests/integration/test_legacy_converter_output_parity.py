"""Output parity tests against the vendored 1.47 converter implementations."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from dispatch.converters import convert_to_csv as master_csv
from dispatch.converters import convert_to_tweaks as master_tweaks

pytestmark = [pytest.mark.integration, pytest.mark.conversion]

_LEGACY_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_147"

_HEADER = "A" + "VENDOR".ljust(6) + "0000000001" + "010125" + "0000010000"
_DETAIL = (
    "B"
    + "01234567890"
    + "Test Item Description    "
    + "123456"
    + "001050"
    + "01"
    + "000001"
    + "00010"
    + "00199"
    + "001"
    + "000000"
)
_SAMPLE_EDI = "\n".join([_HEADER, _DETAIL]) + "\n"


def _load_legacy_module(name: str):
    from tests.unit.dispatch_tests.conftest import _install_legacy_147_stubs_once

    _install_legacy_147_stubs_once()
    module_name = f"legacy_output_parity_{name}"
    path = _LEGACY_DIR / f"{name}.py"
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _base_parameters() -> dict:
    return {
        "calculate_upc_check_digit": "False",
        "include_a_records": "True",
        "include_c_records": "True",
        "include_headers": "True",
        "filter_ampersand": "False",
        "pad_a_records": "False",
        "a_record_padding": "",
        "a_record_padding_length": 0,
        "override_upc_bool": "False",
        "override_upc_level": 1,
        "override_upc_category_filter": "ALL",
        "retail_uom": "False",
        "force_txt_file_ext": "False",
        "append_a_records": "False",
        "a_record_append_text": "",
        "invoice_date_custom_format": "True",
        "invoice_date_custom_format_string": "%m%d%y",
        "invoice_date_offset": 0,
        "split_prepaid_sales_tax_crec": "False",
        "upc_target_length": 11,
        "upc_padding_pattern": "           ",
    }


def _run_converter(
    converter, input_path: Path, output_path: Path, params: dict
) -> bytes:
    result = converter.edi_convert(
        str(input_path),
        str(output_path),
        {},
        params,
        {123456: ("ALL", "01234567890", "")},
    )
    return Path(result).read_bytes()


@pytest.mark.parametrize(
    ("legacy_name", "master_converter"),
    [("convert_to_csv", master_csv), ("edi_tweaks", master_tweaks)],
)
def test_converter_output_matches_legacy_147(
    tmp_path: Path, legacy_name: str, master_converter
):
    input_path = tmp_path / "input.edi"
    input_path.write_text(_SAMPLE_EDI, encoding="utf-8")
    params = _base_parameters()
    if legacy_name == "edi_tweaks":
        params["invoice_date_offset"] = 0

    if legacy_name == "edi_tweaks":
        legacy_converter = _load_legacy_module(legacy_name)

        legacy_output = tmp_path / "legacy-tweaks"
        legacy_converter.edi_tweak(
            str(input_path),
            str(legacy_output),
            {},
            params,
            {123456: ("ALL", "01234567890", "")},
        )
        legacy_bytes = legacy_output.read_bytes()
    else:
        legacy_converter = _load_legacy_module(legacy_name)
        legacy_bytes = _run_converter(
            legacy_converter, input_path, tmp_path / "legacy-convert", params
        )

    master_bytes = _run_converter(
        master_converter, input_path, tmp_path / "master-convert", params
    )

    assert master_bytes == legacy_bytes


def test_tweaks_short_b_record_matches_legacy_147(tmp_path: Path) -> None:
    """Regression: B record shorter than EDI_B_RECORD_STANDARD_LENGTH.

    A 75-char B record (no parent_item_number) + ``\\n`` from
    ``readlines()`` historically caused ``capture_records`` to populate
    ``parent_item_number`` with a trailing ``\\n`` (``'00000\\n'``). The
    legacy 1.47 reference had a ``if len(writeable_line) < 77`` workaround
    that zeroed it before writing. The master parser must now strip the
    trailing line terminator at the parser boundary so ``parent_item_number``
    is empty in this case, matching legacy output byte-for-byte.

    Without this regression test, future changes to the parser boundary
    could re-introduce the spurious trailing ``\\r\\n\\r\\n`` in the master
    output without being noticed by the standard 76-char B record parity
    case (which captures ``parent_item_number = '000000'`` and so doesn't
    exercise the empty-parent path).
    """
    short_b_edi = (
        "AVENDOR00000000010101250000010000\n"
        "B01234567890Test Item Description    "
        "12345600105001000001000100019900100000\n"  # 75 chars (no parent) + \n
    )
    input_path = tmp_path / "input.edi"
    input_path.write_text(short_b_edi, encoding="utf-8")
    params = _base_parameters()
    params["invoice_date_offset"] = 0

    legacy = _load_legacy_module("edi_tweaks")
    legacy_path = tmp_path / "legacy-tweaks"
    legacy.edi_tweak(
        str(input_path),
        str(legacy_path),
        {},
        params,
        {123456: ("ALL", "01234567890", "")},
    )
    legacy_bytes = legacy_path.read_bytes()

    master_path = tmp_path / "master-tweaks"
    master_result = master_tweaks.edi_convert(
        str(input_path),
        str(master_path),
        {},
        params,
        {123456: ("ALL", "01234567890", "")},
    )
    master_bytes = Path(master_result).read_bytes()

    assert master_bytes == legacy_bytes, (
        f"Master produced {len(master_bytes)} bytes, legacy produced "
        f"{len(legacy_bytes)} bytes. Master output: {master_bytes!r}; "
        f"Legacy output: {legacy_bytes!r}"
    )


@pytest.mark.parametrize(
    "option_name",
    [
        "force_txt_file_ext",
        "calculate_upc_check_digit",
        "retail_uom",
    ],
)
def test_tweaks_option_output_matches_legacy(tmp_path: Path, option_name: str):
    input_path = tmp_path / "input.edi"
    input_path.write_text(_SAMPLE_EDI, encoding="utf-8")
    params = _base_parameters()
    params["invoice_date_custom_format"] = "True"
    params["invoice_date_custom_format_string"] = "%m%d%y"
    params[option_name] = "True"
    if option_name == "calculate_upc_check_digit":
        params["calculate_upc_check_digit"] = "False"
    upc = {123456: ("ALL", "01234567890", "01234567890")}

    legacy = _load_legacy_module("edi_tweaks")
    legacy_path = tmp_path / "legacy-option"
    legacy.edi_tweak(str(input_path), str(legacy_path), {}, params, upc)
    if option_name == "force_txt_file_ext":
        legacy_path = legacy_path.with_suffix(".txt")

    master_path = tmp_path / "master-option"
    master_result = master_tweaks.edi_convert(
        str(input_path), str(master_path), {}, params, upc
    )

    assert Path(master_result).read_bytes() == legacy_path.read_bytes()
