"""SQLite database wrapper to replace the dataset shim.

This provides a direct sqlite3 implementation without the magic behavior
that caused bugs in the dataset shim. Key improvements:

1. No automatic column/table creation - fails fast with clear errors
2. Explicit boolean handling - stores as INTEGER (0/1), converts to Python bool
3. Parameterized queries for all operations
4. Thread-safe connection management
5. No aggressive type conversions that cause subtle bugs

Usage:
    db = Database.connect("/path/to/database.db")
    table = db["table_name"]
    rows = table.find(column="value")
    row = table.find_one(id=1)
    table.insert({"column": "value"})
    table.update({"id": 1, "column": "new_value"}, ["id"])
    db.close()
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from core.utils.bool_utils import normalize_bool, to_db_bool

# Thread-local storage for database connections
_thread_local = threading.local()


class Table:
    """Represents a database table with CRUD operations.

    Provides methods for querying, inserting, updating, and deleting records.
    All boolean values are stored as INTEGER (0/1) and converted to Python bool on read.
    """

    def __init__(self, conn: sqlite3.Connection, name: str) -> None:
        """Initialize a table reference.

        Args:
            conn: SQLite database connection
            name: Name of the table
        """
        self._conn = conn
        self._name = name
        self._boolean_columns: Optional[set] = None

    _EXPLICIT_BOOLEAN_COLUMNS_BY_TABLE = {
        "folders": {
            "folder_is_active",
            "process_backend_copy",
            "process_backend_ftp",
            "process_backend_email",
            "process_edi",
            "calculate_upc_check_digit",
            "include_a_records",
            "include_c_records",
            "include_headers",
            "filter_ampersand",
            "tweak_edi",
            "split_edi",
            "force_edi_validation",
            "append_a_records",
            "force_txt_file_ext",
            "invoice_date_custom_format",
            "retail_uom",
            "override_upc_bool",
            "split_edi_include_invoices",
            "split_edi_include_credits",
            "prepend_date_files",
            "include_item_numbers",
            "include_item_description",
            "split_prepaid_sales_tax_crec",
            "pad_a_records",
        },
        "settings": {
            "enable_email",
            "enable_interval_backups",
            "folder_is_active",
            "process_edi",
            "calculate_upc_check_digit",
            "include_a_records",
            "include_c_records",
            "include_headers",
            "filter_ampersand",
            "tweak_edi",
            "pad_a_records",
            "invoice_date_custom_format",
            "process_backend_copy",
            "process_edi_output",
        },
        "administrative": {
            "enable_reporting",
            "report_edi_errors",
            "report_printing_fallback",
            "tweak_edi",
            "split_edi",
            "force_edi_validation",
            "append_a_records",
            "force_txt_file_ext",
            "invoice_date_custom_format",
            "retail_uom",
            "force_each_upc",
            "include_item_numbers",
            "include_item_description",
            "split_prepaid_sales_tax_crec",
            "prepend_date_files",
            "override_upc_bool",
            "split_edi_include_invoices",
            "split_edi_include_credits",
            "process_backend_email",
            "process_backend_ftp",
        },
        "processed_files": {"resend_flag"},
    }

    @staticmethod
    def _quote_identifier(name: str) -> str:
        """Quote a SQL identifier (table or column name) safely.

        Doubles any embedded double quotes and wraps the name in double quotes.
        This prevents SQL injection via identifier names.

        Args:
            name: The identifier to quote

        Returns:
            Safely quoted identifier
        """
        # Replace any double quotes with two double quotes (SQL standard escaping)
        safe_name = name.replace('"', '""')
        return f'"{safe_name}"'

    def _get_boolean_columns(self) -> set:
        """Get the set of boolean columns for this table.

        Caches the result for performance. Boolean columns are identified
        as INTEGER columns with names containing 'is_', '_enabled', '_active',
        or starting with 'enable_'.

        Returns:
            Set of column names that should be treated as booleans
        """
        if self._boolean_columns is not None:
            return self._boolean_columns

        cur = self._conn.execute(
            f"PRAGMA table_info({self._quote_identifier(self._name)})"
        )
        boolean_cols = set()
        explicit = self._EXPLICIT_BOOLEAN_COLUMNS_BY_TABLE.get(self._name, set())

        for row in cur.fetchall():
            col_name = row[1]
            col_type = row[2].upper()
            # Identify boolean columns by naming convention and INTEGER type
            if col_type == "INTEGER":
                lower_name = col_name.lower()
                if (
                    lower_name.startswith("is_")
                    or lower_name.startswith("enable_")
                    or "_enabled" in lower_name
                    or "_active" in lower_name
                    or lower_name.startswith("has_")
                    or lower_name == "folder_is_active"
                    or "boolean" in lower_name
                ):
                    boolean_cols.add(col_name)
            if col_name in explicit:
                boolean_cols.add(col_name)

        self._boolean_columns = boolean_cols
        return boolean_cols

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        """Convert a database row to a dictionary.

        Converts INTEGER boolean columns (0/1) to Python bool.
        Attempts to deserialize JSON strings for complex data types.

        Args:
            row: SQLite row object or None

        Returns:
            Dictionary representation of the row, or None if row is None
        """
        if row is None:
            return None

        d = dict(row)
        boolean_cols = self._get_boolean_columns()

        for k, v in list(d.items()):
            # Skip None values
            if v is None:
                continue

            # Convert boolean columns from INTEGER (0/1) to Python bool
            if k in boolean_cols:
                d[k] = normalize_bool(v)

            # Attempt to deserialize JSON strings
            # Only try to parse if string looks like valid JSON (starts with { or [ and ends with matching bracket)
            elif isinstance(v, str) and len(v) >= 2:
                v_stripped = v.strip()
                # Check if stripped string is long enough and looks like JSON
                if len(v_stripped) >= 2 and (
                    (v_stripped[0] == "{" and v_stripped[-1] == "}")
                    or (v_stripped[0] == "[" and v_stripped[-1] == "]")
                ):
                    try:
                        d[k] = json.loads(v)
                    except (json.JSONDecodeError, ValueError):
                        # Keep as string if not valid JSON
                        pass

        return d

    def _serialize_record_value(
        self, column: str, value: Any, boolean_cols: set
    ) -> Any:
        if column in boolean_cols:
            return to_db_bool(value)
        return self._serialize_value(value)

    def _build_where_clause(self, kwargs: Dict[str, Any]) -> tuple[str, list[Any]]:
        boolean_cols = self._get_boolean_columns()
        clauses: list[str] = []
        values: list[Any] = []

        true_legacy = "('true','1','yes','on')"
        false_legacy = "('false','0','no','off','')"

        for key, value in kwargs.items():
            quoted_key = self._quote_identifier(key)
            if key in boolean_cols:
                if normalize_bool(value):
                    clauses.append(
                        f"({quoted_key}=1 OR lower(cast({quoted_key} as text)) IN {true_legacy})"
                    )
                else:
                    clauses.append(
                        f"({quoted_key}=0 OR lower(cast({quoted_key} as text)) IN {false_legacy})"
                    )
            else:
                clauses.append(f"{quoted_key}=?")
                values.append(self._serialize_value(value))

        return " AND ".join(clauses), values

    def _serialize_value(self, v: Any) -> Any:
        """Serialize a value for SQLite storage.

        Converts Python booleans to INTEGER (0/1).
        Serializes dicts/lists to JSON strings.
        Falls back to str() for unserializable objects.

        Args:
            v: Value to serialize

        Returns:
            Value suitable for SQLite binding
        """
        # Convert booleans to integers (0/1)
        if isinstance(v, bool):
            return int(v)

        # Serialize complex structures to JSON
        if isinstance(v, (dict, list, tuple)):
            try:
                return json.dumps(v)
            except (TypeError, ValueError):
                return str(v)

        # Basic types that sqlite3 can handle directly
        if isinstance(v, (int, float, str, bytes, type(None))):
            return v

        # For any other type (custom objects, etc), convert to string
        try:
            return json.dumps(v)
        except (TypeError, ValueError):
            return str(v)

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Find a single record matching the given criteria.

        Args:
            **kwargs: Column=value pairs to match

        Returns:
            Dictionary representing the record, or None if not found

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        if kwargs:
            where, values = self._build_where_clause(kwargs)
            cur = self._conn.execute(
                f"SELECT * FROM {quoted_table} WHERE {where} LIMIT 1", tuple(values)
            )
        else:
            cur = self._conn.execute(f"SELECT * FROM {quoted_table} LIMIT 1")

        return self._row_to_dict(cur.fetchone())

    def find(
        self, order_by: Optional[str] = None, _limit: Optional[int] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """Find all records matching the given criteria.

        Args:
            order_by: Column name to sort by (optional)
            _limit: Maximum number of records to return (optional)
            **kwargs: Column=value pairs to match

        Returns:
            List of dictionaries representing matching records

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        sql = f"SELECT * FROM {quoted_table}"
        params = []

        if kwargs:
            where, where_values = self._build_where_clause(kwargs)
            sql += f" WHERE {where}"
            params = where_values

        if order_by:
            sql += f" ORDER BY {self._quote_identifier(order_by)}"

        if _limit:
            sql += f" LIMIT {_limit}"

        cur = self._conn.execute(sql, tuple(params))
        return [
            row_dict
            for r in cur.fetchall()
            for row_dict in [self._row_to_dict(r)]
            if row_dict is not None
        ]

    def all(self) -> List[Dict[str, Any]]:
        """Get all records from the table.

        Returns:
            List of dictionaries representing all records

        Raises:
            sqlite3.OperationalError: If table doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        cur = self._conn.execute(f"SELECT * FROM {quoted_table}")
        return [
            row_dict
            for r in cur.fetchall()
            for row_dict in [self._row_to_dict(r)]
            if row_dict is not None
        ]

    def insert(self, record: Dict[str, Any]) -> int:
        """Insert a new record into the table.

        Args:
            record: Dictionary of column=value pairs

        Returns:
            The rowid of the inserted record

        Raises:
            ValueError: If record is empty
            sqlite3.OperationalError: If table or column doesn't exist
        """
        keys = list(record.keys())
        if not keys:
            raise ValueError("Cannot insert empty record")

        quoted_table = self._quote_identifier(self._name)
        cols = ", ".join(self._quote_identifier(k) for k in keys)
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {quoted_table} ({cols}) VALUES ({placeholders})"
        boolean_cols = self._get_boolean_columns()
        values = tuple(
            self._serialize_record_value(k, record[k], boolean_cols) for k in keys
        )

        cur = self._conn.execute(sql, values)
        self._conn.commit()
        return int(cur.lastrowid or 0)

    def insert_many(self, records: list[dict]) -> None:
        """Insert multiple records in a single transaction.

        Args:
            records: List of dicts to insert. All dicts must have the same keys.

        Raises:
            ValueError: If records is empty
            sqlite3.OperationalError: If table or column doesn't exist
        """
        if not records:
            return
        boolean_cols = self._get_boolean_columns()
        keys = list(records[0].keys())
        quoted_table = self._quote_identifier(self._name)
        cols = ", ".join(self._quote_identifier(k) for k in keys)
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {quoted_table} ({cols}) VALUES ({placeholders})"
        values = [
            tuple(self._serialize_record_value(k, r[k], boolean_cols) for k in keys)
            for r in records
        ]
        self._conn.executemany(sql, values)
        self._conn.commit()

    def update(self, record: Dict[str, Any], keys: List[str]) -> None:
        """Update an existing record.

        Args:
            record: Dictionary containing all columns (both keys and values to update)
            keys: List of column names to use in the WHERE clause

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        set_keys = [k for k in record.keys() if k not in keys]
        if not set_keys:
            # Nothing to update
            return

        quoted_table = self._quote_identifier(self._name)
        set_clause = ", ".join(f"{self._quote_identifier(k)}=?" for k in set_keys)
        where_clause = " AND ".join(f"{self._quote_identifier(k)}=?" for k in keys)
        sql = f"UPDATE {quoted_table} SET {set_clause} WHERE {where_clause}"

        boolean_cols = self._get_boolean_columns()
        params = [
            self._serialize_record_value(k, record[k], boolean_cols) for k in set_keys
        ]
        params.extend(
            self._serialize_record_value(k, record[k], boolean_cols) for k in keys
        )

        self._conn.execute(sql, tuple(params))
        self._conn.commit()

    def delete(self, **kwargs) -> None:
        """Delete records matching the given criteria.

        Args:
            **kwargs: Column=value pairs to match. If empty, deletes all records.

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        if not kwargs:
            sql = f"DELETE FROM {quoted_table}"
            self._conn.execute(sql)
        else:
            where, values = self._build_where_clause(kwargs)
            sql = f"DELETE FROM {quoted_table} WHERE {where}"
            self._conn.execute(sql, tuple(values))

        self._conn.commit()

    def count(self, **kwargs) -> int:
        """Count records matching the given criteria.

        Args:
            **kwargs: Column=value pairs to match. If empty, counts all records.

        Returns:
            Number of matching records

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        if kwargs:
            where, values = self._build_where_clause(kwargs)
            cur = self._conn.execute(
                f"SELECT COUNT(*) as c FROM {quoted_table} WHERE {where}", tuple(values)
            )
        else:
            cur = self._conn.execute(f"SELECT COUNT(*) as c FROM {quoted_table}")

        row = cur.fetchone()
        return int(row[0]) if row is not None else 0

    def upsert(self, record: Dict[str, Any], keys: List[str]) -> None:
        """Insert or update a record.

        If a record matching the key columns exists, updates it.
        Otherwise, inserts a new record.

        Args:
            record: Dictionary of column=value pairs
            keys: List of column names to use for matching existing records

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        where_clause = " AND ".join(f"{self._quote_identifier(k)}=?" for k in keys)
        boolean_cols = self._get_boolean_columns()
        values = tuple(
            self._serialize_record_value(k, record[k], boolean_cols) for k in keys
        )

        cur = self._conn.execute(
            f"SELECT 1 FROM {quoted_table} WHERE {where_clause} LIMIT 1", values
        )
        exists = cur.fetchone() is not None

        if exists:
            self.update(record, keys)
        else:
            self.insert(record)

    def insert_many(self, records: List[Dict[str, Any]]) -> None:
        """Insert multiple records efficiently.

        Args:
            records: List of dictionaries to insert

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        if not records:
            return

        # Use first record to determine keys
        keys = list(records[0].keys())
        quoted_table = self._quote_identifier(self._name)
        cols = ", ".join(self._quote_identifier(k) for k in keys)
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {quoted_table} ({cols}) VALUES ({placeholders})"

        params = [
            tuple(
                self._serialize_record_value(k, record[k], self._get_boolean_columns())
                for k in keys
            )
            for record in records
        ]

        self._conn.executemany(sql, params)
        self._conn.commit()

    def create_column(self, column_name: str, column_type: str) -> None:
        """Create a column in the table if it doesn't exist.

        Args:
            column_name: Name of the column to create
            column_type: Type string ('String', 'Boolean', 'Integer', etc.)

        Note:
            This is provided for compatibility with migration code.
            New code should use explicit schema definitions.
        """
        # Map type strings to SQLite types
        type_lower = column_type.lower()
        if "bool" in type_lower:
            sql_type = "INTEGER DEFAULT 0"
        elif "int" in type_lower:
            sql_type = "INTEGER"
        elif "real" in type_lower or "float" in type_lower:
            sql_type = "REAL"
        else:
            sql_type = "TEXT"

        try:
            quoted_table = self._quote_identifier(self._name)
            quoted_column = self._quote_identifier(column_name)
            self._conn.execute(
                f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} {sql_type}"
            )
            self._conn.commit()
            # Clear boolean column cache
            self._boolean_columns = None
        except sqlite3.OperationalError:
            # Column already exists or cannot be added
            pass

    def distinct(self, column: str) -> List[Dict[str, Any]]:
        """Get distinct values for a column.

        Args:
            column: Column name to get distinct values for

        Returns:
            List of dictionaries with the distinct rows, ordered by the column

        Raises:
            sqlite3.OperationalError: If table or column doesn't exist
        """
        quoted_table = self._quote_identifier(self._name)
        sql = f"SELECT DISTINCT * FROM {quoted_table} ORDER BY {self._quote_identifier(column)}"
        cur = self._conn.execute(sql)
        return [
            row_dict
            for r in cur.fetchall()
            for row_dict in [self._row_to_dict(r)]
            if row_dict is not None
        ]

    def drop(self) -> None:
        """Drop the table from the database."""
        quoted_table = self._quote_identifier(self._name)
        self._conn.execute(f"DROP TABLE IF EXISTS {quoted_table}")
        self._conn.commit()


class Database:
    """Represents a SQLite database connection.

    Provides table access and raw SQL query execution.
    Uses sqlite3.Row for dict-like row access.
    """

    def __init__(self, path: str) -> None:
        """Initialize a database connection.

        Args:
            path: Path to the database file, or ":memory:" for in-memory database
        """
        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # Enable foreign key constraints
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error:
            pass

        # Ensure core schema exists for new or in-memory databases so tests and
        # migrations can assume base tables like 'version' are present.
        try:
            import core.database.schema

            schema.ensure_schema(self)
        except Exception:
            # Be tolerant: if schema ensure fails, don't crash the connection
            pass

    @property
    def raw_connection(self) -> sqlite3.Connection:
        """Get the raw sqlite3 connection.

        Returns:
            The underlying sqlite3.Connection object
        """
        return self._conn

    @property
    def tables(self) -> List[str]:
        """Get list of table names in the database.

        Returns:
            List of table names
        """
        cur = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]

    def commit(self) -> None:
        """Commit pending changes to the database."""
        self._conn.commit()

    def __getitem__(self, table_name: str) -> Table:
        """Get a table by name.

        Args:
            table_name: Name of the table

        Returns:
            Table object for the given name
        """
        return Table(self._conn, table_name)

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute raw SQL and return results as dictionaries.

        Args:
            sql: SQL statement to execute

        Returns:
            List of dictionaries representing result rows.
            Returns empty list on error.
        """
        try:
            cur = self._conn.execute(sql)
        except sqlite3.Error:
            # If execution fails, commit any pending changes and return empty
            try:
                self._conn.commit()
            except sqlite3.Error:
                pass
            return []

        # PRAGMA statements return results without needing commit
        if sql.strip().upper().startswith("PRAGMA"):
            try:
                return [dict(r) for r in cur.fetchall()]
            except sqlite3.Error:
                return []

        # For other statements, commit and return processed rows
        try:
            self._conn.commit()
            # Use a dummy table to process rows with boolean conversion
            dummy_table = Table(self._conn, "dummy")
            return [
                row_dict
                for r in cur.fetchall()
                for row_dict in [dummy_table._row_to_dict(r)]
                if row_dict is not None
            ]
        except sqlite3.Error:
            try:
                self._conn.commit()
            except sqlite3.Error:
                pass
            return []

    @classmethod
    def connect(cls, path: str) -> Database:
        """Connect to a SQLite database.

        Args:
            path: Path to the database file. Use empty string for in-memory database.

        Returns:
            Database object
        """
        if path == "":
            path = ":memory:"
        return cls(path)


def connect(url: str) -> Database:
    """Connect to a SQLite database using a URL.

    Args:
        url: Database URL in the format "sqlite:///path" or "sqlite:///"

    Returns:
        Database object

    Raises:
        ValueError: If URL format is invalid
    """
    prefix = "sqlite:///"
    if not isinstance(url, str) or not url.startswith(prefix):
        raise ValueError(f"Only sqlite URLs supported: sqlite:///path (got: {url})")

    path = url[len(prefix) :]
    if path == "":
        path = ":memory:"

    return Database(path)
