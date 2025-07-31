import pytest
from unittest.mock import MagicMock
import tkinter
import interface

@pytest.fixture
def dummy_db(monkeypatch):
    class DummyTable:
        def find_one(self, **kwargs):
            return {
                "enable_email": True,
                "as400_address": "addr",
                "as400_username": "user",
                "as400_password": "pw",
                "email_address": "a@b.com",
                "email_username": "u",
                "email_password": "p",
                "email_smtp_server": "smtp",
                "smtp_port": "25",
                "odbc_driver": "driver",
                "enable_interval_backups": False,
                "backup_counter_maximum": 1,
            }
        def count(self, **kwargs):
            return 0
        def update(self, obj, keys):
            pass
        def find(self, **kwargs):
            return []
    class DummyFoldersTable(DummyTable):
        pass
    class DummySettingsTable(DummyTable):
        pass
    class DummyDB:
        def __getitem__(self, key):
            return DummyTable()
        settings = DummySettingsTable()
        folders_table = DummyFoldersTable()
    dummy_db = DummyDB()
    monkeypatch.setattr(interface, "database_obj_instance", dummy_db)
    return dummy_db

@pytest.fixture
def dummy_dialog(monkeypatch):
    class DummyDialogBase:
        def __init__(self, *a, **k): pass
        def resizable(self, *a, **k): pass
        def title(self, *a, **k): pass
        def withdraw(self): pass
        def update_idletasks(self): pass
        def cancel(self): pass
        def focus_set(self): pass
    monkeypatch.setattr(interface.dialog, "Dialog", DummyDialogBase)
    return DummyDialogBase

@pytest.fixture
def dummy_tk(monkeypatch):
    # Patch all tkinter/ttk widgets to MagicMock
    widget_names = [
        "Tk", "Label", "Checkbutton", "Entry", "Spinbox", "Button", "Frame", "OptionMenu", "Separator", "Scrollbar", "Listbox", "BooleanVar", "StringVar", "IntVar"
    ]
    for name in widget_names:
        if hasattr(tkinter, name):
            monkeypatch.setattr(tkinter, name, MagicMock)
    import tkinter.ttk as ttk
    for name in widget_names:
        if hasattr(ttk, name):
            monkeypatch.setattr(ttk, name, MagicMock)
    return MagicMock

@pytest.fixture
def dummy_extras(monkeypatch):
    monkeypatch.setattr(interface.tk_extra_widgets, "RightClickMenu", MagicMock)
    monkeypatch.setattr(interface.doingstuffoverlay, "make_overlay", MagicMock)
    monkeypatch.setattr(interface.doingstuffoverlay, "destroy_overlay", MagicMock)
    monkeypatch.setattr(interface, "validate_email", lambda x: True)
    monkeypatch.setattr(interface, "update_reporting", MagicMock())
    monkeypatch.setattr(interface, "refresh_users_list", MagicMock())
    return True

def test_editsettingsdialog_instantiation(dummy_db, dummy_dialog, dummy_tk, dummy_extras, monkeypatch):
    foldersnameinput = {
        "logs_directory": "/tmp",
        "enable_reporting": "True",
        "report_email_destination": "a@b.com",
        "report_printing_fallback": False,
        "report_edi_errors": False,
    }
    dialog = interface.EditSettingsDialog(foldersnameinput)
    assert dialog is not None

def test_editdialog_instantiation(dummy_db, dummy_dialog, dummy_tk, dummy_extras, monkeypatch):
    foldersnameinput = {
        "copy_to_directory": "/tmp",
        "folder_name": "test",
        "convert_to_format": "csv",
    }
    # Simulate a master/root window
    master = MagicMock()
    dialog = interface.EditDialog(master, foldersnameinput)
    assert dialog is not None
