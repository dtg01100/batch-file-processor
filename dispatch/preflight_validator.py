"""Pre-send validation for folder configurations.

This module provides preflight checks that validate all active folder
configurations before the send pipeline begins processing. This catches
misconfigurations early — surfacing them as a dialog in interactive mode
or as log entries in automatic mode — rather than failing per-file during
the run.
"""

import os
from dataclasses import dataclass, field
from typing import Any

from core.structured_logging import get_logger
from dispatch.send_manager import SendManager

logger = get_logger(__name__)


@dataclass
class PreflightIssue:
    """A single preflight validation issue."""

    folder_alias: str
    message: str
    severity: str = "error"  # "error" or "warning"
    field: str = ""


@dataclass
class PreflightResult:
    """Aggregate result of preflight validation across all folders."""

    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when there are no errors (warnings are acceptable)."""
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[PreflightIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def format_message(self) -> str:
        """Format all issues as a human-readable string for display."""
        if not self.issues:
            return ""

        # Group by folder alias, errors first then warnings.
        by_folder: dict[str, list[PreflightIssue]] = {}
        for issue in self.issues:
            by_folder.setdefault(issue.folder_alias, []).append(issue)

        lines: list[str] = []
        for alias, folder_issues in by_folder.items():
            lines.append(f"Folder '{alias}':")
            errors = [i for i in folder_issues if i.severity == "error"]
            warnings = [i for i in folder_issues if i.severity == "warning"]
            for issue in errors:
                lines.append(f"  ERROR: {issue.message}")
            for issue in warnings:
                lines.append(f"  WARNING: {issue.message}")
            lines.append("")

        return "\n".join(lines).rstrip()


class PreflightValidator:
    """Validates folder configurations before the send pipeline starts.

    In interactive (GUI) mode the caller should present the result to the
    user and let them decide whether to continue.  In automatic mode the
    caller should log the issues and proceed — preflight must never block
    an automatic run.
    """

    def __init__(
        self,
        send_manager: SendManager | None = None,
        os_module: Any = None,
    ) -> None:
        self._send_manager = send_manager or SendManager()
        self._os = os_module or os

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_folders(self, folders: list[dict], settings: dict) -> PreflightResult:
        """Run all preflight checks on *folders* with global *settings*.

        Args:
            folders: Active folder configuration rows (raw dict from DB).
            settings: Global application settings dict.

        Returns:
            PreflightResult containing any issues found.

        """
        result = PreflightResult()

        for folder in folders:
            alias = folder.get("alias") or folder.get("folder_name", "Unknown")
            self._validate_backend_config(folder, alias, result)
            self._validate_no_backends(folder, alias, result)
            self._validate_copy_destination(folder, alias, result)
            self._validate_email_settings(folder, alias, settings, result)
            self._validate_ftp_settings(folder, alias, result)

        if result.issues:
            logger.warning(
                "Preflight validation found %d issue(s) across %d folder(s)",
                len(result.issues),
                len(folders),
            )
        else:
            logger.debug("Preflight validation passed for %d folder(s)", len(folders))

        return result

    # ------------------------------------------------------------------
    # Per-folder checks
    # ------------------------------------------------------------------

    def _validate_backend_config(
        self,
        folder: dict,
        alias: str,
        result: PreflightResult,
    ) -> None:
        """Verify that each enabled backend has its required setting."""
        errors = self._send_manager.validate_backend_config(folder)
        for msg in errors:
            result.issues.append(
                PreflightIssue(
                    folder_alias=alias,
                    message=msg,
                    severity="error",
                    field="backend_config",
                )
            )

    def _validate_no_backends(
        self,
        folder: dict,
        alias: str,
        result: PreflightResult,
    ) -> None:
        """Error if the folder has no backends enabled at all."""
        enabled = self._send_manager.get_enabled_backends(folder)
        if not enabled:
            result.issues.append(
                PreflightIssue(
                    folder_alias=alias,
                    message="No send backends are enabled",
                    severity="error",
                    field="backends",
                )
            )

    def _validate_copy_destination(
        self,
        folder: dict,
        alias: str,
        result: PreflightResult,
    ) -> None:
        """Warn if the copy destination directory does not exist."""
        if not folder.get("process_backend_copy"):
            return

        dest = folder.get("copy_to_directory", "")
        if dest and not self._os.path.isdir(dest):
            result.issues.append(
                PreflightIssue(
                    folder_alias=alias,
                    message=(f"Copy destination directory does not exist: {dest}"),
                    severity="warning",
                    field="copy_to_directory",
                )
            )

    def _validate_email_settings(
        self,
        folder: dict,
        alias: str,
        settings: dict,
        result: PreflightResult,
    ) -> None:
        """Error if email is enabled but global SMTP settings are missing."""
        if not folder.get("process_backend_email"):
            return

        missing: list[str] = []
        if not settings.get("email_smtp_server"):
            missing.append("email_smtp_server")
        if not settings.get("smtp_port"):
            missing.append("smtp_port")
        if not settings.get("email_address"):
            missing.append("email_address")

        if missing:
            result.issues.append(
                PreflightIssue(
                    folder_alias=alias,
                    message=(
                        "Email backend is enabled but global SMTP settings "
                        "are missing: " + ", ".join(missing)
                    ),
                    severity="error",
                    field="email_smtp",
                )
            )

    def _validate_ftp_settings(
        self,
        folder: dict,
        alias: str,
        result: PreflightResult,
    ) -> None:
        """Error if FTP is enabled but required fields are empty."""
        if not folder.get("process_backend_ftp"):
            return

        required = {
            "ftp_server": "FTP server",
            "ftp_username": "FTP username",
            "ftp_password": "FTP password",
            "ftp_folder": "FTP folder",
        }
        for key, label in required.items():
            if not folder.get(key):
                result.issues.append(
                    PreflightIssue(
                        folder_alias=alias,
                        message=f"{label} is not configured",
                        severity="error",
                        field=key,
                    )
                )

        ftp_folder = folder.get("ftp_folder", "")
        if ftp_folder and not ftp_folder.endswith("/"):
            result.issues.append(
                PreflightIssue(
                    folder_alias=alias,
                    message="FTP folder path must end with /",
                    severity="error",
                    field="ftp_folder",
                )
            )
