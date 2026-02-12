"""Unit tests for InvFetcher class."""

import pytest
from unittest.mock import MagicMock
from core.edi.inv_fetcher import InvFetcher, QueryRunnerProtocol


class TestInvFetcher:
    """Tests for InvFetcher class."""
    
    @pytest.fixture
    def mock_query_runner(self):
        """Create mock query runner."""
        runner = MagicMock(spec=QueryRunnerProtocol)
        runner.run_query.return_value = []
        return runner
    
    @pytest.fixture
    def settings(self):
        """Sample settings dictionary."""
        return {
            "as400_username": "user",
            "as400_password": "pass",
            "as400_address": "host",
            "odbc_driver": "driver"
        }
    
    @pytest.fixture
    def fetcher(self, mock_query_runner, settings):
        """Create InvFetcher with mock dependencies."""
        return InvFetcher(mock_query_runner, settings)
    
    def test_init_with_query_runner(self, mock_query_runner, settings):
        """Test initialization with injectable query runner."""
        fetcher = InvFetcher(mock_query_runner, settings)
        
        assert fetcher._query_runner is mock_query_runner
        assert fetcher.settings == settings
        assert fetcher.last_invoice_number == 0
        assert fetcher.uom_lut == {0: "N/A"}
    
    def test_init_without_settings(self, mock_query_runner):
        """Test initialization without settings."""
        fetcher = InvFetcher(mock_query_runner)
        
        assert fetcher.settings == {}
    
    def test_fetch_po_returns_cached(self, fetcher):
        """Test fetch_po returns cached value for same invoice."""
        fetcher.po = "PO123"
        fetcher.last_invoice_number = 12345
        
        result = fetcher.fetch_po(12345)
        
        assert result == "PO123"
        # Should not call query runner for cached invoice
        fetcher._query_runner.run_query.assert_not_called()
    
    def test_fetch_po_queries_database(self, fetcher):
        """Test fetch_po queries database for new invoice."""
        fetcher._query_runner.run_query.return_value = [
            {"col1": "PO123", "col2": "Customer Name", "col3": 456}
        ]
        
        result = fetcher.fetch_po(12345)
        
        assert result == "PO123"
        assert fetcher.custname == "Customer Name"
        assert fetcher.custno == 456
        fetcher._query_runner.run_query.assert_called_once()
    
    def test_fetch_po_handles_tuple_results(self, fetcher):
        """Test fetch_po handles tuple results from query."""
        fetcher._query_runner.run_query.return_value = [
            ("PO123", "Customer Name", 456)
        ]
        
        result = fetcher.fetch_po(12345)
        
        assert result == "PO123"
        assert fetcher.custname == "Customer Name"
        assert fetcher.custno == 456
    
    def test_fetch_po_handles_empty_result(self, fetcher):
        """Test fetch_po handles empty query result."""
        fetcher._query_runner.run_query.return_value = []
        
        result = fetcher.fetch_po(12345)
        
        assert result == ""
    
    def test_fetch_po_handles_index_error(self, fetcher):
        """Test fetch_po handles IndexError gracefully."""
        fetcher._query_runner.run_query.return_value = []
        
        result = fetcher.fetch_po(12345)
        
        assert result == ""
    
    def test_fetch_cust_name(self, fetcher):
        """Test fetch_cust_name returns customer name."""
        fetcher._query_runner.run_query.return_value = [
            {"col1": "PO123", "col2": "Test Customer", "col3": 789}
        ]
        
        result = fetcher.fetch_cust_name(12345)
        
        assert result == "Test Customer"
    
    def test_fetch_cust_no(self, fetcher):
        """Test fetch_cust_no returns customer number."""
        fetcher._query_runner.run_query.return_value = [
            {"col1": "PO123", "col2": "Test Customer", "col3": 789}
        ]
        
        result = fetcher.fetch_cust_no(12345)
        
        assert result == 789
    
    def test_fetch_uom_desc_from_invoice(self, fetcher):
        """Test fetch_uom_desc gets UOM from invoice line items."""
        fetcher._query_runner.run_query.return_value = [
            {"BUHUNB": 1, "BUHXTX": "EACH"},
            {"BUHUNB": 2, "BUHXTX": "CASE"}
        ]
        
        result = fetcher.fetch_uom_desc(123, 1, 0, 12345)
        
        # lineno + 1 = 1, so should return "EACH"
        assert result == "EACH"
    
    def test_fetch_uom_desc_caches_uom_lut(self, fetcher):
        """Test fetch_uom_desc caches UOM lookup table."""
        fetcher._query_runner.run_query.return_value = [
            {"BUHUNB": 1, "BUHXTX": "EACH"}
        ]
        
        # First call
        fetcher.fetch_uom_desc(123, 1, 0, 12345)
        
        # Second call with same invno should use cache
        fetcher._query_runner.run_query.reset_mock()
        fetcher.fetch_uom_desc(456, 1, 0, 12345)
        
        # Should not query again for same invoice
        fetcher._query_runner.run_query.assert_not_called()
    
    def test_fetch_uom_desc_resets_on_new_invoice(self, fetcher):
        """Test fetch_uom_desc resets cache for new invoice."""
        fetcher._query_runner.run_query.return_value = [
            {"BUHUNB": 1, "BUHXTX": "EACH"}
        ]
        
        # First invoice
        fetcher.fetch_uom_desc(123, 1, 0, 12345)
        
        # New invoice
        fetcher._query_runner.run_query.return_value = [
            {"BUHUNB": 1, "BUHXTX": "CASE"}
        ]
        result = fetcher.fetch_uom_desc(456, 1, 0, 67890)
        
        assert result == "CASE"
    
    def test_fetch_uom_desc_falls_back_to_item_master(self, fetcher):
        """Test fetch_uom_desc falls back to item master."""
        # First query returns no matching line
        fetcher._query_runner.run_query.return_value = [
            {"BUHUNB": 99, "BUHXTX": "OTHER"}  # lineno 0+1=1 not in this
        ]
        
        # Need to set up for second query (item master)
        def side_effect(query):
            if "odhst" in query:
                return [{"BUHUNB": 99, "BUHXTX": "OTHER"}]
            elif "dsanrep" in query:
                return [{"ANB9TX": "CASE"}]
            return []
        
        fetcher._query_runner.run_query.side_effect = side_effect
        
        result = fetcher.fetch_uom_desc(123, 2, 0, 12345)  # uommult > 1
        
        assert result == "CASE"
    
    def test_fetch_uom_desc_handles_tuple_results(self, fetcher):
        """Test fetch_uom_desc handles tuple results."""
        fetcher._query_runner.run_query.return_value = [
            (1, "EACH"),
            (2, "CASE")
        ]
        
        result = fetcher.fetch_uom_desc(123, 1, 0, 12345)
        
        assert result == "EACH"
    
    def test_fetch_uom_desc_hi_fallback(self, fetcher):
        """Test fetch_uom_desc returns 'HI' when uommult > 1 and no data."""
        fetcher._query_runner.run_query.return_value = []
        
        result = fetcher.fetch_uom_desc(123, 2, 0, 12345)
        
        assert result == "HI"
    
    def test_fetch_uom_desc_lo_fallback(self, fetcher):
        """Test fetch_uom_desc returns 'LO' when uommult <= 1 and no data."""
        fetcher._query_runner.run_query.return_value = []
        
        result = fetcher.fetch_uom_desc(123, 1, 0, 12345)
        
        assert result == "LO"
    
    def test_fetch_uom_desc_handles_exception(self, fetcher):
        """Test fetch_uom_desc handles exceptions gracefully."""
        # Set up the mock to raise an exception on odhst query
        # The exception should be caught and fallback returned
        def side_effect(query):
            raise Exception("DB Error")
        
        fetcher._query_runner.run_query.side_effect = side_effect
        
        # This should catch the exception and return a fallback value
        result = fetcher.fetch_uom_desc(123, 1, 0, 12345)
        
        # Should return fallback value
        assert result in ["HI", "LO", "NA"]
    
    def test_fetch_uom_desc_handles_value_error(self, fetcher):
        """Test fetch_uom_desc handles ValueError in uommult conversion."""
        fetcher._query_runner.run_query.return_value = []
        
        result = fetcher.fetch_uom_desc(123, "invalid", 0, 12345)
        
        assert result == "NA"


class TestInvFetcherProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_inv_fetcher_accepts_protocol_compliant_runner(self):
        """Test InvFetcher accepts any QueryRunnerProtocol implementation."""
        
        class CustomQueryRunner:
            def run_query(self, query, params=None):
                return [{"result": "value"}]
        
        runner = CustomQueryRunner()
        fetcher = InvFetcher(runner)
        
        # Should work without error
        assert fetcher._query_runner is runner


class TestInvFetcherIntegration:
    """Integration tests for InvFetcher."""
    
    @pytest.fixture
    def mock_query_runner(self):
        """Create mock query runner with realistic data."""
        runner = MagicMock()
        
        def query_side_effect(query):
            if "ohhst" in query:
                return [{
                    "bte4cd": "PO-2024-001",
                    "bthinb": "Acme Corporation",
                    "btabnb": 12345
                }]
            elif "odhst" in query:
                return [
                    {"BUHUNB": 1, "BUHXTX": "EACH"},
                    {"BUHUNB": 2, "BUHXTX": "CASE"}
                ]
            elif "dsanrep" in query:
                return [{"ANB8TX": "UNIT"}]
            return []
        
        runner.run_query.side_effect = query_side_effect
        return runner
    
    @pytest.fixture
    def fetcher(self, mock_query_runner):
        """Create InvFetcher with realistic mock."""
        return InvFetcher(mock_query_runner, {"setting": "value"})
    
    def test_full_invoice_fetch_workflow(self, fetcher):
        """Test complete workflow of fetching invoice data."""
        invoice_number = 100001
        
        # Fetch PO
        po = fetcher.fetch_po(invoice_number)
        assert po == "PO-2024-001"
        
        # Fetch customer name (should use cache)
        cust_name = fetcher.fetch_cust_name(invoice_number)
        assert cust_name == "Acme Corporation"
        
        # Fetch customer number (should use cache)
        cust_no = fetcher.fetch_cust_no(invoice_number)
        assert cust_no == 12345
    
    def test_uom_fetch_workflow(self, fetcher):
        """Test UOM fetching workflow."""
        # Fetch UOM for line 1
        uom1 = fetcher.fetch_uom_desc(1001, 1, 0, 100001)
        assert uom1 == "EACH"
        
        # Fetch UOM for line 2 (same invoice, uses cache)
        uom2 = fetcher.fetch_uom_desc(1002, 1, 1, 100001)
        assert uom2 == "CASE"
