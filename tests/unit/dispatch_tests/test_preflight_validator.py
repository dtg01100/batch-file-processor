"""Tests for dispatch.preflight_validator."""

from unittest.mock import MagicMock

from dispatch.preflight_validator import (
    PreflightIssue,
    PreflightResult,
    PreflightValidator,
)
from dispatch.send_manager import SendManager


def _make_folder(**overrides):
    """Build a minimal valid folder dict with overrides."""
    base = {
        "alias": "Test Folder",
        "folder_name": "/path/to/folder",
        "folder_is_active": True,
        "process_backend_copy": False,
        "process_backend_ftp": False,
        "process_backend_email": False,
        "copy_to_directory": "",
        "ftp_server": "",
        "ftp_port": 21,
        "ftp_username": "",
        "ftp_password": "",
        "ftp_folder": "",
        "email_to": "",
    }
    base.update(overrides)
    return base


def _make_settings(**overrides):
    """Build a minimal settings dict with overrides."""
    base = {
        "email_smtp_server": "smtp.example.com",
        "smtp_port": "587",
        "email_address": "sender@example.com",
    }
    base.update(overrides)
    return base


def _make_os_module(dirs_exist=True):
    """Create a fake os module where path.isdir returns dirs_exist."""
    os_mod = MagicMock()
    os_mod.path.isdir.return_value = dirs_exist
    return os_mod


# ------------------------------------------------------------------
# Valid configurations
# ------------------------------------------------------------------


def test_valid_copy_folder():
    """Copy enabled with existing destination directory → valid, no issues."""
    os_mod = _make_os_module(dirs_exist=True)
    validator = PreflightValidator(send_manager=SendManager(), os_module=os_mod)

    folder = _make_folder(
        process_backend_copy=True,
        copy_to_directory="/tmp/dest",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is True
    assert result.issues == []


def test_valid_ftp_folder():
    """FTP enabled with all fields set and trailing slash → valid."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_ftp=True,
        ftp_server="ftp.example.com",
        ftp_username="user",
        ftp_password="pass",
        ftp_folder="/uploads/",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is True
    assert result.issues == []


def test_valid_email_folder():
    """Email enabled with email_to and SMTP settings present → valid."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_email=True,
        email_to="recipient@example.com",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is True
    assert result.issues == []


# ------------------------------------------------------------------
# No backends enabled
# ------------------------------------------------------------------


def test_no_backends_enabled():
    """Folder with all backends disabled → error about no backends."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder()  # all backends False by default
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is False
    assert len(result.errors) >= 1
    messages = [i.message for i in result.errors]
    assert any("No send backends are enabled" in m for m in messages)


# ------------------------------------------------------------------
# Copy backend checks
# ------------------------------------------------------------------


def test_copy_enabled_no_destination():
    """Copy enabled but copy_to_directory empty → error from validate_backend_config."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_copy=True,
        copy_to_directory="",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is False
    error_messages = [i.message for i in result.errors]
    assert any("copy_to_directory" in m for m in error_messages)


def test_copy_destination_not_exists():
    """Copy enabled, directory set but doesn't exist → warning, still valid."""
    os_mod = _make_os_module(dirs_exist=False)
    validator = PreflightValidator(send_manager=SendManager(), os_module=os_mod)

    folder = _make_folder(
        process_backend_copy=True,
        copy_to_directory="/nonexistent/dir",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is True
    assert len(result.warnings) >= 1
    warning_messages = [i.message for i in result.warnings]
    assert any("does not exist" in m for m in warning_messages)


def test_copy_destination_exists():
    """Copy enabled, directory set and exists → no warning."""
    os_mod = _make_os_module(dirs_exist=True)
    validator = PreflightValidator(send_manager=SendManager(), os_module=os_mod)

    folder = _make_folder(
        process_backend_copy=True,
        copy_to_directory="/existing/dir",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is True
    assert result.warnings == []


# ------------------------------------------------------------------
# FTP backend checks
# ------------------------------------------------------------------


def test_ftp_enabled_missing_server():
    """FTP enabled but ftp_server empty → error."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_ftp=True,
        ftp_server="",
        ftp_username="user",
        ftp_password="pass",
        ftp_folder="/uploads/",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is False
    error_fields = [i.field for i in result.errors]
    assert "ftp_server" in error_fields


def test_ftp_enabled_missing_credentials():
    """FTP enabled, server set but username and password empty → errors for each."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_ftp=True,
        ftp_server="ftp.example.com",
        ftp_username="",
        ftp_password="",
        ftp_folder="/uploads/",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is False
    error_fields = [i.field for i in result.errors]
    assert "ftp_username" in error_fields
    assert "ftp_password" in error_fields


def test_ftp_folder_no_trailing_slash():
    """FTP enabled, ftp_folder without trailing / → error."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_ftp=True,
        ftp_server="ftp.example.com",
        ftp_username="user",
        ftp_password="pass",
        ftp_folder="somedir",
    )
    result = validator.validate_folders([folder], _make_settings())

    assert result.is_valid is False
    error_messages = [i.message for i in result.errors]
    assert any("must end with /" in m for m in error_messages)


# ------------------------------------------------------------------
# Email backend checks
# ------------------------------------------------------------------


def test_email_enabled_missing_smtp_settings():
    """Email enabled, email_to set, but email_smtp_server missing → error."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_email=True,
        email_to="recipient@example.com",
    )
    settings = _make_settings(email_smtp_server="")
    result = validator.validate_folders([folder], settings)

    assert result.is_valid is False
    error_messages = [i.message for i in result.errors]
    assert any("email_smtp_server" in m for m in error_messages)


def test_email_all_smtp_missing():
    """Email enabled, all three SMTP settings empty → error listing all three."""
    validator = PreflightValidator(send_manager=SendManager())

    folder = _make_folder(
        process_backend_email=True,
        email_to="recipient@example.com",
    )
    settings = _make_settings(
        email_smtp_server="",
        smtp_port="",
        email_address="",
    )
    result = validator.validate_folders([folder], settings)

    assert result.is_valid is False
    # Should have an error that mentions all three missing fields
    error_messages = [i.message for i in result.errors]
    smtp_error = [m for m in error_messages if "SMTP" in m]
    assert len(smtp_error) >= 1
    combined = " ".join(smtp_error)
    assert "email_smtp_server" in combined
    assert "smtp_port" in combined
    assert "email_address" in combined


# ------------------------------------------------------------------
# Multiple folders
# ------------------------------------------------------------------


def test_multiple_folders():
    """Two folders: one valid, one with issues → issues only for the bad folder."""
    os_mod = _make_os_module(dirs_exist=True)
    validator = PreflightValidator(send_manager=SendManager(), os_module=os_mod)

    good_folder = _make_folder(
        alias="Good Folder",
        process_backend_copy=True,
        copy_to_directory="/tmp/dest",
    )
    bad_folder = _make_folder(
        alias="Bad Folder",
        # no backends enabled → error
    )
    result = validator.validate_folders([good_folder, bad_folder], _make_settings())

    assert result.is_valid is False
    # Only the bad folder should have issues
    folder_aliases_with_issues = {i.folder_alias for i in result.issues}
    assert "Bad Folder" in folder_aliases_with_issues
    assert "Good Folder" not in folder_aliases_with_issues


# ------------------------------------------------------------------
# Empty folders list
# ------------------------------------------------------------------


def test_empty_folders_list():
    """Empty list of folders → valid, no issues."""
    validator = PreflightValidator(send_manager=SendManager())

    result = validator.validate_folders([], _make_settings())

    assert result.is_valid is True
    assert result.issues == []


# ------------------------------------------------------------------
# format_message
# ------------------------------------------------------------------


def test_format_message_groups_by_folder():
    """format_message groups errors and warnings by folder alias."""
    result = PreflightResult(
        issues=[
            PreflightIssue(
                folder_alias="Folder A",
                message="Missing server",
                severity="error",
                field="ftp_server",
            ),
            PreflightIssue(
                folder_alias="Folder A",
                message="Dir not found",
                severity="warning",
                field="copy_to_directory",
            ),
            PreflightIssue(
                folder_alias="Folder B",
                message="No backends",
                severity="error",
                field="backends",
            ),
        ]
    )

    msg = result.format_message()

    # Should contain both folder names
    assert "Folder A" in msg
    assert "Folder B" in msg
    # Errors should appear with ERROR prefix, warnings with WARNING
    assert "ERROR: Missing server" in msg
    assert "WARNING: Dir not found" in msg
    assert "ERROR: No backends" in msg


# ------------------------------------------------------------------
# PreflightResult properties
# ------------------------------------------------------------------


def test_preflight_result_properties():
    """Test is_valid, errors, warnings properties on PreflightResult directly."""
    # Empty result → valid
    empty = PreflightResult()
    assert empty.is_valid is True
    assert empty.errors == []
    assert empty.warnings == []
    assert empty.format_message() == ""

    # Warnings only → still valid
    warnings_only = PreflightResult(
        issues=[
            PreflightIssue(
                folder_alias="F1",
                message="some warning",
                severity="warning",
            ),
        ]
    )
    assert warnings_only.is_valid is True
    assert len(warnings_only.errors) == 0
    assert len(warnings_only.warnings) == 1

    # Errors → not valid
    with_error = PreflightResult(
        issues=[
            PreflightIssue(
                folder_alias="F1",
                message="some error",
                severity="error",
            ),
            PreflightIssue(
                folder_alias="F1",
                message="some warning",
                severity="warning",
            ),
        ]
    )
    assert with_error.is_valid is False
    assert len(with_error.errors) == 1
    assert len(with_error.warnings) == 1
