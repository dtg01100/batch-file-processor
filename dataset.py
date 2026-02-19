"""Minimal shim to replace the external `dataset` dependency.

This provides a very small subset of the dataset API that the
application uses (connect -> Database, table access via __getitem__,
and table methods: find_one, find, all, insert, update, delete, count, upsert).

It uses the standard library sqlite3 under the hood and is intended
only to remove the hard dependency on the external `dataset` package
without requiring changes across the codebase.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional


class Table:
    def __init__(self, conn: sqlite3.Connection, name: str) -> None:
        self._conn = conn
        self._name = name

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        return dict(row) if row is not None else None

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        if kwargs:
            where = " AND ".join(f"{k}=?" for k in kwargs)
            cur = self._conn.execute(f"SELECT * FROM {self._name} WHERE {where} LIMIT 1", tuple(kwargs.values()))
        else:
            cur = self._conn.execute(f"SELECT * FROM {self._name} LIMIT 1")
        return self._row_to_dict(cur.fetchone())

    def find(self, **kwargs) -> List[Dict[str, Any]]:
        if kwargs:
            where = " AND ".join(f"{k}=?" for k in kwargs)
            cur = self._conn.execute(f"SELECT * FROM {self._name} WHERE {where}", tuple(kwargs.values()))
        else:
            cur = self._conn.execute(f"SELECT * FROM {self._name}")
        return [dict(r) for r in cur.fetchall()]

    def all(self) -> List[Dict[str, Any]]:
        cur = self._conn.execute(f"SELECT * FROM {self._name}")
        return [dict(r) for r in cur.fetchall()]

    def insert(self, record: Dict[str, Any]) -> int:
        keys = list(record.keys())
        if not keys:
            raise ValueError("Cannot insert empty record")
        cols = ", ".join(keys)
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {self._name} ({cols}) VALUES ({placeholders})"
        try:
            cur = self._conn.execute(sql, tuple(record[k] for k in keys))
            self._conn.commit()
            return cur.lastrowid
        except sqlite3.OperationalError as e:
            # If the table does not exist, attempt to create it with simple typing and retry
            if 'no such table' in str(e):
                cols_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
                for k in keys:
                    # Avoid adding duplicate id column if caller provided id
                    if k == "id":
                        continue
                    v = record.get(k)
                    # Choose SQL type based on Python value
                    if isinstance(v, bool):
                        sql_t = 'INTEGER'
                    elif isinstance(v, int):
                        sql_t = 'INTEGER'
                    elif isinstance(v, float):
                        sql_t = 'REAL'
                    else:
                        sql_t = 'TEXT'
                    cols_defs.append(f'"{k}" {sql_t}')
                create_sql = f"CREATE TABLE IF NOT EXISTS {self._name} ({', '.join(cols_defs)})"
                self._conn.execute(create_sql)
                self._conn.commit()
                # Retry the insert
                cur = self._conn.execute(sql, tuple(record[k] for k in keys))
                self._conn.commit()
                return cur.lastrowid
            raise

    def update(self, record: Dict[str, Any], keys: List[str]) -> None:
        set_keys = [k for k in record.keys() if k not in keys]
        if not set_keys:
            # Nothing to update
            return
        set_clause = ", ".join(f"{k}=?" for k in set_keys)
        where_clause = " AND ".join(f"{k}=?" for k in keys)
        sql = f"UPDATE {self._name} SET {set_clause} WHERE {where_clause}"
        params = [record[k] for k in set_keys] + [record[k] for k in keys]
        self._conn.execute(sql, tuple(params))
        self._conn.commit()

    def create_column(self, column_name: str, column_type: str) -> None:
        """Create a column in the table if it doesn't already exist.

        column_type is a Dataset-style type like 'String' or 'Boolean'.
        """
        # Map dataset types to SQLite types
        t = column_type.lower()
        if 'bool' in t:
            sql_type = 'INTEGER'
        else:
            sql_type = 'TEXT'
        try:
            self._conn.execute(f"ALTER TABLE {self._name} ADD COLUMN '{column_name}' {sql_type}")
            self._conn.commit()
        except sqlite3.OperationalError:
            # SQLite will raise if column already exists or cannot be added; ignore
            pass

    def delete(self, **kwargs) -> None:
        if not kwargs:
            sql = f"DELETE FROM {self._name}"
            self._conn.execute(sql)
        else:
            where = " AND ".join(f"{k}=?" for k in kwargs)
            sql = f"DELETE FROM {self._name} WHERE {where}"
            self._conn.execute(sql, tuple(kwargs.values()))
        self._conn.commit()

    def count(self, **kwargs) -> int:
        if kwargs:
            where = " AND ".join(f"{k}=?" for k in kwargs)
            cur = self._conn.execute(f"SELECT COUNT(*) as c FROM {self._name} WHERE {where}", tuple(kwargs.values()))
        else:
            cur = self._conn.execute(f"SELECT COUNT(*) as c FROM {self._name}")
        row = cur.fetchone()
        return int(row[0]) if row is not None else 0

    def upsert(self, record: Dict[str, Any], keys: List[str]) -> None:
        # If a matching row exists (by keys), update it; otherwise insert
        where_clause = " AND ".join(f"{k}=?" for k in keys)
        cur = self._conn.execute(f"SELECT 1 FROM {self._name} WHERE {where_clause} LIMIT 1", tuple(record[k] for k in keys))
        exists = cur.fetchone() is not None
        if exists:
            self.update(record, keys)
        else:
            self.insert(record)


class Database:
    def __init__(self, path: str) -> None:
        # Use a persistent file or in-memory database
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

    def __getitem__(self, table_name: str) -> Table:
        return Table(self._conn, table_name)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def query(self, sql: str):
        """Execute raw SQL and return rows as dict-like sqlite3.Row objects."""
        cur = self._conn.execute(sql)
        try:
            # Ensure changes are persisted for DDL/DML
            self._conn.commit()
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            try:
                self._conn.commit()
            except Exception:
                pass
            return []


def connect(url: str) -> Database:
    """Connect to a sqlite database using a url of the form "sqlite:///path".

    If the path part is empty ("sqlite:///"), an in-memory database is used.
    Only a very small subset of the real `dataset` connect behaviour is
    implemented because the repository uses only the basic operations.
    """
    prefix = "sqlite:///"
    if not isinstance(url, str) or not url.startswith(prefix):
        raise ValueError("Only sqlite URLs supported by this shim: sqlite:///path")
    path = url[len(prefix):]
    if path == "":
        path = ":memory:"
    return Database(path)
