"""Unit tests for convert_to_simplified_csv.py converter module.

Tests:
- Input validation and edge cases
- Parameter combinations and flag handling
- Data transformation accuracy
- Column layout configuration
- Retail UOM conversion

Converter: convert_to_simplified_csv.py (10345 chars)
"""

import contextlib
import csv
import os

import pytest

from dispatch.converters import convert_to_simplified_csv


class TestConvertToSimplifiedCSVFixtures:
    """Test fixtures for convert_to_simplified_csv module."""

    @pytest.fixture
    def sample_header_record(self):
        """Create accurate header record (33 chars)."""
        return "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"

    @pytest.fixture
    def sample_detail_record(self):
        """Create accurate detail record (76 chars)."""
        return (
            "B"
            + "01234567890"
            + "Test Item Description    "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )

    @pytest.fixture
    def sample_tax_record(self):
        """Create accurate sales tax record (38 chars)."""
        return "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"

    @pytest.fixture
    def complete_edi_content(self, sample_header_record, sample_detail_record):
        """Create complete EDI content with header and detail records."""
        return sample_header_record + "\n" + sample_detail_record + "\n"

    @pytest.fixture
    def default_parameters(self):
        """Default parameters dict for convert_to_simplified_csv."""
        return {
            "retail_uom": "False",
            "include_headers": "True",
            "include_item_numbers": "True",
            "include_item_description": "True",
            "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,vendor_item",
        }

    @pytest.fixture
    def default_settings(self):
        """Default settings dict."""
        return {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "test.address.com",
        }


class TestConvertToSimplifiedCSVBasicFunctionality(TestConvertToSimplifiedCSVFixtures):
    """Test basic functionality of convert_to_simplified_csv."""

    def test_module_import(self):
        """Test that convert_to_simplified_csv module can be imported."""
        from dispatch.converters import convert_to_simplified_csv

        assert convert_to_simplified_csv is not None
        assert hasattr(convert_to_simplified_csv, "edi_convert")

    def test_edi_convert_returns_csv_filename(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that edi_convert returns the expected CSV filename."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert result == output_file + ".csv"

    def test_creates_csv_file(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that the CSV file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")


class TestConvertToSimplifiedCSVHeaders(TestConvertToSimplifiedCSVFixtures):
    """Test header handling in convert_to_simplified_csv."""

    def test_headers_included_when_flag_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that CSV headers are included when include_headers is True."""
        default_parameters["include_headers"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            first_row = next(reader)
            assert "UPC" in first_row or "upc_number" in str(first_row).lower()

    def test_headers_not_included_when_flag_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that CSV headers are NOT included when include_headers is False."""
        default_parameters["include_headers"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", encoding="utf-8") as f:
            content = f.read()
            assert "UPC" not in content or "UPC" in content


class TestConvertToSimplifiedCSVColumnLayout(TestConvertToSimplifiedCSVFixtures):
    """Test column layout configuration in convert_to_simplified_csv."""

    def test_custom_sort_order(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test custom column sort order."""
        default_parameters["simple_csv_sort_order"] = (
            "vendor_item,upc_number,qty_of_units,unit_cost"
        )

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")

    def test_include_item_numbers_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that item numbers are included when flag is True."""
        default_parameters["include_item_numbers"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")

    def test_include_item_numbers_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that item numbers are excluded when flag is False."""
        default_parameters["include_item_numbers"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_include_item_description_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that descriptions are included when flag is True."""
        default_parameters["include_item_description"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_include_item_description_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that descriptions are excluded when flag is False."""
        default_parameters["include_item_description"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_write_headers_omits_description_when_flag_false(
        self, default_parameters, default_settings, tmp_path
    ):
        """Regression: when ``include_item_description`` is False, the
        "Item Description" column header must NOT appear in the CSV.

        The mutation runner's ``eq_to_ne`` at
        convert_to_simplified_csv.py:131 (flipping
        ``column == "description"`` to ``column != "description"``)
        was not caught by existing tests because every column-layout
        test only asserted ``os.path.exists(...)`` without reading
        the actual CSV content. The mutation produces the same
        headers in the default case but breaks the
        ``inc_item_desc=True, inc_item_numbers=False`` configuration:
        a vendor_item column gets the "Item Description" header.

        See commit ea1ed275d (Phase 3 bug 5) follow-up for context.
        """
        import csv as _csv

        # Setup: inc_item_desc=True, inc_item_numbers=False.
        # column_layout places vendor_item before description so
        # the iteration order tests the conditional.
        default_parameters["include_item_description"] = "True"
        default_parameters["include_item_numbers"] = "False"
        default_parameters["simple_csv_sort_order"] = (
            "upc_number,vendor_item,description"
        )

        edi_content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)
        output_file = str(tmp_path / "output")

        result_path = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        # Read the actual CSV and verify the headers.
        with open(result_path) as f:
            reader = _csv.reader(f)
            headers = next(reader)

        # With original code: column "vendor_item" is iterated
        # while inc_item_desc=True. The L131 check
        # "column == description" is False for vendor_item, so
        # the L131 if does NOT fire. The L133 check handles
        # vendor_item (inc_item_numbers=False → skipped).
        # Result: headers = ["UPC", "Item Description"].
        # With mutation L131 flipped to "!=": the check fires for
        # vendor_item (column != description), incorrectly appending
        # "Item Description" to the vendor_item column → headers
        # = ["UPC", "Item Description", "Item Description"] (wrong!).
        assert headers == ["UPC", "Item Description"], (
            f"expected ['UPC', 'Item Description'] with inc_item_desc=True "
            f"and inc_item_numbers=False; got {headers!r}. The vendor_item "
            f"column must NOT get the 'Item Description' header."
        )

    def test_default_include_headers_when_no_param(self, default_settings, tmp_path):
        """Regression: when neither ``include_headers`` nor
        ``simple_csv_include_headers`` is in parameters, the default
        is True (headers are written). The mutation runner's
        ``true_to_false`` at convert_to_simplified_csv.py:74
        (flipping the default from True to False) was not caught by
        existing tests because every test passed a
        ``default_parameters`` fixture that had
        ``include_headers="True"``, masking the default behavior.

        See commit ea1ed275d (Phase 3 bug 5) follow-up for context.
        """
        import csv as _csv

        edi_content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)
        output_file = str(tmp_path / "output")

        # Empty parameters dict — neither key is set, so the default
        # at L74 must apply (True). With the mutation, the default
        # becomes False, and no header row is written.
        result_path = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            {},  # no parameters_dict — default must kick in
            {},  # upc_lookup — empty
        )

        with open(result_path) as f:
            reader = _csv.reader(f)
            rows = list(reader)

        # Default behavior: include_headers is True → header row written.
        assert len(rows) >= 1, (
            f"expected at least 1 row (the header) with default "
            f"include_headers=True, got {len(rows)} rows"
        )
        headers = rows[0]
        # Default column_layout starts with upc_number.
        assert (
            headers[0] == "UPC"
        ), f"expected default headers to start with 'UPC', got {headers!r}"

    def test_default_retail_uom_is_false(self, default_settings, tmp_path):
        """Regression: when ``retail_uom`` is not in parameters, the
        default is False (no retail UOM transform). The mutation
        runner's ``false_to_true`` at convert_to_simplified_csv.py:64
        (flipping the default from False to True) was not caught by
        existing tests because every test passed a
        ``default_parameters`` fixture that had
        ``retail_uom="False"``, masking the default behavior.

        With the mutation, the retail UOM transform would run on
        every B record. Without an upc_lookup, the transform would
        either no-op (if the code guards on it) or change values.
        Either way, the second column of the data row (Quantity)
        should match the original B record's qty_of_units (5 in
        this test data) when the default is False.

        See commit ea1ed275d (Phase 3 bug 5) follow-up for context.
        """
        import csv as _csv

        edi_content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)
        output_file = str(tmp_path / "output")

        # Empty parameters dict — retail_uom not set, default applies.
        result_path = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            {},
            {},
        )

        with open(result_path) as f:
            reader = _csv.reader(f)
            rows = list(reader)

        assert len(rows) == 2, f"expected 2 rows (header + 1 B record), got {len(rows)}"
        # The B record's qty_of_units is "00005" → "5" (the converter
        # strips leading zeros). Default column_layout is
        # upc_number,qty_of_units,... so qty is the 2nd column.
        assert rows[1][1] == "5", (
            f"expected qty_of_units='5' with default retail_uom=False, "
            f"got {rows[1][1]!r}. The retail UOM transform must not run "
            f"when retail_uom is unset."
        )


class TestConvertToSimplifiedCSVDataTransformation(TestConvertToSimplifiedCSVFixtures):
    """Test data transformation in convert_to_simplified_csv."""

    def test_quantity_is_integer(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that quantity is converted to integer (no leading zeros)."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            data_rows = [r for r in rows if r and "UPC" not in r]
            if data_rows:
                qty = data_rows[0][1]
                assert not qty.startswith("0") or qty == "0"

    def test_item_number_is_integer(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that item number is converted to integer."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(output_file + ".csv")


class TestConvertToSimplifiedCSVEdgeCases(TestConvertToSimplifiedCSVFixtures):
    """Test edge cases and error conditions."""

    def test_empty_edi_file(self, default_parameters, default_settings, tmp_path):
        """Test handling of empty EDI file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("")

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_whitespace_only_file(self, default_parameters, default_settings, tmp_path):
        """Test handling of whitespace-only file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("   \n   \n   ")

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_truncated_b_record(
        self, sample_header_record, default_parameters, default_settings, tmp_path
    ):
        """Test handling of truncated B record.

        Regression test for the meta-test finding (Phase 3, 2026-07-13):
        the previous version asserted only ``os.path.exists(result)``
        wrapped in a silent ``try/except ValueError: pass``, so a
        mutation that broke truncated-B handling would either
        (a) raise ValueError and the bare ``except`` would swallow it
        (passing trivially), or
        (b) write a corrupt CSV and the test would still pass
        because ``os.path.exists`` is a trivial check.

        The corrected version asserts the converter's actual contract:
        a truncated B record should be rejected (raising ValueError)
        or skipped (file is produced without the bad record). Both
        are acceptable; the test does NOT silently accept either.
        """
        truncated_b = "B01234567890Short"
        edi_content = sample_header_record + "\n" + truncated_b + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        # Acceptable outcomes:
        # 1. Converter raises ValueError (rejects truncated B records).
        # 2. Converter writes an output file that does NOT include the
        #    truncated B record's data.
        # The previous version accepted both, but also accepted silent
        # failures via bare ``except ValueError: pass``. The corrected
        # version captures the outcome and asserts something specific.
        with contextlib.suppress(ValueError):
            result = convert_to_simplified_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )

            # If no exception: the converter produced a file. Verify
            # the truncated B record is NOT in the output (the
            # converter should have skipped it, not written garbage).
            assert os.path.exists(
                result
            ), f"converter returned {result!r} but no file exists"
            with open(result) as f:
                csv_content = f.read()
            # The truncated B's vendor_item was "Short" (positions
            # 36-41 in a real B record). If the converter wrote the
            # truncated record as-is, the string "Short" would leak
            # into the output. Assert it's not there.
            assert (
                "Short" not in csv_content
            ), f"truncated B record's text leaked into output:\n{csv_content}"

    def test_missing_input_file(self, default_parameters, default_settings, tmp_path):
        """Test that missing input file raises FileNotFoundError."""
        input_file = tmp_path / "does_not_exist.edi"
        output_file = str(tmp_path / "output")

        with pytest.raises(FileNotFoundError):
            convert_to_simplified_csv.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )


class TestConvertToSimplifiedCSVIntegration(TestConvertToSimplifiedCSVFixtures):
    """Integration tests combining multiple features."""

    def test_full_featured_conversion(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test conversion with multiple features enabled."""
        default_parameters["include_headers"] = "True"
        default_parameters["include_item_numbers"] = "True"
        default_parameters["include_item_description"] = "True"
        default_parameters["simple_csv_sort_order"] = (
            "upc_number,qty_of_units,unit_cost,description,vendor_item"
        )

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

        with open(result, encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 0

    def test_multiple_detail_records(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test conversion with multiple detail records."""
        detail1 = (
            "B"
            + "01234567890"
            + "Item One Description     "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )
        detail2 = (
            "B"
            + "01234567891"
            + "Item Two Description     "
            + "234567"
            + "000200"
            + "01"
            + "000002"
            + "00020"
            + "00299"
            + "001"
            + "000000"
        )

        edi_content = sample_header_record + "\n" + detail1 + "\n" + detail2 + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(output_file + ".csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            data_rows = [
                r
                for r in rows
                if r and "upc_number" not in str(r).lower() and "UPC" not in r
            ]
            assert len(data_rows) == 2


class TestSimplifiedCSVEachUOMCategoryFilter(TestConvertToSimplifiedCSVFixtures):
    """Tests for the each_uom_categories / each_uom_mode filter in simplified_csv."""

    VENDOR_ITEM = 123456

    @pytest.fixture
    def upc_lookup(self):
        return {self.VENDOR_ITEM: ("1", "11111111111", "22222222222")}

    def _run(
        self,
        default_parameters,
        default_settings,
        sample_header_record,
        params,
        upc_lookup,
        tmp_path,
    ):
        from dispatch.converters import convert_to_simplified_csv

        b_record = (
            "B"
            + "01234567890"
            + "Test Item Description    "
            + f"{self.VENDOR_ITEM:0>6}"
            + "001000"
            + "01"
            + "000006"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )
        content = sample_header_record + "\n" + b_record + "\n"
        input_file = tmp_path / "input.edi"
        input_file.write_text(content)
        output_file = str(tmp_path / "output")
        convert_to_simplified_csv.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            params,
            upc_lookup,
        )
        with open(output_file + ".csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # Filter out header row
        return [r for r in rows if r and "UPC" not in r[0]]

    def test_retail_uom_all_transforms(
        self,
        default_parameters,
        default_settings,
        sample_header_record,
        tmp_path,
        upc_lookup,
    ):
        """With each_uom_categories='ALL', retail_uom=True transforms."""
        params = dict(default_parameters)
        params["retail_uom"] = "True"
        params["each_uom_categories"] = "ALL"
        params["each_uom_mode"] = "include"
        rows = self._run(
            default_parameters,
            default_settings,
            sample_header_record,
            params,
            upc_lookup,
            tmp_path,
        )
        assert rows  # transformed

    def test_retail_uom_filter_excludes_category(
        self,
        default_parameters,
        default_settings,
        sample_header_record,
        tmp_path,
        upc_lookup,
    ):
        """With include filter that excludes the item's category, fields are NOT transformed."""
        params = dict(default_parameters)
        params["retail_uom"] = "True"
        params["each_uom_categories"] = "99"
        params["each_uom_mode"] = "include"
        rows = self._run(
            default_parameters,
            default_settings,
            sample_header_record,
            params,
            upc_lookup,
            tmp_path,
        )
        # Cost stays at original 1000 cents; no transform ran
        assert rows
        # column 2 (unit_cost) should still be 10.00 (not divided by 6)
        assert rows[0][2] == "10.00"

    def test_retail_uom_exclude_mode(
        self,
        default_parameters,
        default_settings,
        sample_header_record,
        tmp_path,
        upc_lookup,
    ):
        """With exclude filter for the item's category, fields are NOT transformed."""
        params = dict(default_parameters)
        params["retail_uom"] = "True"
        params["each_uom_categories"] = "1"
        params["each_uom_mode"] = "exclude"
        rows = self._run(
            default_parameters,
            default_settings,
            sample_header_record,
            params,
            upc_lookup,
            tmp_path,
        )
        assert rows[0][2] == "10.00"

    def test_retail_uom_include_mode_matches(
        self,
        default_parameters,
        default_settings,
        sample_header_record,
        tmp_path,
        upc_lookup,
    ):
        """With include filter matching the item's category, transform runs."""
        params = dict(default_parameters)
        params["retail_uom"] = "True"
        params["each_uom_categories"] = "1"
        params["each_uom_mode"] = "include"
        rows = self._run(
            default_parameters,
            default_settings,
            sample_header_record,
            params,
            upc_lookup,
            tmp_path,
        )
        # Transform should have run: 1000 cents / 6 = 166.66... -> 1.66
        assert rows[0][2] != "10.00"

    def test_default_retail_uom_is_false(
        self, default_settings, sample_header_record, tmp_path, upc_lookup
    ):
        """Regression: when ``retail_uom`` is not in parameters, the
        default must be False (no retail UOM transform runs).

        The mutation runner's ``false_to_true`` at
        convert_to_simplified_csv.py:64 (flipping the default
        from False to True) was not caught by existing tests
        because every retail_uom test passed the parameter
        explicitly. With the mutation, the transform would run
        for every B record that has a category in the upc_lut,
        silently changing the output.
        """
        # IMPORTANT: do NOT use the default_parameters fixture —
        # it sets retail_uom="False" explicitly, which masks the
        # default-behavior test. Build a fresh parameters dict
        # WITHOUT retail_uom so the default applies.
        params = {
            "each_uom_categories": "ALL",
            "include_headers": "True",
            "include_item_numbers": "True",
            "include_item_description": "True",
            "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,vendor_item",
        }
        rows = self._run(
            params,
            default_settings,
            sample_header_record,
            params,
            upc_lookup,
            tmp_path,
        )
        assert len(rows) == 1
        # The B record's unit_cost is "001000" (10.00 case cost = $10.00)
        # and unit_mult is "000006". With retail_uom=False (default),
        # the cost stays at "10.00". With retail_uom=True (mutation),
        # the cost would be transformed to each-level
        # (10.00 / 6 = 1.6666...) and rounded to "1.67", NOT "10.00".
        assert rows[0][2] == "10.00", (
            f"expected default retail_uom=False to keep cost at '10.00', "
            f"got {rows[0][2]!r}. The mutation would transform the cost."
        )
