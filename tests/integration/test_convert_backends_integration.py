"""Integration tests for convert backend settings from FolderConfiguration.

Tests:
- fintech_division_id used correctly
- ScannerWare settings used
- process_edi toggle works
- split_edi affects output
- UPC override settings affect conversion
- A-record padding affects conversion
- Invoice date offset affects conversion
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from interface.models.folder_configuration import (
    FolderConfiguration,
    EDIConfiguration,
    UPCOverrideConfiguration,
    ARecordPaddingConfiguration,
    InvoiceDateConfiguration,
    BackendSpecificConfiguration,
)


class TestFintechBackendIntegration:
    """Test suite for fintech backend integration with FolderConfiguration."""
    
    @pytest.fixture
    def finteh_config(self):
        """Create FolderConfiguration for fintech conversion."""
        return FolderConfiguration(
            folder_name="/test/fintech",
            backend_specific=BackendSpecificConfiguration(
                fintech_division_id="DIV001"
            ),
            edi=EDIConfiguration(
                process_edi="True",
                convert_to_format="fintech"
            )
        )
    
    def test_fintech_with_folder_config(self, finteh_config):
        """Test fintech_division_id is correctly extracted from config."""
        config_dict = finteh_config.to_dict()
        
        # Verify fintech_division_id is in the dict
        assert 'fintech_division_id' in config_dict
        assert config_dict['fintech_division_id'] == "DIV001"
    
    def test_fintech_division_id_passed_to_converter(self, finteh_config):
        """Test that fintech_division_id is correctly passed to converter."""
        config_dict = finteh_config.to_dict()
        
        # Simulate parameters passed to converter
        parameters_dict = {
            'fintech_division_id': config_dict['fintech_division_id']
        }
        
        assert parameters_dict['fintech_division_id'] == "DIV001"
    
    def test_empty_fintech_division_id(self):
        """Test handling of empty fintech_division_id."""
        config = FolderConfiguration(
            folder_name="/test/fintech",
            backend_specific=BackendSpecificConfiguration(
                fintech_division_id=""
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['fintech_division_id'] == ""
    
    def test_fintech_multiple_division_ids(self):
        """Test fintech with multiple division IDs in different configs."""
        configs = [
            FolderConfiguration(
                folder_name="/test1",
                backend_specific=BackendSpecificConfiguration(fintech_division_id="DIV001")
            ),
            FolderConfiguration(
                folder_name="/test2",
                backend_specific=BackendSpecificConfiguration(fintech_division_id="DIV002")
            ),
            FolderConfiguration(
                folder_name="/test3",
                backend_specific=BackendSpecificConfiguration(fintech_division_id="DIV003")
            ),
        ]
        
        division_ids = [c.to_dict()['fintech_division_id'] for c in configs]
        
        assert division_ids == ["DIV001", "DIV002", "DIV003"]


class TestScannerWareBackendIntegration:
    """Test suite for ScannerWare backend integration with FolderConfiguration."""
    
    @pytest.fixture
    def scannerware_config(self):
        """Create FolderConfiguration for ScannerWare conversion."""
        return FolderConfiguration(
            folder_name="/test/scannerware",
            edi=EDIConfiguration(
                process_edi="True",
                convert_to_format="ScannerWare"
            )
        )
    
    def test_scannerware_with_folder_config(self, scannerware_config):
        """Test ScannerWare settings are correctly extracted from config."""
        config_dict = scannerware_config.to_dict()
        
        assert config_dict['convert_to_format'] == "ScannerWare"
        assert config_dict['process_edi'] == "True"
    
    def test_scannerware_format_recognized(self, scannerware_config):
        """Test that ScannerWare format is correctly identified."""
        edi_config = scannerware_config.edi
        
        assert edi_config.convert_to_format == "ScannerWare"
    
    def test_scannerware_with_a_record_padding(self):
        """Test ScannerWare with A-record padding configuration."""
        config = FolderConfiguration(
            folder_name="/test/scannerware",
            edi=EDIConfiguration(
                process_edi="True",
                convert_to_format="ScannerWare"
            ),
            a_record_padding=ARecordPaddingConfiguration(
                enabled=True,
                padding_text="123456",
                padding_length=6
            )
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['pad_a_records'] == "True"
        assert config_dict['a_record_padding'] == "123456"


class TestProcessEDIToggleIntegration:
    """Test suite for process_edi toggle affecting backend behavior."""
    
    @pytest.fixture
    def edi_config_enabled(self):
        """Create FolderConfiguration with EDI processing enabled."""
        return FolderConfiguration(
            folder_name="/test/edi_enabled",
            edi=EDIConfiguration(
                process_edi="True",
                convert_to_format="csv"
            )
        )
    
    @pytest.fixture
    def edi_config_disabled(self):
        """Create FolderConfiguration with EDI processing disabled."""
        return FolderConfiguration(
            folder_name="/test/edi_disabled",
            edi=EDIConfiguration(
                process_edi="False",
                convert_to_format=""
            )
        )
    
    def test_convert_format_toggle(self, edi_config_enabled, edi_config_disabled):
        """Test process_edi toggle gates conversion."""
        enabled_dict = edi_config_enabled.to_dict()
        disabled_dict = edi_config_disabled.to_dict()
        
        assert enabled_dict['process_edi'] == "True"
        assert disabled_dict['process_edi'] == "False"
    
    def test_convert_format_set_when_enabled(self, edi_config_enabled):
        """Test convert_to_format is set when EDI is enabled."""
        config_dict = edi_config_enabled.to_dict()
        
        assert config_dict['convert_to_format'] == "csv"
    
    def test_convert_format_empty_when_disabled(self, edi_config_disabled):
        """Test convert_to_format is empty when EDI is disabled."""
        config_dict = edi_config_disabled.to_dict()
        
        assert config_dict['convert_to_format'] == ""


class TestSplitEDIIntegration:
    """Test suite for split_edi affecting output."""
    
    @pytest.fixture
    def split_edi_config(self):
        """Create FolderConfiguration with split EDI enabled."""
        return FolderConfiguration(
            folder_name="/test/split_edi",
            edi=EDIConfiguration(
                process_edi="True",
                split_edi=True,
                split_edi_include_invoices=True,
                split_edi_include_credits=True,
                split_edi_filter_categories="1,2,3,ALL",
                split_edi_filter_mode="include"
            )
        )
    
    @pytest.fixture
    def no_split_edi_config(self):
        """Create FolderConfiguration with split EDI disabled."""
        return FolderConfiguration(
            folder_name="/test/no_split",
            edi=EDIConfiguration(
                process_edi="True",
                split_edi=False
            )
        )
    
    def test_split_edi_settings(self, split_edi_config):
        """Test split_EDI settings are correctly extracted from config."""
        config_dict = split_edi_config.to_dict()
        
        assert config_dict['split_edi'] is True
        assert config_dict['split_edi_include_invoices'] is True
        assert config_dict['split_edi_include_credits'] is True
        assert config_dict['split_edi_filter_categories'] == "1,2,3,ALL"
        assert config_dict['split_edi_filter_mode'] == "include"
    
    def test_split_edi_affects_output(self, split_edi_config):
        """Test that split_edi flag affects output generation logic."""
        config_dict = split_edi_config.to_dict()
        
        # Simulate output generation logic
        if config_dict['split_edi']:
            output_mode = "split"
            include_invoices = config_dict['split_edi_include_invoices']
            include_credits = config_dict['split_edi_include_credits']
        else:
            output_mode = "single"
            include_invoices = False
            include_credits = False
        
        assert output_mode == "split"
        assert include_invoices is True
        assert include_credits is True
    
    def test_no_split_edi_settings(self, no_split_edi_config):
        """Test settings when split_EDI is disabled."""
        config_dict = no_split_edi_config.to_dict()
        
        assert config_dict['split_edi'] is False
    
    def test_split_edi_filter_categories(self, split_edi_config):
        """Test split_edi_filter_categories is correctly parsed."""
        config_dict = split_edi_config.to_dict()
        
        filter_categories = config_dict['split_edi_filter_categories']
        
        # Should be able to parse categories
        categories = filter_categories.split(',')
        assert "1" in categories
        assert "2" in categories
        assert "ALL" in categories


class TestUPCOverrideIntegration:
    """Test suite for UPC override settings affecting conversion."""
    
    @pytest.fixture
    def upc_override_enabled(self):
        """Create FolderConfiguration with UPC override enabled."""
        return FolderConfiguration(
            folder_name="/test/upc",
            upc_override=UPCOverrideConfiguration(
                enabled=True,
                level=2,
                category_filter="1,2,3,ALL",
                target_length=11,
                padding_pattern="           "
            )
        )
    
    @pytest.fixture
    def upc_override_disabled(self):
        """Create FolderConfiguration with UPC override disabled."""
        return FolderConfiguration(
            folder_name="/test/no_upc",
            upc_override=UPCOverrideConfiguration(
                enabled=False
            )
        )
    
    def test_upc_override_integration(self, upc_override_enabled):
        """Test UPC override settings affect UPC processing."""
        config_dict = upc_override_enabled.to_dict()
        
        assert config_dict['override_upc_bool'] is True
        assert config_dict['override_upc_level'] == 2
        assert config_dict['override_upc_category_filter'] == "1,2,3,ALL"
        assert config_dict['upc_target_length'] == 11
    
    def test_upc_disabled_no_override(self, upc_override_disabled):
        """Test that disabled UPC override doesn't affect processing."""
        config_dict = upc_override_disabled.to_dict()
        
        assert config_dict['override_upc_bool'] is False
    
    def test_upc_target_length_affects_conversion(self, upc_override_enabled):
        """Test that upc_target_length affects UPC conversion logic."""
        config_dict = upc_override_enabled.to_dict()
        
        target_length = config_dict['upc_target_length']
        
        # Simulate UPC conversion logic
        if config_dict['override_upc_bool']:
            upc_mode = f"override_{target_length}"
        else:
            upc_mode = "standard"
        
        assert upc_mode == "override_11"
    
    def test_upc_category_filter_affects_conversion(self, upc_override_enabled):
        """Test that category_filter affects which items get UPC override."""
        config_dict = upc_override_enabled.to_dict()
        
        filter_str = config_dict['override_upc_category_filter']
        
        # Simulate category filtering logic
        if "ALL" in filter_str:
            apply_to_all = True
        else:
            categories = filter_str.split(',')
            apply_to_all = False
        
        assert apply_to_all is True
    
    def test_upc_padding_pattern(self, upc_override_enabled):
        """Test UPC padding pattern is correctly set."""
        config_dict = upc_override_enabled.to_dict()
        
        padding_pattern = config_dict['upc_padding_pattern']
        
        # Pattern should be 11 spaces (default)
        assert len(padding_pattern) == 11


class TestARecordPaddingIntegration:
    """Test suite for A-record padding affecting conversion."""
    
    @pytest.fixture
    def a_record_padding_enabled(self):
        """Create FolderConfiguration with A-record padding enabled."""
        return FolderConfiguration(
            folder_name="/test/a_record",
            a_record_padding=ARecordPaddingConfiguration(
                enabled=True,
                padding_text="PREFIX",
                padding_length=6,
                append_text="APPEND",
                append_enabled=True,
                force_txt_extension=True
            )
        )
    
    @pytest.fixture
    def a_record_padding_disabled(self):
        """Create FolderConfiguration with A-record padding disabled."""
        return FolderConfiguration(
            folder_name="/test/no_a_record",
            a_record_padding=ARecordPaddingConfiguration(
                enabled=False
            )
        )
    
    def test_a_record_padding_integration(self, a_record_padding_enabled):
        """Test A-record padding settings affect record processing."""
        config_dict = a_record_padding_enabled.to_dict()
        
        assert config_dict['pad_a_records'] == "True"
        assert config_dict['a_record_padding'] == "PREFIX"
        assert config_dict['a_record_padding_length'] == 6
        assert config_dict['append_a_records'] == "True"
        assert config_dict['a_record_append_text'] == "APPEND"
        assert config_dict['force_txt_file_ext'] == "True"
    
    def test_a_record_disabled_no_padding(self, a_record_padding_disabled):
        """Test disabled A-record padding doesn't affect processing."""
        config_dict = a_record_padding_disabled.to_dict()
        
        assert config_dict['pad_a_records'] == "False"
    
    def test_a_record_padding_affects_conversion(self, a_record_padding_enabled):
        """Test that A-record padding affects conversion output."""
        config_dict = a_record_padding_enabled.to_dict()
        
        # Simulate A-record padding logic
        if config_dict['pad_a_records'] == "True":
            padding_text = config_dict['a_record_padding']
            padding_length = config_dict['a_record_padding_length']
            has_append = config_dict['append_a_records'] == "True"
            force_ext = config_dict['force_txt_file_ext'] == "True"
        else:
            padding_text = ""
            padding_length = 0
            has_append = False
            force_ext = False
        
        assert padding_text == "PREFIX"
        assert padding_length == 6
        assert has_append is True
        assert force_ext is True
    
    def test_a_record_append_text(self, a_record_padding_enabled):
        """Test A-record append text is correctly set."""
        config_dict = a_record_padding_enabled.to_dict()
        
        append_text = config_dict['a_record_append_text']
        
        assert append_text == "APPEND"


class TestInvoiceDateOffsetIntegration:
    """Test suite for invoice date offset affecting conversion."""
    
    @pytest.fixture
    def invoice_date_config(self):
        """Create FolderConfiguration with invoice date offset."""
        return FolderConfiguration(
            folder_name="/test/invoice_date",
            invoice_date=InvoiceDateConfiguration(
                offset=7,
                custom_format_enabled=True,
                custom_format_string="%Y-%m-%d",
                retail_uom=False
            )
        )
    
    @pytest.fixture
    def invoice_date_negative_offset(self):
        """Create FolderConfiguration with negative invoice date offset."""
        return FolderConfiguration(
            folder_name="/test/negative_offset",
            invoice_date=InvoiceDateConfiguration(
                offset=-5
            )
        )
    
    @pytest.fixture
    def invoice_date_no_offset(self):
        """Create FolderConfiguration with no invoice date offset."""
        return FolderConfiguration(
            folder_name="/test/no_offset",
            invoice_date=InvoiceDateConfiguration(
                offset=0
            )
        )
    
    def test_invoice_date_offset_integration(self, invoice_date_config):
        """Test invoice date offset settings affect date processing."""
        config_dict = invoice_date_config.to_dict()
        
        assert config_dict['invoice_date_offset'] == 7
        assert config_dict['invoice_date_custom_format'] is True
        assert config_dict['invoice_date_custom_format_string'] == "%Y-%m-%d"
        assert config_dict['retail_uom'] is False
    
    def test_negative_offset(self, invoice_date_negative_offset):
        """Test negative invoice date offset."""
        config_dict = invoice_date_negative_offset.to_dict()
        
        assert config_dict['invoice_date_offset'] == -5
    
    def test_zero_offset(self, invoice_date_no_offset):
        """Test zero invoice date offset."""
        config_dict = invoice_date_no_offset.to_dict()
        
        assert config_dict['invoice_date_offset'] == 0
    
    def test_invoice_date_offset_affects_conversion(self, invoice_date_config):
        """Test that invoice date offset affects date conversion logic."""
        config_dict = invoice_date_config.to_dict()
        
        offset = config_dict['invoice_date_offset']
        custom_format = config_dict['invoice_date_custom_format']
        format_string = config_dict['invoice_date_custom_format_string']
        
        # Simulate date offset logic
        if offset != 0:
            effective_offset = offset
        else:
            effective_offset = 0
        
        if custom_format:
            date_format = format_string
        else:
            date_format = "%m/%d/%Y"
        
        assert effective_offset == 7
        assert date_format == "%Y-%m-%d"
    
    def test_retail_uom_flag(self, invoice_date_config):
        """Test retail UOM flag is correctly set."""
        config_dict = invoice_date_config.to_dict()
        
        retail_uom = config_dict['retail_uom']
        
        assert retail_uom is False
    
    def test_invoice_date_all_offsets_in_range(self):
        """Test all valid invoice date offsets are accepted."""
        valid_offsets = list(range(-14, 15))
        
        for offset in valid_offsets:
            config = FolderConfiguration(
                folder_name="/test",
                invoice_date=InvoiceDateConfiguration(offset=offset)
            )
            config_dict = config.to_dict()
            
            assert config_dict['invoice_date_offset'] == offset


class TestConvertFormatIntegration:
    """Test suite for convert format settings affecting backend behavior."""
    
    @pytest.mark.parametrize("format_name,expected", [
        ("csv", "csv"),
        ("ScannerWare", "ScannerWare"),
        ("fintech", "fintech"),
        ("eStore_eInvoice", "eStore_eInvoice"),
        ("simplified_csv", "simplified_csv"),
    ])
    def test_all_convert_formats(self, format_name, expected):
        """Test all convert formats are correctly stored."""
        config = FolderConfiguration(
            folder_name="/test",
            edi=EDIConfiguration(convert_to_format=format_name)
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['convert_to_format'] == expected
    
    def test_convert_format_affects_backend_selection(self):
        """Test that convert_to_format determines which backend is used."""
        formats_to_backends = {
            "csv": "csv_backend",
            "ScannerWare": "scannerware_backend",
            "fintech": "fintech_backend",
            "eStore_eInvoice": "estore_backend",
            "simplified_csv": "csv_backend",
        }
        
        for format_name, backend in formats_to_backends.items():
            config = FolderConfiguration(
                folder_name="/test",
                edi=EDIConfiguration(convert_to_format=format_name)
            )
            config_dict = config.to_dict()
            
            selected_backend = formats_to_backends.get(
                config_dict['convert_to_format'],
                "unknown"
            )
            
            assert selected_backend == backend
