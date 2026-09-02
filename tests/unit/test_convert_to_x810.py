"""Unit tests for convert_to_x810.py converter module.

Covers:
- module registration (CONVERTER_METADATA, registry discovery)
- required-parameter validation (missing sender/receiver raises)
- envelope shape: ISA / GS / ST / SE / GE / IEA structure
- BIG date and number mapping from A record
- IT1 line count and per-line field derivation from B records
- C records dropped silently in this phase
- TDS totals from A record invoice_total
- CTT count from B record count
- control-number overrides honored
"""

import os

import pytest

from webapp.pipeline.converters import convert_to_x810
from webapp.pipeline.converters.convert_to_x810 import X810Converter


def _a(invoice_number="INV001", invoice_date="010125", invoice_total="0000050000"):
    return (
        "A"
        + "VENDOR".ljust(6)[:6]
        + invoice_number.ljust(10)[:10]
        + invoice_date.ljust(6)[:6]
        + invoice_total.ljust(10)[:10]
    )


def _b(
    upc="012345678905",
    description="DESC",
    vendor_item="123456",
    unit_cost="00100",
    combo_code="01",
    unit_multiplier="000001",
    qty_of_units="00010",
    suggested_retail="00199",
    price_multi_pack="001",
    parent_item="000000",
):
    return (
        "B"
        + upc.ljust(11)[:11]
        + description.ljust(25)[:25]
        + vendor_item.ljust(6)[:6]
        + unit_cost.ljust(6)[:6]
        + combo_code.ljust(2)[:2]
        + unit_multiplier.ljust(6)[:6]
        + qty_of_units.ljust(5)[:5]
        + suggested_retail.ljust(5)[:5]
        + price_multi_pack.ljust(3)[:3]
        + parent_item.ljust(6)[:6]
    )


def _c():
    return "C" + "TAB" + "Sales Tax".ljust(25)[:25] + "000010000"


@pytest.fixture
def basic_edi():
    return "\n".join(
        [
            _a(),
            _b(),
            _b(upc="999999999999", vendor_item="654321", unit_cost="00250"),
            _c(),
            "",
        ]
    )


@pytest.fixture
def base_params():
    return {
        "x810_sender_id": "SENDER01",
        "x810_receiver_id": "RECEIVER01",
    }


@pytest.fixture
def settings():
    return {}


class TestMetadata:
    def test_metadata_declares_x810(self):
        md = convert_to_x810.CONVERTER_METADATA
        assert md["format_name"] == "x810"
        assert md["display_name"] == "X12 810 (Invoice)"
        assert md["module_name"] == "webapp.pipeline.converters.convert_to_x810"

    def test_registry_picks_up_x810(self):
        from webapp.pipeline.converters.registry import (
            format_exists,
            get_converter_by_name,
            get_format_names,
        )

        assert format_exists("x810")
        assert "x810" in get_format_names()
        meta = get_converter_by_name("x810")
        assert meta is not None
        assert meta.format_name == "x810"

    def test_module_exports_edi_convert(self):
        assert hasattr(convert_to_x810, "edi_convert")
        assert callable(convert_to_x810.edi_convert)


class TestParameterValidation:
    def test_missing_sender_raises(self, basic_edi, tmp_path):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        with pytest.raises(ValueError, match="x810_sender_id"):
            convert_to_x810.edi_convert(
                str(input_file),
                str(tmp_path / "out"),
                {},
                {"x810_receiver_id": "RECEIVER01"},
                {},
            )

    def test_missing_receiver_raises(self, basic_edi, tmp_path):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        with pytest.raises(ValueError, match="x810_receiver_id"):
            convert_to_x810.edi_convert(
                str(input_file),
                str(tmp_path / "out"),
                {},
                {"x810_sender_id": "SENDER01"},
                {},
            )


class TestEnvelopeShape:
    def test_writes_file_with_810_extension(
        self, basic_edi, base_params, settings, tmp_path
    ):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        assert result == str(tmp_path / "out.810")
        assert os.path.exists(result)

    def test_envelope_segments_present(
        self, basic_edi, base_params, settings, tmp_path
    ):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        assert text.startswith("ISA*")
        assert "\nGS*IN*" in text
        assert "\nST*810*" in text
        assert "\nBIG*" in text
        assert "\nIT1*1*" in text
        assert "\nIT1*2*" in text
        assert "\nTDS*" in text
        assert "\nCTT*2~" in text
        assert "\nSE*" in text
        assert "\nGE*1*" in text
        iea = [ln for ln in text.splitlines() if ln.startswith("IEA*")][-1]
        assert iea.startswith("IEA*1*")

    def test_se_segment_count_includes_segments(
        self, basic_edi, base_params, settings, tmp_path
    ):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        se_line = [ln for ln in text.splitlines() if ln.startswith("SE*")][0]
        seg_count = int(se_line.split("*")[1])
        assert seg_count >= 6

    def test_envelope_uses_x_element_separator(
        self, basic_edi, base_params, settings, tmp_path
    ):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        assert "*" in text
        assert "~" in text


class TestFieldMapping:
    def test_big_carries_invoice_number_and_date(
        self, base_params, settings, tmp_path
    ):
        edi = "\n".join([_a(invoice_number="INV00042", invoice_date="070425"), "", ""])
        input_file = tmp_path / "in.edi"
        input_file.write_text(edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        big = [ln for ln in text.splitlines() if ln.startswith("BIG*")][0]
        fields = big.rstrip("~").split("*")
        assert fields[2] == "INV00042"
        assert fields[1] == "20250704"

    def test_it1_unit_price_from_cents_to_dollars(
        self, base_params, settings, tmp_path
    ):
        edi = "\n".join(
            [_a(), _b(unit_cost="00100"), ""]
        )
        input_file = tmp_path / "in.edi"
        input_file.write_text(edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        it1 = [ln for ln in text.splitlines() if ln.startswith("IT1*")][0]
        fields = it1.rstrip("~").split("*")
        assert fields[4] == "1.00"

    def test_tds_total_from_invoice_total_in_dollars(
        self, base_params, settings, tmp_path
    ):
        edi = "\n".join([_a(invoice_total="0000123400"), _b(), ""])
        input_file = tmp_path / "in.edi"
        input_file.write_text(edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        tds = [ln for ln in text.splitlines() if ln.startswith("TDS*")][0]
        assert tds == "TDS*0000001234~"

    def test_ctt_counts_b_records_only(
        self, base_params, settings, tmp_path
    ):
        edi = "\n".join(
            [
                _a(),
                _b(),
                _b(upc="111111111111"),
                _b(upc="222222222222"),
                _c(),
                "",
            ]
        )
        input_file = tmp_path / "in.edi"
        input_file.write_text(edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        ctt = [ln for ln in text.splitlines() if ln.startswith("CTT*")][0]
        assert ctt == "CTT*3~"

    def test_c_records_dropped(
        self, basic_edi, base_params, settings, tmp_path
    ):
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        assert "SAC*" not in text


class TestControlNumbers:
    def test_overrides_appear_in_envelope(self, basic_edi, settings, tmp_path):
        params = {
            "x810_sender_id": "SENDER01",
            "x810_receiver_id": "RECEIVER01",
            "x810_isa_control": "123456789",
            "x810_gs_control": "42",
            "x810_st_control": "0007",
        }
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            params,
            {},
        )
        text = open(result).read()
        isa = text.splitlines()[0]
        assert "123456789" in isa
        ge = [ln for ln in text.splitlines() if ln.startswith("GE*")][0]
        assert ge == "GE*1*42~"
        iea = [ln for ln in text.splitlines() if ln.startswith("IEA*")][0]
        assert iea == "IEA*1*123456789~"
        st_line = [ln for ln in text.splitlines() if ln.startswith("ST*810*")][0]
        assert st_line.endswith("0007~")


class TestEdgeCases:
    def test_header_only_no_b_records(
        self, base_params, settings, tmp_path
    ):
        edi = "\n".join([_a(), _c(), ""])
        input_file = tmp_path / "in.edi"
        input_file.write_text(edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            base_params,
            {},
        )
        text = open(result).read()
        ctt = [ln for ln in text.splitlines() if ln.startswith("CTT*")][0]
        assert ctt == "CTT*0~"
        assert "IT1*" not in text

    def test_bill_to_includes_n1_segment(self, basic_edi, settings, tmp_path):
        params = {
            "x810_sender_id": "SENDER01",
            "x810_receiver_id": "RECEIVER01",
            "x810_bill_to_name": "ACME RETAIL",
        }
        input_file = tmp_path / "in.edi"
        input_file.write_text(basic_edi)
        result = convert_to_x810.edi_convert(
            str(input_file),
            str(tmp_path / "out"),
            settings,
            params,
            {},
        )
        text = open(result).read()
        n1 = [ln for ln in text.splitlines() if ln.startswith("N1*")]
        assert n1 and n1[0] == "N1*BT*ACME RETAIL~"

    def test_class_instantiation(self):
        c = X810Converter()
        assert c is not None
