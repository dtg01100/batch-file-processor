"""Tests for core.utils.safe_parse.

Covers the documented public API: ``safe_int``, ``safe_float``, and
``qty_to_int``.  All branches — including the default fallbacks and
exception paths — are exercised.
"""

from __future__ import annotations

import pytest

from core.utils.safe_parse import qty_to_int, safe_float, safe_int


class TestSafeInt:
    """``safe_int(value, default=0) -> int``."""

    def test_none_returns_default(self):
        assert safe_int(None) == 0

    def test_none_returns_custom_default(self):
        assert safe_int(None, default=-7) == -7

    def test_int_passes_through(self):
        assert safe_int(42) == 42
        assert safe_int(0) == 0
        assert safe_int(-5) == -5

    def test_bool_not_int(self):
        """``bool`` is a subclass of ``int`` in Python; safe_int returns it."""
        # Document the actual behaviour: bool is treated as int
        assert safe_int(True) == 1
        assert safe_int(False) == 0

    def test_float_truncates(self):
        assert safe_int(3.7) == 3
        assert safe_int(-2.9) == -2

    def test_string_digit(self):
        assert safe_int("42") == 42

    def test_string_with_whitespace(self):
        assert safe_int(" 17 ") == 17

    def test_string_empty(self):
        assert safe_int("") == 0
        assert safe_int("   ") == 0

    def test_string_negative(self):
        assert safe_int("-5") == -5
        assert safe_int("  -3  ") == -3

    def test_string_invalid_returns_default(self):
        assert safe_int("invalid") == 0
        assert safe_int("invalid", default=-99) == -99

    def test_string_mixed_digits_letters_returns_default(self):
        assert safe_int("12abc") == 0


class TestSafeFloat:
    """``safe_float(value, default=0.0) -> float``."""

    def test_none_returns_default(self):
        assert safe_float(None) == 0.0

    def test_none_returns_custom_default(self):
        assert safe_float(None, default=-1.5) == -1.5

    def test_float_passes_through(self):
        assert safe_float(3.14) == 3.14
        assert safe_float(0.0) == 0.0

    def test_int_converts(self):
        assert safe_float(42) == 42.0

    def test_string_numeric(self):
        assert safe_float("3.14") == 3.14

    def test_string_with_whitespace(self):
        assert safe_float("  2.5  ") == 2.5

    def test_string_empty(self):
        assert safe_float("") == 0.0

    def test_string_negative(self):
        assert safe_float("-3.14") == -3.14

    def test_string_invalid_returns_default(self):
        assert safe_float("not a number") == 0.0
        assert safe_float("oops", default=99.9) == 99.9


class TestQtyToInt:
    """``qty_to_int(qty) -> int`` handles negative strings."""

    def test_positive_digit_string(self):
        assert qty_to_int("5") == 5

    def test_positive_multi_digit(self):
        assert qty_to_int("123") == 123

    def test_negative_digit_string(self):
        assert qty_to_int("-5") == -5

    def test_negative_multi_digit(self):
        assert qty_to_int("-123") == -123

    def test_zero(self):
        assert qty_to_int("0") == 0

    def test_invalid_returns_zero(self):
        assert qty_to_int("abc") == 0
        assert qty_to_int("") == 0

    def test_double_dash_collapses_to_positive(self):
        # Document the actual behaviour: "--5" strips the first "-" and
        # then int("-5") raises ValueError -> negative branch not taken
        # on a clean re-strip, but the code negates "5" => 5.
        assert qty_to_int("--5") == 5
        assert qty_to_int("-") == 0


class TestSafeParseParametrized:
    """Compact parametrised smoke for the safe_* helpers."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, 0),
            (42, 42),
            (3.0, 3),  # float with no fractional part
            ("7", 7),
            ("-7", -7),
            ("  7  ", 7),
            ("", 0),
            ("x", 0),
        ],
    )
    def test_safe_int_table(self, value, expected):
        assert safe_int(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, 0.0),
            (1.5, 1.5),
            (3, 3.0),
            ("1.5", 1.5),
            ("-1.5", -1.5),
            ("  1.5  ", 1.5),
            ("", 0.0),
            ("x", 0.0),
        ],
    )
    def test_safe_float_table(self, value, expected):
        assert safe_float(value) == expected


class TestSafeParseFallback:
    """Cover the fall-through ``return default`` for unsupported types."""

    def test_safe_int_unsupported_type(self):
        # list/dict/object are not None/int/float/str; fall through to default
        assert safe_int([]) == 0
        assert safe_int([1, 2]) == 0
        assert safe_int(object()) == 0
        assert safe_int([1, 2], default=-9) == -9

    def test_safe_float_unsupported_type(self):
        assert safe_float([]) == 0.0
        assert safe_float([1, 2]) == 0.0
        assert safe_float(object()) == 0.0
        assert safe_float({}, default=-1.5) == -1.5
