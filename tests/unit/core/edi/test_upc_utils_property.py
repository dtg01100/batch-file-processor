"""Property-based tests for core.edi.upc_utils.

These tests exercise UPC parsing, validation, and padding invariants over
broad input spaces to protect behavior before refactoring.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from core.edi.upc_utils import (
    apply_retail_uom_transform,
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


def test_validate_upc_hardcoded_valid_oracle() -> None:
    """Hardcoded valid UPC values must validate; mutations to calc_check_digit
    cannot make this test pass because the input is independent of the function.
    """
    assert validate_upc("041800000265") is True
    assert validate_upc("041800000260") is False


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


def test_calc_check_digit_hardcoded_oracle() -> None:
    """Hardcoded check-digit values: validates the function's output
    directly against precomputed constants, independent of the function
    itself. Catches any consistent mutation to ``calc_check_digit`` that
    the self-referential int-coercion test would silently pass.

    Values were computed by hand from the algorithm in
    ``core/edi/upc_utils.py`` and re-verified in this venv:

        >>> calc_check_digit("04180000026"), calc_check_digit("00000000000"),
        ... calc_check_digit("12345678901"), calc_check_digit("99999999999"),
        ... calc_check_digit("11111111111")
        (5, 0, 2, 3, 7)
    """
    assert calc_check_digit("04180000026") == 5
    assert calc_check_digit("00000000000") == 0
    assert calc_check_digit("12345678901") == 2
    assert calc_check_digit("99999999999") == 3
    assert calc_check_digit("11111111111") == 7
    # Also confirm the int-coercion path returns the same hardcoded value
    # for at least one input. The int-coercion test above covers the
    # random case; this one pins a specific value.
    assert calc_check_digit(4180000026) == 5
    assert calc_check_digit(12345678901) == 2


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


def test_pad_upc_hardcoded_oracle() -> None:
    """Hardcoded ``pad_upc`` output values. The idempotency test above
    (which asserts ``pad_upc(s, t, fill) == pad_upc(pad_upc(s, t, fill), t, fill)``)
    is self-referential: a consistent mutation to ``pad_upc`` that
    returns its input unchanged would still pass. This test pins
    the actual output for known inputs so any such mutation is
    caught.
    """
    # Right-pad with default space char
    assert pad_upc("12345", 10) == "     12345"
    assert pad_upc("", 5) == "     "
    assert pad_upc("123", 8) == "     123"
    # Already at target length: returned unchanged
    assert pad_upc("12345", 5) == "12345"
    # Below target length with explicit fill char
    assert pad_upc("0", 1) == "0"
    # Above target length: truncated
    assert pad_upc("123456", 3) == "123"


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


# ---------------------------------------------------------------------------
# apply_retail_uom_transform — the upc_utils wrapper.
#
# The function is a thin passthrough to ``core.edi.retail_uom``. The
# behavioral surface (record mutation, success/failure return) is exercised
# in ``tests/unit/test_utils.py::TestApplyRetailUomTransform`` against the
# ``core.utils.utils`` wrapper. The two wrappers share the same underlying
# implementation, so the tests below pin the upc_utils-specific surface.
#
# The hardcoded-oracle tests are critical: the wrapper is one line of code,
# so the meaningful mutation risk is ``return None`` / ``return record``
# mistakes (silently breaking callers that check the return value) and a
# broken passthrough (returning a different value than the call target).
# ---------------------------------------------------------------------------


def _make_b_record(
    vendor_item: str = "000123",
    unit_cost: str = "001200",
    unit_multiplier: str = "000012",
    qty_of_units: str = "00010",
    upc_number: str = "00000000000",
) -> dict:
    """Build a minimal B-record dict for apply_retail_uom_transform."""
    return {
        "vendor_item": vendor_item,
        "unit_cost": unit_cost,
        "unit_multiplier": unit_multiplier,
        "qty_of_units": qty_of_units,
        "upc_number": upc_number,
    }


def test_apply_retail_uom_transform_passthrough_returns_true() -> None:
    """A valid record with a matching UPC must round-trip True and mutate unit_multiplier."""
    record = _make_b_record()
    upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
    assert apply_retail_uom_transform(record, upc_dict) is True
    assert record["unit_multiplier"] == "000001"


def test_apply_retail_uom_transform_passthrough_returns_false_on_zero_multiplier() -> None:
    """Zero unit_multiplier is rejected (matches the retail_uom implementation contract)."""
    record = _make_b_record(unit_multiplier="000000")
    upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
    assert apply_retail_uom_transform(record, upc_dict) is False


def test_apply_retail_uom_transform_passthrough_returns_false_on_bad_vendor_item() -> None:
    """Non-numeric vendor_item must return False; record must be unmodified."""
    record = _make_b_record(vendor_item="ABCDEF")
    upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
    assert apply_retail_uom_transform(record, upc_dict) is False
    assert record["unit_multiplier"] == "000012"


def test_apply_retail_uom_transform_empty_lookup_uses_blank_upc() -> None:
    """Empty upc_lookup falls back to the default 11-space UPC string."""
    record = _make_b_record()
    assert apply_retail_uom_transform(record, {}) is True
    assert record["upc_number"] == "           "
    assert record["unit_multiplier"] == "000001"


def test_apply_retail_uom_transform_multiplies_qty() -> None:
    """qty_of_units becomes unit_multiplier * qty_of_units, zero-padded to 5 chars."""
    record = _make_b_record(unit_multiplier="000012", qty_of_units="00010")
    upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
    assert apply_retail_uom_transform(record, upc_dict) is True
    assert record["qty_of_units"] == "00120"


def test_apply_retail_uom_transform_unit_cost_divided_by_multiplier() -> None:
    """unit_cost becomes (cost/100)/multiplier, scaled back to a 6-digit int, zero-padded."""
    # 1200 cents -> $12.00, /12 = $1.00 -> 100 cents = "000100"
    record = _make_b_record(unit_cost="001200", unit_multiplier="000012")
    upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
    assert apply_retail_uom_transform(record, upc_dict) is True
    assert record["unit_cost"] == "000100"


def test_apply_retail_uom_transform_passthrough_agrees_with_utils_wrapper() -> None:
    """The upc_utils wrapper and the core.utils.utils wrapper must return the
    same bool for the same input. A mutation that breaks only one wrapper
    (e.g., a stray ``return`` or a swapped default) is caught here.
    """
    from core import utils

    record = _make_b_record()
    upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
    expected = utils.apply_retail_uom_transform(dict(record), upc_dict)
    assert apply_retail_uom_transform(record, upc_dict) == expected
