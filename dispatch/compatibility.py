"""Compatibility layer for legacy dispatch imports.

This module provides backward-compatible imports with deprecation warnings.
All new code should import directly from dispatch package modules.

Migration Guide:
    Use explicit orchestrator wiring:
         from dispatch import DispatchOrchestrator, DispatchConfig
         orchestrator = DispatchOrchestrator(config)
         result = orchestrator.process_folder(...)

    OLD: from dispatch import generate_match_lists
    NEW: from dispatch.hash_utils import generate_match_lists

    OLD: from dispatch import EDIValidator
    NEW: from dispatch.edi_validator import EDIValidator

Deprecation Timeline:
    - v1.0: Compatibility layer introduced (current)
    - v1.1: Deprecation warnings added
    - v2.0: Compatibility layer removed, direct imports required
"""

import warnings
from typing import Any, Dict

from core.utils.bool_utils import normalize_bool


def _normalize_legacy_true_false(value: Any) -> bool:
    """Normalize legacy true/false string flags.

    Handles all stored forms: string "True"/"False" (legacy), integer 1/0
    (modern), and string "1"/"0" (produced by the v41→v42 migration due to
    SQLite TEXT affinity converting integer writes back to strings).

    Does NOT accept "yes"/"no" or other truthy strings - only the documented
    legacy formats.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        stripped = value.strip()
        lower_val = stripped.lower()
        if lower_val in ("true", "1"):
            return True
        if lower_val in ("false", "0", ""):
            return False
    return False


def parse_legacy_process_edi_flag(value: Any) -> bool:
    """Parse legacy process_edi flag to boolean.

    Args:
        value: Legacy value (string "True"/"False", boolean, etc.)

    Returns:
        Boolean value
    """
    return _normalize_legacy_true_false(value)


def convert_backend_config(legacy_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Convert legacy backend configuration to modern nested format.

    Args:
        legacy_config: Legacy flat configuration dict

    Returns:
        Modern nested configuration dict with 'copy', 'ftp', 'email' keys
    """
    return {
        "copy": {
            "enabled": normalize_bool(legacy_config.get("process_backend_copy", False)),
            "directory": legacy_config.get("copy_to_directory", ""),
        },
        "ftp": {
            "enabled": normalize_bool(legacy_config.get("process_backend_ftp", False)),
            "server": legacy_config.get("ftp_server", ""),
            "port": legacy_config.get("ftp_port", 21),
            "username": legacy_config.get("ftp_username", ""),
            "password": legacy_config.get("ftp_password", ""),
            "folder": legacy_config.get("ftp_folder", ""),
        },
        "email": {
            "enabled": normalize_bool(
                legacy_config.get("process_backend_email", False)
            ),
            "to": legacy_config.get("email_to", ""),
            "subject": legacy_config.get("email_subject_line", ""),
        },
    }


def modern_config_to_legacy(modern_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert modern backend configuration to legacy flat format.

    Args:
        modern_config: Modern nested configuration dict

    Returns:
        Legacy flat configuration dict
    """
    legacy = {}

    # Copy backend
    copy_cfg = modern_config.get("copy", {})
    legacy["process_backend_copy"] = copy_cfg.get("enabled", False)
    legacy["copy_to_directory"] = copy_cfg.get("directory", "")

    # FTP backend
    ftp_cfg = modern_config.get("ftp", {})
    legacy["process_backend_ftp"] = ftp_cfg.get("enabled", False)
    legacy["ftp_server"] = ftp_cfg.get("server", "")
    legacy["ftp_port"] = ftp_cfg.get("port", 21)
    legacy["ftp_username"] = ftp_cfg.get("username", "")
    legacy["ftp_password"] = ftp_cfg.get("password", "")
    legacy["ftp_folder"] = ftp_cfg.get("folder", "")

    # Email backend
    email_cfg = modern_config.get("email", {})
    legacy["process_backend_email"] = email_cfg.get("enabled", False)
    legacy["email_to"] = email_cfg.get("to", "")
    legacy["email_subject_line"] = email_cfg.get("subject", "")

    return legacy


def legacy_config_to_modern(legacy_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy folder configuration to modern format.

    Args:
        legacy_config: Legacy folder configuration dict

    Returns:
        Modern configuration dict with nested 'edi' and 'backends' sections
    """
    modern = {
        "id": legacy_config.get("id"),
        "name": legacy_config.get("folder_name", ""),
        "alias": legacy_config.get("alias", ""),
        "edi": {
            "enabled": parse_legacy_process_edi_flag(legacy_config.get("process_edi")),
            "force_validation": legacy_config.get("force_edi_validation", False),
        },
        "backends": convert_backend_config(legacy_config),
    }
    return modern


# Module-level deprecation message
_DEPRECATION_MSG = (
    "Importing {name} from dispatch.compatibility is deprecated. "
    "Import directly from dispatch module instead. "
    "See dispatch/compatibility.py for migration guide."
)


def __getattr__(name: str) -> Any:
    """Lazy import with deprecation warning.

    This allows importing any name from dispatch.compatibility
    while issuing a deprecation warning.

    Args:
        name: The name to import

    Returns:
        The requested object from the dispatch package

    Raises:
        AttributeError: If the name doesn't exist in dispatch
    """
    # Map of legacy names to their new locations
    _import_map = {
        # Core components
        "DispatchOrchestrator": "dispatch.orchestrator",
        "DispatchConfig": "dispatch.orchestrator",
        "FolderResult": "dispatch.orchestrator",
        "FileResult": "dispatch.orchestrator",
        # Validators
        "EDIValidator": "dispatch.edi_validator",
        # Managers
        "SendManager": "dispatch.send_manager",
        "ErrorHandler": "dispatch.error_handler",
        # Hash utilities
        "generate_match_lists": "dispatch.hash_utils",
        "generate_file_hash": "dispatch.hash_utils",
        # File utilities
        "build_output_filename": "dispatch.file_utils",
        "do_clear_old_files": "dispatch.file_utils",
        # Interfaces
        "DatabaseInterface": "dispatch.interfaces",
        "FileSystemInterface": "dispatch.interfaces",
        "BackendInterface": "dispatch.interfaces",
        # Log Sender
        "EmailConfig": "dispatch.log_sender",
        "LogSender": "dispatch.log_sender",
        "LogEntry": "dispatch.log_sender",
        "SMTPEmailService": "dispatch.log_sender",
        "MockEmailService": "dispatch.log_sender",
        "MockUIService": "dispatch.log_sender",
        "NullUIService": "dispatch.log_sender",
        # Print Service
        "PrintServiceProtocol": "dispatch.print_service",
        "WindowsPrintService": "dispatch.print_service",
        "UnixPrintService": "dispatch.print_service",
        "MockPrintService": "dispatch.print_service",
        "NullPrintService": "dispatch.print_service",
        "RunLogPrinter": "dispatch.print_service",
        # Processed Files Tracker
        "ProcessedFileRecord": "dispatch.processed_files_tracker",
        "InMemoryDatabase": "dispatch.processed_files_tracker",
        "ProcessedFilesTracker": "dispatch.processed_files_tracker",
    }

    if name in _import_map:
        warnings.warn(
            _DEPRECATION_MSG.format(name=name), DeprecationWarning, stacklevel=3
        )
        module_path = _import_map[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, name)

    raise AttributeError(f"module 'dispatch.compatibility' has no attribute '{name}'")


# Note: We don't use __all__ here because the lazy loading via __getattr__
# handles all exports dynamically. Static analysis tools won't see these
# exports, but they work correctly at runtime. Use dispatch/__init__.py
# for static exports.
