"""
business_logic.interface_logic

Extracted non-UI logic from interface.py:
- validate_email
- check_logs_directory
- add_folder
- check_folder_exists
- avoid_duplicate_export_file
- export_processed_report

The functions are small, focused and accept dependencies (database objects, config dicts)
so they remain testable and UI-free.
"""
from typing import Any, Dict, Optional, Tuple
import os
import copy
import hashlib
import zipfile
from io import StringIO
import time
import datetime

# External modules used by the original logic
import batch_log_sender  # used by export step (kept for parity)
import utils  # for do_clear_old_files used in export_processed_report

# Centralized logging for the package
import logging
from business_logic.logging import setup_logging as _setup_logging

# Ensure logging is configured when module is imported by tests/CLI
_setup_logging()
logger = logging.getLogger("batch_file_processor")

def validate_email(email: str) -> bool:
    """Return True if the given email string looks like an email address.

    Uses the same regular expression that existed in interface.py.
    """
    import re

    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    return True if re.fullmatch(regex, email) else False


def check_logs_directory(logs_directory: Dict[str, Any]) -> bool:
    """Return True if logs_directory['logs_directory'] is writable.

    This mirrors the simple filesystem check present in the original code.
    """
    try:
        test_path = os.path.join(logs_directory["logs_directory"], "test_log_file")
        with open(test_path, "w", encoding="utf-8") as test_log_file:
            test_log_file.write("teststring")
        os.remove(test_path)
        return True
    except IOError:
        return False


def add_folder(database_obj: Any, folder_path: str) -> None:
    """Add a folder record to the database using the template defaults.

    Parameters:
    - database_obj: object with .oversight_and_defaults and .folders_table attributes
    - folder_path: filesystem path of the folder to add

    This function preserves the logic used to compute a unique alias.
    """
    SKIP_LIST = [
        "folder_name",
        "alias",
        "id",
        "logs_directory",
        "errors_folder",
        "enable_reporting",
        "report_printing_fallback",
        "single_add_folder_prior",
        "batch_add_folder_prior",
        "export_processed_folder_prior",
        "report_edi_errors",
    ]
    template = database_obj.oversight_and_defaults.find_one(id=1)
    template_settings = {k: v for k, v in template.items() if k not in SKIP_LIST}

    folder_name = os.path.basename(folder_path)
    counter = 1
    while database_obj.folders_table.find_one(alias=folder_name):
        folder_name = os.path.basename(folder_path) + f" {counter}"
        counter += 1

    template_settings["folder_name"] = folder_path
    template_settings["alias"] = folder_name
    database_obj.folders_table.insert({**template_settings})


def check_folder_exists(database_obj: Any, check_folder: str) -> Dict[str, Optional[Any]]:
    """Check whether check_folder is already present in database_obj.folders_table.

    Returns a dict with keys 'truefalse' (bool) and 'matched_folder' (row or None).
    """
    folder_list = database_obj.folders_table.all()
    for possible_folder in folder_list:
        possible_folder_string = possible_folder["folder_name"]
        if os.path.normpath(possible_folder_string) == os.path.normpath(check_folder):
            return {"truefalse": True, "matched_folder": possible_folder}
    return {"truefalse": False, "matched_folder": None}


def avoid_duplicate_export_file(file_name: str, file_extension: str) -> str:
    """Return a file path that does not already exist by appending (n) when needed.

    Maintains the same behavior as the original helper.
    """
    if not os.path.exists(file_name + file_extension):
        return file_name + file_extension
    else:
        i = 1
        while True:
            potential_file_path = file_name + " (" + str(i) + ")" + file_extension
            if not os.path.exists(potential_file_path):
                return potential_file_path
            i += 1


def export_processed_report(database_obj: Any, folder_id: int, output_folder: str) -> str:
    """Export a CSV of processed files for folder_id into output_folder.

    Returns the path to the created export file.

    Parameters:
    - database_obj: object with .folders_table and .processed_files attributes
    - folder_id: id of the folder to export
    - output_folder: destination folder path
    """
    folder_alias = database_obj.folders_table.find_one(id=folder_id)["alias"]

    export_file_path = avoid_duplicate_export_file(
        os.path.join(output_folder, folder_alias + " processed report"), ".csv"
    )

    with open(export_file_path, "w", encoding="utf-8") as processed_log:
        processed_log.write(
            "File,Date,Copy Destination,FTP Destination,Email Destination\n"
        )
        for line in database_obj.processed_files.find(folder_id=folder_id):
            processed_log.write(
                f"{line['file_name']},"
                f"{line['sent_date_time'].strftime('%Y-%m-%d %H:%M:%S')},"
                f"{line['copy_destination']},"
                f"{line['ftp_destination']},"
                f"{line['email_destination']}"
                "\n"
            )

    return export_file_path


__all__ = [
    "validate_email",
    "check_logs_directory",
    "add_folder",
    "check_folder_exists",
    "avoid_duplicate_export_file",
    "export_processed_report",
]