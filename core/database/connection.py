"""
Framework-agnostic database connection using Python's sqlite3 module.

Provides Table and DatabaseConnection classes with the same API as the
Qt-based implementation but without any Qt dependency.
"""

import sqlite3
from typing import Any, Dict, List, Optional


class Table:
    """Dataset-like API wrapper over sqlite3 for a single table."""

    def __init__(self, connection: sqlite3.Connection, table_name: str):
        self._connection = connection
        self._table_name = table_name

    def _dict_to_where(self, **kwargs) -> tuple[str, List[Any]]:
        if not kwargs:
            return "", []
        conditions = []
        values = []
        for key, value in kwargs.items():
            conditions.append(f'"{key}" = ?')
            values.append(value)
        return " WHERE " + " AND ".join(conditions), values

    def _dict_to_set(self, data: Dict[str, Any]) -> tuple[str, str, List[Any]]:
        columns = [f'"{key}"' for key in data.keys()]
        placeholders = ["?"] * len(data)
        values = list(data.values())
        return ", ".join(columns), ", ".join(placeholders), values

    def find(self, order_by: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        where_clause, where_values = self._dict_to_where(**kwargs)
        order_clause = f' ORDER BY "{order_by}"' if order_by else ""
        sql = f'SELECT * FROM "{self._table_name}"{where_clause}{order_clause}'

        cursor = self._connection.execute(sql, where_values)
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        results = self.find(**kwargs)
        return results[0] if results else None

    def all(self) -> List[Dict[str, Any]]:
        return self.find()

    def insert(self, data: Dict[str, Any]) -> None:
        columns, placeholders, values = self._dict_to_set(data)
        sql = f'INSERT INTO "{self._table_name}" ({columns}) VALUES ({placeholders})'
        self._connection.execute(sql, values)
        self._connection.commit()

    def insert_many(self, records: List[Dict[str, Any]]) -> None:
        for record in records:
            self.insert(record)

    def update(self, data: Dict[str, Any], keys: List[str]) -> None:
        set_parts = []
        set_values = []
        where_parts = []
        where_values = []

        for key, value in data.items():
            if key in keys:
                where_parts.append(f'"{key}" = ?')
                where_values.append(value)
            else:
                set_parts.append(f'"{key}" = ?')
                set_values.append(value)

        if not set_parts:
            return

        set_clause = ", ".join(set_parts)
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"

        sql = f'UPDATE "{self._table_name}" SET {set_clause} WHERE {where_clause}'
        self._connection.execute(sql, set_values + where_values)
        self._connection.commit()

    def delete(self, **kwargs) -> None:
        where_clause, where_values = self._dict_to_where(**kwargs)
        if not where_clause:
            self._connection.execute(f'DELETE FROM "{self._table_name}"')
        else:
            self._connection.execute(
                f'DELETE FROM "{self._table_name}"{where_clause}', where_values
            )
        self._connection.commit()

    def drop(self) -> None:
        self._connection.execute(f'DROP TABLE IF EXISTS "{self._table_name}"')
        self._connection.commit()

    def count(self, **kwargs) -> int:
        where_clause, where_values = self._dict_to_where(**kwargs)
        sql = f'SELECT COUNT(*) FROM "{self._table_name}"{where_clause}'
        cursor = self._connection.execute(sql, where_values)
        return cursor.fetchone()[0]

    def distinct(self, column: str) -> List[Any]:
        sql = f'SELECT DISTINCT "{column}" FROM "{self._table_name}"'
        cursor = self._connection.execute(sql)
        return [row[0] for row in cursor.fetchall()]

    def create_column(self, column_name: str, column_type: Any) -> None:
        type_map = {
            "String": "TEXT",
            "Integer": "INTEGER",
            "Boolean": "INTEGER",
            "Float": "REAL",
        }
        type_str = str(column_type)
        if "'" in type_str:
            type_str = type_str.split("'")[1]
        sql_type = type_map.get(type_str, "TEXT")
        sql = f'ALTER TABLE "{self._table_name}" ADD COLUMN "{column_name}" {sql_type}'
        self._connection.execute(sql)
        self._connection.commit()

    def __iter__(self):
        return iter(self.all())


class DatabaseConnection:
    """Dataset-like wrapper providing table access via dict-style indexing."""

    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def __getitem__(self, table_name: str) -> Table:
        return Table(self._connection, table_name)

    def query(self, sql: str) -> None:
        self._connection.execute(sql)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def create_table(self, table_name: str) -> None:
        pass

    @property
    def raw_connection(self) -> sqlite3.Connection:
        return self._connection


def connect(database_path: str) -> DatabaseConnection:
    """Create a new database connection."""
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(connection)


def connect_memory() -> DatabaseConnection:
    """Create an in-memory database connection."""
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    return DatabaseConnection(connection)
