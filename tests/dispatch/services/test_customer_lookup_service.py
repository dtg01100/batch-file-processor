import pytest
from unittest.mock import MagicMock
from dispatch.services.customer_lookup_service import CustomerLookupService


class TestCustomerLookupService:
    def test_lookup_found(self):
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = [
            {"Customer Number": "123", "Customer Name": "Acme Corp"}
        ]
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        result = service.lookup("INV001")
        assert result["Customer_Number"] == "123"

    def test_lookup_not_found_raises(self):
        from core.exceptions import CustomerLookupError
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = []
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        with pytest.raises(CustomerLookupError):
            service.lookup("INV001")

    def test_build_header_dict_strip_spaces(self):
        mock_query_runner = MagicMock()
        service = CustomerLookupService(mock_query_runner, "SELECT ...")
        raw = {"Customer Number": "123"}
        result = service._build_header_dict(raw, [])
        assert "Customer Number" not in result
        assert "Customer_Number" in result