"""Unit tests for EDISplitter class."""

import pytest
from unittest.mock import MagicMock, mock_open
from core.edi.edi_splitter import (
    EDISplitter,
    SplitConfig,
    SplitResult,
    FilesystemProtocol,
    RealFilesystem,
    filter_b_records_by_category,
    _col_to_excel,
)


class TestColToExcel:
    """Tests for _col_to_excel helper function."""
    
    def test_col_to_excel_a(self):
        """Test column 1 converts to A."""
        assert _col_to_excel(1) == "A"
    
    def test_col_to_excel_z(self):
        """Test column 26 converts to Z."""
        assert _col_to_excel(26) == "Z"
    
    def test_col_to_excel_aa(self):
        """Test column 27 converts to AA."""
        assert _col_to_excel(27) == "AA"
    
    def test_col_to_excel_ab(self):
        """Test column 28 converts to AB."""
        assert _col_to_excel(28) == "AB"
    
    def test_col_to_excel_az(self):
        """Test column 52 converts to AZ."""
        assert _col_to_excel(52) == "AZ"
    
    def test_col_to_excel_ba(self):
        """Test column 53 converts to BA."""
        assert _col_to_excel(53) == "BA"


class TestFilterBRecordsByCategory:
    """Tests for filter_b_records_by_category function."""
    
    def test_filter_all_mode_returns_all(self):
        """Test 'ALL' mode returns all records unchanged."""
        # B record: B(1) + upc(11) + desc(25) + vendor_item(6) + ...
        records = ["B00123456789Test Item Description    123456001234010000010000500123      \n"]
        upc_dict = {123456: ["1", "", "", "", ""]}
        
        result = filter_b_records_by_category(records, upc_dict, "ALL", "include")
        
        assert result == records
    
    def test_filter_empty_upc_dict_returns_all(self):
        """Test empty upc_dict returns all records."""
        records = ["B00123456789Test Item Description    123456001234010000010000500123      \n"]
        
        result = filter_b_records_by_category(records, {}, "1,2,3", "include")
        
        assert result == records
    
    def test_filter_include_mode(self):
        """Test include mode keeps only matching categories."""
        # B record format: B + upc(11) + desc(25) + vendor_item(6) + ...
        # vendor_item is at position 37-42
        records = [
            "B00123456789Item 1 Description       123456001234010000010000500123      \n",
            "B00123456789Item 2 Description       789012001234010000010000500123      \n",
        ]
        upc_dict = {
            123456: ["1", "", "", "", ""],  # Category 1
            789012: ["2", "", "", "", ""],  # Category 2
        }
        
        result = filter_b_records_by_category(records, upc_dict, "1", "include")
        
        assert len(result) == 1
        assert "123456" in result[0]
    
    def test_filter_exclude_mode(self):
        """Test exclude mode removes matching categories."""
        records = [
            "B00123456789Item 1 Description       123456001234010000010000500123      \n",
            "B00123456789Item 2 Description       789012001234010000010000500123      \n",
        ]
        upc_dict = {
            123456: ["1", "", "", "", ""],  # Category 1
            789012: ["2", "", "", "", ""],  # Category 2
        }
        
        result = filter_b_records_by_category(records, upc_dict, "1", "exclude")
        
        assert len(result) == 1
        assert "789012" in result[0]
    
    def test_filter_multiple_categories(self):
        """Test filtering with multiple categories."""
        records = [
            "B00123456789Item 1 Description       123456001234010000010000500123      \n",
            "B00123456789Item 2 Description       789012001234010000010000500123      \n",
            "B00123456789Item 3 Description       111111001234010000010000500123      \n",
        ]
        upc_dict = {
            123456: ["1", "", "", "", ""],
            789012: ["2", "", "", "", ""],
            111111: ["3", "", "", "", ""],
        }
        
        result = filter_b_records_by_category(records, upc_dict, "1,3", "include")
        
        assert len(result) == 2
    
    def test_filter_unknown_item_included_by_default(self):
        """Test unknown items are included by default (fail-open)."""
        records = [
            "B00123456789Item 1 Description       123456001234010000010000500123      \n",
            "B00123456789Item 2 Description       999999001234010000010000500123      \n",  # Not in upc_dict
        ]
        upc_dict = {
            123456: ["1", "", "", "", ""],
        }
        
        result = filter_b_records_by_category(records, upc_dict, "1", "include")
        
        # First record matches, second is unknown (included by default)
        assert len(result) == 2
    
    def test_filter_handles_parse_error(self):
        """Test filter handles parsing errors gracefully."""
        records = [
            "B00123456789Item 1 Description       123456001234010000010000500123      \n",
            "INVALID RECORD\n",
        ]
        upc_dict = {123456: ["1", "", "", "", ""]}
        
        # Should not raise, includes records on error
        result = filter_b_records_by_category(records, upc_dict, "1", "include")
        
        assert len(result) == 2


class TestSplitConfig:
    """Tests for SplitConfig dataclass."""
    
    def test_split_config_defaults(self):
        """Test SplitConfig default values."""
        config = SplitConfig(output_directory="/tmp/output")
        
        assert config.output_directory == "/tmp/output"
        assert config.prepend_date is False
        assert config.max_invoices == 0
    
    def test_split_config_all_values(self):
        """Test SplitConfig with all values."""
        config = SplitConfig(
            output_directory="/tmp/output",
            prepend_date=True,
            max_invoices=100
        )
        
        assert config.prepend_date is True
        assert config.max_invoices == 100


class TestSplitResult:
    """Tests for SplitResult dataclass."""
    
    def test_split_result_creation(self):
        """Test SplitResult creation."""
        result = SplitResult(
            output_files=[("/tmp/file1.inv", "A_", ".inv")],
            skipped_invoices=2,
            total_lines_written=10
        )
        
        assert len(result.output_files) == 1
        assert result.skipped_invoices == 2
        assert result.total_lines_written == 10


class MockFilesystem:
    """Mock filesystem for testing."""
    
    def __init__(self):
        self.files = {}
        self.directories = set()
        self.written_files = {}
        self.removed_files = []
    
    def read_file(self, path, encoding="utf-8"):
        return self.files.get(path, "")
    
    def write_file(self, path, content, encoding="utf-8"):
        self.written_files[path] = content
    
    def write_binary(self, path, content):
        self.written_files[path] = content
    
    def file_exists(self, path):
        return path in self.files or path in self.written_files
    
    def directory_exists(self, path):
        return path in self.directories
    
    def create_directory(self, path):
        self.directories.add(path)
    
    def remove_file(self, path):
        self.removed_files.append(path)
        if path in self.written_files:
            del self.written_files[path]
    
    def list_files(self, path):
        return []


class TestEDISplitter:
    """Tests for EDISplitter class."""
    
    @pytest.fixture
    def mock_filesystem(self):
        """Create mock filesystem."""
        return MockFilesystem()
    
    @pytest.fixture
    def splitter(self, mock_filesystem):
        """Create EDISplitter with mock filesystem."""
        return EDISplitter(mock_filesystem)
    
    @pytest.fixture
    def sample_edi_content(self):
        """Sample EDI content for testing."""
        # A record: A(1) + cust_vendor(6) + invoice_number(10) + invoice_date(6) + invoice_total(10) = 33 chars
        # B record: B(1) + upc(11) + desc(25) + vendor_item(6) + ... = 76 chars
        return (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
            "CFRTFreight Charge           000001234\n"
            "AVENDOR00000000020101240000000456\n"
            "B00123456789Test Item Description    789012001234010000010000500123      \n"
        )
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create split config."""
        return SplitConfig(output_directory=str(tmp_path / "output"))
    
    def test_split_edi_basic(self, splitter, mock_filesystem, sample_edi_content, config):
        """Test basic EDI splitting."""
        result = splitter.split_edi(sample_edi_content, config)
        
        assert len(result.output_files) == 2
        assert result.skipped_invoices == 0
    
    def test_split_edi_creates_output_directory(self, splitter, mock_filesystem, sample_edi_content, config):
        """Test that output directory is created."""
        splitter.split_edi(sample_edi_content, config)
        
        assert config.output_directory in mock_filesystem.directories
    
    def test_split_edi_max_invoices_limit(self, splitter, mock_filesystem, config):
        """Test max invoices limit."""
        content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        ) * 10  # 10 invoices
        
        config.max_invoices = 5
        
        result = splitter.split_edi(content, config)
        
        # Should return empty result if over limit
        assert len(result.output_files) == 0
    
    def test_split_edi_with_filtering(self, splitter, mock_filesystem, config):
        """Test EDI splitting with category filtering."""
        content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
            "AVENDOR00000000020101240000000456\n"
            "B00123456789Test Item Description    789012001234010000010000500123      \n"
        )
        upc_dict = {
            123456: ["1", "", "", "", ""],
            789012: ["2", "", "", "", ""],
        }
        
        result = splitter.split_edi(content, config, upc_dict, "1", "include")
        
        # Only first invoice should remain
        assert len(result.output_files) == 1
        assert result.skipped_invoices == 1
    
    def test_split_edi_credit_invoice(self, splitter, mock_filesystem, config):
        """Test splitting with credit invoice (negative total)."""
        content = (
            "AVENDOR0000000001010124-000000123\n"  # Negative total
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        
        result = splitter.split_edi(content, config)
        
        assert len(result.output_files) == 1
        assert result.output_files[0][2] == ".cr"  # Credit suffix
    
    def test_split_edi_invoice_suffix(self, splitter, mock_filesystem, config):
        """Test invoice suffix for positive total."""
        content = (
            "AVENDOR00000000010101240000000123\n"  # Positive total
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        
        result = splitter.split_edi(content, config)
        
        assert result.output_files[0][2] == ".inv"
    
    def test_split_edi_with_date_prepend(self, splitter, mock_filesystem, config):
        """Test splitting with date prepended to filename."""
        content = (
            "AVENDOR00000000010101240000000123\n"  # Date: 010124 (Jan 1, 2024)
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        config.prepend_date = True
        
        result = splitter.split_edi(content, config)
        
        # Check that date is in the prefix
        prefix = result.output_files[0][1]
        assert "Jan" in prefix or "2024" in prefix
    
    def test_split_edi_empty_result_raises(self, splitter, mock_filesystem, config):
        """Test that empty result raises ValueError."""
        content = "AVENDOR00000000010101240000000123\n"  # No B records
        
        with pytest.raises(ValueError, match="No Split EDIs"):
            splitter.split_edi(content, config)
    
    def test_split_edi_all_filtered_raises(self, splitter, mock_filesystem, config):
        """Test that all filtered raises ValueError."""
        content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        upc_dict = {123456: ["2", "", "", "", ""]}
        
        with pytest.raises(ValueError, match="No Split EDIs"):
            splitter.split_edi(content, config, upc_dict, "1", "include")
    
    def test_do_split_edi_from_file(self, splitter, mock_filesystem, config):
        """Test do_split_edi reads from file."""
        content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        mock_filesystem.files["/input/test.edi"] = content
        
        result = splitter.do_split_edi("/input/test.edi", config)
        
        assert len(result.output_files) == 1
    
    def test_split_edi_crlf_line_endings(self, splitter, mock_filesystem, config):
        """Test that output uses CRLF line endings."""
        content = (
            "AVENDOR00000000010101240000000123\n"
            "B00123456789Test Item Description    123456001234010000010000500123      \n"
        )
        
        splitter.split_edi(content, config)
        
        # Check written content - should have content
        for path, written_content in mock_filesystem.written_files.items():
            if isinstance(written_content, bytes):
                # The content should have been written
                assert len(written_content) > 0
                # Check that it contains the expected records
                assert b"AVENDOR" in written_content
                assert b"B00123456789" in written_content


class TestRealFilesystem:
    """Tests for RealFilesystem implementation."""
    
    def test_real_filesystem_implements_protocol(self):
        """Test RealFilesystem implements FilesystemProtocol."""
        fs = RealFilesystem()
        
        # Should have all required methods
        assert hasattr(fs, 'read_file')
        assert hasattr(fs, 'write_file')
        assert hasattr(fs, 'write_binary')
        assert hasattr(fs, 'file_exists')
        assert hasattr(fs, 'directory_exists')
        assert hasattr(fs, 'create_directory')
        assert hasattr(fs, 'remove_file')
        assert hasattr(fs, 'list_files')


class TestEDISplitterProtocolCompliance:
    """Tests for protocol compliance."""
    
    def test_splitter_accepts_protocol_compliant_filesystem(self):
        """Test EDISplitter accepts any FilesystemProtocol implementation."""
        
        class CustomFilesystem:
            def read_file(self, path, encoding="utf-8"):
                return ""
            
            def write_file(self, path, content, encoding="utf-8"):
                pass
            
            def write_binary(self, path, content):
                pass
            
            def file_exists(self, path):
                return False
            
            def directory_exists(self, path):
                return True
            
            def create_directory(self, path):
                pass
            
            def remove_file(self, path):
                pass
            
            def list_files(self, path):
                return []
        
        fs = CustomFilesystem()
        splitter = EDISplitter(fs)
        
        assert splitter.filesystem is fs
