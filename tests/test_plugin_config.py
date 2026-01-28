"""Test plugin configuration system."""

import pytest
from plugin_config import ConfigField, PluginConfigMixin, PluginRegistry
from convert_base import BaseConverter
from send_base import BaseSendBackend


class TestConfigField:
    def test_boolean_field_creation(self):
        field = ConfigField(
            key="test_bool", label="Test Boolean", type="boolean", default=True
        )
        assert field.key == "test_bool"
        assert field.default == True
        assert field.type == "boolean"

    def test_string_field_with_validation(self):
        field = ConfigField(
            key="test_str",
            label="Test String",
            type="string",
            default="",
            required=True,
            placeholder="Enter value",
        )
        assert field.required == True
        assert field.placeholder == "Enter value"

    def test_select_field_requires_options(self):
        with pytest.raises(ValueError):
            ConfigField(
                key="test_select",
                label="Test Select",
                type="select",
                default="",
                options=[],
            )

    def test_field_from_dict(self):
        data = {
            "key": "test",
            "label": "Test",
            "type": "integer",
            "default": 0,
            "min_value": 0,
            "max_value": 100,
        }
        field = ConfigField.from_dict(data)
        assert field.min_value == 0
        assert field.max_value == 100


class TestPluginConfigMixin:
    def test_get_config_fields(self):
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "param1",
                    "label": "Parameter 1",
                    "type": "string",
                    "default": "",
                }
            ]

        fields = TestPlugin.get_config_fields()
        assert len(fields) == 1
        assert fields[0].key == "param1"

    def test_get_default_config(self):
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "param1",
                    "label": "Parameter 1",
                    "type": "boolean",
                    "default": True,
                },
                {
                    "key": "param2",
                    "label": "Parameter 2",
                    "type": "string",
                    "default": "test",
                },
            ]

        defaults = TestPlugin.get_default_config()
        assert defaults["param1"] == True
        assert defaults["param2"] == "test"

    def test_validate_config_required_fields(self):
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "required_param",
                    "label": "Required",
                    "type": "string",
                    "default": "",
                    "required": True,
                }
            ]

        valid, errors = TestPlugin.validate_config({"required_param": "value"})
        assert valid == True
        assert len(errors) == 0

        valid, errors = TestPlugin.validate_config({"required_param": ""})
        assert valid == False
        assert len(errors) > 0

    def test_validate_config_integer_bounds(self):
        class TestPlugin(PluginConfigMixin):
            CONFIG_FIELDS = [
                {
                    "key": "int_param",
                    "label": "Integer",
                    "type": "integer",
                    "default": 10,
                    "min_value": 0,
                    "max_value": 100,
                }
            ]

        valid, errors = TestPlugin.validate_config({"int_param": 50})
        assert valid == True

        valid, errors = TestPlugin.validate_config({"int_param": -1})
        assert valid == False

        valid, errors = TestPlugin.validate_config({"int_param": 150})
        assert valid == False


class TestPluginRegistry:
    def test_register_convert_plugin(self):
        class TestConverter(BaseConverter):
            PLUGIN_ID = "test_converter"
            PLUGIN_NAME = "Test Converter"
            CONFIG_FIELDS = []

            def initialize_output(self):
                pass

            def process_record_a(self, record):
                pass

            def process_record_b(self, record):
                pass

            def process_record_c(self, record):
                pass

            def finalize_output(self):
                return ""

        PluginRegistry.register_convert_plugin(TestConverter)
        retrieved = PluginRegistry.get_convert_plugin("test_converter")
        assert retrieved == TestConverter

    def test_register_send_plugin(self):
        class TestSender(BaseSendBackend):
            PLUGIN_ID = "test_sender"
            PLUGIN_NAME = "Test Sender"
            CONFIG_FIELDS = []

            def _send(self):
                pass

        PluginRegistry.register_send_plugin(TestSender)
        retrieved = PluginRegistry.get_send_plugin("test_sender")
        assert retrieved == TestSender

    def test_list_plugins(self):
        convert_plugins = PluginRegistry.list_convert_plugins()
        assert isinstance(convert_plugins, list)

        send_plugins = PluginRegistry.list_send_plugins()
        assert isinstance(send_plugins, list)


class TestActualPlugins:
    """Test actual plugin implementations."""

    def test_csv_converter_has_config(self):
        from convert_to_csv import CsvConverter

        assert CsvConverter.PLUGIN_ID == "csv"
        assert len(CsvConverter.CONFIG_FIELDS) > 0

        fields = CsvConverter.get_config_fields()
        field_keys = [f.key for f in fields]
        assert "include_headers" in field_keys
        assert "calculate_upc_check_digit" in field_keys

    def test_fintech_converter_has_config(self):
        from convert_to_fintech import FintechConverter

        assert FintechConverter.PLUGIN_ID == "fintech"
        assert len(FintechConverter.CONFIG_FIELDS) > 0

        fields = FintechConverter.get_config_fields()
        assert fields[0].key == "fintech_division_id"
        assert fields[0].required == True

    def test_copy_backend_has_config(self):
        from copy_backend import CopySendBackend

        assert CopySendBackend.PLUGIN_ID == "copy"
        assert len(CopySendBackend.CONFIG_FIELDS) > 0

        fields = CopySendBackend.get_config_fields()
        assert fields[0].key == "copy_to_directory"

    def test_ftp_backend_has_config(self):
        from ftp_backend import FTPSendBackend

        assert FTPSendBackend.PLUGIN_ID == "ftp"
        fields = FTPSendBackend.get_config_fields()
        field_keys = [f.key for f in fields]
        assert "ftp_server" in field_keys
        assert "ftp_port" in field_keys
        assert "ftp_username" in field_keys

    def test_email_backend_has_config(self):
        from email_backend import EmailSendBackend

        assert EmailSendBackend.PLUGIN_ID == "email"
        fields = EmailSendBackend.get_config_fields()
        field_keys = [f.key for f in fields]
        assert "email_to" in field_keys
        assert "email_subject_line" in field_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
