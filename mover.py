import os
import threading

from PyQt6.QtSql import QSqlDatabase, QSqlQuery

import backup_increment
import folders_database_migrator

# Import DatabaseConnection wrapper from database_manager
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "interface", "database"))
from database_manager import DatabaseConnection


class DbMigrationThing:
    def __init__(self, original_folder_path, new_folder_path):
        self.original_folder_path = original_folder_path
        self.new_folder_path = new_folder_path
        self.number_of_folders = 0
        self.progress_of_folders = 0

    def do_migrate(self, progress_bar, master, original_database_path):
        def database_preimport_operations():
            global new_database_connection
            global modified_new_folder_path

            orig_db = QSqlDatabase.addDatabase("QSQLITE", "original")
            orig_db.setDatabaseName(original_database_path)
            if not orig_db.open():
                raise RuntimeError(
                    f"Failed to open original database: {orig_db.lastError().text()}"
                )
            original_database_connection_for_migrate = DatabaseConnection(orig_db)

            backup_increment.do_backup(self.original_folder_path)
            modified_new_folder_path = backup_increment.do_backup(self.new_folder_path)

            original_db_version = original_database_connection_for_migrate["version"]
            original_db_version_dict = original_db_version.find_one(id=1)

            new_db = QSqlDatabase.addDatabase("QSQLITE", "new")
            new_db.setDatabaseName(modified_new_folder_path)
            if not new_db.open():
                raise RuntimeError(
                    f"Failed to open new database: {new_db.lastError().text()}"
                )
            new_database_connection = DatabaseConnection(new_db)

            new_db_version = new_database_connection["version"]
            new_db_version_dict = new_db_version.find_one(id=1)

            if int(new_db_version_dict["version"]) < int(
                original_db_version_dict["version"]
            ):
                print("db needs upgrading")
                folders_database_migrator.upgrade_database(
                    new_database_connection, None, "Null"
                )

        preimport_operations_thread_object = threading.Thread(
            target=database_preimport_operations
        )
        preimport_operations_thread_object.start()
        progress_bar.configure(mode="indeterminate", maximum=100)
        progress_bar.start()
        while preimport_operations_thread_object.is_alive():
            master.update()
        progress_bar.stop()
        progress_bar.configure(maximum=100, value=0, mode="determinate")

        new_db = QSqlDatabase.addDatabase("QSQLITE", "new_reload")
        new_db.setDatabaseName(modified_new_folder_path)
        if not new_db.open():
            raise RuntimeError(
                f"Failed to open new database: {new_db.lastError().text()}"
            )
        new_database_connection = DatabaseConnection(new_db)
        new_folders_table = new_database_connection["folders"]

        orig_db = QSqlDatabase.addDatabase("QSQLITE", "original_reload")
        orig_db.setDatabaseName(original_database_path)
        if not orig_db.open():
            raise RuntimeError(
                f"Failed to open original database: {orig_db.lastError().text()}"
            )
        original_database_connection = DatabaseConnection(orig_db)
        old_folders_table = original_database_connection["folders"]

        self.number_of_folders = new_folders_table.count(folder_is_active="True")
        self.progress_of_folders = 0
        progress_bar.configure(
            maximum=self.number_of_folders, value=self.progress_of_folders
        )

        def test_line_for_match(line):
            line_match = False
            new_db_line = None
            for db_line in old_folders_table.find(folder_is_active="True"):
                if os.path.samefile(db_line["folder_name"], line["folder_name"]):
                    new_db_line = db_line
                    line_match = True
                    break
            return line_match, new_db_line

        for line in new_folders_table.find(folder_is_active="True"):
            try:
                line_match, new_db_line = test_line_for_match(line)
                print(str(line_match))
                if line_match is True:
                    update_db_line = new_db_line
                    if new_db_line["process_backend_copy"] is True:
                        print("merging copy backend settings")
                        update_db_line.update(
                            dict(
                                process_backend_copy=new_db_line[
                                    "process_backend_copy"
                                ],
                                copy_to_directory=new_db_line["copy_to_directory"],
                                id=line["id"],
                            )
                        )
                    if new_db_line["process_backend_ftp"] is True:
                        print("merging ftp backend settings")
                        update_db_line.update(
                            dict(
                                ftp_server=new_db_line["ftp_server"],
                                ftp_folder=new_db_line["ftp_folder"],
                                ftp_username=new_db_line["ftp_username"],
                                ftp_password=new_db_line["ftp_password"],
                                ftp_port=new_db_line["ftp_port"],
                                id=line["id"],
                            )
                        )
                    if new_db_line["process_backend_email"] is True:
                        print("merging email backend settings")
                        update_db_line.update(
                            dict(
                                email_to=new_db_line["email_to"],
                                email_subject_line=new_db_line["email_subject_line"],
                                id=line["id"],
                            )
                        )
                    old_folders_table.update(update_db_line, ["id"])

                else:
                    print("adding line")
                    del line["id"]
                    print(line)
                    old_folders_table.insert(line)
            except Exception as error:
                print("import of folder failed with " + str(error))
            self.progress_of_folders += 1
            progress_bar.configure(value=self.progress_of_folders)
            master.update()
