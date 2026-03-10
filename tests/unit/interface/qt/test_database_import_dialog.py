"""Behavioral tests for Qt database import workflow internals.

These tests focus on `ImportThread` and `DbMigrationJob` logic that was
previously covered only by placeholder assertions.
"""

from unittest.mock import MagicMock

from PyQt6.QtWidgets import QMessageBox

from interface.qt.dialogs.database_import_dialog import DbMigrationJob, ImportThread


class TestImportThread:

    def test_run_cancels_when_old_version_prompt_rejected(self, monkeypatch):
        version_table = MagicMock()
        version_table.find_one.return_value = {"version": "13", "os": "Linux"}
        new_db_connection = {"version": version_table}

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.sqlite_wrapper.Database.connect",
            lambda _: new_db_connection,
        )
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.No,
        )

        migrate_job = MagicMock()
        thread = ImportThread(
            migrate_job=migrate_job,
            new_db_path="/tmp/new.db",
            original_db_path="/tmp/original.db",
            platform="Linux",
            db_version="41",
            backup_path="/tmp/backup",
        )

        finished_events = []
        thread.finished.connect(
            lambda success, message: finished_events.append((success, message))
        )

        thread.run()

        assert finished_events == [(False, "Import cancelled by user")]
        migrate_job.do_migrate.assert_not_called()

    def test_run_executes_migration_for_compatible_version(self, monkeypatch):
        version_table = MagicMock()
        version_table.find_one.return_value = {"version": "41", "os": "Linux"}
        new_db_connection = {"version": version_table}

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.sqlite_wrapper.Database.connect",
            lambda _: new_db_connection,
        )

        migrate_job = MagicMock()
        thread = ImportThread(
            migrate_job=migrate_job,
            new_db_path="/tmp/new.db",
            original_db_path="/tmp/original.db",
            platform="Linux",
            db_version="41",
            backup_path="/tmp/backup",
        )

        finished_events = []
        thread.finished.connect(
            lambda success, message: finished_events.append((success, message))
        )

        thread.run()

        migrate_job.do_migrate.assert_called_once_with(
            thread, "/tmp/new.db", "/tmp/original.db"
        )
        assert finished_events == [(True, "Import completed successfully")]

    def test_run_emits_error_when_connect_fails(self, monkeypatch):
        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.sqlite_wrapper.Database.connect",
            lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        thread = ImportThread(
            migrate_job=MagicMock(),
            new_db_path="/tmp/new.db",
            original_db_path="/tmp/original.db",
            platform="Linux",
            db_version="41",
            backup_path="/tmp/backup",
        )

        error_events = []
        thread.error.connect(lambda message: error_events.append(message))

        thread.run()

        assert len(error_events) == 1
        assert error_events[0].startswith("Import failed: boom")


class TestDbMigrationJob:

    def test_migrate_folder_merges_copy_ftp_email_fields(self, monkeypatch):
        job = DbMigrationJob("/tmp/original.db", "/tmp/new.db")

        old_folder = {
            "folder_name": "/same/path",
            "process_backend_copy": True,
            "copy_to_directory": "/copy/dest",
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
            "ftp_folder": "/upload",
            "ftp_username": "user",
            "ftp_password": "pass",
            "process_backend_email": True,
            "email_recipients": "a@example.com",
            "email_subject": "subject",
            "email_from": "from@example.com",
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "smtp_username": "smtp_user",
            "smtp_password": "smtp_pass",
            "smtp_use_tls": True,
        }
        old_folders = MagicMock()
        old_folders.find.return_value = [old_folder]

        folders_table = MagicMock()
        new_db = {"folders": folders_table}

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda _lhs, _rhs: True,
        )

        job._migrate_folder(
            folder={"id": 99, "folder_name": "/same/path"},
            old_folders=old_folders,
            new_db=new_db,
        )

        folders_table.update.assert_called_once()
        update_payload = folders_table.update.call_args.args[0]
        assert update_payload["id"] == 99
        assert update_payload["process_backend_copy"] is True
        assert update_payload["copy_to_directory"] == "/copy/dest"
        assert update_payload["ftp_server"] == "ftp.example.com"
        assert update_payload["email_recipients"] == "a@example.com"
        assert update_payload["smtp_use_tls"] is True

    def test_migrate_folder_falls_back_to_string_match_when_samefile_errors(
        self, monkeypatch
    ):
        job = DbMigrationJob("/tmp/original.db", "/tmp/new.db")

        old_folder = {
            "folder_name": "C:/shared/path",
            "process_backend_copy": True,
            "copy_to_directory": "D:/copy",
        }
        old_folders = MagicMock()
        old_folders.find.return_value = [old_folder]

        folders_table = MagicMock()
        new_db = {"folders": folders_table}

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda _lhs, _rhs: (_ for _ in ()).throw(OSError("cross-platform path")),
        )

        job._migrate_folder(
            folder={"id": 7, "folder_name": "C:/shared/path"},
            old_folders=old_folders,
            new_db=new_db,
        )

        folders_table.update.assert_called_once()
        update_payload = folders_table.update.call_args.args[0]
        assert update_payload["id"] == 7
        assert update_payload["copy_to_directory"] == "D:/copy"

    def test_migrate_folder_no_match_skips_update(self, monkeypatch):
        job = DbMigrationJob("/tmp/original.db", "/tmp/new.db")

        old_folders = MagicMock()
        old_folders.find.return_value = [{"folder_name": "/different/path"}]

        folders_table = MagicMock()
        new_db = {"folders": folders_table}

        monkeypatch.setattr(
            "interface.qt.dialogs.database_import_dialog.os.path.samefile",
            lambda _lhs, _rhs: False,
        )

        job._migrate_folder(
            folder={"id": 12, "folder_name": "/target/path"},
            old_folders=old_folders,
            new_db=new_db,
        )

        folders_table.update.assert_not_called()
