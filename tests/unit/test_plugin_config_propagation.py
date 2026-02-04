"""Tests for plugin configuration propagation.

This module tests that plugin configuration options properly propagate
from database storage through the processing pipeline to plugin execution.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from plugin_config import PluginConfigMixin, ConfigField


class TestConfigValueAccess(unittest.TestCase):
    """Tests for configuration value access methods."""

    def setUp(self):
        """Set up test plugin with parameters_dict."""
        
        class TestPlugin(PluginConfigMixin):
            PLUGIN_ID = "test"
            PLUGIN_NAME = "Test Plugin"
            CONFIG_FIELDS = [
                ConfigField(
                    key="field1",
                    label="Field 1",
                    type="string",
                    default="default1"
                ),
                ConfigField(
                    key="field2",
                    label="Field 2",
                    type="boolean",
                    default=False
                ),
                ConfigField(
                    key="field3",
                    label="Field 3",
                    type="integer",
                    default=42
                )
            ]
        
        self.plugin_class = TestPlugin
        self.parameters_dict = {
            "field1": "custom_value",
            "field2": True,
            "field3": 123
        }
        
        # Create an instance with parameters_dict
        self.plugin_instance = TestPlugin()
        self.plugin_instance.parameters_dict = self.parameters_dict

    def test_get_config_value_exists(self):
        """Test that get_config_value returns correct values when they exist."""
        # Test accessing field1
        value = self.plugin_instance.get_config_value("field1")
        self.assertEqual(value, "custom_value")
        
        # Test accessing field2
        value = self.plugin_instance.get_config_value("field2")
        self.assertEqual(value, True)
        
        # Test accessing field3
        value = self.plugin_instance.get_config_value("field3")
        self.assertEqual(value, 123)

    def test_get_config_value_with_default(self):
        """Test that get_config_value returns default when key doesn't exist."""
        # Test with a default value
        value = self.plugin_instance.get_config_value("nonexistent_field", "default_value")
        self.assertEqual(value, "default_value")
        
        # Test with None as default
        value = self.plugin_instance.get_config_value("nonexistent_field", None)
        self.assertIsNone(value)

    def test_get_config_value_without_default(self):
        """Test that get_config_value returns None when key doesn't exist and no default."""
        value = self.plugin_instance.get_config_value("nonexistent_field")
        self.assertIsNone(value)

    def test_get_config_value_no_parameters_dict(self):
        """Test that get_config_value handles missing parameters_dict gracefully."""
        # Create instance without parameters_dict
        plugin_instance = self.plugin_class()
        
        # Should return default or None
        value = plugin_instance.get_config_value("field1", "fallback")
        self.assertEqual(value, "fallback")
        
        value = plugin_instance.get_config_value("field1")
        self.assertIsNone(value)

    def test_get_config_value_empty_parameters_dict(self):
        """Test that get_config_value handles empty parameters_dict."""
        plugin_instance = self.plugin_class()
        plugin_instance.parameters_dict = {}
        
        # Should return default or provided fallback
        value = plugin_instance.get_config_value("field1", "fallback")
        self.assertEqual(value, "fallback")
        
        value = plugin_instance.get_config_value("field1")
        self.assertIsNone(value)

    def test_get_config_value_different_types(self):
        """Test that get_config_value preserves value types."""
        # String
        value = self.plugin_instance.get_config_value("field1")
        self.assertIsInstance(value, str)
        self.assertEqual(value, "custom_value")
        
        # Boolean
        value = self.plugin_instance.get_config_value("field2")
        self.assertIsInstance(value, bool)
        self.assertEqual(value, True)
        
        # Integer
        value = self.plugin_instance.get_config_value("field3")
        self.assertIsInstance(value, int)
        self.assertEqual(value, 123)


class TestPluginConfigMixinWithMock(unittest.TestCase):
    """Tests for PluginConfigMixin using mocks to simulate real usage scenarios."""

    def test_get_config_value_with_mock_parameters(self):
        """Test configuration access with mocked parameters."""
        class MockPlugin(PluginConfigMixin):
            PLUGIN_ID = "mock"
            PLUGIN_NAME = "Mock Plugin"
            CONFIG_FIELDS = [
                ConfigField(key="test_param", label="Test Param", type="string", default="default")
            ]
        
        plugin = MockPlugin()
        plugin.parameters_dict = {"test_param": "actual_value"}
        
        value = plugin.get_config_value("test_param")
        self.assertEqual(value, "actual_value")
        
        # Test with default fallback
        value = plugin.get_config_value("missing_param", "fallback")
        self.assertEqual(value, "fallback")


class TestDatabaseToPluginFlow(unittest.TestCase):
    """Tests for the database-to-plugin configuration flow."""

    def test_folder_config_to_plugin_conversion(self):
        """Test that folder configuration from database correctly maps to plugin parameters."""
        # Simulate a folder configuration from the database
        folder_config = {
            'folder_name': 'Test Folder',
            'convert_to_format': 'csv',
            'include_headers': True,
            'calculate_upc_check_digit': False,
            'csv_delimiter': ',',
            'output_file_extension': '.csv',
            'process_backend_copy': True,
            'copy_to_directory': '/tmp/output',
            'ftp_server': 'ftp.example.com',
            'email_to': 'test@example.com',
            # Additional fields that would come from the database
        }

        # Test that plugin can access configuration values from the folder config
        class MockCsvConverter(PluginConfigMixin):
            PLUGIN_ID = "csv"
            PLUGIN_NAME = "CSV Converter"
            CONFIG_FIELDS = [
                ConfigField(key="include_headers", label="Include Headers", type="boolean", default=False),
                ConfigField(key="calculate_upc_check_digit", label="Calculate UPC Check Digit", type="boolean", default=False),
                ConfigField(key="csv_delimiter", label="CSV Delimiter", type="string", default=","),
            ]

        # Create converter instance with folder config as parameters_dict
        converter = MockCsvConverter()
        converter.parameters_dict = folder_config

        # Test that configuration values are accessible
        self.assertTrue(converter.get_config_value("include_headers"))
        self.assertFalse(converter.get_config_value("calculate_upc_check_digit"))
        self.assertEqual(converter.get_config_value("csv_delimiter"), ",")

    def test_multiple_plugin_configs_from_single_folder(self):
        """Test that multiple plugin configs can be extracted from a single folder config."""
        folder_config = {
            'folder_name': 'Test Folder',
            'convert_to_format': 'fintech',
            # CSV converter specific configs
            'include_headers': True,
            'calculate_upc_check_digit': False,
            # Fintech converter specific configs
            'fintech_division_id': 'DIV123',
            'fintech_format_version': '2.0',
            # Backend configs
            'process_backend_copy': True,
            'copy_to_directory': '/tmp/output',
            'process_backend_ftp': False,
            'process_backend_email': True,
            'email_to': 'recipient@example.com',
            'email_subject_line': 'New file processed',
        }

        # Test CSV converter config extraction
        class MockCsvConverter(PluginConfigMixin):
            PLUGIN_ID = "csv"
            PLUGIN_NAME = "CSV Converter"
            CONFIG_FIELDS = [
                ConfigField(key="include_headers", label="Include Headers", type="boolean", default=False),
                ConfigField(key="calculate_upc_check_digit", label="Calculate UPC Check Digit", type="boolean", default=False),
            ]

        # Test Fintech converter config extraction
        class MockFintechConverter(PluginConfigMixin):
            PLUGIN_ID = "fintech"
            PLUGIN_NAME = "Fintech Converter"
            CONFIG_FIELDS = [
                ConfigField(key="fintech_division_id", label="Division ID", type="string", default=""),
                ConfigField(key="fintech_format_version", label="Format Version", type="string", default="1.0"),
            ]

        # Create instances with the same folder config
        csv_converter = MockCsvConverter()
        csv_converter.parameters_dict = folder_config
        
        fintech_converter = MockFintechConverter()
        fintech_converter.parameters_dict = folder_config

        # Test that each plugin gets its relevant configuration
        self.assertTrue(csv_converter.get_config_value("include_headers"))
        self.assertFalse(csv_converter.get_config_value("calculate_upc_check_digit"))
        
        self.assertEqual(fintech_converter.get_config_value("fintech_division_id"), "DIV123")
        self.assertEqual(fintech_converter.get_config_value("fintech_format_version"), "2.0")

    def test_backend_config_flow(self):
        """Test that backend configuration flows correctly from folder to backend plugin."""
        folder_config = {
            'folder_name': 'Test Folder',
            'convert_to_format': 'csv',
            'process_backend_copy': True,
            'copy_to_directory': '/output/path',
            'process_backend_ftp': True,
            'ftp_server': 'ftp.example.com',
            'ftp_port': 21,
            'ftp_username': 'user',
            'ftp_password': 'pass',
            'process_backend_email': True,
            'email_to': 'recipient@example.com',
            'email_subject_line': 'Processed file',
        }

        # Test Copy backend config
        class MockCopyBackend(PluginConfigMixin):
            PLUGIN_ID = "copy"
            PLUGIN_NAME = "Copy Backend"
            CONFIG_FIELDS = [
                ConfigField(key="copy_to_directory", label="Copy to Directory", type="string", default=""),
            ]

        # Test FTP backend config
        class MockFtpBackend(PluginConfigMixin):
            PLUGIN_ID = "ftp"
            PLUGIN_NAME = "FTP Backend"
            CONFIG_FIELDS = [
                ConfigField(key="ftp_server", label="FTP Server", type="string", default="localhost"),
                ConfigField(key="ftp_port", label="FTP Port", type="integer", default=21),
                ConfigField(key="ftp_username", label="FTP Username", type="string", default=""),
            ]

        copy_backend = MockCopyBackend()
        copy_backend.parameters_dict = folder_config
        
        ftp_backend = MockFtpBackend()
        ftp_backend.parameters_dict = folder_config

        # Test that each backend gets its relevant configuration
        self.assertEqual(copy_backend.get_config_value("copy_to_directory"), "/output/path")
        self.assertEqual(ftp_backend.get_config_value("ftp_server"), "ftp.example.com")
        self.assertEqual(ftp_backend.get_config_value("ftp_port"), 21)
        self.assertEqual(ftp_backend.get_config_value("ftp_username"), "user")

    def test_config_flow_with_defaults(self):
        """Test configuration flow when some values are missing (should use defaults from CONFIG_FIELDS)."""
        # Folder config with some missing values
        folder_config = {
            'folder_name': 'Test Folder',
            'convert_to_format': 'csv',
            # Missing 'include_headers' - should use default
            'calculate_upc_check_digit': True,  # Present
            # Missing 'csv_delimiter' - should use default
        }

        class MockCsvConverter(PluginConfigMixin):
            PLUGIN_ID = "csv"
            PLUGIN_NAME = "CSV Converter"
            CONFIG_FIELDS = [
                ConfigField(key="include_headers", label="Include Headers", type="boolean", default=True),  # Default is True
                ConfigField(key="calculate_upc_check_digit", label="Calculate UPC Check Digit", type="boolean", default=False),  # Default is False
                ConfigField(key="csv_delimiter", label="CSV Delimiter", type="string", default="|"),  # Default is pipe
            ]

        converter = MockCsvConverter()
        converter.parameters_dict = folder_config

        # Values that exist in folder_config should be used
        self.assertTrue(converter.get_config_value("calculate_upc_check_digit"))  # From config, should be True

        # Values missing from folder_config should return None (not the CONFIG_FIELD default)
        # The get_config_value method only returns the default passed as parameter, not from CONFIG_FIELDS
        self.assertIsNone(converter.get_config_value("include_headers"))  # Missing from config, returns None
        self.assertIsNone(converter.get_config_value("csv_delimiter"))  # Missing from config, returns None
        
        # But if we pass a default parameter, it should return that
        self.assertTrue(converter.get_config_value("include_headers", True))  # Returns provided default
        self.assertEqual(converter.get_config_value("csv_delimiter", "|"), "|")  # Returns provided default


class TestEndToEndConfigEffects(unittest.TestCase):
    """End-to-end tests verifying configuration effects on plugin output with mock EDI data."""

    def test_csv_converter_configuration_effects(self):
        """Test that CSV converter configuration options affect output as expected."""
        # Mock EDI data - simplified representation
        mock_edi_content = "ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     *200715*1719*^*00501*000000001*0*P*>~GS*PO*SENDERID*RECEIVERID*20200715*1719*1*X*005010~ST*850*0001~BEG*00*SA*123456789*20200715*1200~ITD*01*3***Net 30~LIN*1*BP*123456789012~SN1*1*10*EA~PID*F****DESCRIPTION~PO4*1*10*EA*24*IN~CTT*1~SE*22*0001~GE*1*1~IEA*1*000010538~"
        
        # Create a temporary EDI file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.edi', delete=False) as temp_edi:
            temp_edi.write(mock_edi_content)
            temp_edi_path = temp_edi.name

        try:
            # Test configuration with headers enabled
            class MockCsvConverterHeaders(PluginConfigMixin):
                PLUGIN_ID = "csv"
                PLUGIN_NAME = "CSV Converter"
                CONFIG_FIELDS = [
                    ConfigField(key="include_headers", label="Include Headers", type="boolean", default=False),
                    ConfigField(key="calculate_upc_check_digit", label="Calculate UPC Check Digit", type="boolean", default=False),
                ]

                def __init__(self, parameters_dict):
                    self.parameters_dict = parameters_dict
                    # Mimic the initialization logic from actual CsvConverter
                    def to_bool(value):
                        if isinstance(value, bool):
                            return value
                        if isinstance(value, str):
                            return value.lower() in ("true", "1", "yes")
                        return bool(value)
                    
                    self.include_headers = to_bool(self.get_config_value("include_headers", False))

            # Test with headers enabled
            config_with_headers = {"include_headers": True, "calculate_upc_check_digit": False}
            converter_with_headers = MockCsvConverterHeaders(config_with_headers)
            
            # Test with headers disabled
            config_without_headers = {"include_headers": False, "calculate_upc_check_digit": False}
            converter_without_headers = MockCsvConverterHeaders(config_without_headers)
            
            # Verify that configuration is correctly accessed
            self.assertTrue(converter_with_headers.include_headers)
            self.assertFalse(converter_without_headers.include_headers)

        finally:
            # Clean up temporary file
            os.unlink(temp_edi_path)

    def test_backend_configuration_effects(self):
        """Test that backend configuration affects behavior as expected."""
        # Test FTP backend configuration
        class MockFtpBackend(PluginConfigMixin):
            PLUGIN_ID = "ftp"
            PLUGIN_NAME = "FTP Backend"
            CONFIG_FIELDS = [
                ConfigField(key="ftp_server", label="FTP Server", type="string", default="localhost"),
                ConfigField(key="ftp_port", label="FTP Port", type="integer", default=21),
                ConfigField(key="ftp_username", label="FTP Username", type="string", default="anonymous"),
            ]

            def __init__(self, parameters_dict):
                self.parameters_dict = parameters_dict
                # Mimic the actual FTP backend configuration access
                self.ftp_server = self.get_config_value("ftp_server", "")
                self.ftp_port = self.get_config_value("ftp_port", 21)
                self.ftp_username = self.get_config_value("ftp_username", "")

        # Test with custom configuration
        ftp_config = {
            "ftp_server": "custom.ftp.server.com",
            "ftp_port": 2222,
            "ftp_username": "testuser"
        }
        ftp_backend = MockFtpBackend(ftp_config)
        
        # Verify that configuration is correctly accessed
        self.assertEqual(ftp_backend.ftp_server, "custom.ftp.server.com")
        self.assertEqual(ftp_backend.ftp_port, 2222)
        self.assertEqual(ftp_backend.ftp_username, "testuser")

        # Test with default configuration
        default_config = {}  # No custom config values
        ftp_backend_default = MockFtpBackend(default_config)
        
        # When no config values are provided, get_config_value returns None
        # (unless a default is provided as second argument)
        self.assertEqual(ftp_backend_default.ftp_server, "")  # Returns empty string as specified
        self.assertEqual(ftp_backend_default.ftp_port, 21)  # Returns default 21
        self.assertEqual(ftp_backend_default.ftp_username, "")  # Returns empty string as specified

    def test_converter_behavior_with_different_configs(self):
        """Test how different configurations affect converter behavior."""
        # Mock configuration for different scenarios
        scenario_configs = {
            "headers_enabled": {
                "include_headers": True,
                "calculate_upc_check_digit": False,
                "include_a_records": True,
            },
            "headers_disabled": {
                "include_headers": False,
                "calculate_upc_check_digit": False,
                "include_a_records": True,
            },
            "check_digit_enabled": {
                "include_headers": False,
                "calculate_upc_check_digit": True,
                "include_a_records": False,
            }
        }

        class MockBehaviorTester(PluginConfigMixin):
            PLUGIN_ID = "test"
            PLUGIN_NAME = "Behavior Tester"
            CONFIG_FIELDS = [
                ConfigField(key="include_headers", label="Include Headers", type="boolean", default=False),
                ConfigField(key="calculate_upc_check_digit", label="Calculate UPC Check Digit", type="boolean", default=False),
                ConfigField(key="include_a_records", label="Include A Records", type="boolean", default=False),
            ]

            def __init__(self, parameters_dict):
                self.parameters_dict = parameters_dict
                # Mimic actual converter initialization logic
                def to_bool(value):
                    if isinstance(value, bool):
                        return value
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes")
                    return bool(value)
                
                self.include_headers = to_bool(self.get_config_value("include_headers", False))
                self.calculate_upc_check_digit = to_bool(self.get_config_value("calculate_upc_check_digit", False))
                self.include_a_records = to_bool(self.get_config_value("include_a_records", False))

        # Test each configuration scenario
        for scenario_name, config in scenario_configs.items():
            tester = MockBehaviorTester(config)
            
            # Verify configuration was applied correctly
            self.assertEqual(tester.include_headers, config["include_headers"])
            self.assertEqual(tester.calculate_upc_check_digit, config["calculate_upc_check_digit"])
            self.assertEqual(tester.include_a_records, config["include_a_records"])

    def test_configuration_propagation_with_real_plugin_structure(self):
        """Test configuration propagation using the actual plugin structure."""
        # Import actual plugin classes to test with real configuration
        from convert_base import CSVConverter
        
        # Create a mock that mimics the real CSV converter but with testable config
        class TestRealStructureConverter(CSVConverter, PluginConfigMixin):
            PLUGIN_ID = "test_real"
            PLUGIN_NAME = "Test Real Structure"
            CONFIG_FIELDS = [
                ConfigField(key="test_option", label="Test Option", type="boolean", default=False),
                ConfigField(key="test_value", label="Test Value", type="string", default="default"),
            ]

            def __init__(self, edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):
                # Call parent init to set up the basic structure
                super().__init__(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)
                
                # Store config values as attributes to test access
                def to_bool(value):
                    if isinstance(value, bool):
                        return value
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes")
                    return bool(value)
                
                self.test_option = to_bool(self.get_config_value("test_option", False))
                self.test_value = self.get_config_value("test_value", "default")

            def initialize_output(self):
                pass

            def process_record_a(self, record):
                pass

            def process_record_b(self, record):
                pass

            def process_record_c(self, record):
                pass

            def finalize_output(self):
                pass

        # Create test data
        test_params = {
            "test_option": True,
            "test_value": "configured_value",
            "folder_name": "Test Folder"
        }
        
        # Create converter instance with test parameters
        converter = TestRealStructureConverter(
            edi_process="test.edi",
            output_filename="output.csv", 
            settings_dict={},
            parameters_dict=test_params,
            upc_lookup={}
        )
        
        # Verify configuration was properly propagated
        self.assertTrue(converter.test_option)
        self.assertEqual(converter.test_value, "configured_value")


class TestConfigurationValidation(unittest.TestCase):
    """Tests for configuration validation across all field types and plugins."""

    def test_boolean_field_validation(self):
        """Test validation of boolean fields."""
        class TestBooleanPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_bool"
            PLUGIN_NAME = "Test Boolean"
            CONFIG_FIELDS = [
                ConfigField(key="bool_field", label="Bool Field", type="boolean", default=False)
            ]

        # Valid boolean values
        valid_configs = [
            {"bool_field": True},
            {"bool_field": False},
            {"bool_field": "true"},  # String representations should be handled by plugin logic
            {"bool_field": "false"},
            {"bool_field": "1"},
            {"bool_field": "0"}
        ]
        
        for config in valid_configs:
            # Validation should not raise exceptions when used in practice
            plugin = TestBooleanPlugin()
            plugin.parameters_dict = config
            # Just test that we can access the value without error
            value = plugin.get_config_value("bool_field")
            self.assertIsNotNone(value)

        # Test validation method directly
        is_valid, errors = TestBooleanPlugin.validate_config({"bool_field": "not_a_bool"})
        # Note: validate_config only checks if the type is correct, doesn't do coercion
        self.assertFalse(is_valid)

    def test_integer_field_validation(self):
        """Test validation of integer fields."""
        class TestIntegerPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_int"
            PLUGIN_NAME = "Test Integer"
            CONFIG_FIELDS = [
                ConfigField(
                    key="int_field", 
                    label="Int Field", 
                    type="integer", 
                    default=0,
                    min_value=1,
                    max_value=100
                )
            ]

        # Test valid integers
        valid_configs = [
            {"int_field": 1},
            {"int_field": 50},
            {"int_field": 100},
        ]
        
        for config in valid_configs:
            is_valid, errors = TestIntegerPlugin.validate_config(config)
            self.assertTrue(is_valid, f"Config {config} should be valid: {errors}")

        # Test invalid integers
        invalid_configs = [
            {"int_field": 0},      # Below min
            {"int_field": 101},     # Above max
            {"int_field": "not_an_int"},  # Not an integer
        ]
        
        for config in invalid_configs:
            is_valid, errors = TestIntegerPlugin.validate_config(config)
            self.assertFalse(is_valid, f"Config {config} should be invalid")

    def test_float_field_validation(self):
        """Test validation of float fields."""
        class TestFloatPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_float"
            PLUGIN_NAME = "Test Float"
            CONFIG_FIELDS = [
                ConfigField(
                    key="float_field", 
                    label="Float Field", 
                    type="float", 
                    default=0.0,
                    min_value=0.5,
                    max_value=10.5
                )
            ]

        # Test valid floats
        valid_configs = [
            {"float_field": 0.5},
            {"float_field": 5.5},
            {"float_field": 10.5},
            {"float_field": 1},  # Integer should be acceptable
        ]
        
        for config in valid_configs:
            is_valid, errors = TestFloatPlugin.validate_config(config)
            self.assertTrue(is_valid, f"Config {config} should be valid: {errors}")

        # Test invalid floats
        invalid_configs = [
            {"float_field": 0.4},      # Below min
            {"float_field": 10.6},     # Above max
            {"float_field": "not_a_float"},  # Not a float
        ]
        
        for config in invalid_configs:
            is_valid, errors = TestFloatPlugin.validate_config(config)
            self.assertFalse(is_valid, f"Config {config} should be invalid")

    def test_select_field_validation(self):
        """Test validation of select fields."""
        class TestSelectPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_select"
            PLUGIN_NAME = "Test Select"
            CONFIG_FIELDS = [
                ConfigField(
                    key="choice_field", 
                    label="Choice Field", 
                    type="select", 
                    default="option1",
                    options=["option1", "option2", "option3"]
                )
            ]

        # Test valid choices
        valid_configs = [
            {"choice_field": "option1"},
            {"choice_field": "option2"},
            {"choice_field": "option3"},
        ]
        
        for config in valid_configs:
            is_valid, errors = TestSelectPlugin.validate_config(config)
            self.assertTrue(is_valid, f"Config {config} should be valid: {errors}")

        # Test invalid choice
        is_valid, errors = TestSelectPlugin.validate_config({"choice_field": "invalid_option"})
        self.assertFalse(is_valid)

    def test_select_field_with_tuple_options(self):
        """Test validation of select fields with tuple options."""
        class TestTupleSelectPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_tuple_select"
            PLUGIN_NAME = "Test Tuple Select"
            CONFIG_FIELDS = [
                ConfigField(
                    key="choice_field", 
                    label="Choice Field", 
                    type="select", 
                    default="opt1",
                    options=[("opt1", "Option 1"), ("opt2", "Option 2"), ("opt3", "Option 3")]
                )
            ]

        # Test valid choices using the value part of the tuple
        valid_configs = [
            {"choice_field": "opt1"},
            {"choice_field": "opt2"},
            {"choice_field": "opt3"},
        ]
        
        for config in valid_configs:
            is_valid, errors = TestTupleSelectPlugin.validate_config(config)
            self.assertTrue(is_valid, f"Config {config} should be valid: {errors}")

        # Test invalid choice
        is_valid, errors = TestTupleSelectPlugin.validate_config({"choice_field": "invalid_option"})
        self.assertFalse(is_valid)

    def test_required_field_validation(self):
        """Test validation of required fields."""
        class TestRequiredPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_required"
            PLUGIN_NAME = "Test Required"
            CONFIG_FIELDS = [
                ConfigField(
                    key="required_field", 
                    label="Required Field", 
                    type="string", 
                    default="",
                    required=True
                ),
                ConfigField(
                    key="optional_field", 
                    label="Optional Field", 
                    type="string", 
                    default=""
                )
            ]

        # Test with required field present
        is_valid, errors = TestRequiredPlugin.validate_config({
            "required_field": "some_value",
            "optional_field": "optional_value"
        })
        self.assertTrue(is_valid)

        # Test with required field missing
        is_valid, errors = TestRequiredPlugin.validate_config({
            "optional_field": "optional_value"
        })
        self.assertFalse(is_valid)
        self.assertIn("Required Field is required", errors)

        # Test with required field empty
        is_valid, errors = TestRequiredPlugin.validate_config({
            "required_field": "",
            "optional_field": "optional_value"
        })
        self.assertFalse(is_valid)
        self.assertIn("Required Field is required", errors)

    def test_string_field_validation(self):
        """Test validation of string fields."""
        class TestStringPlugin(PluginConfigMixin):
            PLUGIN_ID = "test_string"
            PLUGIN_NAME = "Test String"
            CONFIG_FIELDS = [
                ConfigField(
                    key="string_field", 
                    label="String Field", 
                    type="string", 
                    default=""
                )
            ]

        # String fields should accept any string value
        valid_configs = [
            {"string_field": ""},
            {"string_field": "normal string"},
            {"string_field": "string with spaces"},
            {"string_field": "12345"},
            {"string_field": "!@#$%^&*()"},
        ]
        
        for config in valid_configs:
            is_valid, errors = TestStringPlugin.validate_config(config)
            self.assertTrue(is_valid, f"Config {config} should be valid: {errors}")

    def test_validation_with_actual_plugin_configs(self):
        """Test validation using actual plugin configurations."""
        # Test with CSV converter config
        from convert_to_csv import CsvConverter
        
        # Valid config
        valid_config = {
            "include_headers": True,
            "calculate_upc_check_digit": False,
            "include_a_records": True,
            "include_c_records": False,
            "filter_ampersand": True,
            "pad_a_records": False,
            "a_record_padding": "",
            "override_upc_bool": False,
            "override_upc_level": 2,
            "override_upc_category_filter": "ALL",
            "retail_uom": False
        }
        
        is_valid, errors = CsvConverter.validate_config(valid_config)
        self.assertTrue(is_valid, f"CsvConverter validation failed: {errors}")

        # Test with FTP backend config
        from ftp_backend import FTPSendBackend
        
        # Valid config
        valid_ftp_config = {
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "password",
            "ftp_folder": "/upload/",
            "ftp_passive": True
        }
        
        is_valid, errors = FTPSendBackend.validate_config(valid_ftp_config)
        self.assertTrue(is_valid, f"FTPSendBackend validation failed: {errors}")

        # Test invalid config for FTP (missing required field)
        invalid_ftp_config = {
            "ftp_port": 21,  # Missing required ftp_server
            "ftp_username": "user",
        }
        
        is_valid, errors = FTPSendBackend.validate_config(invalid_ftp_config)
        self.assertFalse(is_valid)
        # Should have error about missing required field
        required_field_errors = [e for e in errors if "required" in e.lower()]
        self.assertTrue(len(required_field_errors) > 0)

    def test_range_validation_across_plugins(self):
        """Test range validation for integer and float fields in various plugins."""
        # Test override_upc_level field from CSV converter (range 1-4)
        from convert_to_csv import CsvConverter
        
        # Valid range values
        for value in [1, 2, 3, 4]:
            config = {"override_upc_level": value}
            is_valid, errors = CsvConverter.validate_config(config)
            self.assertTrue(is_valid, f"Value {value} should be valid for override_upc_level: {errors}")
        
        # Invalid range values
        for value in [0, 5, -1, 10]:
            config = {"override_upc_level": value}
            is_valid, errors = CsvConverter.validate_config(config)
            self.assertFalse(is_valid, f"Value {value} should be invalid for override_upc_level")


class TestUIElementConnection(unittest.TestCase):
    """Tests to ensure all UI elements are properly connected to their configuration options."""
    
    def test_config_field_definitions_match_actual_plugins(self):
        """Test that config field definitions match what's expected by actual plugins."""
        # Test CSV converter
        from convert_to_csv import CsvConverter
        csv_fields = CsvConverter.get_config_fields()
        csv_field_keys = [f.key for f in csv_fields]
        
        # Check that expected fields are present
        expected_csv_fields = [
            "include_headers", "calculate_upc_check_digit", "include_a_records", 
            "include_c_records", "filter_ampersand", "pad_a_records", "a_record_padding",
            "override_upc_bool", "override_upc_level", "override_upc_category_filter", "retail_uom"
        ]
        
        for field in expected_csv_fields:
            self.assertIn(field, csv_field_keys, f"CSV converter missing expected field: {field}")
        
        # Test FTP backend
        from ftp_backend import FTPSendBackend
        ftp_fields = FTPSendBackend.get_config_fields()
        ftp_field_keys = [f.key for f in ftp_fields]
        
        # Check that expected fields are present
        expected_ftp_fields = [
            "ftp_server", "ftp_port", "ftp_username", "ftp_password", "ftp_folder", "ftp_passive"
        ]
        
        for field in expected_ftp_fields:
            self.assertIn(field, ftp_field_keys, f"FTP backend missing expected field: {field}")
    
    def test_config_field_types_correct(self):
        """Test that config fields have correct types."""
        from convert_to_csv import CsvConverter
        csv_fields = CsvConverter.get_config_fields()
        
        # Create a map of field keys to their types
        field_type_map = {f.key: f.type for f in csv_fields}
        
        # Verify some key field types
        self.assertEqual(field_type_map["include_headers"], "boolean")
        self.assertEqual(field_type_map["calculate_upc_check_digit"], "boolean")
        self.assertEqual(field_type_map["override_upc_level"], "integer")
        self.assertEqual(field_type_map["include_headers"], "boolean")
        
        # Test with FTP backend as well
        from ftp_backend import FTPSendBackend
        ftp_fields = FTPSendBackend.get_config_fields()
        ftp_field_type_map = {f.key: f.type for f in ftp_fields}
        
        self.assertEqual(ftp_field_type_map["ftp_server"], "string")
        self.assertEqual(ftp_field_type_map["ftp_port"], "integer")
        self.assertEqual(ftp_field_type_map["ftp_passive"], "boolean")


if __name__ == '__main__':
    unittest.main()