"""Property-based tests for core.edi.c_rec_generator.

Exercises the pure C-record formatting helpers and the public
`generate_c_record` / `generate_c_records_for_invoice` functions.

`fetch_splitted_sales_tax_totals` is intentionally excluded — it
requires a real query runner.
"""

import io
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.edi.c_rec_generator import (
    CRecGenerator,
    CRecordConfig,
    QueryRunnerProtocol,
)

pytestmark = [pytest.mark.unit, pytest.mark.edi, pytest.mark.property]


_SENTINEL_RUNNER = object()


def _gen() -> CRecGenerator:
    """Construct a CRecGenerator with a sentinel query runner.

    Tests must not invoke the runner; if they do, AttributeError
    on the sentinel will fail loudly.
    """
    return CRecGenerator(query_runner=_SENTINEL_RUNNER)  # type: ignore[arg-type]


@st.composite
def _amounts(draw, max_value: float = 9_999_999.99) -> float:
    """Strategy for finite, non-NaN float amounts bounded by max_value.

    The bound keeps the formatted 2-decimal fixed-point representation
    at 9 characters or fewer (so the 9-digit padding contract holds).
    """
    sign = draw(st.sampled_from([-1, 1]))
    magnitude = draw(
        st.floats(
            min_value=0.0,
            max_value=max_value,
            allow_nan=False,
            allow_infinity=False,
            width=64,
        )
    )
    return sign * magnitude


@settings(max_examples=100)
@given(amount=st.floats(
    min_value=0.0,
    max_value=9999999.99,
    allow_nan=False,
    allow_infinity=False,
))
def test_format_amount_str_is_exactly_9_chars_for_nonneg(amount: float) -> None:
    """_format_amount_str returns exactly 9 characters for non-negative amounts."""
    gen = _gen()
    result = gen._format_amount_str(amount)
    assert len(result) == 9


@settings(max_examples=100)
@given(amount=st.floats(
    min_value=-9999999.99,
    max_value=-0.01,
    allow_nan=False,
    allow_infinity=False,
))
def test_format_amount_str_is_10_chars_for_negative(amount: float) -> None:
    """Negative amounts are 10 chars (9 digits + leading '-')."""
    gen = _gen()
    result = gen._format_amount_str(amount)
    assert len(result) == 10
    assert result.startswith("-")


@settings(max_examples=100)
@given(amount=_amounts(max_value=99999999.99))
def test_format_amount_str_starts_with_minus_iff_negative(amount: float) -> None:
    """Negative amounts get a leading '-'; non-negative do not."""
    gen = _gen()
    result = gen._format_amount_str(amount)
    if amount < 0:
        assert result.startswith("-")
        assert result[1:].isdigit()
    else:
        assert not result.startswith("-")
        assert result.isdigit()


@settings(max_examples=100)
@given(
    amount=_amounts(max_value=99999999.99),
)
def test_format_amount_str_abs_value_padded_to_9_digits(amount: float) -> None:
    """|amount| formatted as 2-decimal-fixed-point is right-justified to 9."""
    gen = _gen()
    result = gen._format_amount_str(amount)
    sign = "-" if amount < 0 else ""
    expected_core = f"{abs(amount):.2f}".replace(".", "").rjust(9, "0")
    assert result == f"{sign}{expected_core}"


@settings(max_examples=100)
@given(amount=st.floats(min_value=0.0, max_value=0.0, allow_nan=False))
def test_format_amount_str_zero_is_all_zeros(amount: float) -> None:
    """Zero amount is '000000000'."""
    gen = _gen()
    assert gen._format_amount_str(amount) == "000000000"


@settings(max_examples=100)
@given(
    charge_type=st.text(
        alphabet=st.characters(max_codepoint=127), min_size=0, max_size=5
    ),
    description=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
        min_size=0,
        max_size=40,
    ),
    amount=st.floats(
        min_value=-99999999.99,
        max_value=99999999.99,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_generate_c_record_starts_with_C(
    charge_type: str, description: str, amount: float
) -> None:
    """A generated C record begins with 'C'."""
    gen = _gen()
    line = gen.generate_c_record(charge_type, description, amount)
    assert line.startswith("C")
    assert line.endswith("\n")


@settings(max_examples=100)
@given(
    description=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
        min_size=0,
        max_size=25,
    ),
    amount=st.floats(
        min_value=-99999999.99,
        max_value=99999999.99,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_generate_c_record_description_is_padded_to_25(
    description: str, amount: float
) -> None:
    """The description field is left-justified and padded to 25 characters.

    Field layout of a C record (after the leading 'C' and 3-char charge type):
        C + charge_type(3) + description(25) + amount(9) + newline
    So characters at index 4..28 (inclusive) are the description field.
    """
    gen = _gen()
    line = gen.generate_c_record("TAB", description, amount)
    body = line.rstrip("\n")
    assert body.startswith("CTAB")
    desc_field = body[4 : 4 + 25]
    assert len(desc_field) == 25
    assert desc_field.startswith(description)


@settings(max_examples=100)
@given(
    amount=_amounts(max_value=99999999.99),
)
def test_generate_c_record_amount_field_is_9_chars(amount: float) -> None:
    """The amount field of a generated C record is 9 characters wide."""
    gen = _gen()
    line = gen.generate_c_record("TAB", "Sales Tax", amount)
    body = line.rstrip("\n")
    # 1 ('C') + 3 (charge type) + 25 (description) = 29; amount starts at 29
    amount_field = body[29 : 29 + 9]
    assert len(amount_field) == 9


@settings(max_examples=50)
@given(
    charges=st.lists(
        st.fixed_dictionaries(
            {
                "type": st.text(
                    alphabet=st.characters(max_codepoint=127),
                    min_size=1,
                    max_size=3,
                ),
                "description": st.text(
                    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
                    min_size=0,
                    max_size=20,
                ),
                "amount": st.floats(
                    min_value=-99999.99,
                    max_value=99999.99,
                    allow_nan=False,
                    allow_infinity=False,
                ),
            }
        ),
        min_size=0,
        max_size=10,
    ),
)
def test_generate_c_records_for_invoice_returns_one_per_charge(
    charges: list[dict],
) -> None:
    """Output list length equals input charges length."""
    gen = _gen()
    records = gen.generate_c_records_for_invoice({}, charges)
    assert len(records) == len(charges)
    for record in records:
        assert record.startswith("C")
        assert record.endswith("\n")


@settings(max_examples=50)
@given(
    charges=st.lists(
        st.fixed_dictionaries(
            {
                "description": st.text(
                    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
                    min_size=0,
                    max_size=10,
                ),
                "amount": st.floats(
                    min_value=-99999.99,
                    max_value=99999.99,
                    allow_nan=False,
                    allow_infinity=False,
                ),
            }
        ),
        min_size=1,
        max_size=5,
    ),
)
def test_generate_c_records_for_invoice_uses_default_charge_type_when_missing(
    charges: list[dict],
) -> None:
    """Charges without a 'type' key fall back to config.charge_type."""
    config = CRecordConfig(charge_type="ZZZ")
    gen = CRecGenerator(query_runner=_SENTINEL_RUNNER, config=config)  # type: ignore[arg-type]
    records = gen.generate_c_records_for_invoice({}, charges)
    for record in records:
        # After 'C', the next 3 chars are the charge type
        assert record[1:4] == "ZZZ"


def test_fetch_splitted_sales_tax_totals_skips_zero_amounts() -> None:
    """A prepaid amount of 0 must NOT produce a 'Prepaid Sales Tax' C record.

    L116 `if qry_ret_prepaid is not None and qry_ret_prepaid != 0:` — a
    mutation flipping `!=` to `==` would emit a C record for the zero
    case. Same for the non-prepaid branch at L119.
    """
    runner = MagicMock(spec=QueryRunnerProtocol)
    runner.run_query.return_value = [(100.0, 0.0)]
    gen = CRecGenerator(query_runner=runner)
    out = io.StringIO()
    gen.fetch_splitted_sales_tax_totals(out)
    output = out.getvalue()
    assert "Prepaid" not in output
    assert "CTABSales Tax" in output


def test_fetch_splitted_sales_tax_totals_writes_nonzero_prepaid() -> None:
    """A non-zero prepaid amount produces a 'Prepaid Sales Tax' C record."""
    runner = MagicMock(spec=QueryRunnerProtocol)
    runner.run_query.return_value = [(0.0, 50.0)]
    gen = CRecGenerator(query_runner=runner)
    out = io.StringIO()
    gen.fetch_splitted_sales_tax_totals(out)
    output = out.getvalue()
    assert "CTABPrepaid" in output
    assert "CTABSales Tax" not in output


def test_fetch_splitted_sales_tax_totals_empty_query_sets_unappended_false() -> None:
    """An empty query result sets unappended_records=False and writes nothing.

    L110 `if not qry_ret: self.unappended_records = False; return`. A
    mutation negating the condition would skip the early return and
    unpack qry_ret[0] (TypeError on empty list).
    """
    runner = MagicMock(spec=QueryRunnerProtocol)
    runner.run_query.return_value = []
    gen = CRecGenerator(query_runner=runner)
    gen.set_invoice_number("42")
    out = io.StringIO()
    gen.fetch_splitted_sales_tax_totals(out)
    assert out.getvalue() == ""
    assert gen.unappended_records is False


def test_init_default_config_is_crecord_config_instance() -> None:
    """When no config is passed, __init__ falls back to a CRecordConfig.

    L73 `self.config = config or CRecordConfig()`. The `or` -> `and`
    mutation would resolve `None and CRecordConfig()` to `None` when
    no config is supplied; the contract is that .config must be a
    CRecordConfig in that case.
    """
    runner = MagicMock(spec=QueryRunnerProtocol)
    gen = CRecGenerator(query_runner=runner)
    assert isinstance(gen.config, CRecordConfig)
    assert gen.config.default_uom == "EA"
    assert gen.config.charge_type == "TAB"
