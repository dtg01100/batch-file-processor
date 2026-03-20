"""Unit tests for convert_base.py - BaseEDIConverter and supporting classes.

Tests:
- EDIRecord dataclass functionality
- ConversionContext dataclass functionality
- BaseEDIConverter template method pattern
- Hook method dispatching
- Record type filtering
- Error handling and cleanup
- Utility functions
"""

import csv
from abc import ABC
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    create_csv_writer,
    normalize_parameter,
)

# =============================================================================
# Test Fixtures
# =============================================================================


class TestFixtures:
    """Shared fixtures for all test classes."""

    @pytest.fixture
    def sample_edi_record_a(self):
        """Create a sample A record."""
        return EDIRecord(
            record_type="A",
            raw_line="AVENDOR00000000010101250000010000",
            fields={
                "record_type": "A",
                "cust_vendor": "VENDOR",
                "invoice_number": "0000000001",
                "invoice_date": "010125",
                "invoice_total": "0000010000",
            },
        )

    @pytest.fixture
    def sample_edi_record_b(self):
        """Create a sample B record."""
        return EDIRecord(
            record_type="B",
            raw_line="B01234567890Test Item Description    123456000100010000010001000199001000000",
            fields={
                "record_type": "B",
                "upc_number": "01234567890",
                "description": "Test Item Description    ",
                "vendor_item": "123456",
                "unit_cost": "000100",
                "combo_code": "01",
                "unit_multiplier": "000001",
                "qty_of_units": "00010",
                "suggested_retail_price": "00199",
                "price_multi_pack": "001",
                "parent_item_number": "000000",
            },
        )

    @pytest.fixture
    def sample_edi_record_c(self):
        """Create a sample C record."""
        return EDIRecord(
            record_type="C",
            raw_line="CTABSales Tax                 000010000",
            fields={
                "record_type": "C",
                "charge_type": "TAB",
                "description": "Sales Tax                 ",
                "amount": "000010000",
            },
        )

    @pytest.fixture
    def sample_context(self):
        """Create a sample conversion context."""
        return ConversionContext(
            edi_filename="/tmp/test.edi",
            output_filename="/tmp/test_output",
            settings_dict={"test_setting": "value"},
            parameters_dict={"test_param": "value"},
            upc_lut={123456: ("CAT1", "012345678905", "012345678900")},
        )

    @pytest.fixture
    def sample_edi_content(self):
        """Create sample EDI file content."""
        return (
            "AVENDOR00000000010101250000010000\n"
            "B01234567890Test Item Description    123456000100010000010001000199001000000\n"
            "CTABSales Tax                 000010000\n"
        )


# =============================================================================
# EDIRecord Tests
# =============================================================================


class TestEDIRecord:
    """Test suite for EDIRecord dataclass."""

    def test_edi_record_creation(self):
        """Test that EDIRecord can be created with all fields."""
        record = EDIRecord(
            record_type="B", raw_line="test line", fields={"key": "value"}
        )

        assert record.record_type == "B"
        assert record.raw_line == "test line"
        assert record.fields == {"key": "value"}

    def test_edi_record_immutable(self):
        """Test that EDIRecord fields can be modified (dataclass is not frozen)."""
        record = EDIRecord(record_type="B", raw_line="test", fields={})

        # Should be able to modify
        record.record_type = "A"
        assert record.record_type == "A"


# =============================================================================
# ConversionContext Tests
# =============================================================================


class TestConversionContext:
    """Test suite for ConversionContext dataclass."""

    def test_context_creation(self):
        """Test that ConversionContext can be created with required fields."""
        context = ConversionContext(
            edi_filename="input.edi",
            output_filename="output",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        assert context.edi_filename == "input.edi"
        assert context.output_filename == "output"
        assert context.arec_header is None
        assert context.line_num == 0
        assert context.records_processed == 0
        assert context.output_file is None
        assert context.csv_writer is None
        assert context.user_data == {}

    def test_get_output_path_default(self):
        """Test get_output_path with default extension."""
        context = ConversionContext(
            edi_filename="input.edi",
            output_filename="/path/to/output",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        assert context.get_output_path() == "/path/to/output.csv"

    def test_get_output_path_custom(self):
        """Test get_output_path with custom extension."""
        context = ConversionContext(
            edi_filename="input.edi",
            output_filename="/path/to/output",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        assert context.get_output_path(".txt") == "/path/to/output.txt"
        assert context.get_output_path("") == "/path/to/output"

    def test_user_data_storage(self):
        """Test that user_data can store arbitrary values."""
        context = ConversionContext(
            edi_filename="input.edi",
            output_filename="output",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        context.user_data["custom_key"] = "custom_value"
        context.user_data["number"] = 42

        assert context.user_data["custom_key"] == "custom_value"
        assert context.user_data["number"] == 42


# =============================================================================
# Concrete Mock Converter Implementation
# =============================================================================


class MockConverter(BaseEDIConverter):
    """Concrete implementation of BaseEDIConverter for testing."""

    def __init__(self):
        self.initialize_called = False
        self.finalize_called = False
        self.a_records = []
        self.b_records = []
        self.c_records = []
        self.unknown_records = []

    def _initialize_output(self, context):
        """Initialize test output."""
        self.initialize_called = True
        context.output_file = MagicMock()
        context.csv_writer = MagicMock()
        context.user_data["initialized"] = True

    def process_a_record(self, record, context):
        """Process A record."""
        self.a_records.append(record)
        context.arec_header = record.fields

    def process_b_record(self, record, context):
        """Process B record."""
        self.b_records.append(record)

    def process_c_record(self, record, context):
        """Process C record."""
        self.c_records.append(record)

    def _finalize_output(self, context):
        """Finalize test output."""
        self.finalize_called = True

    def _handle_unknown_record(self, record, context):
        """Handle unknown record type."""
        self.unknown_records.append(record)


class FilteringTestConverter(MockConverter):
    """Test converter with record type filtering."""

    def _should_process_record_type(self, record_type, context):
        """Filter out C records."""
        return record_type != "C"


# =============================================================================
# BaseEDIConverter Tests
# =============================================================================


class TestBaseEDIConverter(TestFixtures):
    """Test suite for BaseEDIConverter template method pattern."""

    def test_base_class_is_abstract(self):
        """Test that BaseEDIConverter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEDIConverter()

    def test_concrete_class_can_be_instantiated(self):
        """Test that a concrete implementation can be instantiated."""
        converter = MockConverter()
        assert converter is not None

    @patch("dispatch.converters.convert_base.utils")
    def test_edi_convert_full_workflow(self, mock_utils, tmp_path, sample_edi_content):
        """Test the complete edi_convert workflow."""
        # Setup
        mock_utils.capture_records.side_effect = [
            {
                "record_type": "A",
                "cust_vendor": "VENDOR",
                "invoice_number": "0000000001",
                "invoice_date": "010125",
                "invoice_total": "0000010000",
            },
            {
                "record_type": "B",
                "upc_number": "01234567890",
                "description": "Test Item",
                "vendor_item": "123456",
                "unit_cost": "000100",
                "combo_code": "01",
                "unit_multiplier": "000001",
                "qty_of_units": "00010",
                "suggested_retail_price": "00199",
                "price_multi_pack": "001",
                "parent_item_number": "000000",
            },
            {
                "record_type": "C",
                "charge_type": "TAB",
                "description": "Sales Tax",
                "amount": "000010000",
            },
            None,  # EOF
        ]

        # Create input file
        input_file = tmp_path / "test.edi"
        input_file.write_text(sample_edi_content)

        output_file = tmp_path / "output"

        # Execute
        converter = MockConverter()
        result = converter.edi_convert(str(input_file), str(output_file), {}, {}, {})

        # Verify
        assert converter.initialize_called is True
        assert converter.finalize_called is True
        assert len(converter.a_records) == 1
        assert len(converter.b_records) == 1
        assert len(converter.c_records) == 1
        assert result == str(output_file) + ".csv"

    @patch("dispatch.converters.convert_base.utils")
    def test_record_dispatching(self, mock_utils, tmp_path):
        """Test that records are dispatched to correct handlers."""
        mock_utils.capture_records.side_effect = [
            {"record_type": "A", "invoice_number": "0001"},
            {"record_type": "B", "vendor_item": "123"},
            {"record_type": "C", "amount": "100"},
            None,
        ]

        input_file = tmp_path / "test.edi"
        input_file.write_text("A...\nB...\nC...")

        converter = MockConverter()
        converter.edi_convert(str(input_file), str(tmp_path / "out"), {}, {}, {})

        assert len(converter.a_records) == 1
        assert len(converter.b_records) == 1
        assert len(converter.c_records) == 1

    @patch("dispatch.converters.convert_base.utils")
    def test_record_filtering(self, mock_utils, tmp_path):
        """Test that _should_process_record_type filters records."""
        mock_utils.capture_records.side_effect = [
            {"record_type": "A", "invoice_number": "0001"},
            {"record_type": "B", "vendor_item": "123"},
            {"record_type": "C", "amount": "100"},
            None,
        ]

        input_file = tmp_path / "test.edi"
        input_file.write_text("A...\nB...\nC...")

        converter = FilteringTestConverter()
        converter.edi_convert(str(input_file), str(tmp_path / "out"), {}, {}, {})

        # A and B should be processed, C should be filtered
        assert len(converter.a_records) == 1
        assert len(converter.b_records) == 1
        assert len(converter.c_records) == 0  # Filtered out

    @patch("dispatch.converters.convert_base.utils")
    def test_arec_header_storage(self, mock_utils, tmp_path):
        """Test that A record header is stored in context."""
        mock_utils.capture_records.side_effect = [
            {"record_type": "A", "invoice_number": "INV001"},
            {"record_type": "B", "vendor_item": "123"},
            None,
        ]

        input_file = tmp_path / "test.edi"
        input_file.write_text("A...\nB...")

        converter = MockConverter()
        context = ConversionContext(
            edi_filename=str(input_file),
            output_filename=str(tmp_path / "out"),
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        # Manually test process_a_record
        record = EDIRecord("A", "line", {"invoice_number": "INV001"})
        converter.process_a_record(record, context)

        assert context.arec_header == {"invoice_number": "INV001"}

    @patch("dispatch.converters.convert_base.utils")
    def test_error_cleanup(self, mock_utils, tmp_path):
        """Test that resources are cleaned up on error."""
        mock_utils.capture_records.side_effect = ValueError("Parse error")

        input_file = tmp_path / "test.edi"
        input_file.write_text("invalid")

        converter = MockConverter()

        with pytest.raises(ValueError, match="Parse error"):
            converter.edi_convert(str(input_file), str(tmp_path / "out"), {}, {}, {})

        # Initialize should have been called
        assert converter.initialize_called is True


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_create_csv_writer_default(self):
        """Test create_csv_writer with default parameters."""
        mock_file = MagicMock()
        writer = create_csv_writer(mock_file)

        assert writer is not None

    def test_create_csv_writer_custom_dialect(self):
        """Test create_csv_writer with custom dialect."""
        mock_file = MagicMock()
        writer = create_csv_writer(
            mock_file, dialect="unix", lineterminator="\n", quoting=csv.QUOTE_MINIMAL
        )

        assert writer is not None

    def test_normalize_parameter_true_values(self):
        """Test normalize_parameter with truthy string values."""
        assert normalize_parameter("True") is True
        assert normalize_parameter("true") is True
        assert normalize_parameter("1") is True
        assert normalize_parameter("yes") is True
        assert normalize_parameter("on") is True

    def test_normalize_parameter_false_values(self):
        """Test normalize_parameter with falsy string values."""
        assert normalize_parameter("False") is False
        assert normalize_parameter("false") is False
        assert normalize_parameter("0") is False
        assert normalize_parameter("no") is False
        assert normalize_parameter("off") is False

    def test_normalize_parameter_default(self):
        """Test normalize_parameter with default value."""
        assert normalize_parameter(None, default="default") == "default"
        assert normalize_parameter("", default="default") == "default"

    def test_normalize_parameter_non_string(self):
        """Test normalize_parameter with non-string values."""
        assert normalize_parameter(123) == 123
        assert normalize_parameter([1, 2, 3]) == [1, 2, 3]
        assert normalize_parameter({"key": "value"}) == {"key": "value"}


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases(TestFixtures):
    """Test suite for edge cases and error conditions."""

    @patch("dispatch.converters.convert_base.utils")
    def test_empty_edi_file(self, mock_utils, tmp_path):
        """Test handling of empty EDI file."""
        mock_utils.capture_records.return_value = None

        input_file = tmp_path / "empty.edi"
        input_file.write_text("")

        converter = MockConverter()
        converter.edi_convert(str(input_file), str(tmp_path / "out"), {}, {}, {})

        assert converter.initialize_called is True
        assert converter.finalize_called is True
        assert len(converter.a_records) == 0

    @patch("dispatch.converters.convert_base.utils")
    def test_unknown_record_type(self, mock_utils, tmp_path):
        """Test handling of unknown record types."""
        mock_utils.capture_records.side_effect = [
            {"record_type": "X", "unknown": "data"},
            None,
        ]

        input_file = tmp_path / "test.edi"
        input_file.write_text("X...")

        converter = MockConverter()
        converter.edi_convert(str(input_file), str(tmp_path / "out"), {}, {}, {})

        assert len(converter.unknown_records) == 1

    @patch("dispatch.converters.convert_base.utils")
    def test_arec_header_default_storage(
        self, mock_utils, tmp_path, sample_edi_record_a
    ):
        """Test that default process_a_record stores header in context."""

        # Create a converter that doesn't override process_a_record
        class MinimalConverter(BaseEDIConverter):
            def _initialize_output(self, context):
                context.output_file = MagicMock()

            def process_b_record(self, record, context):
                pass

        converter = MinimalConverter()
        context = ConversionContext(
            edi_filename="test.edi",
            output_filename="out",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        # Default process_a_record should store header
        converter.process_a_record(sample_edi_record_a, context)

        assert context.arec_header == sample_edi_record_a.fields

    def test_context_user_data_isolation(self):
        """Test that user_data is isolated between contexts."""
        context1 = ConversionContext(
            edi_filename="a.edi",
            output_filename="out1",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )
        context2 = ConversionContext(
            edi_filename="b.edi",
            output_filename="out2",
            settings_dict={},
            parameters_dict={},
            upc_lut={},
        )

        context1.user_data["key"] = "value1"
        context2.user_data["key"] = "value2"

        assert context1.user_data["key"] == "value1"
        assert context2.user_data["key"] == "value2"


# =============================================================================
# Import/Integration Tests
# =============================================================================


class TestModuleImports:
    """Test suite for module-level imports and integration."""

    def test_module_import(self):
        """Test that convert_base module can be imported."""
        import dispatch.converters.convert_base as cb

        assert cb is not None

    def test_all_classes_importable(self):
        """Test that all public classes can be imported."""
        from dispatch.converters.convert_base import (
            BaseEDIConverter,
            ConversionContext,
            EDIRecord,
            create_csv_writer,
            normalize_parameter,
        )

        assert BaseEDIConverter is not None
        assert ConversionContext is not None
        assert EDIRecord is not None
        assert create_csv_writer is not None
        assert normalize_parameter is not None

    def test_base_edi_converter_is_abc(self):
        """Test that BaseEDIConverter is an abstract base class."""
        from dispatch.converters.convert_base import BaseEDIConverter

        # Check it's a subclass of ABC
        assert issubclass(BaseEDIConverter, ABC)
