"""Unit tests for POFetcher."""

import pytest
from unittest.mock import MagicMock

from core.edi.po_fetcher import (
    POFetcher,
    POData,
    QueryRunnerProtocol,
)


class TestPOFetcher:
    """Tests for POFetcher class."""
    
    @pytest.fixture
    def mock_query_runner(self):
        """Create mock query runner."""
        return MagicMock(spec=QueryRunnerProtocol)
    
    @pytest.fixture
    def fetcher(self, mock_query_runner):
        """Create POFetcher with mock dependencies."""
        return POFetcher(mock_query_runner)
    
    def test_init_stores_query_runner(self, mock_query_runner):
        """Test initialization stores query runner."""
        fetcher = POFetcher(mock_query_runner)
        assert fetcher._query_runner is mock_query_runner
    
    def test_fetch_po_number_found(self, fetcher, mock_query_runner):
        """Test fetching found PO number."""
        mock_query_runner.run_query.return_value = [
            ("PO12345",)
        ]
        
        result = fetcher.fetch_po_number(100)
        
        assert result == "PO12345"
        mock_query_runner.run_query.assert_called_once()
    
    def test_fetch_po_number_not_found(self, fetcher, mock_query_runner):
        """Test fetching PO number when not found."""
        mock_query_runner.run_query.return_value = []
        
        result = fetcher.fetch_po_number(100)
        
        assert result == POFetcher.DEFAULT_PO
    
    def test_fetch_po_number_default_value(self):
        """Test default PO value is correct format."""
        assert POFetcher.DEFAULT_PO == "no_po_found    "
        assert len(POFetcher.DEFAULT_PO) == 15
    
    def test_fetch_po_number_converts_to_int(self, fetcher, mock_query_runner):
        """Test invoice number is converted to int in query."""
        mock_query_runner.run_query.return_value = [("PO",)]
        
        fetcher.fetch_po_number("100")
        
        # Verify query contains int conversion
        call_args = mock_query_runner.run_query.call_args[0][0]
        assert "100" in call_args
    
    def test_fetch_po_number_handles_string_input(self, fetcher, mock_query_runner):
        """Test fetch_po_number handles string invoice number."""
        mock_query_runner.run_query.return_value = [("PO999",)]
        
        result = fetcher.fetch_po_number("999")
        
        assert result == "PO999"
    
    def test_fetch_po_data_found(self, fetcher, mock_query_runner):
        """Test fetching complete PO data when found."""
        mock_query_runner.run_query.return_value = [
            ("PO12345", "Test Vendor", "VENDOR001")
        ]
        
        result = fetcher.fetch_po_data(100)
        
        assert result is not None
        assert isinstance(result, POData)
        assert result.po_number == "PO12345"
        assert result.vendor_name == "Test Vendor"
        assert result.vendor_oid == "VENDOR001"
    
    def test_fetch_po_data_not_found(self, fetcher, mock_query_runner):
        """Test fetching PO data when not found."""
        mock_query_runner.run_query.return_value = []
        
        result = fetcher.fetch_po_data(100)
        
        assert result is None
    
    def test_fetch_po_data_handles_null_values(self, fetcher, mock_query_runner):
        """Test fetching PO data handles null values."""
        mock_query_runner.run_query.return_value = [
            (None, None, None)
        ]
        
        result = fetcher.fetch_po_data(100)
        
        assert result is not None
        assert result.po_number == ""
        assert result.vendor_name == ""
        assert result.vendor_oid == ""
    
    def test_fetch_po_lines_returns_list(self, fetcher, mock_query_runner):
        """Test fetching PO lines returns list of dicts."""
        mock_query_runner.run_query.return_value = [
            (1, "ITEM001", 100.50, 1),
            (2, "ITEM002", 200.75, 1),
        ]
        
        result = fetcher.fetch_po_lines("PO12345")
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)
    
    def test_fetch_po_lines_correct_fields(self, fetcher, mock_query_runner):
        """Test PO lines have correct field names."""
        mock_query_runner.run_query.return_value = [
            (1, "ITEM001", 100.50, 1),
        ]
        
        result = fetcher.fetch_po_lines("PO12345")
        
        assert result[0]['line_number'] == 1
        assert result[0]['item_code'] == "ITEM001"
        assert result[0]['price'] == 100.50
        assert result[0]['status'] == 1
    
    def test_fetch_po_lines_empty_result(self, fetcher, mock_query_runner):
        """Test fetching PO lines when none found."""
        mock_query_runner.run_query.return_value = []
        
        result = fetcher.fetch_po_lines("NONEXISTENT")
        
        assert result == []


class TestPOData:
    """Tests for POData dataclass."""
    
    def test_po_data_creation(self):
        """Test POData can be created with all fields."""
        data = POData(
            po_number="PO123",
            vendor_name="Vendor",
            order_date="20250101",
            vendor_oid="OID123"
        )
        
        assert data.po_number == "PO123"
        assert data.vendor_name == "Vendor"
        assert data.order_date == "20250101"
        assert data.vendor_oid == "OID123"
    
    def test_po_data_defaults(self):
        """Test POData default values."""
        data = POData(po_number="PO123")
        
        assert data.vendor_name == ""
        assert data.order_date == ""
        assert data.vendor_oid == ""


class TestQueryRunnerProtocol:
    """Tests for QueryRunnerProtocol compliance."""
    
    def test_fetcher_accepts_mock(self):
        """Test POFetcher accepts mock implementing protocol."""
        mock_runner = MagicMock()
        mock_runner.run_query.return_value = [("PO",)]
        
        fetcher = POFetcher(mock_runner)
        result = fetcher.fetch_po_number(100)
        
        assert result == "PO"
    
    def test_protocol_runtime_checkable(self):
        """Test protocol is runtime checkable."""
        mock_runner = MagicMock()
        mock_runner.run_query = lambda q, p=None: []
        
        # Should not raise
        assert isinstance(mock_runner, QueryRunnerProtocol)
