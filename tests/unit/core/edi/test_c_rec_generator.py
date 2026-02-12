"""Unit tests for CRecGenerator."""

import pytest
from unittest.mock import MagicMock
from io import StringIO

from core.edi.c_rec_generator import (
    CRecGenerator,
    CRecordConfig,
    QueryRunnerProtocol,
)


class TestCRecGenerator:
    """Tests for CRecGenerator class."""
    
    @pytest.fixture
    def mock_query_runner(self):
        """Create mock query runner."""
        return MagicMock(spec=QueryRunnerProtocol)
    
    @pytest.fixture
    def generator(self, mock_query_runner):
        """Create CRecGenerator with mock dependencies."""
        return CRecGenerator(mock_query_runner)
    
    @pytest.fixture
    def generator_with_config(self, mock_query_runner):
        """Create CRecGenerator with custom config."""
        config = CRecordConfig(
            default_uom='CS',
            default_vendor_oid='VENDOR123',
            charge_type='ABC'
        )
        return CRecGenerator(mock_query_runner, config)
    
    def test_init_stores_query_runner(self, mock_query_runner):
        """Test initialization stores query runner."""
        generator = CRecGenerator(mock_query_runner)
        assert generator._query_runner is mock_query_runner
    
    def test_init_default_config(self, generator):
        """Test default config is created when not provided."""
        assert generator.config is not None
        assert generator.config.default_uom == 'EA'
        assert generator.config.charge_type == 'TAB'
    
    def test_init_custom_config(self, generator_with_config):
        """Test custom config is stored."""
        assert generator_with_config.config.default_uom == 'CS'
        assert generator_with_config.config.charge_type == 'ABC'
    
    def test_set_invoice_number(self, generator):
        """Test setting invoice number."""
        generator.set_invoice_number(100)
        
        assert generator._invoice_number == 100
        assert generator.unappended_records is True
    
    def test_set_invoice_number_converts_to_int(self, generator):
        """Test invoice number is stored as provided."""
        generator.set_invoice_number("200")
        
        assert generator._invoice_number == "200"
        assert generator.unappended_records is True
    
    def test_fetch_splitted_sales_tax_prepaid_only(self, generator, mock_query_runner):
        """Test generating prepaid sales tax C record only."""
        mock_query_runner.run_query.return_value = [
            (0, 100.50)  # non-prepaid=0, prepaid=100.50
        ]
        
        output = StringIO()
        generator.set_invoice_number(100)
        generator.fetch_splitted_sales_tax_totals(output)
        
        content = output.getvalue()
        assert "Prepaid Sales Tax" in content
        # Check that standalone "Sales Tax" is not present (only "Prepaid Sales Tax")
        assert content.count("Sales Tax") == 1  # Only appears once as part of "Prepaid Sales Tax"
        assert generator.unappended_records is False
    
    def test_fetch_splitted_sales_tax_non_prepaid_only(self, generator, mock_query_runner):
        """Test generating non-prepaid sales tax C record only."""
        mock_query_runner.run_query.return_value = [
            (50.25, 0)  # non-prepaid=50.25, prepaid=0
        ]
        
        output = StringIO()
        generator.set_invoice_number(100)
        generator.fetch_splitted_sales_tax_totals(output)
        
        content = output.getvalue()
        assert "Sales Tax" in content
        assert "Prepaid Sales Tax" not in content
    
    def test_fetch_splitted_sales_tax_both(self, generator, mock_query_runner):
        """Test generating both sales tax C records."""
        mock_query_runner.run_query.return_value = [
            (50.25, 100.50)  # both present
        ]
        
        output = StringIO()
        generator.set_invoice_number(100)
        generator.fetch_splitted_sales_tax_totals(output)
        
        content = output.getvalue()
        assert "Prepaid Sales Tax" in content
        assert "Sales Tax" in content
    
    def test_fetch_splitted_sales_tax_none_values(self, generator, mock_query_runner):
        """Test handling None values from query."""
        mock_query_runner.run_query.return_value = [
            (None, None)
        ]
        
        output = StringIO()
        generator.set_invoice_number(100)
        generator.fetch_splitted_sales_tax_totals(output)
        
        content = output.getvalue()
        assert content == ""
    
    def test_fetch_splitted_sales_tax_zero_values(self, generator, mock_query_runner):
        """Test handling zero values from query."""
        mock_query_runner.run_query.return_value = [
            (0, 0)
        ]
        
        output = StringIO()
        generator.set_invoice_number(100)
        generator.fetch_splitted_sales_tax_totals(output)
        
        content = output.getvalue()
        assert content == ""
    
    def test_write_line_positive_amount(self, generator):
        """Test writing C record with positive amount."""
        output = StringIO()
        generator._write_line("Test Charge", 100.50, output)
        
        content = output.getvalue()
        assert content.startswith("CTAB")
        assert "Test Charge" in content
        assert "-" not in content
    
    def test_write_line_negative_amount(self, generator):
        """Test writing C record with negative amount."""
        output = StringIO()
        generator._write_line("Test Charge", -100.50, output)
        
        content = output.getvalue()
        assert content.startswith("CTAB")
        assert "-" in content
    
    def test_write_line_formats_description(self, generator):
        """Test description is padded to 25 characters."""
        output = StringIO()
        generator._write_line("Test", 100, output)
        
        content = output.getvalue()
        # "Test" should be padded to 25 chars
        assert "Test" in content
        assert "Test                    " in content  # 25 chars total
    
    def test_write_line_formats_amount(self, generator):
        """Test amount is formatted correctly."""
        output = StringIO()
        generator._write_line("Test", 123.45, output)
        
        content = output.getvalue()
        # Amount should be 9 digits, no decimal
        assert "12345" in content  # 123.45 -> "12345" padded
    
    def test_write_line_uses_config_charge_type(self, generator_with_config):
        """Test _write_line uses config charge type."""
        output = StringIO()
        generator_with_config._write_line("Test", 100, output)
        
        content = output.getvalue()
        assert content.startswith("CABC")  # Custom charge type
    
    def test_generate_c_record_returns_string(self, generator):
        """Test generate_c_record returns formatted string."""
        result = generator.generate_c_record(
            charge_type="TAX",
            description="Sales Tax",
            amount=50.00
        )
        
        assert isinstance(result, str)
        assert result.startswith("CTAX")
        assert result.endswith("\n")
    
    def test_generate_c_record_with_custom_charge_type(self, generator):
        """Test generate_c_record with custom charge type."""
        result = generator.generate_c_record(
            charge_type="FRT",
            description="Freight",
            amount=25.00
        )
        
        assert result.startswith("CFRT")
    
    def test_generate_c_records_for_invoice(self, generator):
        """Test generating multiple C records."""
        invoice_data = {'invoice_number': '12345'}
        charges = [
            {'type': 'TAX', 'description': 'Sales Tax', 'amount': 10.00},
            {'type': 'FRT', 'description': 'Freight', 'amount': 5.00},
        ]
        
        results = generator.generate_c_records_for_invoice(invoice_data, charges)
        
        assert len(results) == 2
        assert results[0].startswith("CTAX")
        assert results[1].startswith("CFRT")
    
    def test_generate_c_records_for_invoice_uses_defaults(self, generator):
        """Test generate_c_records uses default charge type."""
        invoice_data = {'invoice_number': '12345'}
        charges = [
            {'description': 'Test', 'amount': 10.00},
        ]
        
        results = generator.generate_c_records_for_invoice(invoice_data, charges)
        
        # Should use default charge type 'TAB'
        assert results[0].startswith("CTAB")
    
    def test_unappended_records_resets_after_fetch(self, generator, mock_query_runner):
        """Test unappended_records resets after fetch."""
        mock_query_runner.run_query.return_value = [(0, 100)]
        
        output = StringIO()
        generator.set_invoice_number(100)
        assert generator.unappended_records is True
        
        generator.fetch_splitted_sales_tax_totals(output)
        assert generator.unappended_records is False


class TestCRecordConfig:
    """Tests for CRecordConfig dataclass."""
    
    def test_config_defaults(self):
        """Test config default values."""
        config = CRecordConfig()
        
        assert config.default_uom == 'EA'
        assert config.default_vendor_oid == ''
        assert config.charge_type == 'TAB'
    
    def test_config_custom_values(self):
        """Test config with custom values."""
        config = CRecordConfig(
            default_uom='CS',
            default_vendor_oid='VENDOR123',
            charge_type='ABC'
        )
        
        assert config.default_uom == 'CS'
        assert config.default_vendor_oid == 'VENDOR123'
        assert config.charge_type == 'ABC'


class TestQueryRunnerProtocol:
    """Tests for QueryRunnerProtocol compliance."""
    
    def test_generator_accepts_mock(self):
        """Test CRecGenerator accepts mock implementing protocol."""
        mock_runner = MagicMock()
        mock_runner.run_query.return_value = [(0, 100)]
        
        generator = CRecGenerator(mock_runner)
        generator.set_invoice_number(100)
        
        output = StringIO()
        generator.fetch_splitted_sales_tax_totals(output)
        
        assert mock_runner.run_query.called
    
    def test_protocol_runtime_checkable(self):
        """Test protocol is runtime checkable."""
        mock_runner = MagicMock()
        mock_runner.run_query = lambda q, p=None: []
        
        # Should not raise
        assert isinstance(mock_runner, QueryRunnerProtocol)


class TestCRecordFormat:
    """Tests for C record output format compliance."""
    
    @pytest.fixture
    def mock_query_runner(self):
        """Create mock query runner."""
        return MagicMock(spec=QueryRunnerProtocol)
    
    @pytest.fixture
    def generator(self, mock_query_runner):
        """Create CRecGenerator with mock dependencies."""
        return CRecGenerator(mock_query_runner)
    
    def test_c_record_line_length(self, generator):
        """Test C record line has correct format."""
        # C records: C + 3 char type + 25 char desc + 9 char amount + newline
        result = generator.generate_c_record("TAB", "Test Charge", 100)
        
        # Remove newline for length check
        line = result.rstrip('\n')
        # C(1) + TAB(3) + desc(25) + amount(9) = 38 chars
        assert len(line) == 38
    
    def test_c_record_starts_with_c(self, generator):
        """Test C record starts with 'C'."""
        result = generator.generate_c_record("TAB", "Test", 100)
        assert result[0] == 'C'
    
    def test_c_record_ends_with_newline(self, generator):
        """Test C record ends with newline."""
        result = generator.generate_c_record("TAB", "Test", 100)
        assert result.endswith('\n')
    
    def test_amount_negative_formatting(self, generator):
        """Test negative amount is formatted with leading minus."""
        result = generator.generate_c_record("TAB", "Test", -100.50)
        
        # Negative amounts should have a minus sign
        assert '-' in result
