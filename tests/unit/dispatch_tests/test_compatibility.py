"""Tests for dispatch/compatibility.py - Legacy compatibility utilities."""

import pytest

from dispatch.compatibility import (
    legacy_config_to_modern,
    modern_config_to_legacy,
    convert_backend_config,
    parse_legacy_process_edi_flag,
)


class TestCompatibility:
    """Tests for compatibility functions."""

    def test_parse_legacy_process_edi_flag(self):
        """Test parsing legacy process_edi flag."""
        # Test string "True"
        assert parse_legacy_process_edi_flag("True") is True

        # Test string "true"
        assert parse_legacy_process_edi_flag("true") is True

        # Test string "TRUE"
        assert parse_legacy_process_edi_flag("TRUE") is True

        # Test string "False"
        assert parse_legacy_process_edi_flag("False") is False

        # Test string "false"
        assert parse_legacy_process_edi_flag("false") is False

        # Test string "FALSE"
        assert parse_legacy_process_edi_flag("FALSE") is False

        # Test None
        assert parse_legacy_process_edi_flag(None) is False

        # Test empty string
        assert parse_legacy_process_edi_flag("") is False

        # Test other values
        assert parse_legacy_process_edi_flag("yes") is False
        assert parse_legacy_process_edi_flag("1") is False
        assert parse_legacy_process_edi_flag("0") is False

    def test_convert_backend_config(self):
        """Test backend config conversion."""
        legacy_config = {
            "process_backend_copy": True,
            "copy_to_directory": "/tmp/output",
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/uploads",
            "process_backend_email": True,
            "email_to": "test@example.com",
            "email_subject_line": "File: %filename%",
        }

        modern_config = convert_backend_config(legacy_config)

        assert modern_config["copy"]["enabled"] == True
        assert modern_config["copy"]["directory"] == "/tmp/output"

        assert modern_config["ftp"]["enabled"] == True
        assert modern_config["ftp"]["server"] == "ftp.example.com"
        assert modern_config["ftp"]["port"] == 21
        assert modern_config["ftp"]["username"] == "user"
        assert modern_config["ftp"]["password"] == "pass"
        assert modern_config["ftp"]["folder"] == "/uploads"

        assert modern_config["email"]["enabled"] == True
        assert modern_config["email"]["to"] == "test@example.com"
        assert modern_config["email"]["subject"] == "File: %filename%"

    def test_convert_backend_config_disabled(self):
        """Test backend config conversion with disabled backends."""
        legacy_config = {
            "process_backend_copy": False,
            "copy_to_directory": "",
            "process_backend_ftp": False,
            "ftp_server": "",
            "ftp_port": 0,
            "ftp_username": "",
            "ftp_password": "",
            "ftp_folder": "",
            "process_backend_email": False,
            "email_to": "",
            "email_subject_line": "",
        }

        modern_config = convert_backend_config(legacy_config)

        assert modern_config["copy"]["enabled"] == False
        assert modern_config["ftp"]["enabled"] == False
        assert modern_config["email"]["enabled"] == False

    def test_modern_config_to_legacy(self):
        """Test modern to legacy config conversion."""
        modern_config = {
            "copy": {"enabled": True, "directory": "/tmp/output"},
            "ftp": {
                "enabled": True,
                "server": "ftp.example.com",
                "port": 21,
                "username": "user",
                "password": "pass",
                "folder": "/uploads",
            },
            "email": {
                "enabled": True,
                "to": "test@example.com",
                "subject": "File: %filename%",
            },
        }

        legacy_config = modern_config_to_legacy(modern_config)

        assert legacy_config["process_backend_copy"] == True
        assert legacy_config["copy_to_directory"] == "/tmp/output"

        assert legacy_config["process_backend_ftp"] == True
        assert legacy_config["ftp_server"] == "ftp.example.com"
        assert legacy_config["ftp_port"] == 21
        assert legacy_config["ftp_username"] == "user"
        assert legacy_config["ftp_password"] == "pass"
        assert legacy_config["ftp_folder"] == "/uploads"

        assert legacy_config["process_backend_email"] == True
        assert legacy_config["email_to"] == "test@example.com"
        assert legacy_config["email_subject_line"] == "File: %filename%"

    def test_legacy_config_to_modern(self):
        """Test legacy to modern config conversion."""
        legacy_config = {
            "id": 1,
            "folder_name": "/path/to/folder",
            "alias": "Test Folder",
            "process_backend_copy": True,
            "copy_to_directory": "/tmp/output",
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "user",
            "ftp_password": "pass",
            "ftp_folder": "/uploads",
            "process_backend_email": True,
            "email_to": "test@example.com",
            "email_subject_line": "File: %filename%",
            "process_edi": "True",
            "force_edi_validation": False,
        }

        modern_config = legacy_config_to_modern(legacy_config)

        assert modern_config["id"] == 1
        assert modern_config["name"] == "/path/to/folder"
        assert modern_config["alias"] == "Test Folder"
        assert modern_config["edi"]["enabled"] == True
        assert modern_config["edi"]["force_validation"] == False

        assert modern_config["backends"]["copy"]["enabled"] == True
        assert modern_config["backends"]["copy"]["directory"] == "/tmp/output"

        assert modern_config["backends"]["ftp"]["enabled"] == True
        assert modern_config["backends"]["ftp"]["server"] == "ftp.example.com"
        assert modern_config["backends"]["ftp"]["port"] == 21
        assert modern_config["backends"]["ftp"]["username"] == "user"
        assert modern_config["backends"]["ftp"]["password"] == "pass"
        assert modern_config["backends"]["ftp"]["folder"] == "/uploads"

        assert modern_config["backends"]["email"]["enabled"] == True
        assert modern_config["backends"]["email"]["to"] == "test@example.com"
        assert modern_config["backends"]["email"]["subject"] == "File: %filename%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
