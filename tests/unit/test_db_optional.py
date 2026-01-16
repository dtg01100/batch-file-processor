import pytest
from pathlib import Path

def test_is_db_available_returns_false_when_disabled(monkeypatch):
    import os
    from query_runner import is_db_available, PYODBC_AVAILABLE
    
    monkeypatch.setenv("BATCH_PROCESSOR_DB_ENABLED", "false")
    
    import importlib
    importlib.reload(importlib.import_module("query_runner"))
    
    from query_runner import is_db_available as check_db
    
    assert check_db() is False


def test_null_query_runner_returns_empty_results():
    from query_runner import NullQueryRunner
    
    runner = NullQueryRunner()
    results = runner.run_arbitrary_query("SELECT * FROM table")
    
    assert results == []


def test_inv_fetcher_handles_disabled_db(monkeypatch):
    import os
    monkeypatch.setenv("BATCH_PROCESSOR_DB_ENABLED", "false")
    
    from utils import invFetcher
    settings = {
        "as400_username": "test",
        "as400_password": "test",
        "as400_address": "test",
        "odbc_driver": "test"
    }
    fetcher = invFetcher(settings)
    
    assert fetcher.fetch_po(12345) == ""
    assert fetcher.fetch_cust_name(12345) == ""
    assert fetcher.fetch_cust_no(12345) == 0
    assert fetcher.fetch_uom_desc(12345, 1, 1, 999) == "N/A"
    
    monkeypatch.undo()
