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
import json


class Table:
    def __init__(self, conn: sqlite3.Connection, name: str) -> None:
        self._conn = conn
        self._name = name

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        d = dict(row)
        # Convert SQLite booleans (0/1 integers) to Python booleans
        for k, v in d.items():
            # Skip 'id' column to avoid incorrect boolean conversion
            if k == 'id':
                continue
            # Integers 0/1 are often used for booleans in this DB
            if isinstance(v, int) and (v == 0 or v == 1):
                d[k] = bool(v)
            # If a value is a JSON-serialized dict/list, deserialize it for callers
            elif isinstance(v, str) and v and (v[0] == '{' or v[0] == '['):
                try:
                    parsed = json.loads(v)
                    d[k] = parsed
                except Exception:
                    # leave as string if parsing fails
                    d[k] = v
        return d

    def _serialize_value(self, v: Any) -> Any:
        """Serialize values that sqlite3 cannot bind directly into supported types.

        - dict/list/tuple: JSON-serialize, falling back to str on failure
        - bool: convert to int
        - unsupported objects: convert to str so sqlite can bind them
        """
        # Convert booleans to ints for sqlite compatibility
        if isinstance(v, bool):
            return int(v)

        # Serialize complex structures into JSON
        if isinstance(v, (dict, list, tuple)):
            try:
                return json.dumps(v)
            except Exception:
                return str(v)

        # Common primitive types are fine
        if isinstance(v, (int, float, str)):
            return v

        # Fallback for any other type: use string representation
        try:
            return str(v)
        except Exception:
            # last resort, return original (may still fail)
            return v

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        try:
            if kwargs:
                where = " AND ".join(f"{k}=?" for k in kwargs)
                cur = self._conn.execute(f"SELECT * FROM {self._name} WHERE {where} LIMIT 1", tuple(kwargs.values()))
            else:
                cur = self._conn.execute(f"SELECT * FROM {self._name} LIMIT 1")
            return self._row_to_dict(cur.fetchone())
        except sqlite3.OperationalError as e:
            if 'no such table' in str(e):
                return None
            raise

    def find(self, **kwargs) -> List[Dict[str, Any]]:
        order_by = kwargs.pop('order_by', None)
        _limit = kwargs.pop('_limit', None)
        
        sql = f"SELECT * FROM {self._name}"
        params = []
        
        if kwargs:
            where = " AND ".join(f"{k}=?" for k in kwargs)
            sql += f" WHERE {where}"
            params = list(kwargs.values())
        
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        if _limit:
            sql += f" LIMIT {_limit}"
        
        cur = self._conn.execute(sql, tuple(params))
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def all(self) -> List[Dict[str, Any]]:
        cur = self._conn.execute(f"SELECT * FROM {self._name}")
        return [self._row_to_dict(r) for r in cur.fetchall()]

    def insert(self, record: Dict[str, Any]) -> int:
        keys = list(record.keys())
        if not keys:
            raise ValueError("Cannot insert empty record")
        cols = ", ".join(keys)
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {self._name} ({cols}) VALUES ({placeholders})"
        try:
            cur = self._conn.execute(sql, tuple(self._serialize_value(record[k]) for k in keys))
            self._conn.commit()
            return cur.lastrowid
        except sqlite3.OperationalError as e:
            msg = str(e)
            # If the table does not exist, attempt to create it with simple typing and retry
            if 'no such table' in msg:
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
                cur = self._conn.execute(sql, tuple(self._serialize_value(record[k]) for k in keys))
                self._conn.commit()
                return cur.lastrowid
            # Missing column(s) - attempt to add them and retry
            if 'has no column named' in msg or 'no such column' in msg:
                # determine existing columns
                cur = self._conn.execute(f"PRAGMA table_info({self._name})")
                existing = {r[1] for r in cur.fetchall()}
                for k in keys:
                    if k in existing:
                        continue
                    v = record.get(k)
                    if isinstance(v, bool):
                        sql_t = 'INTEGER'
                    elif isinstance(v, int):
                        sql_t = 'INTEGER'
                    elif isinstance(v, float):
                        sql_t = 'REAL'
                    else:
                        sql_t = 'TEXT'
                    try:
                        self._conn.execute(f"ALTER TABLE {self._name} ADD COLUMN '{k}' {sql_t}")
                    except sqlite3.OperationalError:
                        pass
                self._conn.commit()
                # Retry
                cur = self._conn.execute(sql, tuple(self._serialize_value(record[k]) for k in keys))
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
        params = [self._serialize_value(record[k]) for k in set_keys] + [self._serialize_value(record[k]) for k in keys]
        try:
            self._conn.execute(sql, tuple(params))
            self._conn.commit()
        except sqlite3.OperationalError as e:
            msg = str(e)
            if 'has no column named' in msg or 'no such column' in msg:
                # add missing columns based on record values
                cur = self._conn.execute(f"PRAGMA table_info({self._name})")
                existing = {r[1] for r in cur.fetchall()}
                for k in set_keys + keys:
                    if k in existing:
                        continue
                    v = record.get(k)
                    if isinstance(v, bool):
                        sql_t = 'INTEGER'
                    elif isinstance(v, int):
                        sql_t = 'INTEGER'
                    elif isinstance(v, float):
                        sql_t = 'REAL'
                    else:
                        sql_t = 'TEXT'
                    try:
                        self._conn.execute(f"ALTER TABLE {self._name} ADD COLUMN '{k}' {sql_t}")
                    except sqlite3.OperationalError:
                        pass
                self._conn.commit()
                # retry
                self._conn.execute(sql, tuple(params))
                self._conn.commit()
            else:
                raise

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

    def insert_many(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        # Use first record to determine keys
        keys = list(records[0].keys())
        cols = ", ".join(keys)
        placeholders = ", ".join("?" for _ in keys)
        sql = f"INSERT INTO {self._name} ({cols}) VALUES ({placeholders})"
        params = [tuple(self._serialize_value(record[k]) for k in keys) for record in records]
        try:
            self._conn.executemany(sql, params)
            self._conn.commit()
        except sqlite3.OperationalError as e:
            # If the table does not exist, attempt to create it with simple typing and retry
            if 'no such table' in str(e):
                cols_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
                for k in keys:
                    # Avoid adding duplicate id column if caller provided id
                    if k == "id":
                        continue
                    v = records[0].get(k)
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
                self._conn.executemany(sql, params)
                self._conn.commit()
            else:
                raise

    def upsert(self, record: Dict[str, Any], keys: List[str]) -> None:
        # If a matching row exists (by keys), update it; otherwise insert
        where_clause = " AND ".join(f"{k}=?" for k in keys)
        cur = self._conn.execute(f"SELECT 1 FROM {self._name} WHERE {where_clause} LIMIT 1", tuple(self._serialize_value(record[k]) for k in keys))
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

    @property
    def tables(self) -> List[str]:
        """Get list of table names in the database."""
        cur = self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cur.fetchall()]

    def commit(self) -> None:
        """Commit changes to the database."""
        self._conn.commit()

    def __getitem__(self, table_name: str) -> Table:
        return Table(self._conn, table_name)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def query(self, sql: str):
        """Execute raw SQL and return rows as dict-like sqlite3.Row objects.

        Any errors during execution or fetch are caught and an empty list is
        returned so callers need not wrap every call in try/except.
        """
        try:
            cur = self._conn.execute(sql)
        except sqlite3.DatabaseError:
            # If execution fails (e.g. missing table, syntax error), commit any
            # pending changes and return empty.
            try:
                self._conn.commit()
            except Exception:
                pass
            return []
        
        # Handle PRAGMA statements specially - they don't need commit and return raw dict
        if sql.strip().upper().startswith('PRAGMA'):
            try:
                return [dict(r) for r in cur.fetchall()]
            except Exception:
                return []
        
        try:
            # Ensure changes are persisted for DDL/DML and return processed rows
            self._conn.commit()
            return [Table(self._conn, 'dummy')._row_to_dict(r) for r in cur.fetchall()]
        except Exception:
            try:
                self._conn.commit()
            except Exception:
                pass
            return []
        try:
            self._conn.close()
        except Exception:
            pass

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
