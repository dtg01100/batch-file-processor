"""Comprehensive unit tests for utils.py.

Tests cover:
- normalize_bool() - converts any value to Python bool
- to_db_bool() - converts to SQLite integer (0 or 1)
- from_db_bool() - converts DB values to Python bool
- dactime_from_datetime() - converts datetime to DAC time string
- datetime_from_dactime() - converts DAC time string to datetime
- datetime_from_invtime() - converts invoice time string to datetime
- dactime_from_invtime() - converts invoice time string to DAC time
- apply_retail_uom_transform() - transforms B record to each-level retail UOM
- apply_upc_override() - overrides UPC from lookup table
- do_clear_old_files() - removes oldest files when folder exceeds maximum count
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from utils import (
    normalize_bool,
    to_db_bool,
    from_db_bool,
    dactime_from_datetime,
    datetime_from_dactime,
    datetime_from_invtime,
    dactime_from_invtime,
    apply_retail_uom_transform,
    apply_upc_override,
    do_clear_old_files,
)


# =============================================================================
# normalize_bool() tests
# =============================================================================


class TestNormalizeBool:
    """Tests for normalize_bool() function."""

    # --- bool passthrough ---

    def test_true_passthrough(self):
        assert normalize_bool(True) is True

    def test_false_passthrough(self):
        assert normalize_bool(False) is False

    # --- string truthy values ---

    @pytest.mark.parametrize(
        "value",
        ["true", "True", "TRUE", "1", "yes", "on"],
    )
    def test_string_truthy_values(self, value):
        assert normalize_bool(value) is True

    # --- string falsy values ---

    @pytest.mark.parametrize(
        "value",
        ["false", "False", "0", "no", "off", ""],
    )
    def test_string_falsy_values(self, value):
        assert normalize_bool(value) is False

    # --- whitespace handling ---

    def test_whitespace_padded_true(self):
        """Whitespace around 'true' should be stripped before comparison."""
        assert normalize_bool(" true ") is True

    def test_whitespace_only_is_false(self):
        """A string of only whitespace strips to empty string → False."""
        assert normalize_bool("  ") is False

    # --- unrecognized non-empty string ---

    def test_unrecognized_string_is_truthy(self):
        """An unrecognized non-empty string is truthy (bool of non-empty string)."""
        assert normalize_bool("random") is True

    # --- None ---

    def test_none_is_false(self):
        assert normalize_bool(None) is False

    # --- integer values ---

    @pytest.mark.parametrize(
        "value, expected",
        [
            (1, True),
            (0, False),
            (-1, True),
            (42, True),
        ],
    )
    def test_integer_values(self, value, expected):
        assert normalize_bool(value) is expected

    # --- float values ---

    @pytest.mark.parametrize(
        "value, expected",
        [
            (0.0, False),
            (1.5, True),
        ],
    )
    def test_float_values(self, value, expected):
        assert normalize_bool(value) is expected

    # --- list values ---

    def test_empty_list_is_false(self):
        assert normalize_bool([]) is False

    def test_nonempty_list_is_true(self):
        assert normalize_bool([1]) is True

    # --- dict values ---

    def test_empty_dict_is_false(self):
        assert normalize_bool({}) is False

    def test_nonempty_dict_is_true(self):
        assert normalize_bool({"a": 1}) is True

    # --- return type is always bool ---

    def test_return_type_is_bool_for_int(self):
        result = normalize_bool(1)
        assert type(result) is bool

    def test_return_type_is_bool_for_string(self):
        result = normalize_bool("true")
        assert type(result) is bool


# =============================================================================
# to_db_bool() tests
# =============================================================================


class TestToDbBool:
    """Tests for to_db_bool() function."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (True, 1),
            (False, 0),
            ("true", 1),
            ("false", 0),
            (1, 1),
            (0, 0),
            (None, 0),
        ],
    )
    def test_to_db_bool_values(self, value, expected):
        assert to_db_bool(value) == expected

    def test_return_type_is_int_for_true(self):
        result = to_db_bool(True)
        assert type(result) is int

    def test_return_type_is_int_for_false(self):
        result = to_db_bool(False)
        assert type(result) is int

    def test_return_type_is_int_for_string(self):
        result = to_db_bool("true")
        assert type(result) is int

    def test_return_type_is_int_for_none(self):
        result = to_db_bool(None)
        assert type(result) is int

    def test_returns_only_zero_or_one(self):
        """to_db_bool must only ever return 0 or 1."""
        for value in [True, False, "yes", "no", 42, 0, None, [], [1]]:
            result = to_db_bool(value)
            assert result in (0, 1), f"Expected 0 or 1 for {value!r}, got {result!r}"


# =============================================================================
# from_db_bool() tests
# =============================================================================


class TestFromDbBool:
    """Tests for from_db_bool() function."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("True", True),    # legacy string format
            ("False", False),  # legacy string format
            (1, True),         # new integer format
            (0, False),        # new integer format
            ("1", True),       # string integer from DB
            ("0", False),      # string integer from DB
            (None, False),     # NULL in database
        ],
    )
    def test_from_db_bool_values(self, value, expected):
        assert from_db_bool(value) is expected

    def test_return_type_is_bool(self):
        for value in ["True", "False", 1, 0, "1", "0", None]:
            result = from_db_bool(value)
            assert type(result) is bool, (
                f"Expected bool for {value!r}, got {type(result).__name__}"
            )


# =============================================================================
# Date conversion function tests
# =============================================================================


class TestDactimeFromDatetime:
    """Tests for dactime_from_datetime() function."""

    def test_year_2000(self):
        """Year 2000 → century digit 1 (20 - 19 = 1)."""
        dt = datetime(2000, 1, 1)
        result = dactime_from_datetime(dt)
        assert result == "1000101"

    def test_year_1999(self):
        """Year 1999 → century digit 0 (19 - 19 = 0)."""
        dt = datetime(1999, 12, 31)
        result = dactime_from_datetime(dt)
        assert result == "0991231"

    def test_year_2025(self):
        """Year 2025 → century digit 1 (20 - 19 = 1)."""
        dt = datetime(2025, 6, 15)
        result = dactime_from_datetime(dt)
        assert result == "1250615"

    def test_returns_string(self):
        dt = datetime(2020, 3, 5)
        result = dactime_from_datetime(dt)
        assert isinstance(result, str)

    def test_length_is_seven(self):
        dt = datetime(2020, 3, 5)
        result = dactime_from_datetime(dt)
        assert len(result) == 7


class TestDatetimeFromDactime:
    """Tests for datetime_from_dactime() function."""

    def test_dactime_1000101(self):
        """DAC time 1000101 → 2000-01-01."""
        result = datetime_from_dactime(1000101)
        assert result == datetime(2000, 1, 1)

    def test_dactime_0991231(self):
        """DAC time 991231 → 1999-12-31."""
        result = datetime_from_dactime(991231)
        assert result == datetime(1999, 12, 31)

    def test_dactime_1250615(self):
        """DAC time 1250615 → 2025-06-15."""
        result = datetime_from_dactime(1250615)
        assert result == datetime(2025, 6, 15)

    def test_returns_datetime(self):
        result = datetime_from_dactime(1000101)
        assert isinstance(result, datetime)

    def test_roundtrip_with_dactime_from_datetime(self):
        """dactime_from_datetime and datetime_from_dactime should be inverses."""
        original = datetime(2023, 7, 4)
        dactime_str = dactime_from_datetime(original)
        recovered = datetime_from_dactime(int(dactime_str))
        assert recovered == original


class TestDatetimeFromInvtime:
    """Tests for datetime_from_invtime() function."""

    def test_basic_date(self):
        """'010125' → January 1, 2025."""
        result = datetime_from_invtime("010125")
        assert result == datetime(2025, 1, 1)

    def test_december_date(self):
        """'123124' → December 31, 2024."""
        result = datetime_from_invtime("123124")
        assert result == datetime(2024, 12, 31)

    def test_returns_datetime(self):
        result = datetime_from_invtime("060523")
        assert isinstance(result, datetime)

    def test_format_mmddyy(self):
        """Verify the format is MMDDYY."""
        result = datetime_from_invtime("030422")
        assert result.month == 3
        assert result.day == 4
        assert result.year == 2022


class TestDactimeFromInvtime:
    """Tests for dactime_from_invtime() function."""

    def test_basic_conversion(self):
        """'010125' (Jan 1, 2025) → '1250101'."""
        result = dactime_from_invtime("010125")
        assert result == "1250101"

    def test_december_conversion(self):
        """'123124' (Dec 31, 2024) → '1241231'."""
        result = dactime_from_invtime("123124")
        assert result == "1241231"

    def test_returns_string(self):
        result = dactime_from_invtime("060523")
        assert isinstance(result, str)

    def test_length_is_seven(self):
        result = dactime_from_invtime("060523")
        assert len(result) == 7

    def test_consistent_with_component_functions(self):
        """dactime_from_invtime should equal dactime_from_datetime(datetime_from_invtime(x))."""
        invtime = "091523"
        expected = dactime_from_datetime(datetime_from_invtime(invtime))
        assert dactime_from_invtime(invtime) == expected


# =============================================================================
# apply_retail_uom_transform() tests
# =============================================================================


class TestApplyRetailUomTransform:
    """Tests for apply_retail_uom_transform() function."""

    def _make_record(
        self,
        vendor_item="000123",
        unit_cost="001200",
        unit_multiplier="000012",
        qty_of_units="00010",
        upc_number="00000000000",
    ):
        """Build a minimal B record dict."""
        return {
            "vendor_item": vendor_item,
            "unit_cost": unit_cost,
            "unit_multiplier": unit_multiplier,
            "qty_of_units": qty_of_units,
            "upc_number": upc_number,
        }

    def test_basic_transformation_applies(self):
        """A valid record with a matching UPC should be transformed."""
        record = self._make_record(
            vendor_item="000123",
            unit_cost="001200",
            unit_multiplier="000012",
            qty_of_units="00010",
        )
        upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
        result = apply_retail_uom_transform(record, upc_dict)
        assert result is True

    def test_basic_transformation_modifies_unit_multiplier(self):
        """After transformation, unit_multiplier should be '000001'."""
        record = self._make_record(
            vendor_item="000123",
            unit_cost="001200",
            unit_multiplier="000012",
            qty_of_units="00010",
        )
        upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
        apply_retail_uom_transform(record, upc_dict)
        assert record["unit_multiplier"] == "000001"

    def test_basic_transformation_updates_upc(self):
        """After transformation, upc_number should come from the lookup."""
        record = self._make_record(
            vendor_item="000123",
            unit_cost="001200",
            unit_multiplier="000012",
            qty_of_units="00010",
        )
        upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
        apply_retail_uom_transform(record, upc_dict)
        assert record["upc_number"] == "12345678901"

    def test_basic_transformation_multiplies_qty(self):
        """qty_of_units should be multiplied by unit_multiplier."""
        record = self._make_record(
            vendor_item="000123",
            unit_cost="001200",
            unit_multiplier="000012",
            qty_of_units="00010",
        )
        upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
        apply_retail_uom_transform(record, upc_dict)
        # 12 * 10 = 120
        assert int(record["qty_of_units"]) == 120

    def test_no_match_in_upc_dict_returns_true(self):
        """When vendor_item is not in upc_dict, transform still applies but uses blank UPC."""
        record = self._make_record(
            vendor_item="000999",
            unit_cost="001200",
            unit_multiplier="000012",
            qty_of_units="00010",
        )
        upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
        result = apply_retail_uom_transform(record, upc_dict)
        # No match → blank UPC, but transformation still proceeds
        assert result is True
        assert record["upc_number"] == "           "  # 11 spaces

    def test_zero_multiplier_returns_false(self):
        """A zero unit_multiplier should cause the function to return False."""
        record = self._make_record(
            vendor_item="000123",
            unit_cost="001200",
            unit_multiplier="000000",
            qty_of_units="00010",
        )
        upc_dict = {123: ["GROCERY", "12345678901", "00000000000"]}
        result = apply_retail_uom_transform(record, upc_dict)
        assert result is False

    def test_unparseable_vendor_item_returns_false(self):
        """Non-numeric vendor_item should cause the function to return False."""
        record = self._make_record(vendor_item="ABCDEF")
        upc_dict = {}
        result = apply_retail_uom_transform(record, upc_dict)
        assert result is False

    def test_unparseable_unit_cost_returns_false(self):
        """Non-numeric unit_cost should cause the function to return False."""
        record = self._make_record(unit_cost="XXXXXX")
        upc_dict = {}
        result = apply_retail_uom_transform(record, upc_dict)
        assert result is False

    def test_empty_upc_dict_uses_blank_upc(self):
        """Empty upc_dict should result in blank UPC but successful transform."""
        record = self._make_record(
            vendor_item="000123",
            unit_cost="001200",
            unit_multiplier="000006",
            qty_of_units="00005",
        )
        result = apply_retail_uom_transform(record, {})
        assert result is True
        assert record["upc_number"] == "           "  # 11 spaces


# =============================================================================
# apply_upc_override() tests
# =============================================================================


class TestApplyUpcOverride:
    """Tests for apply_upc_override() function."""

    def _make_record(self, vendor_item="000123", upc_number="00000000000"):
        return {"vendor_item": vendor_item, "upc_number": upc_number}

    def test_override_with_all_category_filter(self):
        """With category_filter='ALL', override should always apply."""
        record = self._make_record(vendor_item="000123")
        upc_dict = {123: ["GROCERY", "12345678901", "99999999999"]}
        result = apply_upc_override(record, upc_dict, override_level=1, category_filter="ALL")
        assert result is True
        assert record["upc_number"] == "12345678901"

    def test_override_with_specific_category_match(self):
        """When item's category is in the filter list, override should apply."""
        record = self._make_record(vendor_item="000123")
        upc_dict = {123: ["GROCERY", "12345678901", "99999999999"]}
        result = apply_upc_override(
            record, upc_dict, override_level=1, category_filter="GROCERY,DAIRY"
        )
        assert result is True
        assert record["upc_number"] == "12345678901"

    def test_override_with_category_filter_no_match(self):
        """When item's category is NOT in the filter list, override should not apply."""
        record = self._make_record(vendor_item="000123")
        upc_dict = {123: ["GROCERY", "12345678901", "99999999999"]}
        result = apply_upc_override(
            record, upc_dict, override_level=1, category_filter="DAIRY,FROZEN"
        )
        assert result is False
        # upc_number should remain unchanged when no override applied
        assert record["upc_number"] == "00000000000"

    def test_upc_not_in_dict_returns_false(self):
        """When vendor_item is not in upc_dict, return False and clear upc_number."""
        record = self._make_record(vendor_item="000999")
        upc_dict = {123: ["GROCERY", "12345678901", "99999999999"]}
        result = apply_upc_override(record, upc_dict, override_level=1, category_filter="ALL")
        assert result is False
        assert record["upc_number"] == ""

    def test_empty_upc_dict_returns_false(self):
        """Empty upc_dict should return False immediately."""
        record = self._make_record(vendor_item="000123")
        result = apply_upc_override(record, {}, override_level=1, category_filter="ALL")
        assert result is False

    def test_override_level_selects_correct_upc(self):
        """override_level should select the correct index from the lookup list."""
        record = self._make_record(vendor_item="000123")
        upc_dict = {123: ["GROCERY", "11111111111", "22222222222", "33333333333"]}
        apply_upc_override(record, upc_dict, override_level=2, category_filter="ALL")
        assert record["upc_number"] == "22222222222"

    def test_default_override_level_is_1(self):
        """Default override_level should be 1."""
        record = self._make_record(vendor_item="000123")
        upc_dict = {123: ["GROCERY", "11111111111", "22222222222"]}
        apply_upc_override(record, upc_dict, category_filter="ALL")
        assert record["upc_number"] == "11111111111"

    def test_default_category_filter_is_all(self):
        """Default category_filter should be 'ALL'."""
        record = self._make_record(vendor_item="000123")
        upc_dict = {123: ["GROCERY", "11111111111"]}
        result = apply_upc_override(record, upc_dict)
        assert result is True

    def test_non_numeric_vendor_item_returns_false(self):
        """Non-numeric vendor_item should be handled gracefully."""
        record = self._make_record(vendor_item="ABCDEF")
        upc_dict = {123: ["GROCERY", "12345678901"]}
        result = apply_upc_override(record, upc_dict, category_filter="ALL")
        assert result is False


# =============================================================================
# do_clear_old_files() tests
# =============================================================================


class TestDoClearOldFiles:
    """Tests for do_clear_old_files() function.

    do_clear_old_files(folder_path, maximum_files) removes the oldest files
    (by ctime) until the folder contains at most maximum_files files.
    """

    def test_no_files_removed_when_at_limit(self, tmp_path):
        """When file count equals maximum_files, nothing should be removed."""
        for i in range(3):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")
        do_clear_old_files(str(tmp_path), 3)
        assert len(list(tmp_path.iterdir())) == 3

    def test_no_files_removed_when_below_limit(self, tmp_path):
        """When file count is below maximum_files, nothing should be removed."""
        for i in range(2):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")
        do_clear_old_files(str(tmp_path), 5)
        assert len(list(tmp_path.iterdir())) == 2

    def test_removes_files_to_reach_limit(self, tmp_path):
        """When file count exceeds maximum_files, files should be removed."""
        for i in range(5):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")
        do_clear_old_files(str(tmp_path), 3)
        assert len(list(tmp_path.iterdir())) == 3

    def test_removes_all_files_when_limit_is_zero(self, tmp_path):
        """When maximum_files is 0, all files should be removed."""
        for i in range(4):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")
        do_clear_old_files(str(tmp_path), 0)
        assert len(list(tmp_path.iterdir())) == 0

    def test_empty_folder_does_nothing(self, tmp_path):
        """An empty folder should not raise any errors."""
        do_clear_old_files(str(tmp_path), 3)
        assert len(list(tmp_path.iterdir())) == 0

    def test_removes_oldest_file_by_ctime(self, tmp_path):
        """The oldest file (by ctime) should be removed first."""
        import time

        # Create files with distinct ctimes by patching os.path.getctime
        file_a = tmp_path / "file_a.txt"
        file_b = tmp_path / "file_b.txt"
        file_c = tmp_path / "file_c.txt"
        file_a.write_text("a")
        file_b.write_text("b")
        file_c.write_text("c")

        ctime_map = {
            str(tmp_path / "file_a.txt"): 1000.0,  # oldest
            str(tmp_path / "file_b.txt"): 2000.0,
            str(tmp_path / "file_c.txt"): 3000.0,  # newest
        }

        original_getctime = os.path.getctime

        def mock_getctime(path):
            return ctime_map.get(path, original_getctime(path))

        with patch("os.path.getctime", side_effect=mock_getctime):
            do_clear_old_files(str(tmp_path), 2)

        remaining = {f.name for f in tmp_path.iterdir()}
        assert "file_a.txt" not in remaining
        assert len(remaining) == 2
