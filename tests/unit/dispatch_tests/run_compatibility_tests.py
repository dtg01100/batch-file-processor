#!/usr/bin/env python3
"""Run compatibility tests directly without pytest."""

import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from dispatch.compatibility import (
    convert_backend_config,
    legacy_config_to_modern,
    modern_config_to_legacy,
    parse_legacy_process_edi_flag,
)


def test_parse_legacy_process_edi_flag():
    """Test parsing legacy process_edi flag."""
    print("Testing parse_legacy_process_edi_flag()...")

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

    print("✓ parse_legacy_process_edi_flag() passed")


def test_convert_backend_config():
    """Test backend config conversion."""
    print("\nTesting convert_backend_config()...")

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

    print("✓ convert_backend_config() passed")


def test_convert_backend_config_disabled():
    """Test backend config conversion with disabled backends."""
    print("\nTesting convert_backend_config() with disabled backends...")

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

    print("✓ convert_backend_config() with disabled backends passed")


def test_modern_config_to_legacy():
    """Test modern to legacy config conversion."""
    print("\nTesting modern_config_to_legacy()...")

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

    print("✓ modern_config_to_legacy() passed")


def test_legacy_config_to_modern():
    """Test legacy to modern config conversion."""
    print("\nTesting legacy_config_to_modern()...")

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

    print("✓ legacy_config_to_modern() passed")


if __name__ == "__main__":
    try:
        print("Running dispatch layer compatibility tests...")
        print("=" * 50)

        test_parse_legacy_process_edi_flag()
        test_convert_backend_config()
        test_convert_backend_config_disabled()
        test_modern_config_to_legacy()
        test_legacy_config_to_modern()

        print("\n" + "=" * 50)
        print("All compatibility tests passed! ✓")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        print(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        print(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)
