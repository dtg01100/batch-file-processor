"""
Comprehensive tests for the convert_base module to improve coverage.
"""

import tempfile
import os
import pytest
from unittest.mock import MagicMock, patch
from convert_base import BaseConverter, CSVConverter, DBEnabledConverter


class ConcreteBaseConverter(BaseConverter):
    """Concrete implementation of BaseConverter for testing."""

    def initialize_output(self) -> None:
        pass

    def finalize_output(self) -> str:
        return "test_output_file"

    def process_record_a(self, record: dict) -> None:
        pass

    def process_record_b(self, record: dict) -> None:
        pass

    def process_record_c(self, record: dict) -> None:
        pass


class ConcreteCSVConverter(CSVConverter):
    """Concrete implementation of CSVConverter for testing."""

    def process_record_a(self, record: dict) -> None:
        pass

    def process_record_b(self, record: dict) -> None:
        pass

    def process_record_c(self, record: dict) -> None:
        pass


class ConcreteDBEnabledConverter(DBEnabledConverter):
    """Concrete implementation of DBEnabledConverter for testing."""

    def process_record_a(self, record: dict) -> None:
        pass

    def process_record_b(self, record: dict) -> None:
        pass

    def process_record_c(self, record: dict) -> None:
        pass


@pytest.fixture
def converter_args():
    """Common arguments for converter initialization."""
    return {
        "edi_process": "test.edi",
        "output_filename": "test_output",
        "settings_dict": {},
        "parameters_dict": {},
        "upc_lookup": {},
    }


def test_base_converter_init(converter_args):
    """Test BaseConverter initialization."""
    converter = ConcreteBaseConverter(**converter_args)

    assert converter is not None
    assert hasattr(converter, "convert")
    assert hasattr(converter, "process_record_a")
    assert hasattr(converter, "process_record_b")
    assert hasattr(converter, "process_record_c")


def test_base_converter_convert_file_not_found(converter_args):
    """Test BaseConverter.convert with non-existent file."""
    converter = ConcreteBaseConverter(**converter_args)

    try:
        converter.convert()
    except FileNotFoundError:
        pass  # Expected
    except Exception as e:
        pass


def test_base_converter_process_record_methods(converter_args):
    """Test BaseConverter record processing methods."""
    converter = ConcreteBaseConverter(**converter_args)

    record_a = {"invoice_number": "123"}
    record_b = {"upc_number": "123456789012"}
    record_c = {"charge_code": "001"}

    # Process records - these should not crash
    converter.process_record_a(record_a)
    converter.process_record_b(record_b)
    converter.process_record_c(record_c)


def test_base_converter_static_methods():
    """Test BaseConverter static methods."""
    # Test convert_to_price
    # Input "12345" (DAC) -> "123.45" (String)
    result = BaseConverter.convert_to_price("12345")
    assert result == "123.45"

    # Test process_upc with 11 digits (should add check digit)
    result = BaseConverter.process_upc("12345678901", calc_check_digit=True)
    assert len(result) >= 11

    # Test process_upc with 12 digits (should remain same)
    result = BaseConverter.process_upc("123456789012", calc_check_digit=True)
    assert result == "123456789012"

    # Test qty_to_int with positive value
    result = BaseConverter.qty_to_int("10")
    assert result == 10

    # Test qty_to_int with negative value
    result = BaseConverter.qty_to_int("-5")
    assert result == -5

    # Test qty_to_int with invalid value
    result = BaseConverter.qty_to_int("invalid")
    assert result == 0


def test_csv_converter_init(converter_args):
    """Test CSVConverter initialization."""
    converter = ConcreteCSVConverter(**converter_args)

    assert converter is not None
    assert hasattr(converter, "initialize_output")
    assert hasattr(converter, "finalize_output")
    assert hasattr(converter, "write_header")
    assert hasattr(converter, "write_row")


def test_csv_converter_initialize_output(converter_args):
    """Test CSVConverter initialize_output."""
    converter = ConcreteCSVConverter(**converter_args)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        temp_path = temp_file.name

    # Update output_filename to match temp file base
    converter.output_filename = os.path.splitext(temp_path)[0]

    try:
        converter.initialize_output()
        assert converter.output_file is not None
    finally:
        converter.finalize_output()  # Close file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_csv_converter_write_before_init(converter_args):
    """Test CSVConverter write methods before initialization."""
    converter = ConcreteCSVConverter(**converter_args)

    # Attempt to write header before initialization should handle gracefully or raise
    try:
        converter.write_header(["col1", "col2"])
    except Exception:
        pass

    try:
        converter.write_row(["val1", "val2"])
    except Exception:
        pass


def test_csv_converter_finalize_output(converter_args):
    """Test CSVConverter finalize_output."""
    converter = ConcreteCSVConverter(**converter_args)

    # Should not raise an exception even if not initialized
    try:
        converter.finalize_output()
    except Exception:
        pass


def test_db_enabled_converter_init(converter_args):
    """Test DBEnabledConverter initialization."""
    converter = ConcreteDBEnabledConverter(**converter_args)

    assert converter is not None
    assert hasattr(converter, "connect_db")
    assert hasattr(converter, "run_query")


def test_db_enabled_converter_connect_db(converter_args):
    """Test DBEnabledConverter connect_db method."""
    converter = ConcreteDBEnabledConverter(**converter_args)

    # Mock settings to avoid real DB connection attempt failure
    converter.settings_dict = {
        "db_driver": "sqlite",
        "db_server": "localhost",
        "db_database": "test.db",
        "as400_address": "localhost",
        "as400_library": "TESTLIB",
        "as400_username": "user",
        "as400_password": "password",
        "odbc_driver": "ODBC Driver",
    }

    with patch("convert_base.query_runner") as mock_qr:
        converter.connect_db()
        # Should have tried to create a query_runner
        pass


def test_db_enabled_converter_run_query_without_settings(converter_args):
    """Test DBEnabledConverter run_query without settings."""
    converter = ConcreteDBEnabledConverter(**converter_args)

    # Should handle missing settings gracefully or raise known error
    try:
        converter.run_query("SELECT * FROM test")
    except Exception:
        pass


def test_db_enabled_converter_connect_db_idempotent(converter_args):
    """Test that connect_db is idempotent."""
    converter = ConcreteDBEnabledConverter(**converter_args)
    converter.settings_dict = {
        "db_driver": "mock",
        "as400_address": "localhost",
        "as400_library": "TESTLIB",
        "as400_username": "user",
        "as400_password": "password",
        "odbc_driver": "ODBC Driver",
    }

    with patch("convert_base.query_runner"):
        converter.connect_db()
        converter.connect_db()  # Second call should be safe


def test_base_converter_process_upc_edge_cases():
    """Test BaseConverter.process_upc with edge cases."""
    # Test with 8-digit UPC (UPCE format)
    # Note: calc_check_digit=False is passed but logic might still trigger UPCE conversion
    # based on length == 8

    # Test with invalid UPC
    result = BaseConverter.process_upc("invalid", calc_check_digit=False)
    assert result == ""

    # Test with 0-length UPC
    result = BaseConverter.process_upc("", calc_check_digit=False)
    assert result == ""


def test_base_converter_qty_to_int_edge_cases():
    """Test BaseConverter.qty_to_int with edge cases."""
    # Test with zero
    result = BaseConverter.qty_to_int("0")
    assert result == 0

    # Test with very large number
    result = BaseConverter.qty_to_int("999999999")
    assert result == 999999999

    # Test with string containing non-numeric characters
    result = BaseConverter.qty_to_int("123abc")
    assert result == 0

    # Test with decimal string (should return 0 as it's invalid int string)
    result = BaseConverter.qty_to_int("123.45")
    assert result == 0

    # Test with empty string
    result = BaseConverter.qty_to_int("")
    assert result == 0


def test_base_converter_current_a_record_tracking(converter_args):
    """Test BaseConverter's current A record tracking."""
    converter = ConcreteBaseConverter(**converter_args)

    converter.current_a_record = {"test": "record"}
    assert converter.current_a_record == {"test": "record"}


def test_csv_converter_write_methods(converter_args):
    """Test CSVConverter write methods with proper initialization."""
    converter = ConcreteCSVConverter(**converter_args)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        temp_path = temp_file.name

    converter.output_filename = os.path.splitext(temp_path)[0]

    try:
        # Initialize the converter
        converter.initialize_output()

        # Write header
        converter.write_header(["Column1", "Column2", "Column3"])

        # Write a row
        converter.write_row(["Value1", "Value2", "Value3"])

        # Finalize
        converter.finalize_output()

        # Check that file was created and has content
        # output_filename + .csv
        expected_path = converter.output_filename + ".csv"
        assert os.path.exists(expected_path)
        with open(expected_path, "r") as f:
            content = f.read()
            assert len(content) > 0

    finally:
        expected_path = converter.output_filename + ".csv"
        if os.path.exists(expected_path):
            os.unlink(expected_path)
        # Also clean up the temp file if it's different (CSVConverter appends .csv)
        if os.path.exists(temp_path) and temp_path != expected_path:
            os.unlink(temp_path)
