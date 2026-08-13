"""Pydantic schema for the webapp settings HTTP boundary.

The desktop app stores application settings in two singleton (id=1)
records:

- ``settings`` — email/SMTP, AS400/SSH credentials, interval backups
- ``administrative`` (oversight_and_defaults) — reporting toggles,
  logs directory, default copy destination

``GET/PUT /api/settings`` expose the editable subset of both records as
one nested payload, grouped the way the browser renders the Settings
card. Non-editable bookkeeping (``backup_counter``) stays internal.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_email: bool = False
    email_address: str = ""
    email_username: str = ""
    email_password: str = ""
    email_smtp_server: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)


class AS400Settings(BaseModel):
    """IBM i / DB2 SSH connection used by converters + UPC lookups."""

    model_config = ConfigDict(extra="forbid")

    as400_address: str = ""
    as400_username: str = ""
    as400_password: str = ""
    ssh_key_filename: str = ""


class BackupSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_interval_backups: bool = False
    backup_counter_maximum: int = Field(default=100, ge=1)


class ReportingSettings(BaseModel):
    """Oversight table: reporting toggles + the shared path defaults."""

    model_config = ConfigDict(extra="forbid")

    enable_reporting: bool = False
    report_email_destination: str = ""
    report_edi_errors: bool = False
    report_printing_fallback: bool = False
    logs_directory: str = ""
    copy_to_directory: str = ""


class SettingsSchema(BaseModel):
    """Wire representation of the editable application settings."""

    model_config = ConfigDict(extra="forbid")

    email: EmailSettings = Field(default_factory=EmailSettings)
    as400: AS400Settings = Field(default_factory=AS400Settings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    reporting: ReportingSettings = Field(default_factory=ReportingSettings)


def _as_bool(value: Any, *, default: bool = False) -> bool:
    """Coerce a DB cell to bool, tolerating legacy string values."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def settings_row_to_payload(
    settings_row: dict[str, Any], oversight_row: dict[str, Any]
) -> SettingsSchema:
    """Build a ``SettingsSchema`` from the two singleton DB records.

    Args:
        settings_row: The id=1 row from the ``settings`` table.
        oversight_row: The id=1 row from the ``administrative`` table.

    Returns:
        A populated ``SettingsSchema``. Missing keys fall back to the
        Pydantic defaults, keeping the schema tolerant of legacy rows
        that pre-date some columns.

    """
    return SettingsSchema(
        email=EmailSettings(
            enable_email=_as_bool(settings_row.get("enable_email")),
            email_address=settings_row.get("email_address", "") or "",
            email_username=settings_row.get("email_username", "") or "",
            email_password=settings_row.get("email_password", "") or "",
            email_smtp_server=settings_row.get("email_smtp_server", "") or "",
            smtp_port=_as_int(settings_row.get("smtp_port"), 587),
        ),
        as400=AS400Settings(
            as400_address=settings_row.get("as400_address", "") or "",
            as400_username=settings_row.get("as400_username", "") or "",
            as400_password=settings_row.get("as400_password", "") or "",
            ssh_key_filename=settings_row.get("ssh_key_filename", "") or "",
        ),
        backup=BackupSettings(
            enable_interval_backups=_as_bool(settings_row.get("enable_interval_backups")),
            backup_counter_maximum=_as_int(
                settings_row.get("backup_counter_maximum"), 100
            ),
        ),
        reporting=ReportingSettings(
            enable_reporting=_as_bool(oversight_row.get("enable_reporting")),
            report_email_destination=(
                oversight_row.get("report_email_destination", "") or ""
            ),
            report_edi_errors=_as_bool(oversight_row.get("report_edi_errors")),
            report_printing_fallback=_as_bool(
                oversight_row.get("report_printing_fallback")
            ),
            logs_directory=oversight_row.get("logs_directory", "") or "",
            copy_to_directory=oversight_row.get("copy_to_directory", "") or "",
        ),
    )


def payload_to_settings_row(schema: SettingsSchema) -> dict[str, Any]:
    """Flatten the email/as400/backup groups to ``settings`` columns."""
    return {
        "id": 1,
        "enable_email": schema.email.enable_email,
        "email_address": schema.email.email_address,
        "email_username": schema.email.email_username,
        "email_password": schema.email.email_password,
        "email_smtp_server": schema.email.email_smtp_server,
        "smtp_port": schema.email.smtp_port,
        "as400_address": schema.as400.as400_address,
        "as400_username": schema.as400.as400_username,
        "as400_password": schema.as400.as400_password,
        "ssh_key_filename": schema.as400.ssh_key_filename,
        "enable_interval_backups": schema.backup.enable_interval_backups,
        "backup_counter_maximum": schema.backup.backup_counter_maximum,
    }


def payload_to_oversight_row(schema: SettingsSchema) -> dict[str, Any]:
    """Flatten the reporting group to ``administrative`` columns."""
    return {
        "id": 1,
        "enable_reporting": schema.reporting.enable_reporting,
        "report_email_destination": schema.reporting.report_email_destination,
        "report_edi_errors": schema.reporting.report_edi_errors,
        "report_printing_fallback": schema.reporting.report_printing_fallback,
        "logs_directory": schema.reporting.logs_directory,
        "copy_to_directory": schema.reporting.copy_to_directory,
    }
