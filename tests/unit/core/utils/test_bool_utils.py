"""Unit tests for bool utility functions."""

import pytest

from core.utils.bool_utils import from_db_bool, normalize_bool, to_db_bool


class TestNormalizeBool:
    """Tests for normalize_bool."""

    @pytest.mark.parametrize(
        "value",
        ["true", "TRUE", " yes ", "1", "on"],
    )
    def test_truthy_strings(self, value):
        """Truthy string values normalize to True."""
        assert normalize_bool(value) is True

    @pytest.mark.parametrize(
        "value",
        ["false", "FALSE", " no ", "0", "off", "", "   "],
    )
    def test_falsy_strings(self, value):
        """Falsy string values normalize to False."""
        assert normalize_bool(value) is False

    @pytest.mark.parametrize("value", ["abc", " y ", "T"])
    def test_non_empty_unknown_strings_are_truthy(self, value):
        """Unknown non-empty strings default to truthy."""
        assert normalize_bool(value) is True

    def test_none_is_false(self):
        """None normalizes to False."""
        assert normalize_bool(None) is False

    @pytest.mark.parametrize(
        "value,expected",
        [(0, False), (1, True), (-1, True), (0.0, False), (0.1, True)],
    )
    def test_numbers(self, value, expected):
        """Numeric values follow Python truthiness."""
        assert normalize_bool(value) is expected

    @pytest.mark.parametrize(
        "value,expected",
        [([], False), ([1], True), ({}, False), ({"k": "v"}, True)],
    )
    def test_containers(self, value, expected):
        """Containers follow Python truthiness."""
        assert normalize_bool(value) is expected


class TestDbBoolConversions:
    """Tests for to_db_bool and from_db_bool."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (True, 1),
            (False, 0),
            ("true", 1),
            ("false", 0),
            ("1", 1),
            ("0", 0),
            (None, 0),
            ([1], 1),
            ([], 0),
        ],
    )
    def test_to_db_bool(self, value, expected):
        """to_db_bool returns integer 0/1."""
        assert to_db_bool(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1, True),
            (0, False),
            ("True", True),
            ("False", False),
            ("1", True),
            ("0", False),
            (None, False),
        ],
    )
    def test_from_db_bool(self, value, expected):
        """from_db_bool normalizes legacy and integer DB forms."""
        assert from_db_bool(value) is expected
