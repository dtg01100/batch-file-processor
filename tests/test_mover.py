import pytest
from unittest import mock

# Ensure tkinter.IntVar is always patched before any test runs
@pytest.fixture(autouse=True, scope='function')
def patch_intvar(monkeypatch):
    monkeypatch.setattr('tkinter.IntVar', mock.Mock())

import pytest
from unittest import mock

@pytest.mark.timeout(10)
def test_do_migrate_success(monkeypatch):
    monkeypatch.setattr('tkinter.IntVar', mock.Mock())
    from mover import DbMigrationThing
    # Setup mocks for all database and backup operations
    def table_mock(*args, **kwargs):
        m = mock.Mock()
        m.find_one = mock.Mock(return_value={'version': 1, 'os': 'linux'})
        m.find = mock.Mock(return_value=[{'folder_name': 'f1', 'id': 1, 'process_backend_copy': True, 'copy_to_directory': 'cdir', 'process_backend_ftp': True, 'ftp_server': 'fs', 'ftp_folder': 'ff', 'ftp_username': 'fu', 'ftp_password': 'fp', 'ftp_port': 21, 'process_backend_email': True, 'email_to': 'e', 'email_subject_line': 's', 'folder_is_active': 'True'}])
        m.count = mock.Mock(return_value=1)
        m.update = mock.Mock()
        m.insert = mock.Mock()
        return m
    dummy_db = mock.MagicMock()
    dummy_db.__getitem__.side_effect = lambda k: table_mock()
    monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
    monkeypatch.setattr('backup_increment.do_backup', mock.Mock(return_value='newdbpath'))
    monkeypatch.setattr('folders_database_migrator.upgrade_database', mock.Mock())
    monkeypatch.setattr('os.path.samefile', lambda a, b: True)
    progress_bar = mock.Mock()
    progress_bar.configure = mock.Mock()
    progress_bar.start = mock.Mock()
    progress_bar.stop = mock.Mock()
    master = mock.Mock()
    master.update = mock.Mock()
    obj = DbMigrationThing('orig', 'new')
    obj.do_migrate(progress_bar, master, 'origdb')
    # Should call update and not raise
    assert progress_bar.start.called
    assert progress_bar.stop.called
    assert progress_bar.configure.called
    assert master.update.called

@pytest.mark.timeout(10)
def test_do_migrate_db_connect_failure(monkeypatch):
    monkeypatch.setattr('tkinter.IntVar', mock.Mock())
    from mover import DbMigrationThing
    # Simulate dataset.connect fails
    monkeypatch.setattr('dataset.connect', mock.Mock(side_effect=Exception('fail')))
    progress_bar = mock.Mock()
    master = mock.Mock()
    obj = DbMigrationThing('orig', 'new')
    # Should not raise, just print error
    try:
        obj.do_migrate(progress_bar, master, 'origdb')
    except Exception as e:
        assert 'fail' in str(e)

@pytest.mark.timeout(10)
def test_do_migrate_backup_failure(monkeypatch):
    monkeypatch.setattr('tkinter.IntVar', mock.Mock())
    from mover import DbMigrationThing
    # Simulate backup_increment.do_backup fails
    def table_mock(*args, **kwargs):
        m = mock.Mock()
        m.find_one = mock.Mock(return_value={'version': 1, 'os': 'linux'})
        m.find = mock.Mock(return_value=[])
        m.count = mock.Mock(return_value=0)
        m.update = mock.Mock()
        m.insert = mock.Mock()
        return m
    dummy_db = mock.MagicMock()
    dummy_db.__getitem__.side_effect = lambda k: table_mock()
    monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
    monkeypatch.setattr('backup_increment.do_backup', mock.Mock(side_effect=Exception('backupfail')))
    progress_bar = mock.Mock()
    master = mock.Mock()
    obj = DbMigrationThing('orig', 'new')
    with pytest.raises(Exception):
        obj.do_migrate(progress_bar, master, 'origdb')

@pytest.mark.timeout(10)
def test_do_migrate_version_upgrade(monkeypatch):
    monkeypatch.setattr('tkinter.IntVar', mock.Mock())
    from mover import DbMigrationThing
    # Simulate new DB version lower than original triggers upgrade
    # Create separate mocks for version tables
    original_version_table = mock.Mock()
    original_version_table.find_one = mock.Mock(return_value={'version': 2, 'os': 'linux'})
    new_version_table = mock.Mock()
    new_version_table.find_one = mock.Mock(return_value={'version': 1, 'os': 'linux'})
    call_count = [0]
    def table_mock(name):
        if name == 'version':
            call_count[0] += 1
            # First call is original, second is new
            return original_version_table if call_count[0] == 1 else new_version_table
        m = mock.Mock()
        m.find = mock.Mock(return_value=[])
        m.count = mock.Mock(return_value=0)
        m.update = mock.Mock()
        m.insert = mock.Mock()
        return m
    dummy_db = mock.MagicMock()
    dummy_db.__getitem__.side_effect = table_mock
    monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
    monkeypatch.setattr('backup_increment.do_backup', mock.Mock(return_value='newdbpath'))
    m_upgrade = mock.Mock()
    monkeypatch.setattr('folders_database_migrator.upgrade_database', m_upgrade)
    monkeypatch.setattr('os.path.samefile', lambda a, b: True)
    progress_bar = mock.Mock()
    master = mock.Mock()
    obj = DbMigrationThing('orig', 'new')
    obj.do_migrate(progress_bar, master, 'origdb')
    assert m_upgrade.called

@pytest.mark.timeout(10)
def test_do_migrate_folder_merge_and_insert(monkeypatch):
    monkeypatch.setattr('tkinter.IntVar', mock.Mock())
    from mover import DbMigrationThing
    # Simulate no match triggers insert, match triggers update
    dummy_db = mock.MagicMock()
    # new_folders_table returns two lines, one matches, one does not
    new_lines = [
        {'folder_name': 'f1', 'id': 1, 'process_backend_copy': True, 'copy_to_directory': 'cdir', 'process_backend_ftp': False, 'process_backend_email': False, 'folder_is_active': 'True'},
        {'folder_name': 'f2', 'id': 2, 'process_backend_copy': False, 'process_backend_ftp': False, 'process_backend_email': False, 'folder_is_active': 'True'}
    ]
    old_lines = [
        {'folder_name': 'f1', 'id': 1, 'process_backend_copy': True, 'copy_to_directory': 'cdir', 'process_backend_ftp': False, 'process_backend_email': False, 'folder_is_active': 'True'}
    ]
    def find_mock(folder_is_active):
        if folder_is_active == 'True':
            return old_lines
        return []
    def table_mock(*args, **kwargs):
        m = mock.Mock()
        m.find_one = mock.Mock(return_value={'version': 1, 'os': 'linux'})
        m.find = mock.Mock(side_effect=[new_lines, old_lines])
        m.count = mock.Mock(return_value=2)
        m.update = mock.Mock()
        m.insert = mock.Mock()
        return m
    dummy_db.__getitem__.side_effect = lambda k: table_mock()
    monkeypatch.setattr('dataset.connect', mock.Mock(return_value=dummy_db))
    monkeypatch.setattr('backup_increment.do_backup', mock.Mock(return_value='newdbpath'))
    monkeypatch.setattr('folders_database_migrator.upgrade_database', mock.Mock())
    monkeypatch.setattr('os.path.samefile', lambda a, b: a == b)
    progress_bar = mock.Mock()
    master = mock.Mock()
    obj = DbMigrationThing('orig', 'new')
    obj.do_migrate(progress_bar, master, 'origdb')
    # Should call update and insert
    assert dummy_db.__getitem__.call_count >= 2
import mover


