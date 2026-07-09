"""Property-based tests for core.edi.edi_transformer.

Exercises the pure price-formatting helpers across broad input spaces.
"""

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.edi.edi_transformer import (
    _extract_dollars,
    convert_to_price,
    convert_to_price_decimal,
    dac_str_int_to_int,
)

pytestmark = [pytest.mark.unit, pytest.mark.edi, pytest.mark.property]


_DIGITS = st.characters(whitelist_categories=("Nd",))
_DIGIT_STRINGS = st.text(alphabet=_DIGITS, min_size=1, max_size=12)
_NONEMPTY_DIGIT_STRINGS = st.text(alphabet=_DIGITS, min_size=1, max_size=12)


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_convert_to_price_ends_with_last_two_digits_of_input(s: str) -> None:
    """The trailing two characters of the output match the input's last two."""
    result = convert_to_price(s)
    assert result.endswith(s[-2:])


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_convert_to_price_contains_exactly_one_dot(s: str) -> None:
    """Exactly one '.' separates integer and fractional parts."""
    result = convert_to_price(s)
    assert result.count(".") == 1
    int_part, _, frac_part = result.partition(".")
    assert int_part.isdigit()
    assert frac_part.isdigit()


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_convert_to_price_no_leading_zeros_in_integer_part(s: str) -> None:
    """Integer portion has no leading zeros (except the literal '0')."""
    result = convert_to_price(s)
    int_part = result.split(".")[0]
    assert int_part == "0" or not int_part.startswith("0")


@settings(max_examples=100)
@given(s=_NONEMPTY_DIGIT_STRINGS)
def test_convert_to_price_strips_leading_zeros_from_dollar_portion(
    s: str,
) -> None:
    """`convert_to_price` output's integer part equals the input's
    dollars (with leading zeros stripped)."""
    expected_int = s[:-2].lstrip("0") or "0"
    result = convert_to_price(s)
    actual_int = result.split(".")[0]
    assert actual_int == expected_int


def test_convert_to_price_empty_string_returns_zero_zero() -> None:
    """An empty input produces '0.00'."""
    assert convert_to_price("") == "0.00"


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_convert_to_price_decimal_returns_decimal_or_zero(s: str) -> None:
    """convert_to_price_decimal returns a Decimal or 0."""
    result = convert_to_price_decimal(s)
    assert isinstance(result, (Decimal, int))


@settings(max_examples=100)
@given(s=st.text(alphabet=_DIGITS, min_size=2, max_size=12))
def test_convert_to_price_decimal_decimal_matches_convert_to_price(
    s: str,
) -> None:
    """When the function returns a Decimal, it must equal convert_to_price."""
    result = convert_to_price_decimal(s)
    if isinstance(result, int):
        return
    expected_str = convert_to_price(s)
    assert Decimal(expected_str) == result


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_convert_to_price_is_deterministic(s: str) -> None:
    """convert_to_price is a pure function."""
    assert convert_to_price(s) == convert_to_price(s)


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_convert_to_price_decimal_is_deterministic(s: str) -> None:
    """convert_to_price_decimal is a pure function."""
    assert convert_to_price_decimal(s) == convert_to_price_decimal(s)


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_extract_dollars_strips_leading_zeros(s: str) -> None:
    """`_extract_dollars` strips leading zeros from the dollars portion."""
    expected = s[:-2].lstrip("0") or "0"
    assert _extract_dollars(s) == expected


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_dac_str_int_to_int_parses_digits(s: str) -> None:
    """dac_str_int_to_int returns an int (possibly 0) for any digit string."""
    result = dac_str_int_to_int(s)
    assert isinstance(result, int)
    assert result >= 0
