import pytest
from unittest import mock
import builtins

# Patch all tkinter, dataset, and file operations for non-UI, non-database side effects
def make_databaseobj_patches():
    patches = [
        mock.patch('os.path.isfile', return_value=True),
        mock.patch('dataset.connect'),
        mock.patch('builtins.open', mock.mock_open()),
        mock.patch('tkinter.Tk'),
        mock.patch('tkinter.ttk.Label'),
        mock.patch('tkinter.ttk.Frame'),
        mock.patch('tkinter.ttk.Checkbutton'),
        mock.patch('tkinter.ttk.Entry'),
        mock.patch('tkinter.ttk.OptionMenu'),
        mock.patch('tkinter.ttk.Spinbox'),
        mock.patch('tkinter.ttk.Separator'),
        mock.patch('tkinter.ttk.Button'),
        mock.patch('tkinter.Listbox'),
        mock.patch('tkinter.Scrollbar'),
        mock.patch('tkinter.BooleanVar'),
        mock.patch('tkinter.StringVar'),
        mock.patch('tkinter.IntVar'),
        mock.patch('tkinter.messagebox.showerror'),
        mock.patch('tkinter.messagebox.showinfo'),
        mock.patch('tkinter.messagebox.askokcancel'),
        mock.patch('tkinter.messagebox.askyesno'),
        mock.patch('tkinter.filedialog.askdirectory'),
        mock.patch('tk_extra_widgets.RightClickMenu'),
    ]
    return patches

@pytest.mark.timeout(5)
def test_database_file_creation_success(monkeypatch):
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        # Simulate file does not exist, creation succeeds
        monkeypatch.setattr('os.path.isfile', lambda path: False)
        m_create = mock.Mock()
        monkeypatch.setattr('create_database.do', m_create)
        import interface
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        # Patch db_version
        class DummyTable:
            def find_one(self, id):
                return {'version': 1, 'os': 'linux'}
        dummy_db = {'version': DummyTable(), 'folders': {}, 'emails_to_send': {}, 'working_batch_emails_to_send': {}, 'sent_emails_removal_queue': {}, 'administrative': {}, 'processed_files': {}, 'settings': {}}
        monkeypatch.setattr(interface, 'dataset', mock.Mock(connect=mock.Mock(return_value=dummy_db)))
        # Should not raise
        interface.DatabaseObj('dummy.db')

@pytest.mark.timeout(5)
def test_database_file_creation_failure(monkeypatch):
    # Simulate file does not exist, creation fails
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        monkeypatch.setattr('os.path.isfile', lambda path: False)
        monkeypatch.setattr('create_database.do', mock.Mock(side_effect=Exception('fail')))
        import interface
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        # Patch error logging
        def open_fail(*a, **k):
            raise Exception('logfail')
        monkeypatch.setattr('builtins.open', open_fail)
        with pytest.raises(SystemExit):
            interface.DatabaseObj('dummy.db')

@pytest.mark.timeout(5)
def test_database_connection_failure(monkeypatch):
    # Simulate database connection fails
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        monkeypatch.setattr('os.path.isfile', lambda path: True)
        monkeypatch.setattr('dataset.connect', mock.Mock(side_effect=Exception('dbfail')))
        monkeypatch.setattr('builtins.open', mock.mock_open())
        import interface
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        with pytest.raises(SystemExit):
            interface.DatabaseObj('dummy.db')

@pytest.mark.timeout(5)
def test_database_version_upgrade(monkeypatch):
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        # Simulate version lower than required triggers upgrade
        monkeypatch.setattr('os.path.isfile', lambda path: True)
        class DummyTable:
            def find_one(self, id):
                return {'version': 0, 'os': 'linux'}
        dummy_db = {'version': DummyTable(), 'folders': {}, 'emails_to_send': {}, 'working_batch_emails_to_send': {}, 'sent_emails_removal_queue': {}, 'administrative': {}, 'processed_files': {}, 'settings': {}}
        monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
        m_backup = mock.Mock()
        m_upgrade = mock.Mock()
        monkeypatch.setattr('backup_increment.do_backup', m_backup)
        monkeypatch.setattr('folders_database_migrator.upgrade_database', m_upgrade)
        import interface
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        interface.DatabaseObj('dummy.db')
        assert m_backup.called
        assert m_upgrade.called

@pytest.mark.timeout(5)
def test_database_version_too_new(monkeypatch):
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        # Simulate version higher than supported triggers error
        monkeypatch.setattr('os.path.isfile', lambda path: True)
        class DummyTable:
            def find_one(self, id):
                return {'version': 2, 'os': 'linux'}
        dummy_db = {'version': DummyTable(), 'folders': {}, 'emails_to_send': {}, 'working_batch_emails_to_send': {}, 'sent_emails_removal_queue': {}, 'administrative': {}, 'processed_files': {}, 'settings': {}}
        monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
        import interface
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        with pytest.raises(SystemExit):
            interface.DatabaseObj('dummy.db')

@pytest.mark.timeout(5)
def test_database_os_mismatch(monkeypatch):
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        # Simulate OS mismatch triggers error
        monkeypatch.setattr('os.path.isfile', lambda path: True)
        class DummyTable:
            def find_one(self, id):
                return {'version': 1, 'os': 'windows'}
        dummy_db = {'version': DummyTable(), 'folders': {}, 'emails_to_send': {}, 'working_batch_emails_to_send': {}, 'sent_emails_removal_queue': {}, 'administrative': {}, 'processed_files': {}, 'settings': {}}
        monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
        import interface
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        with pytest.raises(SystemExit):
            interface.DatabaseObj('dummy.db')

@pytest.mark.timeout(5)
def test_reload_connection_failure(monkeypatch):
    # Simulate reload connection fails
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        import interface
        db = mock.MagicMock()
        db.__getitem__.side_effect = lambda k: {}
        monkeypatch.setattr('dataset.connect', mock.Mock(side_effect=Exception('dbfail')))
        monkeypatch.setattr('builtins.open', mock.mock_open())
        monkeypatch.setattr('os.path.isfile', lambda path: True)
        monkeypatch.setattr(interface, 'DATABASE_VERSION', 1)
        monkeypatch.setattr(interface, 'VERSION', '1.0')
        monkeypatch.setattr(interface, 'config_folder', 'cfg')
        monkeypatch.setattr(interface, 'running_platform', 'linux')
        with pytest.raises(SystemExit):
            interface.DatabaseObj('dummy.db')

@pytest.mark.timeout(5)
def test_close_calls_close(monkeypatch):
    # Test close method calls database_connection.close
    with contextlib.ExitStack() as stack:
        for patch in make_databaseobj_patches():
            stack.enter_context(patch)
        import interface
        db = mock.Mock()
        db.close = mock.Mock()
        obj = interface.DatabaseObj.__new__(interface.DatabaseObj)
        obj.database_connection = db
        obj.close()
        db.close.assert_called_once()
import contextlib
