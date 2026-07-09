"""Property-based tests for core.edi.upc_utils.

These tests exercise UPC parsing, validation, and padding invariants over
broad input spaces to protect behavior before refactoring.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from core.edi.upc_utils import (
    calc_check_digit,
    convert_upce_to_upca,
    pad_upc,
    validate_upc,
)

pytestmark = [pytest.mark.unit, pytest.mark.edi, pytest.mark.property]


_DIGITS = st.characters(whitelist_categories=("Nd",))
_DIGIT_STRINGS = st.text(alphabet=_DIGITS, min_size=1, max_size=12)


def _fixed_digits(length: int) -> st.SearchStrategy[str]:
    """Strategy for a fixed-length digit string."""
    return st.text(alphabet=_DIGITS, min_size=length, max_size=length)


@settings(max_examples=100)
@given(d=_fixed_digits(11))
def test_validate_upc_accepts_check_digit(d: str) -> None:
    """validate_upc should accept a UPC whose check digit matches."""
    full = d + str(calc_check_digit(d))
    assert validate_upc(full) is True


@settings(max_examples=100)
@given(
    d=_fixed_digits(11),
    wrong=st.integers(min_value=0, max_value=9),
)
def test_validate_upc_rejects_wrong_check_digit(
    d: str, wrong: int
) -> None:
    """A UPC with a mismatched final digit should fail validation."""
    expected = calc_check_digit(d)
    assume((expected - wrong) % 10 != 0)
    bad = d + str(wrong)
    assert validate_upc(bad) is False


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_calc_check_digit_is_single_digit(s: str) -> None:
    """Check digit is always 0-9."""
    assert 0 <= calc_check_digit(s) <= 9


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_calc_check_digit_is_deterministic(s: str) -> None:
    """calc_check_digit is a pure function."""
    assert calc_check_digit(s) == calc_check_digit(s)


@settings(max_examples=100)
@given(s=_DIGIT_STRINGS)
def test_calc_check_digit_accepts_int_input(s: str) -> None:
    """calc_check_digit accepts both str and int forms of the same digits."""
    if not s:
        return
    assert calc_check_digit(s) == calc_check_digit(int(s))


@settings(max_examples=50)
@given(
    upce=_fixed_digits(6),
)
def test_convert_upce_to_upca_returns_12_digits_for_6char_input(
    upce: str,
) -> None:
    """A 6-digit UPC-E always expands to a 12-digit UPC-A."""
    result = convert_upce_to_upca(upce)
    assert len(result) == 12
    assert result.isdigit()


@settings(max_examples=50)
@given(
    upce=_fixed_digits(7),
)
def test_convert_upce_to_upca_returns_12_digits_for_7char_input(
    upce: str,
) -> None:
    """A 7-digit UPC-E always expands to a 12-digit UPC-A."""
    result = convert_upce_to_upca(upce)
    assert len(result) == 12
    assert result.isdigit()


@settings(max_examples=50)
@given(
    upce=_fixed_digits(8),
)
def test_convert_upce_to_upca_returns_12_digits_for_8char_input(
    upce: str,
) -> None:
    """An 8-digit UPC-E always expands to a 12-digit UPC-A."""
    result = convert_upce_to_upca(upce)
    assert len(result) == 12
    assert result.isdigit()


@settings(max_examples=50)
@given(
    s=st.text(min_size=1, max_size=20),
)
def test_convert_upce_to_upca_rejects_invalid_length(s: str) -> None:
    """Non-6/7/8 digit inputs return empty string."""
    if len(s) in (6, 7, 8):
        return
    assert convert_upce_to_upca(s) == ""


@settings(max_examples=100)
@given(
    upce=_fixed_digits(6),
)
def test_convert_upce_to_upca_produces_valid_upca_check_digit(
    upce: str,
) -> None:
    """The expanded UPC-A must pass validate_upc."""
    result = convert_upce_to_upca(upce)
    assert validate_upc(result) is True


@settings(max_examples=100)
@given(
    s=st.text(alphabet=st.characters(max_codepoint=127), min_size=0, max_size=20),
    target=st.integers(min_value=0, max_value=20),
    fill=st.sampled_from([" ", "0", "X"]),
)
def test_pad_upc_length_is_exactly_target(
    s: str, target: int, fill: str
) -> None:
    """pad_upc always returns a string of length target."""
    assert len(pad_upc(s, target, fill_char=fill)) == target


@settings(max_examples=100)
@given(
    s=st.text(min_size=0, max_size=10),
    target=st.integers(min_value=0, max_value=20),
    fill=st.sampled_from([" ", "0", "X"]),
)
def test_pad_upc_idempotent_when_already_target_length(
    s: str, target: int, fill: str
) -> None:
    """pad_upc is idempotent: padding a padded value yields the same value."""
    once = pad_upc(s, target, fill_char=fill)
    twice = pad_upc(once, target, fill_char=fill)
    assert once == twice


@settings(max_examples=50)
@given(
    s=st.text(alphabet=st.characters(max_codepoint=127), min_size=1, max_size=20),
    target=st.integers(min_value=0, max_value=20),
    fill=st.sampled_from([" ", "0", "X"]),
)
def test_pad_upc_uses_fill_char(s: str, target: int, fill: str) -> None:
    """Any padding added to reach target length uses the fill character."""
    if len(s) >= target:
        return
    result = pad_upc(s, target, fill_char=fill)
    padding_region = result[: target - len(s)]
    assert all(c == fill for c in padding_region)
