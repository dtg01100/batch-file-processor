import unittest
import importlib
import pytest
from unittest.mock import MagicMock, patch
from interface import DatabaseObj

class TestInterface(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module('interface')

    def test_import(self):
        # Just test that the module imports without error
        try:
            importlib.reload(self.module)
        except Exception as e:
            self.fail(f"interface import failed: {e}")

class DummyDB:
    def __init__(self):
        self.tables = {}
    def __getitem__(self, key):
        return self.tables.setdefault(key, DummyTable())

class DummyTable:
    def find_one(self, **kwargs):
        return {"version": 32, "os": "Linux"}
    def count(self, **kwargs):
        return 0
    def update(self, obj, keys):
        pass
    def find(self, **kwargs):
        return []

def test_databaseobj_init_creates_db(tmp_path):
    fake_path = tmp_path / "fake.db"
    called = {}
    def fake_os_path_exists(path):
        return False
    def fake_tk_Tk():
        called["tk"] = True
        class DummyTk:
            def destroy(self): pass
            def update(self): pass
        return DummyTk()
    def fake_ttk_Label(*a, **k):
        class Dummy:
            def pack(self): pass
        return Dummy()
    def fake_open_file(*a, **k):
        class Dummy:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def write(self, x): pass
        return Dummy()
    def fake_now():
        return "now"
    DatabaseObj(
        str(fake_path),
        os_path_exists=fake_os_path_exists,
        tk_Tk=fake_tk_Tk,
        ttk_Label=fake_ttk_Label,
        open_file=fake_open_file,
        now=fake_now,
        showerror=lambda *a, **k: None,
        askokcancel=lambda *a, **k: True,
        askdirectory=lambda *a, **k: "",
        smtplib_SMTP=lambda *a, **k: MagicMock(),
        running_platform="Linux",
        config_folder="/tmp",
        database_version="32",
        version="v",
    )
    assert called["tk"]

def test_databaseobj_reload(tmp_path):
    fake_path = tmp_path / "fake2.db"
    dummy_db = DummyDB()
    dummy_db.tables["version"] = DummyTable()
    dummy_db.tables["folders"] = DummyTable()
    dummy_db.tables["emails_to_send"] = DummyTable()
    dummy_db.tables["working_batch_emails_to_send"] = DummyTable()
    dummy_db.tables["sent_emails_removal_queue"] = DummyTable()
    dummy_db.tables["administrative"] = DummyTable()
    dummy_db.tables["processed_files"] = DummyTable()
    dummy_db.tables["settings"] = DummyTable()
    with patch("interface.dataset.connect", return_value=dummy_db):
        obj = DatabaseObj(
            str(fake_path),
            os_path_exists=lambda x: True,
            tk_Tk=lambda: MagicMock(),
            ttk_Label=lambda *a, **k: MagicMock(),
            open_file=lambda *a, **k: MagicMock(__enter__=lambda s: s, __exit__=lambda s, *a: None, write=lambda s, x: None),
            now=lambda: "now",
            showerror=lambda *a, **k: None,
            askokcancel=lambda *a, **k: True,
            askdirectory=lambda *a, **k: "",
            smtplib_SMTP=lambda *a, **k: MagicMock(),
            running_platform="Linux",
            config_folder="/tmp",
            database_version="32",
            version="v",
        )
        obj.reload(str(fake_path))
        assert hasattr(obj, "folders_table")
        assert hasattr(obj, "emails_table")
        assert hasattr(obj, "settings")

if __name__ == '__main__':
    unittest.main()
