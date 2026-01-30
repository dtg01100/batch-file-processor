"""
Comprehensive unit tests for convert_base.py module.

Tests the BaseConverter, CSVConverter, and especially DBEnabledConverter classes.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from convert_base import BaseConverter, CSVConverter, DBEnabledConverter, create_edi_convert_wrapper


class MockConverter(BaseConverter):
    """Mock converter for testing abstract base class."""
    
    PLUGIN_ID = "mock"
    PLUGIN_NAME = "Mock Converter"
    PLUGIN_DESCRIPTION = "Test converter"
    CONFIG_FIELDS = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records_processed = []
        
    def initialize_output(self):
        self.records_processed = []
        
    def process_record_a(self, record):
        self.records_processed.append(('A', record))
        
    def process_record_b(self, record):
        self.records_processed.append(('B', record))
        
    def process_record_c(self, record):
        self.records_processed.append(('C', record))
        
    def finalize_output(self):
        return self.edi_process + '.out'


class TestBaseConverter(unittest.TestCase):
    """Tests for BaseConverter abstract base class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.edi_file = os.path.join(self.temp_dir, 'test.edi')
        with open(self.edi_file, 'w') as f:
            f.write('A123456789012345012345000012345\n')
            f.write('B1234567890Test Description     123450123450012345012340123\n')
            f.write('C001Test Charge              000010000\n')
        
        self.settings = {'test_setting': 'value'}
        self.parameters = {'test_param': 'value'}
        self.upc_lookup = {}
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test converter initialization."""
        converter = MockConverter(
            self.edi_file,
            os.path.join(self.temp_dir, 'output'),
            self.settings,
            self.parameters,
            self.upc_lookup
        )
        
        self.assertEqual(converter.edi_process, self.edi_file)
        self.assertEqual(converter.settings_dict, self.settings)
        self.assertEqual(converter.parameters_dict, self.parameters)
        self.assertEqual(converter.upc_lookup, self.upc_lookup)
        self.assertEqual(converter.lines, [])
        self.assertIsNone(converter.current_a_record)
    
    def test_convert_to_price(self):
        """Test DAC price format conversion."""
        # Normal case
        self.assertEqual(BaseConverter.convert_to_price("00012345"), "123.45")
        # Zero case
        self.assertEqual(BaseConverter.convert_to_price("00000000"), "0.00")
        # Single digit
        self.assertEqual(BaseConverter.convert_to_price("00000005"), "0.05")
        # Empty/short
        self.assertEqual(BaseConverter.convert_to_price(""), "0.00")
        self.assertEqual(BaseConverter.convert_to_price("1"), "0.01")
    
    def test_qty_to_int_positive(self):
        """Test positive quantity conversion."""
        self.assertEqual(BaseConverter.qty_to_int("0010"), 10)
        self.assertEqual(BaseConverter.qty_to_int("123"), 123)
        self.assertEqual(BaseConverter.qty_to_int("0"), 0)
    
    def test_qty_to_int_negative(self):
        """Test negative quantity conversion."""
        self.assertEqual(BaseConverter.qty_to_int("-010"), -10)
        self.assertEqual(BaseConverter.qty_to_int("-100"), -100)
    
    def test_qty_to_int_invalid(self):
        """Test invalid quantity handling."""
        self.assertEqual(BaseConverter.qty_to_int("abc"), 0)
        self.assertEqual(BaseConverter.qty_to_int(""), 0)
    
    def test_process_upc_12_digit(self):
        """Test 12-digit UPC passthrough."""
        with patch('utils.calc_check_digit'):
            result = BaseConverter.process_upc("123456789012")
            self.assertEqual(result, "123456789012")
    
    def test_process_upc_11_digit(self):
        """Test 11-digit UPC with check digit calculation."""
        with patch('utils.calc_check_digit', return_value=5):
            result = BaseConverter.process_upc("12345678901")
            self.assertEqual(result, "123456789015")
    
    def test_process_upc_8_digit(self):
        """Test 8-digit UPCE conversion."""
        with patch('utils.convert_UPCE_to_UPCA', return_value="041800000265"):
            result = BaseConverter.process_upc("04182635")
            self.assertEqual(result, "041800000265")
    
    def test_process_upc_invalid(self):
        """Test invalid UPC handling."""
        result = BaseConverter.process_upc("invalid")
        self.assertEqual(result, "")
        
        result = BaseConverter.process_upc("12345")  # Wrong length
        self.assertEqual(result, "")
    
    def test_convert_reads_file(self):
        """Test convert method reads EDI file."""
        converter = MockConverter(
            self.edi_file,
            os.path.join(self.temp_dir, 'output'),
            self.settings,
            self.parameters,
            self.upc_lookup
        )
        
        result = converter.convert()
        
        # Should have read the file
        self.assertEqual(len(converter.lines), 3)
        # Should have processed records
        self.assertEqual(len(converter.records_processed), 3)
        # Should return output path
        self.assertEqual(result, self.edi_file + '.out')
    
    def test_convert_file_not_found(self):
        """Test convert raises FileNotFoundError for missing file."""
        converter = MockConverter(
            '/nonexistent/file.edi',
            os.path.join(self.temp_dir, 'output'),
            self.settings,
            self.parameters,
            self.upc_lookup
        )
        
        with self.assertRaises(FileNotFoundError):
            converter.convert()
    
    def test_current_a_record_tracking(self):
        """Test that current_a_record is updated when A record is processed."""
        converter = MockConverter(
            self.edi_file,
            os.path.join(self.temp_dir, 'output'),
            self.settings,
            self.parameters,
            self.upc_lookup
        )
        
        converter.convert()
        
        # After convert, current_a_record should be set to the last A record
        self.assertIsNotNone(converter.current_a_record)
        self.assertEqual(converter.current_a_record['record_type'], 'A')


class TestCSVConverter(unittest.TestCase):
    """Tests for CSVConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.edi_file = os.path.join(self.temp_dir, 'test.edi')
        with open(self.edi_file, 'w') as f:
            f.write('A123456789012345012345000012345\n')
        
        self.output_file = os.path.join(self.temp_dir, 'output')
        self.settings = {}
        self.parameters = {}
        self.upc_lookup = {}
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialize_output(self):
        """Test CSV output file initialization."""
        converter = CSVConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        converter.initialize_output()
        
        self.assertIsNotNone(converter.csv_file)
        self.assertIsNotNone(converter.output_file)
    
    def test_write_header_before_init_raises(self):
        """Test write_header raises RuntimeError before initialize_output."""
        converter = CSVConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        with self.assertRaises(RuntimeError) as context:
            converter.write_header(['Col1', 'Col2'])
        
        self.assertIn("not initialized", str(context.exception))
    
    def test_write_row_before_init_raises(self):
        """Test write_row raises RuntimeError before initialize_output."""
        converter = CSVConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        with self.assertRaises(RuntimeError) as context:
            converter.write_row(['data1', 'data2'])
        
        self.assertIn("not initialized", str(context.exception))
    
    def test_finalize_output_closes_file(self):
        """Test finalize_output closes the output file."""
        converter = CSVConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        converter.initialize_output()
        result = converter.finalize_output()
        
        self.assertEqual(result, self.output_file + '.csv')


class TestDBEnabledConverter(unittest.TestCase):
    """Tests for DBEnabledConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.edi_file = os.path.join(self.temp_dir, 'test.edi')
        with open(self.edi_file, 'w') as f:
            f.write('A123456789012345012345000012345\n')
        
        self.output_file = os.path.join(self.temp_dir, 'output')
        self.settings = {
            'as400_username': 'test_user',
            'as400_password': 'test_pass',
            'as400_address': 'test_host',
            'odbc_driver': 'test_driver'
        }
        self.parameters = {}
        self.upc_lookup = {}
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('convert_base.query_runner')
    def test_connect_db_lazy_initialization(self, mock_query_runner):
        """Test database connection is lazily initialized."""
        mock_query_instance = MagicMock()
        mock_query_runner.return_value = mock_query_instance
        
        converter = DBEnabledConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        # query_object should be None initially
        self.assertIsNone(converter.query_object)
        self.assertFalse(converter._db_connected)
        
        # Connect to database
        converter.connect_db()
        
        # Now query_object should be set
        self.assertIsNotNone(converter.query_object)
        self.assertTrue(converter._db_connected)
        mock_query_runner.assert_called_once_with(
            'test_user', 'test_pass', 'test_host', 'test_driver'
        )
    
    @patch('convert_base.query_runner')
    def test_connect_db_idempotent(self, mock_query_runner):
        """Test connect_db is idempotent (safe to call multiple times)."""
        mock_query_instance = MagicMock()
        mock_query_runner.return_value = mock_query_instance
        
        converter = DBEnabledConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        # Connect multiple times
        converter.connect_db()
        converter.connect_db()
        converter.connect_db()
        
        # query_runner should only be called once
        mock_query_runner.assert_called_once()
    
    @patch('convert_base.query_runner')
    def test_run_query_connects_db(self, mock_query_runner):
        """Test run_query automatically connects to database."""
        mock_query_instance = MagicMock()
        mock_query_instance.run_arbitrary_query.return_value = [('row1',), ('row2',)]
        mock_query_runner.return_value = mock_query_instance
        
        converter = DBEnabledConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        # Run query without explicit connect_db call
        result = converter.run_query("SELECT * FROM test")
        
        # Should have auto-connected
        self.assertTrue(converter._db_connected)
        mock_query_instance.run_arbitrary_query.assert_called_once_with("SELECT * FROM test")
        self.assertEqual(result, [('row1',), ('row2',)])
    
    def test_run_query_without_settings_raises(self):
        """Test run_query raises error when settings are missing."""
        converter = DBEnabledConverter(
            self.edi_file, self.output_file, {}, self.parameters, self.upc_lookup
        )
        
        with self.assertRaises(KeyError):
            converter.run_query("SELECT * FROM test")
    
    @patch('convert_base.query_runner')
    def test_inheritance_from_csv_converter(self, mock_query_runner):
        """Test DBEnabledConverter inherits CSVConverter functionality."""
        converter = DBEnabledConverter(
            self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup
        )
        
        # Should have CSVConverter attributes
        self.assertEqual(converter.csv_dialect, "excel")
        self.assertEqual(converter.lineterminator, "\r\n")
        
        # Should be able to initialize CSV output
        converter.initialize_output()
        self.assertIsNotNone(converter.csv_file)


class TestCreateEdiConvertWrapper(unittest.TestCase):
    """Tests for create_edi_convert_wrapper function."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.edi_file = os.path.join(self.temp_dir, 'test.edi')
        with open(self.edi_file, 'w') as f:
            f.write('A123456789012345012345000012345\n')
        
        self.output_file = os.path.join(self.temp_dir, 'output')
        self.settings = {}
        self.parameters = {}
        self.upc_lookup = {}
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_wrapper_creates_function(self):
        """Test wrapper creates a callable function."""
        wrapper = create_edi_convert_wrapper(MockConverter)
        
        # Should be callable
        self.assertTrue(callable(wrapper))
    
    def test_wrapper_runs_converter(self):
        """Test wrapper function runs the converter."""
        wrapper = create_edi_convert_wrapper(MockConverter)
        
        # Should run without error
        result = wrapper(self.edi_file, self.output_file, self.settings, self.parameters, self.upc_lookup)
        
        # Should return output path
        self.assertEqual(result, self.edi_file + '.out')


class TestBaseConverterStaticMethods(unittest.TestCase):
    """Tests for BaseConverter static methods."""
    
    def test_convert_to_price_edge_cases(self):
        """Test convert_to_price with edge cases."""
        # Very small
        self.assertEqual(BaseConverter.convert_to_price("01"), "0.01")
        # Very large
        self.assertEqual(BaseConverter.convert_to_price("99999999"), "999999.99")
        # With explicit None (should handle gracefully)
        with self.assertRaises((TypeError, IndexError)):
            BaseConverter.convert_to_price(None)
    
    def test_process_upc_with_calc_check_digit_false(self):
        """Test process_upc with calc_check_digit=False."""
        # 11-digit with calc disabled should return empty
        result = BaseConverter.process_upc("12345678901", calc_check_digit=False)
        self.assertEqual(result, "")
    
    def test_process_upc_non_numeric(self):
        """Test process_upc with non-numeric input."""
        result = BaseConverter.process_upc("abcdefghij")
        self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
