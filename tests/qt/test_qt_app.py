"""Tests for QtBatchFileSenderApp using pytest-qt."""
import pytest
from unittest.mock import MagicMock


@pytest.mark.qt
class TestQtBatchFileSenderApp:

    def test_construction_stores_parameters(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp(appname="Test", version="1.0", database_version="33")
        assert app._appname == "Test"
        assert app._version == "1.0"
        assert app._database_version == "33"

    def test_database_property_raises_before_init(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        with pytest.raises(RuntimeError, match="Database not initialized"):
            _ = app.database

    def test_folder_manager_property_raises_before_init(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        with pytest.raises(RuntimeError, match="Folder manager not initialized"):
            _ = app.folder_manager

    def test_args_property_raises_before_init(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        with pytest.raises(RuntimeError, match="Arguments not parsed"):
            _ = app.args

    def test_database_injected(self):
        from interface.qt.app import QtBatchFileSenderApp
        mock_db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=mock_db)
        assert app._database is mock_db

    def test_shutdown_closes_database(self):
        from interface.qt.app import QtBatchFileSenderApp
        mock_db = MagicMock()
        app = QtBatchFileSenderApp(database_obj=mock_db)
        app.shutdown()
        mock_db.close.assert_called_once()

    def test_shutdown_no_db_no_error(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app.shutdown()

    def test_set_main_button_states_no_folders(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._database.folders_table.count.return_value = 0
        app._database.processed_files.count.return_value = 0
        app._process_folder_button = MagicMock()
        app._processed_files_button = MagicMock()
        app._allow_resend_button = MagicMock()
        app._set_main_button_states()
        app._process_folder_button.setEnabled.assert_called_with(False)

    def test_set_main_button_states_with_folders(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        app._database.folders_table.count.side_effect = lambda **kw: 5 if not kw else 3
        app._database.processed_files.count.return_value = 10
        app._process_folder_button = MagicMock()
        app._processed_files_button = MagicMock()
        app._allow_resend_button = MagicMock()
        app._set_main_button_states()
        app._process_folder_button.setEnabled.assert_called_with(True)
        app._processed_files_button.setEnabled.assert_called_with(True)
        app._allow_resend_button.setEnabled.assert_called_with(True)

    def test_disable_folder(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._disable_folder(42)
        app._folder_manager.disable_folder.assert_called_once_with(42)
        app._refresh_users_list.assert_called_once()

    def test_set_folders_filter(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._refresh_users_list = MagicMock()
        app._set_folders_filter("test")
        assert app._folder_filter == "test"
        app._refresh_users_list.assert_called_once()

    def test_delete_folder_confirmed(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._ui_service.ask_yes_no.return_value = True
        app._folder_manager = MagicMock()
        app._refresh_users_list = MagicMock()
        app._set_main_button_states = MagicMock()
        app._delete_folder_entry_wrapper(42, "test")
        app._folder_manager.delete_folder_with_related.assert_called_once_with(42)

    def test_delete_folder_cancelled(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._ui_service = MagicMock()
        app._ui_service.ask_yes_no.return_value = False
        app._folder_manager = MagicMock()
        app._delete_folder_entry_wrapper(42, "test")
        app._folder_manager.delete_folder_with_related.assert_not_called()

    def test_disable_all_email_backends(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        row1 = {"id": 1, "process_backend_email": True}
        row2 = {"id": 2, "process_backend_email": True}
        app._database.folders_table.find.return_value = [row1, row2]
        app._disable_all_email_backends()
        assert row1["process_backend_email"] is False
        assert row2["process_backend_email"] is False
        assert app._database.folders_table.update.call_count == 2

    def test_update_reporting(self):
        from interface.qt.app import QtBatchFileSenderApp
        app = QtBatchFileSenderApp()
        app._database = MagicMock()
        changes = {"id": 1, "enable_reporting": True}
        app._update_reporting(changes)
        app._database.oversight_and_defaults.update.assert_called_once_with(changes, ["id"])
