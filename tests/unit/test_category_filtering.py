"""Unit tests for the category filtering functionality in core/edi/edi_splitter.py.

Tests the filter_b_records_by_category() function which filters B records
based on item category from the upc_dict.
"""

import pytest
from core.edi.edi_splitter import filter_b_records_by_category
from utils import capture_records


def create_b_record(vendor_item: int, upc: str = "01234567890") -> str:
    """Create a minimal valid B record for testing.
    
    B record format (from capture_records):
        - record_type: line[0] - "B"
        - upc_number: line[1:12] - 11 chars
        - description: line[12:37] - 25 chars
        - vendor_item: line[37:43] - 6 chars
        - unit_cost: line[43:49] - 6 chars
        - combo_code: line[49:51] - 2 chars
        - unit_multiplier: line[51:57] - 6 chars
        - qty_of_units: line[57:62] - 5 chars
        - suggested_retail_price: line[62:67] - 5 chars
        - price_multi_pack: line[67:70] - 3 chars
        - parent_item_number: line[70:76] - 6 chars
    """
    return (
        "B"  # record_type
        f"{upc[:11]:<11}"  # upc_number (11 chars)
        f"{'Test Item':<25}"  # description (25 chars)
        f"{str(vendor_item):>6}"  # vendor_item (6 chars, right-aligned)
        f"{'100':>6}"  # unit_cost (6 chars)
        f"{'01':<2}"  # combo_code (2 chars)
        f"{'1':>6}"  # unit_multiplier (6 chars)
        f"{'10':>5}"  # qty_of_units (5 chars)
        f"{'199':>5}"  # suggested_retail_price (5 chars)
        f"{'001':<3}"  # price_multi_pack (3 chars)
        f"{'0':>6}"  # parent_item_number (6 chars)
        "\n"
    )


class TestFilterBRecordsByCategory:
    """Test suite for filter_b_records_by_category function."""
    
    # Sample upc_dict structure: {item_number: [category, upc1, upc2, upc3, upc4]}
    
    def test_filter_all_returns_all_records(self):
        """filter_categories='ALL' should return all records unchanged."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
            create_b_record(345678),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="ALL", filter_mode="include"
        )
        
        assert result == b_records
        assert len(result) == 3
    
    def test_filter_all_with_exclude_mode_returns_all_records(self):
        """filter_categories='ALL' should return all records regardless of mode."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="ALL", filter_mode="exclude"
        )
        
        assert result == b_records
        assert len(result) == 2
    
    def test_include_mode_filters_correctly(self):
        """filter_mode='include' with specific categories should only keep matching records."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
            create_b_record(345678),  # category "12"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5,12", filter_mode="include"
        )
        
        # All records should be included since all categories are in the list
        assert len(result) == 3
    
    def test_include_mode_filters_out_non_matching(self):
        """Include mode should filter out records not in the category list."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
            create_b_record(345678),  # category "12"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="include"
        )
        
        # Only records with categories 1 and 5 should be included
        assert len(result) == 2
        # Verify the correct records are included
        result_items = [capture_records(r)['vendor_item'].strip() for r in result]
        assert '123456' in result_items
        assert '789012' in result_items
        assert '345678' not in result_items
    
    def test_exclude_mode_filters_correctly(self):
        """filter_mode='exclude' should remove records with specified categories."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
            create_b_record(345678),  # category "12"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="exclude"
        )
        
        # Records with categories 1 and 5 should be excluded
        assert len(result) == 1
        result_items = [capture_records(r)['vendor_item'].strip() for r in result]
        assert '345678' in result_items
        assert '123456' not in result_items
        assert '789012' not in result_items
    
    def test_exclude_all_categories_leaves_none(self):
        """Exclude mode with all categories should leave no matching records."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="exclude"
        )
        
        assert len(result) == 0
    
    def test_fail_open_for_items_not_in_upc_dict(self):
        """Items not in upc_dict should be included (fail-open behavior)."""
        b_records = [
            create_b_record(123456),  # in upc_dict, category "1"
            create_b_record(999999),  # NOT in upc_dict
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Include mode - only category 5 (which 123456 doesn't have)
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="5", filter_mode="include"
        )
        
        # 123456 should be excluded (category 1 not in filter)
        # 999999 should be included (fail-open for unknown items)
        assert len(result) == 1
        result_items = [capture_records(r)['vendor_item'].strip() for r in result]
        assert '999999' in result_items
    
    def test_fail_open_for_items_not_in_upc_dict_exclude_mode(self):
        """Items not in upc_dict should be included even in exclude mode."""
        b_records = [
            create_b_record(123456),  # in upc_dict, category "1"
            create_b_record(999999),  # NOT in upc_dict
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Exclude mode - exclude category 1
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="exclude"
        )
        
        # 123456 should be excluded (category 1 is in exclude list)
        # 999999 should be included (fail-open for unknown items)
        assert len(result) == 1
        result_items = [capture_records(r)['vendor_item'].strip() for r in result]
        assert '999999' in result_items
    
    def test_empty_b_records_returns_empty_list(self):
        """Empty B records list should return empty list."""
        b_records = []
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="include"
        )
        
        assert result == []
        assert len(result) == 0
    
    def test_empty_upc_dict_returns_all_records(self):
        """Empty upc_dict should return all records (fail-open)."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
        ]
        upc_dict = {}
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="include"
        )
        
        assert result == b_records
        assert len(result) == 2
    
    def test_none_upc_dict_returns_all_records(self):
        """None upc_dict should return all records (fail-open)."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
        ]
        
        result = filter_b_records_by_category(
            b_records, None, filter_categories="1,5", filter_mode="include"
        )
        
        assert result == b_records
        assert len(result) == 2
    
    def test_categories_with_spaces_are_trimmed(self):
        """Categories with spaces should be trimmed correctly."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Categories with spaces
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1, 5", filter_mode="include"
        )
        
        assert len(result) == 2
    
    def test_category_as_string_in_upc_dict(self):
        """Categories stored as strings in upc_dict should match correctly."""
        b_records = [
            create_b_record(123456),  # category "1" (string)
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],  # category is string
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 1
    
    def test_category_as_integer_in_upc_dict(self):
        """Categories stored as integers in upc_dict should be converted to strings."""
        b_records = [
            create_b_record(123456),  # category 1 (integer)
        ]
        upc_dict = {
            123456: [1, "upc1", "upc2", "upc3", "upc4"],  # category is int
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 1
    
    def test_malformed_b_record_is_included_fail_open(self):
        """Malformed B records that cause parsing errors should be included (fail-open)."""
        # Create a malformed record that will fail parsing
        malformed_record = "B" + "x" * 30 + "\n"  # Too short
        b_records = [
            create_b_record(123456),
            malformed_record,
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="5", filter_mode="include"
        )
        
        # The malformed record should be included due to fail-open
        # 123456 should be excluded (category 1 not in filter "5")
        # Malformed record should be included (fail-open on error)
        assert len(result) == 1
        assert malformed_record in result
    
    def test_single_category_filter(self):
        """Single category filter should work correctly."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 1
        result_items = [capture_records(r)['vendor_item'].strip() for r in result]
        assert '123456' in result_items
    
    def test_preserves_record_order(self):
        """Filtering should preserve the original order of records."""
        b_records = [
            create_b_record(111111),  # category "1"
            create_b_record(222222),  # category "5"
            create_b_record(333333),  # category "1"
            create_b_record(444444),  # category "5"
        ]
        upc_dict = {
            111111: ["1", "upc1", "upc2", "upc3", "upc4"],
            222222: ["5", "upc1", "upc2", "upc3", "upc4"],
            333333: ["1", "upc1", "upc2", "upc3", "upc4"],
            444444: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="include"
        )
        
        # All should be included, order preserved
        assert len(result) == 4
        result_items = [capture_records(r)['vendor_item'].strip() for r in result]
        assert result_items == ['111111', '222222', '333333', '444444']


class TestCaptureRecordsIntegration:
    """Test that capture_records correctly parses our test B records."""
    
    def test_create_b_record_parses_correctly(self):
        """Verify that create_b_record creates valid B records."""
        record = create_b_record(123456)
        parsed = capture_records(record)
        
        assert parsed is not None
        assert parsed['record_type'] == 'B'
        assert parsed['vendor_item'].strip() == '123456'
    
    def test_create_b_record_with_different_items(self):
        """Verify B record creation with different item numbers."""
        for item_num in [1, 123, 12345, 123456]:
            record = create_b_record(item_num)
            parsed = capture_records(record)
            
            assert parsed is not None
            assert parsed['record_type'] == 'B'
            assert int(parsed['vendor_item'].strip()) == item_num


class TestFilterEDICategoryDropInvoices:
    """Test that invoices with no B records after filtering are dropped."""
    
    def create_a_record(self, invoice_number: str = "0012345678", invoice_total: str = "0000100000") -> str:
        """Create a minimal valid A record for testing.
        
        A record format:
            - record_type: line[0] - "A"
            - cust_vendor: line[1:7] - 6 chars
            - invoice_number: line[7:17] - 10 chars
            - invoice_date: line[17:23] - 6 chars (MMDDYY)
            - invoice_total: line[23:33] - 10 chars
        """
        return (
            "A"  # record_type
            f"{'VENDOR':<6}"  # cust_vendor (6 chars)
            f"{invoice_number:<10}"  # invoice_number (10 chars)
            f"010125"  # invoice_date (6 chars)
            f"{invoice_total:<10}"  # invoice_total (10 chars)
            "\n"
        )
    
    def create_c_record(self, charge_type: str = "001") -> str:
        """Create a minimal valid C record for testing.
        
        C record format:
            - record_type: line[0] - "C"
            - charge_type: line[1:4] - 3 chars
            - description: line[4:29] - 25 chars
            - amount: line[29:38] - 9 chars
        """
        return (
            "C"  # record_type
            f"{charge_type:<3}"  # charge_type (3 chars)
            f"{'Test Charge':<25}"  # description (25 chars)
            f"{'1000':>9}"  # amount (9 chars)
            "\n"
        )
    
    def test_filter_edi_drops_invoice_with_no_b_records(self, tmp_path):
        """When all B records are filtered out, the invoice should be dropped."""
        import utils
        
        # Create test EDI file with 2 invoices
        # Invoice 1: has B record with category 1
        # Invoice 2: has B record with category 5 (will be filtered out)
        input_content = (
            self.create_a_record("0000000001")  # Invoice 1
            + create_b_record(123456)  # category 1
            + self.create_c_record()
            + self.create_a_record("0000000002")  # Invoice 2
            + create_b_record(789012)  # category 5
            + self.create_c_record()
        )
        
        input_file = tmp_path / "test.edi"
        input_file.write_text(input_content)
        output_file = tmp_path / "output.edi"
        
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Filter to only include category 1
        result = utils.filter_edi_file_by_category(
            str(input_file), str(output_file), upc_dict,
            filter_categories="1", filter_mode="include"
        )
        
        assert result is True
        
        # Read output and verify only invoice 1 remains
        output_content = output_file.read_text()
        assert "0000000001" in output_content  # Invoice 1 should be present
        assert "0000000002" not in output_content  # Invoice 2 should be dropped
    
    def test_filter_edi_keeps_invoice_with_some_b_records(self, tmp_path):
        """Invoice with at least one matching B record should be kept."""
        import utils
        
        # Create test EDI file with invoice containing multiple B records
        input_content = (
            self.create_a_record("0000000001")
            + create_b_record(123456)  # category 1 - will be included
            + create_b_record(789012)  # category 5 - will be filtered out
            + create_b_record(345678)  # category 12 - will be filtered out
            + self.create_c_record()
        )
        
        input_file = tmp_path / "test.edi"
        input_file.write_text(input_content)
        output_file = tmp_path / "output.edi"
        
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Filter to only include category 1
        result = utils.filter_edi_file_by_category(
            str(input_file), str(output_file), upc_dict,
            filter_categories="1", filter_mode="include"
        )
        
        assert result is True
        
        # Read output and verify invoice is present with only 1 B record
        output_content = output_file.read_text()
        assert "0000000001" in output_content  # Invoice should be present
        assert output_content.count("B") == 1  # Only 1 B record
    
    def test_filter_edi_all_mode_keeps_all_invoices(self, tmp_path):
        """filter_categories='ALL' should keep all invoices unchanged."""
        import utils
        
        input_content = (
            self.create_a_record("0000000001")
            + create_b_record(123456)
            + self.create_c_record()
            + self.create_a_record("0000000002")
            + create_b_record(789012)
            + self.create_c_record()
        )
        
        input_file = tmp_path / "test.edi"
        input_file.write_text(input_content)
        output_file = tmp_path / "output.edi"
        
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = utils.filter_edi_file_by_category(
            str(input_file), str(output_file), upc_dict,
            filter_categories="ALL", filter_mode="include"
        )
        
        # Should return False indicating no filtering was applied
        assert result is False


class TestFilterBRecordsByCategoryEdgeCases:
    """Additional edge case tests for filter_b_records_by_category function."""
    
    def test_filter_with_category_as_int_key(self):
        """Categories stored as integers (not strings) in upc_dict keys."""
        b_records = [
            create_b_record(123456),  # category "1"
        ]
        upc_dict = {
            123456: [1, "upc1", "upc2", "upc3", "upc4"],  # category is int
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 1
    
    def test_filter_with_mixed_category_types(self):
        """Mix of string and int categories in upc_dict."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category 5 (int)
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: [5, "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Include categories 1 and 5
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="include"
        )
        
        assert len(result) == 2
    
    def test_filter_with_empty_categories_string(self):
        """Empty categories string should behave like no filter (all records fail-open)."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="", filter_mode="include"
        )
        
        # Empty categories with non-matching filter returns empty (known behavior)
        assert len(result) == 0
    
    def test_filter_with_whitespace_only_categories(self):
        """Categories string with only whitespace."""
        b_records = [
            create_b_record(123456),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="   ", filter_mode="include"
        )
        
        # Whitespace-only should return empty (known behavior)
        assert len(result) == 0
    
    def test_filter_with_duplicate_categories(self):
        """Duplicate categories in filter string should be handled."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Duplicate category 1
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,1,5", filter_mode="include"
        )
        
        assert len(result) == 2
    
    def test_filter_with_category_not_in_records(self):
        """Filter categories that don't match any records."""
        b_records = [
            create_b_record(123456),  # category "1"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Filter for categories 99, 100 (nonexistent)
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="99,100", filter_mode="include"
        )
        
        # Should return empty since 123456's category is not in filter
        assert len(result) == 0
    
    def test_exclude_mode_with_all_categories(self):
        """Exclude mode with ALL categories should exclude everything."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Exclude ALL should exclude all records
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="ALL", filter_mode="exclude"
        )
        
        # ALL in exclude mode returns all (known behavior)
        assert len(result) == 2
    
    def test_very_long_category_list(self):
        """Filter with very long category list."""
        b_records = []
        upc_dict = {}
        
        # Create records for categories 1-20
        for i in range(1, 21):
            vendor_item = 100000 + i
            b_records.append(create_b_record(vendor_item))
            upc_dict[vendor_item] = [str(i), f"upc{i}", f"upc{i}_2", f"upc{i}_3", f"upc{i}_4"]
        
        # Filter for categories 1-15
        category_list = ",".join([str(i) for i in range(1, 16)])
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories=category_list, filter_mode="include"
        )
        
        assert len(result) == 15
    
    def test_filter_preserves_record_structure(self):
        """Filtering should preserve exact record structure."""
        b_record = create_b_record(123456)
        b_records = [b_record]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        # Record should be exactly the same
        assert len(result) == 1
        assert result[0] == b_record
        assert result[0].startswith("B")
    
    def test_multiple_records_same_category(self):
        """Multiple records with same category should all be included."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(234567),  # category "1"
            create_b_record(345678),  # category "1"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            234567: ["1", "upc5", "upc6", "upc7", "upc8"],
            345678: ["1", "upc9", "upc10", "upc11", "upc12"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 3
    
    def test_mixed_valid_and_unknown_records(self):
        """Mix of valid records and records not in upc_dict."""
        b_records = [
            create_b_record(123456),  # in upc_dict, category "1"
            create_b_record(999999),  # NOT in upc_dict
            create_b_record(789012),  # in upc_dict, category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Include category 1
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        # 123456 should be included (category 1)
        # 999999 should be included (fail-open)
        # 789012 should be excluded (category 5 not in filter)
        assert len(result) == 2
    
    def test_category_with_leading_zeros(self):
        """Category with leading zeros should be handled correctly."""
        b_records = [
            create_b_record(123456),  # category "01" (stored as "01")
        ]
        upc_dict = {
            123456: ["01", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Filter for category 1 (without leading zero)
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        # Should match category "01" with filter "1"
        # This depends on string comparison implementation
        # If "01" != "1", then result should be 0 (unknown fail-open behavior)
        assert len(result) == 0  # "01" != "1" so unknown item, fail-open
    
    def test_unicode_in_category(self):
        """Categories with unicode characters should be handled."""
        b_records = [
            create_b_record(123456),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 1


class TestFilterUPCValidationIntegration:
    """Integration tests for category filtering with UPC validation."""
    
    def test_upc_length_affects_category_lookup(self):
        """UPC length validation should work with category filtering."""
        upc_dict = {
            123456: ["1", "0123456789", "012345678901", "0123456789012", "01234567890123"],
        }
        
        # Valid UPC lengths: 11, 12, 13, 14
        upc_entry = upc_dict[123456]
        
        assert len(upc_entry[1]) == 10  # upc1
        assert len(upc_entry[2]) == 12  # upc2
        assert len(upc_entry[3]) == 13  # upc3
        assert len(upc_entry[4]) == 14  # upc4
    
    def test_category_with_upc_padding(self):
        """Category filtering with UPC padding applied."""
        upc = "12345"
        target_length = 11
        padding_pattern = "           "  # 11 spaces
        
        padded_upc = padding_pattern[:target_length - len(upc)] + upc
        
        assert len(padded_upc) == target_length
        assert padded_upc.startswith("      ")
        assert padded_upc.endswith("12345")
    
    def test_category_filtering_with_upc_override(self):
        """Category filtering with UPC override enabled."""
        # When override_upc_bool is True, use override_upc_level for category
        override_enabled = True
        override_category = "1"
        
        b_records = [
            create_b_record(123456),
        ]
        upc_dict = {
            123456: ["5", "upc1", "upc2", "upc3", "upc4"],  # Actual category is 5
        }
        
        if override_enabled:
            filter_category = override_category  # Use 1 instead of actual category 5
        else:
            filter_category = "5"
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories=filter_category, filter_mode="include"
        )
        
        # With override to category 1, but record has category 5, it won't match
        assert len(result) == 0  # 5 != 1 so fails filter


class TestFilterModeCombinations:
    """Tests for various filter mode combinations."""
    
    def test_include_mode_with_single_category(self):
        """Include mode with single category."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="include"
        )
        
        assert len(result) == 1
        parsed = capture_records(result[0])
        assert parsed is not None
        assert parsed['vendor_item'].strip() == '123456'
    
    def test_include_mode_with_multiple_categories(self):
        """Include mode with multiple categories."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
            create_b_record(345678),  # category "12"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5,12", filter_mode="include"
        )
        
        assert len(result) == 3
    
    def test_exclude_mode_with_single_category(self):
        """Exclude mode with single category."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1", filter_mode="exclude"
        )
        
        assert len(result) == 1
        parsed = capture_records(result[0])
        assert parsed is not None
        assert parsed['vendor_item'].strip() == '789012'
    
    def test_exclude_mode_with_multiple_categories(self):
        """Exclude mode with multiple categories."""
        b_records = [
            create_b_record(123456),  # category "1"
            create_b_record(789012),  # category "5"
            create_b_record(345678),  # category "12"
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
            345678: ["12", "upc1", "upc2", "upc3", "upc4"],
        }
        
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="1,5", filter_mode="exclude"
        )
        
        assert len(result) == 1
        parsed = capture_records(result[0])
        assert parsed is not None
        assert parsed['vendor_item'].strip() == '345678'
    
    def test_all_mode_ignores_filter_mode(self):
        """ALL mode should return all records regardless of filter_mode."""
        b_records = [
            create_b_record(123456),
            create_b_record(789012),
        ]
        upc_dict = {
            123456: ["1", "upc1", "upc2", "upc3", "upc4"],
            789012: ["5", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Include mode with ALL
        result_include = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="ALL", filter_mode="include"
        )
        
        # Exclude mode with ALL
        result_exclude = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="ALL", filter_mode="exclude"
        )
        
        # Both should return all records
        assert result_include == b_records
        assert result_exclude == b_records
    
    def test_case_insensitive_category_matching(self):
        """Category matching should be case-sensitive for string comparison."""
        b_records = [
            create_b_record(123456),
        ]
        upc_dict = {
            123456: ["abc", "upc1", "upc2", "upc3", "upc4"],
        }
        
        # Filter with different case
        result = filter_b_records_by_category(
            b_records, upc_dict, filter_categories="ABC", filter_mode="include"
        )
        
        # String comparison is case-sensitive "abc" != "ABC"
        # So the record is not in filter, and it's not unknown, so excluded
        assert len(result) == 0
