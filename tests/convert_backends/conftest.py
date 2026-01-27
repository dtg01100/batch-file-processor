"""
Pytest configuration and fixtures for convert_to backend testing.

Provides reusable fixtures for testing all 10 convert_to backend converters
to ensure they never regress.
"""

import os
import pytest
from pathlib import Path


# ============================================================================
# PATH FIXTURES
# ============================================================================

@pytest.fixture
def data_dir():
    """Return path to convert_backends test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def edi_basic(data_dir):
    """Path to basic valid EDI file."""
    return str(data_dir / "basic_edi.txt")


@pytest.fixture
def edi_complex(data_dir):
    """Path to complex multi-invoice EDI file."""
    return str(data_dir / "complex_edi.txt")


@pytest.fixture
def edi_edge_cases(data_dir):
    """Path to edge cases EDI file."""
    return str(data_dir / "edge_cases_edi.txt")


@pytest.fixture
def edi_malformed(data_dir):
    """Path to malformed EDI file."""
    return str(data_dir / "malformed_edi.txt")


@pytest.fixture
def edi_empty(data_dir):
    """Path to empty EDI file."""
    return str(data_dir / "empty_edi.txt")


@pytest.fixture
def edi_fintech(data_dir):
    """Path to EDI file formatted for fintech converter (numeric invoice numbers)."""
    return str(data_dir / "fintech_edi.txt")


# ============================================================================
# REAL CORPUS FIXTURES - Access to alledi/ corpus (165K+ production EDI files)
# ============================================================================

@pytest.fixture
def alledi_dir():
    """Return path to alledi corpus directory if available locally."""
    corpus_path = Path("/workspaces/batch-file-processor/alledi")
    if not corpus_path.exists():
        pytest.skip("alledi corpus not available locally")
    return corpus_path


@pytest.fixture
def corpus_sample_files(alledi_dir):
    """Return list of sample production EDI files from corpus (first 10 numbered files)."""
    # Numbered files (e.g., 010042.001) are the production format
    files = sorted(alledi_dir.glob("[0-9]*.[0-9]*"))
    return [str(f) for f in files[:10]]


@pytest.fixture
def corpus_001_file(alledi_dir):
    """Return path to corpus file 001.edi - reference format (not production)."""
    path = alledi_dir / "001.edi"
    if not path.exists():
        pytest.skip("001.edi not found in corpus")
    return str(path)


@pytest.fixture
def corpus_002_file(alledi_dir):
    """Return path to corpus file 002.edi - reference format (not production)."""
    path = alledi_dir / "002.edi"
    if not path.exists():
        pytest.skip("002.edi not found in corpus")
    return str(path)


@pytest.fixture
def corpus_010042_file(alledi_dir):
    """Return path to corpus file 010042.001 - PRODUCTION FORMAT (numbered files)."""
    path = alledi_dir / "010042.001"
    if not path.exists():
        pytest.skip("010042.001 not found in corpus")
    return str(path)


@pytest.fixture
def corpus_large_files(alledi_dir):
    """Return list of larger production EDI files from corpus (>5KB)."""
    # Numbered files (e.g., 010042.XXX) are the production format
    files = sorted(alledi_dir.glob("[0-9]*.[0-9]*"))
    large_files = [f for f in files if f.stat().st_size > 5120][:5]
    if not large_files:
        pytest.skip("No large corpus files found (>5KB)")
    return [str(f) for f in large_files]


@pytest.fixture
def corpus_edge_cases(alledi_dir):
    """Return paths to production corpus files with various sizes for edge case testing."""
    # Numbered files (e.g., 010042.XXX) are the production format
    files = sorted(alledi_dir.glob("[0-9]*.[0-9]*"))
    
    # Find smallest file, medium, and largest
    sorted_by_size = sorted(files, key=lambda f: f.stat().st_size)
    
    edge_files = {}
    if sorted_by_size:
        edge_files['smallest'] = str(sorted_by_size[0])
    if len(sorted_by_size) > len(sorted_by_size) // 2:
        edge_files['medium'] = str(sorted_by_size[len(sorted_by_size) // 2])
    if len(sorted_by_size) > 1:
        edge_files['largest'] = str(sorted_by_size[-1])
    
    if not edge_files:
        pytest.skip("Insufficient corpus files for edge case testing")
    
    return edge_files


# ============================================================================
# SETTINGS & PARAMETERS FIXTURES
# ============================================================================

@pytest.fixture
def settings_dict():
    """Return default settings dictionary for converters."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "localhost",
        "odbc_driver": "mock_driver",
    }


@pytest.fixture
def csv_parameters():
    """Return default parameters for CSV converters."""
    return {
        "calculate_upc_check_digit": "False",
        "include_a_records": "True",
        "include_c_records": "True",
        "include_headers": "True",
        "filter_ampersand": "False",
        "pad_a_records": "False",
        "a_record_padding": "000000",
        "override_upc_bool": "False",
        "override_upc_level": 0,
        "override_upc_category_filter": "",
        "retail_uom": False,
    }


@pytest.fixture
def scannerware_parameters():
    """Return default parameters for scannerware converter."""
    return {
        "a_record_padding": "000000",
        "append_a_records": "False",
        "a_record_append_text": "",
        "force_txt_file_ext": "False",
        "invoice_date_offset": 0,
    }


@pytest.fixture
def scansheet_parameters():
    """Return default parameters for scansheet converter."""
    return {
        "a_record_padding": "000000",
        "append_a_records": "False",
        "a_record_append_text": "",
        "include_headers": "True",
        "header_text": "Invoice Header",
        "include_invoice_totals": "True",
    }


@pytest.fixture
def fintech_parameters():
    """Return default parameters for fintech converter."""
    return {
        "include_headers": "True",
        "include_a_records": "True",
        "include_c_records": "True",
        "a_record_padding": "000000",
        "pad_a_records": "False",
        "fintech_division_id": "12345",  # Required parameter
    }


@pytest.fixture
def simplified_csv_parameters():
    """Return default parameters for simplified CSV converter."""
    return {
        "include_headers": "True",
        "filter_by_customer": "False",
        "customer_filter": "",
        "retail_uom": False,  # Required parameter
        "include_item_numbers": "True",  # Required parameter
        "include_item_description": "True",  # Required parameter
        "simple_csv_sort_order": "description,vendor_item,unit_cost,qty_of_units",  # Required parameter
    }


@pytest.fixture
def yellowdog_parameters():
    """Return default parameters for yellowdog CSV converter."""
    return {
        "include_headers": "True",
        "delimiter": ",",
    }


@pytest.fixture
def custom_parameters():
    """Return default parameters for custom converters."""
    return {
        "a_record_padding": "000000",
        "include_headers": "True",
        "customer_specific_field": "",
    }


@pytest.fixture
def estore_parameters():
    """Return default parameters for eStore converters."""
    return {
        "include_package_info": "True",
        "include_pricing": "True",
        "xml_format": "generic",
        "output_encoding": "UTF-8",
        "estore_store_number": "12345",
        "estore_Vendor_OId": "67890",
        "estore_vendor_NameVendorOID": "Test Vendor",
        "estore_c_record_OID": "10025",
    }


# ============================================================================
# UPC LOOKUP FIXTURES
# ============================================================================

@pytest.fixture
def upc_lookup_basic():
    """Return basic mock UPC lookup dictionary."""
    lookup = {
        "012345678901": {
            "description": "Product Description",
            "category": "1001",
            "cost": 10.00,
            "retail": 15.99,
        },
        "098765432101": {
            "description": "Another Product Name",
            "category": "1002",
            "cost": 20.00,
            "retail": 29.99,
        },
        "111111111111": {
            "description": "Third Product Here",
            "category": "1003",
            "cost": 5.00,
            "retail": 8.99,
        },
        "222222222222": {
            "description": "Fourth Product Line",
            "category": "1004",
            "cost": 15.00,
            "retail": 22.99,
        },
    }
    
    # Add fintech-style entries (vendor_item -> (category, upc, case_upc))
    lookup[561234] = ("1001", "012345678901", "012345678902")
    lookup[987654] = ("1002", "098765432101", "098765432102")
    
    return lookup


@pytest.fixture
def upc_lookup_empty():
    """Return empty UPC lookup."""
    return {}


@pytest.fixture
def upc_lookup_callable():
    """Return callable UPC lookup (mock function)."""
    def lookup_func(upc):
        """Mock UPC lookup function."""
        defaults = {
            "description": f"Mock Product {upc}",
            "category": "9999",
            "cost": 0.00,
            "retail": 0.00,
        }
        return defaults
    return lookup_func


# ============================================================================
# OUTPUT VALIDATION FIXTURES & UTILITIES
# ============================================================================

@pytest.fixture
def validate_csv():
    """Return CSV validation function."""
    def _validate(filepath, expected_rows=None, expected_cols=None, has_headers=True):
        """Validate CSV file format."""
        import csv
        
        assert os.path.exists(filepath), f"File not found: {filepath}"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) > 0, "CSV file is empty"
        
        if has_headers:
            assert len(rows) > 1, "CSV has headers but no data rows"
        
        if expected_cols:
            assert len(rows[0]) == expected_cols, f"Expected {expected_cols} columns, got {len(rows[0])}"
        
        if expected_rows:
            assert len(rows) == expected_rows, f"Expected {expected_rows} rows, got {len(rows)}"
        
        return rows
    
    return _validate


@pytest.fixture
def validate_txt():
    """Return TXT validation function."""
    def _validate(filepath, expected_lines=None, encoding='utf-8'):
        """Validate TXT file format."""
        assert os.path.exists(filepath), f"File not found: {filepath}"
        
        with open(filepath, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        assert len(lines) > 0, "TXT file is empty"
        
        if expected_lines:
            assert len(lines) == expected_lines, f"Expected {expected_lines} lines, got {len(lines)}"
        
        return lines
    
    return _validate


@pytest.fixture
def mock_query_runner():
    """Mock query_runner for database-dependent converters."""
    from unittest.mock import MagicMock, patch
    
    # Create mock query runner
    mock_runner = MagicMock()
    
    # Mock the run_arbitrary_query method to return sample invoice data
    def mock_query_result(query_string):
        # Return sample data that matches what the converters expect
        query_lower = query_string.lower()
        
        if "ohhst" in query_lower and ("bte4cd" in query_lower or "bthinb" in query_lower):  # invFetcher fetch_po/fetch_cust
            return [("PO12345", "Test Customer")]
        elif "odhst" in query_lower and "buhhnb" in query_lower and "buhunb" in query_lower:  # fetch_uom_desc (lineno -> uom)
            return [(1, "EA"), (2, "CS"), (3, "BX")]
        elif "dsanrep" in query_lower and "anbacd" in query_lower:  # fetch_uom_desc (itemno -> uom)
            return [("Each",)]
        elif "odhst" in query_lower and "bubacd" in query_lower and "bus3qt" in query_lower:  # Jolley/Stewarts UOM lookup
            return [(12345, 1, "EA"), (12345, 12, "CS"), (67890, 6, "BX")]
        elif "ohhst" in query_lower and "dsabrep" in query_lower:  # Jolley/Stewarts customer lookup
            return [
                ("Salesperson Name", "20231225", "NET30", 30, "ACTIVE", 1001, "Test Customer", 
                 "123 Main St", "Anytown", "CA", "12345", "5551234567", "test@example.com", 
                 "secondary@example.com", "ACTIVE", 1000, "Corporate Customer", "456 Corp Ave", 
                 "Big City", "NY", "67890", "5559876543", "corp@example.com", "corp2@example.com")
            ]
        else:  # Regular invoice item queries
            return [
                ("123456789012", "ITEM001", "Test Item 1", "12", "EA", 10, 5.99, 7.99),
                ("234567890123", "ITEM002", "Test Item 2", "6", "EA", 5, 12.99, 15.99),
                ("345678901234", "ITEM003", "Test Item 3", "24", "EA", 2, 8.49, 10.99),
            ]
    
    mock_runner.run_arbitrary_query.side_effect = mock_query_result
    
    # Patch the query_runner import in all database-dependent converters
    with patch('convert_to_scansheet_type_a.query_runner', return_value=mock_runner), \
         patch('convert_to_jolley_custom.query_runner', return_value=mock_runner), \
         patch('convert_to_stewarts_custom.query_runner', return_value=mock_runner), \
         patch('convert_to_estore_einvoice_generic.query_runner', return_value=mock_runner), \
         patch('convert_base.query_runner', return_value=mock_runner), \
         patch('utils.query_runner', return_value=mock_runner):  # For utils.invFetcher
        yield mock_runner


@pytest.fixture
def validate_output_file():
    """Return generic output file validation function."""
    def _validate(filepath, expected_extension=None):
        """Validate output file exists and has correct extension."""
        assert os.path.exists(filepath), f"Output file not found: {filepath}"
        
        if expected_extension:
            assert filepath.endswith(expected_extension), \
                f"Expected extension {expected_extension}, got {os.path.splitext(filepath)[1]}"
        
        # Check file has content
        assert os.path.getsize(filepath) > 0, f"Output file is empty: {filepath}"
        
        return True
    
    return _validate


# ============================================================================
# PYTEST MARKERS
# ============================================================================

def pytest_configure(config):
    """Register custom markers for convert backend tests."""
    config.addinivalue_line(
        "markers", "convert_backend: mark test as convert backend test"
    )
    config.addinivalue_line(
        "markers", "convert_smoke: mark test as quick smoke test for converters"
    )
    config.addinivalue_line(
        "markers", "convert_parameters: mark test as parameter variation test"
    )
    config.addinivalue_line(
        "markers", "convert_integration: mark test as integration test for converters"
    )
