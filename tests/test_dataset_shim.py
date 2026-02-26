import pytest
import sqlite3
import json
from datetime import datetime, date

from dataset import connect


def test_connect_invalid_url_raises():
    with pytest.raises(ValueError):
        connect("not-sqlite:///")


def test_in_memory_insert_find_and_json_boolean_handling():
    db = connect("sqlite:///")
    t = db["people"]

    rid = t.insert({"name": "Alice", "active": True, "meta": {"x": 1}})
    assert isinstance(rid, int) and rid > 0

    row = t.find_one(id=rid)
    assert row is not None
    assert row["name"] == "Alice"
    assert isinstance(row["active"], bool) and row["active"] is True
    assert row["meta"] == {"x": 1}

    # all() returns raw sqlite values (JSON remains a string)
    raw = t.all()
    assert isinstance(raw, list) and raw
    assert isinstance(raw[0]["meta"], str)


def test_insert_empty_record_raises():
    db = connect("sqlite:///")
    t = db["empty_test"]
    with pytest.raises(ValueError):
        t.insert({})


def test_find_order_by_and_limit():
    db = connect("sqlite:///")
    t = db["fruits"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        # table may not exist yet; that's fine for the test
        pass
    t.insert({"name": "pear"})
    t.insert({"name": "apple"})
    t.insert({"name": "banana"})

    results = t.find(order_by="name", _limit=2)
    assert len(results) == 2
    names = [r["name"] for r in results]
    assert names == sorted(names)


def test_update_and_count_and_delete():
    db = connect("sqlite:///")
    t = db["items"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
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
    t = db["bulk"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
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
    t = db["schema_test"]
    # create a column on a table that may not exist yet
    t.create_column("flag", "Boolean")
    # inserting should work with the new column
    t.insert({"flag": True, "note": "ok"})
    info = db.query(f"PRAGMA table_info(schema_test)")
    names = {c["name"] for c in info}
    assert "flag" in names


def test_find_one_on_nonexistent_table_returns_none():
    db = connect("sqlite:///")
    t = db["no_such_table_xyz"]
    assert t.find_one() is None


def test_count_with_conditions_and_boolean_filters():
    db = connect("sqlite:///")
    t = db["counts"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
    t.insert({"flag": True})
    t.insert({"flag": False})
    assert t.count() == 2
    assert t.count(flag=True) == 1
    assert t.count(flag=False) == 1


def test_delete_without_conditions_clears_table():
    db = connect("sqlite:///")
    t = db["clearme"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
    t.insert({"a": 1})
    t.insert({"a": 2})
    assert t.count() == 2
    t.delete()
    assert t.count() == 0


def test_insert_with_various_types_serialization():
    db = connect("sqlite:///")
    t = db["types"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
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
    t = db["bad"]
    class Bad:
        def __str__(self):
            return "bad"
    bad = Bad()
    # ensure table exists first with a simple insert
    t.insert({"x": "init"})
    # monkeypatch json.dumps to raise
    monkeypatch.setattr(json, "dumps", lambda v: (_ for _ in ()).throw(ValueError("nope")))
    # now insert object that cannot be serialized; fallback to str should happen
    rid = t.insert({"x": bad})
    r = t.find_one(id=rid)
    assert r["x"] == "bad"


def test_upsert_with_missing_columns_creates_and_updates():
    db = connect("sqlite:///")
    t = db["upsert_test"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
    # ensure table exists by inserting a dummy
    t.insert({"a": 0, "b": 0})
    # upsert record with new column
    t.upsert({"a": 1, "b": 2}, keys=["a"])  # should insert
    assert t.find_one(a=1)["b"] == 2
    # upsert again with new column c should add column
    t.upsert({"a": 1, "b": 3, "c": 4}, keys=["a"])
    rec = t.find_one(a=1)
    assert rec["b"] == 3
    assert rec["c"] == 4


def test_update_with_missing_columns_creates_columns():
    db = connect("sqlite:///")
    t = db["upd_test"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
    t.insert({"id": 1, "x": 1})
    # update with new column y
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
    t = db["foo"]
    t.insert({"a": 1})
    tbls = db.tables
    assert "foo" in tbls


def test_find_with_conditions_and_all_return_types():
    db = connect("sqlite:///")
    t = db["conds"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
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
    t = db["dupcol"]
    t.create_column("foo", "String")
    t.create_column("foo", "String")  # should silently ignore
    t.insert({"foo": "bar"})
    assert t.find_one()["foo"] == "bar"


def test_update_with_no_set_keys_is_noop():
    db = connect("sqlite:///")
    t = db["noop"]
    try:
        t.delete()
    except sqlite3.OperationalError:
        pass
    t.insert({"id": 1, "a": 1})
    # call update with only keys argument results in no change
    t.update({"id": 1}, keys=["id"])
    assert t.find_one(id=1)["a"] == 1


def test_query_invalid_sql_returns_empty():
    db = connect("sqlite:///")
    # invalid query should return empty list rather than raising
    assert db.query("SELECT * FROM doesnotexist") == []
