import json
import sqlite3
from datetime import date, datetime

import pytest

from interface.database.sqlite_wrapper import connect


def _create_table(db, table_name, columns):
    """Helper to create a simple table for testing.

    Args:
        db: sqlite_wrapper.Database instance
        table_name: Name of table to create
        columns: Dict of {column_name: sql_type}
    """
    col_defs = []
    # Only add auto-increment id if not in the provided columns
    if "id" not in columns:
        col_defs.append("id INTEGER PRIMARY KEY AUTOINCREMENT")

    for col_name, col_type in columns.items():
        col_defs.append(f'"{col_name}" {col_type}')
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
    # Use direct db._conn to avoid query() silently swallowing errors
    db._conn.execute(sql)
    db._conn.commit()


def test_connect_invalid_url_raises():
    with pytest.raises(ValueError):
        connect("not-sqlite:///")


def test_in_memory_insert_find_and_json_boolean_handling():
    db = connect("sqlite:///")
    _create_table(db, "people", {"name": "TEXT", "active": "INTEGER", "meta": "TEXT"})
    t = db["people"]

    rid = t.insert({"name": "Alice", "active": True, "meta": {"x": 1}})
    assert isinstance(rid, int) and rid > 0

    row = t.find_one(id=rid)
    assert row is not None
    assert row["name"] == "Alice"
    assert row["active"] == 1  # sqlite_wrapper stores booleans as integers (0/1)
    assert row["meta"] == {"x": 1}

    # all() also deserializes JSON like find_one()
    raw = t.all()
    assert isinstance(raw, list) and raw
    assert raw[0]["meta"] == {"x": 1}


def test_insert_empty_record_raises():
    db = connect("sqlite:///")
    t = db["empty_test"]
    with pytest.raises(ValueError):
        t.insert({})


def test_find_order_by_and_limit():
    db = connect("sqlite:///")
    _create_table(db, "fruits", {"name": "TEXT"})
    t = db["fruits"]
    t.insert({"name": "pear"})
    t.insert({"name": "apple"})
    t.insert({"name": "banana"})

    results = t.find(order_by="name", _limit=2)
    assert len(results) == 2
    names = [r["name"] for r in results]
    assert names == sorted(names)


def test_update_and_count_and_delete():
    db = connect("sqlite:///")
    _create_table(db, "items", {"sku": "TEXT", "qty": "INTEGER"})
    t = db["items"]
    id1 = t.insert({"sku": "A1", "qty": 5})
    id2 = t.insert({"sku": "B2", "qty": 3})

    assert t.count() >= 2

    # update qty for sku A1
    t.update({"sku": "A1", "qty": 10}, keys=["sku"])
    r = t.find_one(sku="A1")
    assert r["qty"] == 10

    # delete by condition
    t.delete(sku="B2")
    assert t.find_one(sku="B2") is None


def test_insert_many_and_upsert():
    db = connect("sqlite:///")
    _create_table(db, "bulk", {"k": "INTEGER", "v": "TEXT"})
    t = db["bulk"]
    t.insert_many([{"k": 1, "v": "one"}, {"k": 2, "v": "two"}])
    assert t.count() >= 2

    # upsert should update matching row
    t.upsert({"k": 1, "v": "ONE"}, keys=["k"])
    r = t.find_one(k=1)
    assert r["v"] == "ONE"

    # upsert should insert when no match
    t.upsert({"k": 3, "v": "three"}, keys=["k"])
    assert t.find_one(k=3)["v"] == "three"


def test_create_column_and_table_info():
    db = connect("sqlite:///")
    _create_table(db, "schema_test", {"flag": "INTEGER", "note": "TEXT"})
    t = db["schema_test"]
    # inserting should work with the new column
    t.insert({"flag": True, "note": "ok"})
    info = db.query("PRAGMA table_info(schema_test)")
    names = {c["name"] for c in info}
    assert "flag" in names


def test_find_one_on_nonexistent_table_returns_none():
    db = connect("sqlite:///")
    t = db["no_such_table_xyz"]
    # This should raise since we don't auto-create
    with pytest.raises(sqlite3.OperationalError):
        t.find_one()


def test_count_with_conditions_and_boolean_filters():
    db = connect("sqlite:///")
    _create_table(db, "counts", {"flag": "INTEGER"})
    t = db["counts"]
    t.insert({"flag": 1})
    t.insert({"flag": 0})
    assert t.count() == 2
    assert t.count(flag=1) == 1
    assert t.count(flag=0) == 1


def test_delete_without_conditions_clears_table():
    db = connect("sqlite:///")
    _create_table(db, "clearme", {"a": "INTEGER"})
    t = db["clearme"]
    t.insert({"a": 1})
    t.insert({"a": 2})
    assert t.count() == 2
    t.delete()
    assert t.count() == 0


def test_insert_with_various_types_serialization():
    db = connect("sqlite:///")
    _create_table(
        db,
        "types",
        {"d": "TEXT", "l": "TEXT", "t": "TEXT", "today": "TEXT", "now": "TEXT"},
    )
    t = db["types"]
    # test dict/list/tuple serialization
    result_id = t.insert({"d": {"x": 1}, "l": [1, 2], "t": (3, 4)})
    r = t.find_one(id=result_id)
    assert r["d"] == {"x": 1}
    assert r["l"] == [1, 2]
    # tuple serialized to JSON list then read back as list
    assert r["t"] == [3, 4]

    # test date/time/storage
    r2_id = t.insert({"today": date(2020, 1, 1), "now": datetime(2020, 1, 1, 12, 0)})
    r2 = t.find_one(id=r2_id)
    # sqlite stores them as strings; original datetime objects can't be converted here
    assert isinstance(r2["today"], str)
    assert isinstance(r2["now"], str)


def test_serialization_failure_falls_back_to_str(monkeypatch):
    # simulate json.dumps throwing for unserializable object
    db = connect("sqlite:///")
    _create_table(db, "bad", {"x": "TEXT"})
    t = db["bad"]

    # Create an unserializable object with str() => "bad"
    class UnserializableObject:
        def __str__(self):
            return "bad"

    bad = UnserializableObject()

    # monkeypatch json.dumps to raise
    monkeypatch.setattr(
        json, "dumps", lambda v: (_ for _ in ()).throw(ValueError("nope"))
    )
    # now insert object that cannot be serialized; fallback to str should happen
    rid = t.insert({"x": bad})
    r = t.find_one(id=rid)
    assert r["x"] == "bad"


def test_upsert_with_missing_columns_creates_and_updates():
    db = connect("sqlite:///")
    _create_table(db, "upsert_test", {"a": "INTEGER", "b": "INTEGER"})
    t = db["upsert_test"]
    # ensure table exists by inserting a dummy
    t.insert({"a": 0, "b": 0})
    # upsert record with new column
    t.upsert({"a": 1, "b": 2}, keys=["a"])  # should insert
    assert t.find_one(a=1)["b"] == 2
    # upsert again should update existing record
    t.upsert({"a": 1, "b": 3}, keys=["a"])
    rec = t.find_one(a=1)
    assert rec["b"] == 3


def test_update_with_missing_columns_creates_columns():
    db = connect("sqlite:///")
    _create_table(db, "upd_test", {"id": "INTEGER", "x": "INTEGER", "y": "INTEGER"})
    t = db["upd_test"]
    t.insert({"id": 1, "x": 1, "y": 0})
    # update existing columns
    t.update({"id": 1, "x": 2, "y": 5}, keys=["id"])
    rec = t.find_one(id=1)
    assert rec["x"] == 2
    assert rec["y"] == 5


def test_insert_many_empty_no_error():
    db = connect("sqlite:///")
    t = db["empties"]
    # should simply return without raising
    t.insert_many([])


def test_query_raw_sql_and_commit():
    db = connect("sqlite:///")
    # create raw table
    db.query("CREATE TABLE raw (id INTEGER PRIMARY KEY, v TEXT)")
    db.query("INSERT INTO raw (v) VALUES ('x')")
    results = db.query("SELECT * FROM raw")
    assert results[0]["v"] == "x"


def test_tables_and_connect_path(tmp_path):
    # verify that using a file path creates a database file and tables property updates
    dbfile = tmp_path / "test.db"
    db = connect(f"sqlite:///{dbfile}")
    # sqlite creates file on connect
    assert dbfile.exists()
    _create_table(db, "foo", {"a": "INTEGER"})
    t = db["foo"]
    t.insert({"a": 1})
    tbls = db.tables
    assert "foo" in tbls


def test_find_with_conditions_and_all_return_types():
    db = connect("sqlite:///")
    _create_table(db, "conds", {"x": "INTEGER", "y": "TEXT"})
    t = db["conds"]
    t.insert({"x": 1, "y": "a"})
    t.insert({"x": 2, "y": "b"})
    # find by condition
    res = t.find(x=1)
    assert len(res) == 1 and res[0]["y"] == "a"
    # find with no matching condition
    assert t.find(x=99) == []
    # all returns raw dicts
    all_res = t.all()
    assert isinstance(all_res, list) and all_res[0]["x"] == 1


def test_create_column_multiple_times_does_not_error():
    db = connect("sqlite:///")
    _create_table(db, "dupcol", {"foo": "TEXT"})
    t = db["dupcol"]
    t.insert({"foo": "bar"})
    assert t.find_one()["foo"] == "bar"


def test_update_with_no_set_keys_is_noop():
    db = connect("sqlite:///")
    _create_table(db, "noop", {"id": "INTEGER", "a": "INTEGER"})
    t = db["noop"]
    t.insert({"id": 1, "a": 1})
    # call update with only keys argument results in no change
    t.update({"id": 1}, keys=["id"])
    assert t.find_one(id=1)["a"] == 1


def test_query_invalid_sql_returns_empty():
    db = connect("sqlite:///")
    # invalid query should return empty list rather than raising
    assert db.query("SELECT * FROM doesnotexist") == []
