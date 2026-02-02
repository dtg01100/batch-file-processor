"""Database migration to add plugin_config JSON column.

This migration consolidates individual plugin parameter columns into a single
JSON column for flexible plugin configuration storage.
"""

import json
import sqlite3
from typing import Union


def migrate_folder_row_to_json(row_dict: dict) -> dict:
    """Convert a folder row's plugin parameters to JSON config format.

    Args:
        row_dict: Dictionary of folder row data

    Returns:
        Dictionary with convert_plugin_config and send_plugin_configs
    """
    convert_format = row_dict.get("convert_to_format", "csv")

    convert_config = {}
    send_configs = {"copy": {}, "ftp": {}, "email": {}}

    if convert_format == "csv":
        convert_config = {
            "calculate_upc_check_digit": row_dict.get(
                "calculate_upc_check_digit", "False"
            ),
            "include_a_records": row_dict.get("include_a_records", "False"),
            "include_c_records": row_dict.get("include_c_records", "False"),
            "include_headers": row_dict.get("include_headers", "False"),
            "filter_ampersand": row_dict.get("filter_ampersand", "False"),
            "pad_a_records": row_dict.get("pad_a_records", "False"),
            "a_record_padding": row_dict.get("a_record_padding", ""),
            "override_upc_bool": row_dict.get("override_upc_bool", False),
            "override_upc_level": row_dict.get("override_upc_level", 1),
            "override_upc_category_filter": row_dict.get(
                "override_upc_category_filter", "ALL"
            ),
            "retail_uom": row_dict.get("retail_uom", False),
        }
    elif convert_format == "scannerware":
        convert_config = {
            "pad_a_records": row_dict.get("pad_a_records", "False"),
            "a_record_padding": row_dict.get("a_record_padding", ""),
            "append_a_records": row_dict.get("append_a_records", "False"),
            "a_record_append_text": row_dict.get("a_record_append_text", ""),
            "force_txt_file_ext": row_dict.get("force_txt_file_ext", "False"),
            "invoice_date_offset": row_dict.get("invoice_date_offset", 0),
        }
    elif convert_format == "simplified_csv":
        convert_config = {
            "include_headers": row_dict.get("include_headers", "False"),
            "include_item_numbers": row_dict.get("include_item_numbers", False),
            "include_item_description": row_dict.get("include_item_description", False),
            "retail_uom": row_dict.get("retail_uom", False),
            "simple_csv_sort_order": row_dict.get(
                "simple_csv_sort_order",
                "upc_number,qty_of_units,unit_cost,description,vendor_item",
            ),
        }
    elif convert_format == "estore_einvoice":
        convert_config = {
            "estore_store_number": row_dict.get("estore_store_number", ""),
            "estore_Vendor_OId": row_dict.get("estore_Vendor_OId", ""),
            "estore_vendor_NameVendorOID": row_dict.get(
                "estore_vendor_NameVendorOID", ""
            ),
        }
    elif convert_format == "estore_einvoice_generic":
        convert_config = {
            "estore_store_number": row_dict.get("estore_store_number", ""),
            "estore_Vendor_OId": row_dict.get("estore_Vendor_OId", ""),
            "estore_c_record_OID": row_dict.get("estore_c_record_OID", ""),
            "estore_vendor_NameVendorOID": row_dict.get(
                "estore_vendor_NameVendorOID", ""
            ),
        }
    elif convert_format == "fintech":
        convert_config = {
            "fintech_division_id": row_dict.get("fintech_division_id", "")
        }

    send_configs["copy"] = {"copy_to_directory": row_dict.get("copy_to_directory", "")}

    send_configs["ftp"] = {
        "ftp_server": row_dict.get("ftp_server", ""),
        "ftp_port": row_dict.get("ftp_port", 21),
        "ftp_folder": row_dict.get("ftp_folder", "/"),
        "ftp_username": row_dict.get("ftp_username", ""),
        "ftp_password": row_dict.get("ftp_password", ""),
        "ftp_passive": True,
    }

    send_configs["email"] = {
        "email_to": row_dict.get("email_to", ""),
        "email_cc": row_dict.get("email_cc", ""),
        "email_subject_line": row_dict.get("email_subject_line", ""),
    }

    return {
        "convert_plugin_config": convert_config,
        "send_plugin_configs": send_configs,
    }


def apply_migration(db: Union[sqlite3.Connection, "DatabaseConnection"]) -> bool:
    """Apply the plugin_config migration to the database.

    Args:
        db: Open sqlite3 connection or DatabaseConnection wrapper

    Returns:
        True if migration successful, False otherwise
    """
    connection = db.raw_connection if hasattr(db, "raw_connection") else db
    cursor = connection.cursor()

    cursor.execute("ALTER TABLE folders ADD COLUMN plugin_config TEXT")

    cursor.execute("SELECT * FROM folders")
    columns = [description[0] for description in cursor.description]
    rows_to_update = []

    for row in cursor.fetchall():
        row_dict = dict(zip(columns, row))
        row_id = row_dict["id"]
        plugin_configs = migrate_folder_row_to_json(row_dict)
        rows_to_update.append((json.dumps(plugin_configs), row_id))

    for config_json, row_id in rows_to_update:
        try:
            cursor.execute(
                "UPDATE folders SET plugin_config = ? WHERE id = ?",
                (config_json, row_id),
            )
        except sqlite3.Error as e:
            print(f"Failed to update row {row_id}: {e}")
            return False

    connection.commit()
    return True


def rollback_migration(db: Union[sqlite3.Connection, "DatabaseConnection"]) -> bool:
    """Rollback the plugin_config migration.

    Args:
        db: Open sqlite3 connection or DatabaseConnection wrapper

    Returns:
        True if rollback successful, False otherwise
    """
    return True
