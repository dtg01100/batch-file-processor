import pytest
from unittest.mock import MagicMock
from dispatch.services.uom_lookup_service import UOMLookupService


class TestUOMLookupService:
    def test_get_uom_found_exact_match(self):
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = [
            {"itemno": "123", "uom_mult": "6", "uom_code": "CS"},
            {"itemno": "123", "uom_mult": "12", "uom_code": "EA"},
        ]
        service = UOMLookupService(mock_query_runner)
        service.uom_lookup_list = mock_query_runner.run_query.return_value

        result = service.get_uom("123", "6")
        assert result == "CS"

    def test_get_uom_no_lookup_list(self):
        service = UOMLookupService(MagicMock())
        service.uom_lookup_list = []
        assert service.get_uom("123", "6") == "?"

    def test_init_uom_lookup(self):
        mock_query_runner = MagicMock()
        mock_query_runner.run_query.return_value = [{"itemno": "123"}]
        service = UOMLookupService(mock_query_runner)

        result = service.init_uom_lookup("INV001")

        mock_query_runner.run_query.assert_called_once()
        assert len(result) == 1
