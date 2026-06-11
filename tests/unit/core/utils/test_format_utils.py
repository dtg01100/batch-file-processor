"""Tests for core.utils.format_utils."""

from __future__ import annotations

from core.utils.format_utils import normalize_convert_to_format


class TestNormalizeConvertToFormat:
    """``normalize_convert_to_format(value) -> str``."""

    def test_none_returns_empty(self):
        assert normalize_convert_to_format(None) == ""

    def test_lowercases(self):
        assert normalize_convert_to_format("FOO") == "foo"
        assert normalize_convert_to_format("FooBar") == "foobar"

    def test_strips_whitespace(self):
        assert normalize_convert_to_format("  hello  ") == "hello"

    def test_replaces_spaces_with_underscore(self):
        assert normalize_convert_to_format("hello world") == "hello_world"

    def test_replaces_hyphens_with_underscore(self):
        assert normalize_convert_to_format("hello-world") == "hello_world"

    def test_collapses_multiple_underscores(self):
        assert normalize_convert_to_format("hello__world") == "hello_world"
        assert normalize_convert_to_format("a___b") == "a_b"

    def test_replaces_non_alphanumeric_with_underscore(self):
        assert normalize_convert_to_format("hello.world") == "hello_world"
        assert normalize_convert_to_format("hello!world") == "hello_world"
        assert normalize_convert_to_format("a&b#c") == "a_b_c"

    def test_strips_leading_and_trailing_underscores(self):
        assert normalize_convert_to_format("__hello__") == "hello"
        assert normalize_convert_to_format("-hello-") == "hello"
        assert normalize_convert_to_format("!hello!") == "hello"

    def test_estore_einvoice(self):
        """Document the canonical example from the docstring."""
        assert normalize_convert_to_format("Estore eInvoice") == "estore_einvoice"

    def test_tweaks_with_whitespace(self):
        """Document the canonical example from the docstring."""
        assert normalize_convert_to_format("  Tweaks  ") == "tweaks"

    def test_empty_string(self):
        assert normalize_convert_to_format("") == ""

    def test_only_underscores(self):
        assert normalize_convert_to_format("___") == ""

    def test_only_punctuation(self):
        assert normalize_convert_to_format("!!!") == ""

    def test_numbers_preserved(self):
        assert normalize_convert_to_format("foo123") == "foo123"

    def test_int_input(self):
        # Non-string inputs are coerced to str first
        assert normalize_convert_to_format(42) == "42"

    def test_combined(self):
        assert (
            normalize_convert_to_format("  Scansheet Type-A!  ") == "scansheet_type_a"
        )
