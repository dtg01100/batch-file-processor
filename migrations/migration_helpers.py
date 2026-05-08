"""Shared helper functions and constants for database migrations.

Extracted from folders_database_migrator to avoid circular imports
and enable reuse across migration modules.
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)

# Magic string constants
CSV_SORT_ORDER = "upc_number,qty_of_units,unit_cost,description,vendor_item"
REPLACEME_PLACEHOLDER = "replaceme"

# Current schema version - this is the single source of truth for the database version
CURRENT_SCHEMA_VERSION = "50"


def _quote_identifier(name: str) -> str:
    """Quote a SQL identifier, escaping any embedded quotes."""
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _add_column_safe(db, table_name, column_name, default_sql, sql_type="TEXT") -> None:
    """Add a column to a table if it doesn't already exist.

    Args:
        db: A sqlite_wrapper.Database connection.
        table_name: Name of the table to alter.
        column_name: Name of the column to add.
        default_sql: SQL literal for the default value (e.g. '"default_val"', '0').
        sql_type: SQL column type (default "TEXT").

    """
    cursor = db.raw_connection.cursor()
    quoted_table = _quote_identifier(table_name)
    cursor.execute(f"PRAGMA table_info({quoted_table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column_name in existing:
        return
    quoted_column = _quote_identifier(column_name)
    db.query(f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}")
    db.query(f"UPDATE {quoted_table} SET {quoted_column} = {default_sql}")


def _log_migration_step(from_version, to_version) -> None:
    """Log migration step progress."""
    print(f"  Migrating: v{from_version} -> v{to_version}")


def _normalize_legacy_v32_values(database_connection) -> None:
    """Normalize legacy v32 string booleans and display-name convert_to_format values.

    Legacy databases stored boolean columns as Python string literals 'True'/'False'
    and convert_to_format as display names like 'Estore eInvoice Generic'.
    Normalize these to integers (1/0) and canonical tokens (lowercase underscores)
    so that subsequent migrations can use reliable integer comparisons.
    """
    from core.utils.format_utils import normalize_convert_to_format

    cursor = database_connection.raw_connection.cursor()

    _BOOL_COLUMNS = [
        "folder_is_active",
        "include_c_records",
        "pad_a_records",
        "process_edi",
        "filter_ampersand",
        "calculate_upc_check_digit",
        "include_headers",
        "include_a_records",
        "append_a_records",
        "force_txt_file_ext",
        "process_backend_email",
        "process_backend_copy",
        "process_backend_ftp",
        "split_edi",
        "force_edi_validation",
        "tweak_edi",
        "force_each_upc",
        "include_item_numbers",
        "include_item_description",
        "simple_csv_sort_order",
        "split_prepaid_sales_tax_crec",
        "split_edi_include_invoices",
        "split_edi_include_credits",
        "prepend_date_files",
        "rename_file",
        "override_upc_bool",
        "invoice_date_custom_format",
        "retail_uom",
    ]

    for table in ("folders", "administrative"):
        for col in _BOOL_COLUMNS:
            try:
                cursor.execute(
                    f"UPDATE {_quote_identifier(table)} "
                    f"SET {_quote_identifier(col)} = 1 "
                    f"WHERE LOWER(CAST({_quote_identifier(col)} AS TEXT)) = 'true'"
                )
                cursor.execute(
                    f"UPDATE {_quote_identifier(table)} "
                    f"SET {_quote_identifier(col)} = 0 "
                    f"WHERE LOWER(CAST({_quote_identifier(col)} AS TEXT)) = 'false'"
                )
            except sqlite3.OperationalError as e:
                logger.debug("Column %s may not exist yet; skipping: %s", col, e)

        # Normalize convert_to_format via Python for full correctness
        try:
            rows = cursor.execute(
                f"SELECT id, convert_to_format FROM {_quote_identifier(table)} "
                f"WHERE convert_to_format IS NOT NULL AND convert_to_format != ''"
            ).fetchall()
            for row_id, fmt in rows:
                normalized = normalize_convert_to_format(fmt)
                if normalized != fmt:
                    cursor.execute(
                        f"UPDATE {_quote_identifier(table)} "
                        f"SET convert_to_format = ? WHERE id = ?",
                        (normalized, row_id),
                    )
        except sqlite3.OperationalError as e:
            logger.debug("Table %s or column may not exist yet; skipping: %s", table, e)

    database_connection.raw_connection.commit()
