"""
Supplementary unit tests for utils.py - covers invFetcher and uncovered functions.

This module provides comprehensive tests for:
- invFetcher class
- detect_invoice_is_credit()
- do_split_edi()
- capture_records() edge cases
- do_clear_old_files()
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Ensure project root is in path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import utils


class MockQueryRunner:
    """Mock query_runner for testing."""

    def __init__(self, *args, **kwargs):
        self.queries = []

    def run_arbitrary_query(self, query):
        self.queries.append(query)
        return []


class TestInvFetcher(unittest.TestCase):
    """Tests for invFetcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.settings = {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "test_host",
            "odbc_driver": "test_driver",
        }

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_init(self):
        """Test invFetcher initialization."""
        fetcher = utils.invFetcher(self.settings)

        self.assertIsNone(fetcher.query_object)
        self.assertEqual(fetcher.settings, self.settings)
        self.assertEqual(fetcher.last_invoice_number, 0)
        self.assertEqual(fetcher.uom_lut, {0: "N/A"})
        self.assertEqual(fetcher.last_invno, 0)
        self.assertEqual(fetcher.po, "")
        self.assertEqual(fetcher.custname, "")
        self.assertEqual(fetcher.custno, 0)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_db_connect(self):
        """Test _db_connect method."""
        fetcher = utils.invFetcher(self.settings)

        fetcher._db_connect()

        self.assertIsNotNone(fetcher.query_object)
        self.assertIsInstance(fetcher.query_object, MockQueryRunner)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_run_qry_auto_connects(self):
        """Test _run_qry auto-connects if not connected."""
        fetcher = utils.invFetcher(self.settings)

        # Should auto-connect
        result = fetcher._run_qry("SELECT * FROM test")

        self.assertIsNotNone(fetcher.query_object)
        self.assertEqual(len(fetcher.query_object.queries), 1)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_po_caching(self):
        """Test fetch_po caches results for same invoice."""
        fetcher = utils.invFetcher(self.settings)

        # Mock query response
        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = [
            ("PO123", "Customer Name", 456)
        ]

        # First call - should query
        po1 = fetcher.fetch_po(12345)
        self.assertEqual(po1, "PO123")
        self.assertEqual(fetcher.query_object.run_arbitrary_query.call_count, 1)

        # Second call with same invoice - should use cache
        po2 = fetcher.fetch_po(12345)
        self.assertEqual(po2, "PO123")
        # Query should not have been called again
        self.assertEqual(fetcher.query_object.run_arbitrary_query.call_count, 1)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_po_new_invoice(self):
        """Test fetch_po queries for new invoice number."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = [
            ("PO123", "Customer Name", 456)
        ]

        # First invoice
        fetcher.fetch_po(11111)
        self.assertEqual(fetcher.query_object.run_arbitrary_query.call_count, 1)

        # Different invoice - should query again
        fetcher.query_object.run_arbitrary_query.return_value = [
            ("PO456", "Another Customer", 789)
        ]
        po = fetcher.fetch_po(22222)
        self.assertEqual(po, "PO456")
        self.assertEqual(fetcher.query_object.run_arbitrary_query.call_count, 2)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_po_empty_result(self):
        """Test fetch_po handles empty query result."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = []

        po = fetcher.fetch_po(99999)

        self.assertEqual(po, "")  # Should return empty string

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_po_invalid_invoice_number(self):
        """Test fetch_po handles invalid invoice number."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = []

        # Non-numeric invoice
        po = fetcher.fetch_po("invalid")
        self.assertEqual(po, "")

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_cust_name(self):
        """Test fetch_cust_name method."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = [
            ("PO123", "Test Customer", 456)
        ]

        cust_name = fetcher.fetch_cust_name(12345)

        self.assertEqual(cust_name, "Test Customer")

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_cust_no(self):
        """Test fetch_cust_no method."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = [
            ("PO123", "Test Customer", 456)
        ]

        cust_no = fetcher.fetch_cust_no(12345)

        self.assertEqual(cust_no, 456)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_uom_desc_cached(self):
        """Test fetch_uom_desc uses cache for same invoice."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        fetcher.query_object.run_arbitrary_query.return_value = [
            (1, "CASE"),
            (2, "EACH"),
        ]

        # First call - should query
        uom1 = fetcher.fetch_uom_desc(100, 2, 0, 12345)
        self.assertEqual(uom1, "CASE")
        self.assertEqual(fetcher.query_object.run_arbitrary_query.call_count, 1)

        # Same invoice, different line - should use cache
        uom2 = fetcher.fetch_uom_desc(101, 1, 1, 12345)
        self.assertEqual(uom2, "EACH")
        # Should not query again
        self.assertEqual(fetcher.query_object.run_arbitrary_query.call_count, 1)

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_uom_desc_lookup_fallback(self):
        """Test fetch_uom_desc falls back to item lookup."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        # First query returns empty UOM lookup
        fetcher.query_object.run_arbitrary_query.side_effect = [
            [],  # Empty UOM lookup
            [("EACH",)],  # Item lookup fallback
        ]

        uom = fetcher.fetch_uom_desc(100, 1, 0, 12345)

        self.assertEqual(uom, "EACH")

    @patch.object(utils, "HAS_QUERY_RUNNER", True)
    @patch.object(utils, "query_runner", MockQueryRunner)
    def test_fetch_uom_desc_default_fallback(self):
        """Test fetch_uom_desc falls back to HI/LO defaults."""
        fetcher = utils.invFetcher(self.settings)

        fetcher.query_object = MagicMock()
        # All queries fail
        fetcher.query_object.run_arbitrary_query.return_value = []

        # High multiplier should return HI
        uom_high = fetcher.fetch_uom_desc(100, 2, 0, 12345)
        self.assertEqual(uom_high, "HI")

        # Need to reset uom_lut and change side_effect for the second test
        fetcher.uom_lut = {0: "N/A"}
        fetcher.last_invno = 0

        # Low multiplier should return LO
        uom_low = fetcher.fetch_uom_desc(100, 1, 0, 12345)
        self.assertEqual(uom_low, "LO")


class TestDetectInvoiceIsCredit(unittest.TestCase):
    """Tests for detect_invoice_is_credit function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_invoice_positive_total(self):
        """Test positive invoice total returns False."""
        edi_file = os.path.join(self.temp_dir, "positive.edi")
        with open(edi_file, "w") as f:
            # A record with positive total (000012345 = 123.45)
            # A(1) + cust(6) + inv(10) + date(6) + total(10)
            f.write("A1234567890123450123450000012345\n")

        result = utils.detect_invoice_is_credit(edi_file)
        self.assertFalse(result)

    def test_invoice_negative_total(self):
        """Test negative invoice total returns True."""
        edi_file = os.path.join(self.temp_dir, "negative.edi")
        with open(edi_file, "w") as f:
            # A record with negative total (using - prefix)
            # A(1) + cust(6) + inv(10) + date(6) + total(10)
            f.write("A1234567890123450123450-00012345\n")

        result = utils.detect_invoice_is_credit(edi_file)
        self.assertTrue(result)

    def test_non_a_record_raises(self):
        """Test non-A record as first line raises ValueError."""
        edi_file = os.path.join(self.temp_dir, "invalid.edi")
        with open(edi_file, "w") as f:
            f.write("B1234567890Test Description     123450123450012345012340123\n")

        with self.assertRaises(ValueError) as context:
            utils.detect_invoice_is_credit(edi_file)

        self.assertIn("middle of a file", str(context.exception))


class TestDoSplitEdi(unittest.TestCase):
    """Tests for do_split_edi function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = os.path.join(self.temp_dir, "work")

        # Create a multi-invoice EDI file
        self.edi_file = os.path.join(self.temp_dir, "multi.edi")
        with open(self.edi_file, "w") as f:
            # First invoice (positive)
            # A(1) + cust(6) + inv(10) + date(6) + total(10)
            # Date: 010121 (Jan 1, 2021)
            f.write("A12345678901234500101210000012345\n")
            # B(1) + upc(11) + desc(25) + vend(6) + cost(6) + ...
            # Pad B record to be safe
            f.write(
                "B1234567890Test Item 1             123450123450012345012340123000\n"
            )
            # Second invoice (negative/credit)
            f.write("A1234567891123460010121-000012345\n")
            f.write(
                "B1234567891Test Item 2             123460123460012346012340123000\n"
            )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_split_creates_files(self):
        """Test EDI split creates separate files."""
        parameters = {"prepend_date_files": False}

        result = utils.do_split_edi(self.edi_file, self.work_dir, parameters)

        # Should return list of created files
        self.assertEqual(len(result), 2)

        # Files should exist
        for file_path, _, _ in result:
            self.assertTrue(os.path.exists(file_path))

    def test_split_credit_vs_invoice_suffixes(self):
        """Test correct suffixes for credits vs invoices."""
        parameters = {"prepend_date_files": False}

        result = utils.do_split_edi(self.edi_file, self.work_dir, parameters)

        # One should be .inv (invoice), one should be .cr (credit)
        suffixes = [suffix for _, _, suffix in result]
        self.assertIn(".inv", suffixes)
        self.assertIn(".cr", suffixes)

    def test_split_too_many_invoices(self):
        """Test handling of files with too many invoices (>700)."""
        # Create a file with many A records (just the headers)
        many_edi = os.path.join(self.temp_dir, "many.edi")
        with open(many_edi, "w") as f:
            for i in range(701):
                f.write(f"A{i:010d}012345012345000012345\n")

        parameters = {"prepend_date_files": False}
        result = utils.do_split_edi(many_edi, self.work_dir, parameters)

        # Should return empty list for files with >700 invoices
        self.assertEqual(result, [])

    def test_split_with_date_prepend(self):
        """Test splitting with date prepending enabled."""
        parameters = {"prepend_date_files": True}

        result = utils.do_split_edi(self.edi_file, self.work_dir, parameters)

        # File names should contain date
        for file_path, prefix, _ in result:
            self.assertIn("_", prefix)  # Date prefix should be present


class TestCaptureRecords(unittest.TestCase):
    """Tests for capture_records function edge cases."""

    def test_capture_a_record(self):
        """Test capturing A record fields."""
        # A(1) + cust(6) + inv(10) + date(6) + total(10)
        # Date: 010121
        line = "A12345678901234500101210000012345"
        result = utils.capture_records(line)

        self.assertIsNotNone(result)
        self.assertEqual(result["record_type"], "A")
        self.assertEqual(result["cust_vendor"], "123456")
        self.assertEqual(result["invoice_number"], "7890123450")
        self.assertEqual(result["invoice_date"], "010121")
        self.assertEqual(result["invoice_total"], "0000012345")

    def test_capture_b_record(self):
        """Test capturing B record fields."""
        # B(1) + upc(11) + desc(25) + vend(6) + cost(6) + combo(2) + mult(6) + qty(5)
        # Corrected input string to align with fields (25 chars for desc)
        # 123450 (vend) + 123450 (cost) + 00 (combo) + 000001 (mult) + 12345 (qty)
        line = "B23456789012Test Description         123450123450000000011234501234"
        result = utils.capture_records(line)

        self.assertIsNotNone(result)
        self.assertEqual(result["record_type"], "B")
        self.assertEqual(result["upc_number"], "23456789012")
        self.assertEqual(result["description"], "Test Description         ")
        self.assertEqual(result["vendor_item"], "123450")
        self.assertEqual(result["unit_cost"], "123450")
        self.assertEqual(result["qty_of_units"], "12345")

    def test_capture_c_record(self):
        """Test capturing C record fields."""
        line = "C001Test Charge              000010000"
        result = utils.capture_records(line)

        self.assertIsNotNone(result)
        self.assertEqual(result["record_type"], "C")
        self.assertEqual(result["charge_type"], "001")
        self.assertEqual(result["description"], "Test Charge              ")
        self.assertEqual(result["amount"], "000010000")

    def test_capture_end_marker(self):
        """Test capturing end marker returns None."""
        line = "\x1a"  # EOF marker
        result = utils.capture_records(line)

        self.assertIsNone(result)

    def test_capture_invalid_record(self):
        """Test invalid record raises exception."""
        line = "XInvalid record type"

        with self.assertRaises(Exception) as context:
            utils.capture_records(line)

        self.assertIn("Not An EDI", str(context.exception))


class TestDoClearOldFiles(unittest.TestCase):
    """Tests for do_clear_old_files function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_files_to_clear(self):
        """Test with no files (empty folder)."""
        # Should not raise
        utils.do_clear_old_files(self.temp_dir, 10)

    def test_files_under_limit(self):
        """Test when files are under the limit."""
        # Create 3 files
        for i in range(3):
            with open(os.path.join(self.temp_dir, f"file{i}.txt"), "w") as f:
                f.write("content")

        # Limit is 5, should not delete anything
        utils.do_clear_old_files(self.temp_dir, 5)

        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 3)

    def test_files_over_limit(self):
        """Test clearing old files when over limit."""
        import time

        # Create 5 files with delays to ensure different timestamps
        for i in range(5):
            with open(os.path.join(self.temp_dir, f"file{i}.txt"), "w") as f:
                f.write("content")
            time.sleep(0.01)  # Small delay

        # Limit is 3, should delete 2 oldest
        utils.do_clear_old_files(self.temp_dir, 3)

        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 3)
        # Oldest files (file0 and file1) should be deleted
        self.assertNotIn("file0.txt", files)
        self.assertNotIn("file1.txt", files)


class TestUtilityFunctions(unittest.TestCase):
    """Tests for other utility functions."""

    def test_dac_str_int_to_int_positive(self):
        """Test dac_str_int_to_int with positive numbers."""
        self.assertEqual(utils.dac_str_int_to_int("123"), 123)
        self.assertEqual(utils.dac_str_int_to_int("00123"), 123)
        self.assertEqual(utils.dac_str_int_to_int("0"), 0)

    def test_dac_str_int_to_int_negative(self):
        """Test dac_str_int_to_int with negative numbers."""
        self.assertEqual(utils.dac_str_int_to_int("-123"), -123)
        self.assertEqual(utils.dac_str_int_to_int("-00123"), -123)

    def test_dac_str_int_to_int_empty(self):
        """Test dac_str_int_to_int with empty string."""
        self.assertEqual(utils.dac_str_int_to_int(""), 0)
        self.assertEqual(utils.dac_str_int_to_int("   "), 0)

    def test_dac_str_int_to_int_invalid(self):
        """Test dac_str_int_to_int with invalid input."""
        self.assertEqual(utils.dac_str_int_to_int("abc"), 0)
        self.assertEqual(utils.dac_str_int_to_int("12.34"), 0)

    def test_convert_to_price(self):
        """Test convert_to_price function."""
        self.assertEqual(utils.convert_to_price("12345"), "123.45")
        self.assertEqual(utils.convert_to_price("00045"), "0.45")
        self.assertEqual(utils.convert_to_price("10000"), "100.00")

    def test_dactime_from_datetime(self):
        """Test dactime_from_datetime conversion."""
        dt = datetime(2021, 6, 15)
        result = utils.dactime_from_datetime(dt)
        # (2021 - 1900) = 121, format: 1YYMMDD
        self.assertEqual(result, "1210615")

    def test_datetime_from_dactime(self):
        """Test datetime_from_dactime conversion."""
        result = utils.datetime_from_dactime(1210615)
        self.assertEqual(result.year, 2021)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_datetime_from_invtime(self):
        """Test datetime_from_invtime conversion."""
        result = utils.datetime_from_invtime("061521")
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.year, 2021)

    def test_dactime_from_invtime(self):
        """Test dactime_from_invtime conversion."""
        result = utils.dactime_from_invtime("061521")
        self.assertEqual(result, "1210615")


if __name__ == "__main__":
    unittest.main()
