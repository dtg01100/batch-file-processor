"""Property-based tests for core.edi.edi_transformer.

Exercises the pure price-formatting helpers across broad input spaces,
plus the file-backed `detect_invoice_is_credit` paths.
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
    detect_invoice_is_credit,
)

pytestmark = [pytest.mark.unit, pytest.mark.edi, pytest.mark.property]


_DIGITS = st.characters(whitelist_categories=("Nd",))
_DIGIT_STRINGS = st.text(alphabet=_DIGITS, min_size=1, max_size=12)
_NONEMPTY_DIGIT_STRINGS = st.text(alphabet=_DIGITS, min_size=1, max_size=12)


# A canonical positive A-record EDI line (33 chars + newline).
# Length breakdown matches core.constants EDI_A_RECORD widths.
_POS_A_LINE = "AVENDOR0000000001120240000000123\n"


def _write_edi(tmp_path, first_line: str) -> str:
    """Write a one-line EDI file under `tmp_path` and return its path."""
    p = tmp_path / "test.edi"
    p.write_text(first_line)
    return str(p)


@settings(max_examples=200)
@given(s=st.text(alphabet=_DIGITS, min_size=2, max_size=2))
def test_convert_to_price_decimal_two_digit_input_is_decimal(s: str) -> None:
    """A 2-digit input reaches the Decimal branch (not the early `return 0`).

    Pins the `<` vs `<=` boundary in convert_to_price_decimal against
    PRICE_DECIMAL_PLACES (= 2). With `<=` mutated, length exactly 2
    would return 0 (not Decimal), so this test catches it.
    """
    from core.constants import PRICE_DECIMAL_PLACES

    assert len(s) >= PRICE_DECIMAL_PLACES
    result = convert_to_price_decimal(s)
    assert isinstance(result, Decimal), (
        f"len(input)=len(s) at PRICE_DECIMAL_PLACES should return Decimal, "
        f"got {result!r} (type {type(result).__name__})"
    )


def test_detect_invoice_is_credit_returns_bool_for_a_record(tmp_path) -> None:
    """An A-record input yields a bool from detect_invoice_is_credit.

    Pins the `!= "A"` vs `== "A"` mutation at line 75: with the
    mutation, an A record would enter the raise branch and crash;
    this test asserts detect_invoice_is_credit returns normally.
    """
    edi_path = _write_edi(tmp_path, _POS_A_LINE)
    result = detect_invoice_is_credit(edi_path)
    assert isinstance(result, bool)
    assert result is False


def test_detect_invoice_is_credit_raises_on_non_a_first_line(tmp_path) -> None:
    """A first line whose first char is not 'A' and not ' ' raises ValueError.

    Pins line 69 `and_to_or`: with the mutation, `first_line or ...`
    is always truthy, so the raise fires for every non-None-fields
    case. With original code, this test asserts the malformed-input
    raise path actually triggers and produces the cited message.
    Pins line 75 transitively: the L75 raise branch is the same
    family; even though this test exercises L69 primarily, it
    documents the contract.
    """
    edi_path = _write_edi(tmp_path, "ZNOT_EDI_LINE\n")
    with pytest.raises(ValueError, match="does not start with A record"):
        detect_invoice_is_credit(edi_path)


def test_detect_invoice_is_credit_returns_false_on_missing_file(tmp_path) -> None:
    """A missing file path is caught; detect_invoice_is_credit returns False.

    Pins line 59 `false_to_true`: in the except OSError branch, the
    function MUST return False (not True). The L59 mutation flips
    the return — a downstream caller checking "is credit" would
    incorrectly process a missing file as a credit note.

    Also pins line 22 indirectly (the catch handler is otherwise a
    no-op for non-OS exceptions, which are not caught here).
    """
    missing = tmp_path / "does-not-exist.edi"
    assert not missing.exists()  # sanity: test assumes tmp_path did not create it
    result = detect_invoice_is_credit(str(missing))
    assert result is False


def test_detect_invoice_is_credit_blank_first_line_returns_false(tmp_path) -> None:
    """A blank/whitespace first line yields False (no raise).

    Pins line 69 `and_to_or`: original code is `if first_line and
    first_line[0] not in ("A", " "):`. With the mutation to `or`,
    `first_line` (empty string) is falsy but `first_line[0]` would
    be evaluated and raise IndexError. This test feeds a blank
    first line and asserts the function returns False normally.
    """
    edi_path = _write_edi(tmp_path, "   \n")
    result = detect_invoice_is_credit(edi_path)
    assert result is False


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
