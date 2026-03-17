"""Property-based tests for EDI parser/builders.

These tests exercise parser invariants over broad input spaces to protect
behavior before refactoring.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.edi.edi_parser import (
    build_a_record,
    build_b_record,
    build_c_record,
    capture_records,
    parse_a_record,
    parse_b_record,
    parse_c_record,
)

pytestmark = [pytest.mark.unit, pytest.mark.edi]


def _fixed_text(length: int):
    """Strategy for fixed-width EDI field text without line breaks."""
    return st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\n\r",
        ),
        min_size=length,
        max_size=length,
    )


def _line_text(max_size: int = 40):
    """Strategy for single-line suffix text."""
    return st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\n\r",
        ),
        min_size=0,
        max_size=max_size,
    )


@settings(max_examples=100)
@given(
    cust_vendor=_fixed_text(6),
    invoice_number=_fixed_text(10),
    invoice_date=_fixed_text(6),
    invoice_total=_fixed_text(10),
)
def test_a_record_build_parse_roundtrip(
    cust_vendor: str,
    invoice_number: str,
    invoice_date: str,
    invoice_total: str,
) -> None:
    line = build_a_record(
        cust_vendor=cust_vendor,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_total=invoice_total,
    )

    parsed = parse_a_record(line)

    assert parsed.cust_vendor == cust_vendor
    assert parsed.invoice_number == invoice_number
    assert parsed.invoice_date == invoice_date
    assert parsed.invoice_total == invoice_total


@settings(max_examples=100)
@given(
    upc_number=_fixed_text(11),
    description=_fixed_text(25),
    vendor_item=_fixed_text(6),
    unit_cost=_fixed_text(6),
    combo_code=_fixed_text(2),
    unit_multiplier=_fixed_text(6),
    qty_of_units=_fixed_text(5),
    suggested_retail_price=_fixed_text(5),
    price_multi_pack=_fixed_text(3),
    parent_item_number=_fixed_text(6),
)
def test_b_record_build_parse_roundtrip(
    upc_number: str,
    description: str,
    vendor_item: str,
    unit_cost: str,
    combo_code: str,
    unit_multiplier: str,
    qty_of_units: str,
    suggested_retail_price: str,
    price_multi_pack: str,
    parent_item_number: str,
) -> None:
    line = build_b_record(
        upc_number=upc_number,
        description=description,
        vendor_item=vendor_item,
        unit_cost=unit_cost,
        combo_code=combo_code,
        unit_multiplier=unit_multiplier,
        qty_of_units=qty_of_units,
        suggested_retail_price=suggested_retail_price,
        price_multi_pack=price_multi_pack,
        parent_item_number=parent_item_number,
    )

    parsed = parse_b_record(line)

    assert parsed.upc_number == upc_number
    assert parsed.description == description
    assert parsed.vendor_item == vendor_item
    assert parsed.unit_cost == unit_cost
    assert parsed.combo_code == combo_code
    assert parsed.unit_multiplier == unit_multiplier
    assert parsed.qty_of_units == qty_of_units
    assert parsed.suggested_retail_price == suggested_retail_price
    assert parsed.price_multi_pack == price_multi_pack
    assert parsed.parent_item_number == parent_item_number


@settings(max_examples=100)
@given(
    charge_type=_fixed_text(3),
    description=_fixed_text(25),
    amount=_fixed_text(9),
)
def test_c_record_build_parse_roundtrip(
    charge_type: str, description: str, amount: str
) -> None:
    line = build_c_record(
        charge_type=charge_type,
        description=description,
        amount=amount,
    )

    parsed = parse_c_record(line)

    assert parsed.charge_type == charge_type
    assert parsed.description == description
    assert parsed.amount == amount


@settings(max_examples=100)
@given(
    cust_vendor=_fixed_text(6),
    invoice_number=_fixed_text(10),
    invoice_date=_fixed_text(6),
    invoice_total=_fixed_text(10),
    append_text=_line_text(80),
)
def test_capture_a_record_slices_are_stable_with_append_text(
    cust_vendor: str,
    invoice_number: str,
    invoice_date: str,
    invoice_total: str,
    append_text: str,
) -> None:
    line = build_a_record(
        cust_vendor=cust_vendor,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_total=invoice_total,
        append_text=append_text,
    )

    parsed = capture_records(line)

    assert parsed is not None
    assert parsed["record_type"] == "A"
    assert parsed["cust_vendor"] == cust_vendor
    assert parsed["invoice_number"] == invoice_number
    assert parsed["invoice_date"] == invoice_date
    assert parsed["invoice_total"] == invoice_total


@settings(max_examples=100)
@given(
    prefix=st.characters(
        blacklist_characters="ABC\n\r\x1a",
        blacklist_categories=("Cs",),
    ),
    payload=_line_text(120),
)
def test_capture_records_returns_none_for_unknown_record_prefix(
    prefix: str, payload: str
) -> None:
    result = capture_records(prefix + payload)
    assert result is None
