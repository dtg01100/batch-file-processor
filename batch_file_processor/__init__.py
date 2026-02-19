"""Compatibility package to expose top-level modules as package submodules.

This allows a gradual migration to package-style imports without moving files all
at once. Each listed module is imported from the repository root and registered
as a submodule under batch_file_processor so imports like

    import batch_file_processor.utils

continue to work.
"""

import importlib
import sys

__all__ = [
    "backup_increment",
    "batch_log_sender",
    "clear_old_files",
    "convert_to_csv",
    "convert_to_estore_einvoice_generic",
    "convert_to_estore_einvoice",
    "convert_to_fintech",
    "convert_to_jolley_custom",
    "convert_to_scannerware",
    "convert_to_scansheet_type_a",
    "convert_to_simplified_csv",
    "convert_to_stewarts_custom",
    "convert_to_yellowdog_csv",
    "copy_backend",
    "create_database",
    "database_import",
    "dialog",
    "_dispatch_legacy",
    "edi_tweaks",
    "email_backend",
    "folders_database_migrator",
    "ftp_backend",
    "mover",
    "mtc_edi_validator",
    "print_run_log",
    "query_runner",
    "record_error",
    "utils",
    "dispatch_process",
    "main_interface",
    "main_qt",
    "resend_interface",
]

for _mod in __all__:
    try:
        # import the top-level module (file at repository root)
        mod = importlib.import_module(_mod)
        pkg_name = __name__ + "." + _mod
        # register it under the package namespace
        sys.modules[pkg_name] = mod
        setattr(sys.modules[__name__], _mod, mod)
    except Exception:
        # Defer import errors until the actual module is used; skip silently.
        # This keeps package import robust during incremental migration.
        continue
