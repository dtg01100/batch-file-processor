"""Database migration utilities.

This module provides utilities for migrating and merging database files.
It has been refactored to remove tkinter dependencies.
"""

import os
import threading
from typing import Any, Callable, Optional

import dataset

import backup_increment
import folders_database_migrator


class DbMigrationThing:
    """Database migration handler.

    This class handles the migration of folder data between database files.
    It has been refactored to use callback-based progress reporting instead
    of tkinter variables.

    Attributes:
        original_folder_path: Path to the original database file
        new_folder_path: Path to the new database file to import from
    """

    def __init__(self, original_folder_path: str, new_folder_path: str) -> None:
        self.original_folder_path = original_folder_path
        self.new_folder_path = new_folder_path
        self.number_of_folders: int = 0
        self.progress_of_folders: int = 0

    def do_migrate(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        original_database_path: Optional[str] = None,
    ) -> None:
        """Perform the database migration.

        Args:
            progress_callback: Optional callback function(progress, maximum) for
                reporting progress. Replaces tkinter progress_bar parameter.
            original_database_path: Path to the original database file. If not
                provided, uses self.original_folder_path.
        """
        if original_database_path is None:
            original_database_path = self.original_folder_path

        def database_preimport_operations():
            global new_database_connection
            global modified_new_folder_path
            original_database_connection_for_migrate = dataset.connect('sqlite:///' + original_database_path)
            backup_increment.do_backup(self.original_folder_path)
            modified_new_folder_path = backup_increment.do_backup(self.new_folder_path)
            original_db_version = original_database_connection_for_migrate['version']
            original_db_version_dict = original_db_version.find_one(id=1)
            new_database_connection = dataset.connect('sqlite:///' + modified_new_folder_path)
            new_db_version = new_database_connection['version']
            new_db_version_dict = new_db_version.find_one(id=1)
            if int(new_db_version_dict['version']) < int(original_db_version_dict['version']):
                print("db needs upgrading")
                folders_database_migrator.upgrade_database(new_database_connection, None, "Null")

        preimport_operations_thread_object = threading.Thread(target=database_preimport_operations)
        preimport_operations_thread_object.start()

        # Report indeterminate progress
        if progress_callback:
            progress_callback(0, 100)

        while preimport_operations_thread_object.is_alive():
            # Process events if needed (for Qt compatibility)
            try:
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
            except ImportError:
                pass

        # Report determinate progress
        if progress_callback:
            progress_callback(0, 100)

        new_database_connection = dataset.connect('sqlite:///' + modified_new_folder_path)
        new_folders_table = new_database_connection['folders']
        original_database_connection = dataset.connect('sqlite:///' + original_database_path)
        old_folders_table = original_database_connection['folders']

        # Count folders for progress
        active_folders = list(new_folders_table.find(folder_is_active="True"))
        active_folders.extend(list(new_folders_table.find(folder_is_active=1)))
        # Deduplicate by id
        seen_ids = set()
        unique_folders = []
        for folder in active_folders:
            if folder['id'] not in seen_ids:
                seen_ids.add(folder['id'])
                unique_folders.append(folder)

        self.number_of_folders = len(unique_folders)
        self.progress_of_folders = 0

        if progress_callback and self.number_of_folders > 0:
            progress_callback(0, self.number_of_folders)

        def _get_active_folders(table):
            """Get active folders handling both string and integer boolean formats."""
            results = list(table.find(folder_is_active="True"))
            results.extend(list(table.find(folder_is_active=1)))
            # Deduplicate by id
            seen_ids = set()
            unique_results = []
            for row in results:
                if row['id'] not in seen_ids:
                    seen_ids.add(row['id'])
                    unique_results.append(row)
            return unique_results

        def test_line_for_match(line):
            line_match = False
            new_db_line = None
            for db_line in _get_active_folders(old_folders_table):
                try:
                    if os.path.samefile(db_line['folder_name'], line['folder_name']):
                        new_db_line = db_line
                        line_match = True
                        break
                except (OSError, TypeError, ValueError):
                    # Path may not exist on this system; compare as strings
                    if db_line['folder_name'] == line['folder_name']:
                        new_db_line = db_line
                        line_match = True
                        break
            return line_match, new_db_line

        for line in _get_active_folders(new_folders_table):
            try:
                line_match, new_db_line = test_line_for_match(line)
                print(str(line_match))
                if line_match is True:
                    update_db_line = new_db_line
                    if new_db_line.get('process_backend_copy') in (True, 1, "True"):
                        print("merging copy backend settings")
                        update_db_line.update(dict(process_backend_copy=new_db_line['process_backend_copy'],
                                                   copy_to_directory=new_db_line['copy_to_directory'],
                                                   id=line['id']))
                    if new_db_line.get('process_backend_ftp') in (True, 1, "True"):
                        print("merging ftp backend settings")
                        update_db_line.update(dict(ftp_server=new_db_line['ftp_server'],
                                                   ftp_folder=new_db_line['ftp_folder'],
                                                   ftp_username=new_db_line['ftp_username'],
                                                   ftp_password=new_db_line['ftp_password'],
                                                   ftp_port=new_db_line['ftp_port'],
                                                   id=line['id']))
                    if new_db_line.get('process_backend_email') in (True, 1, "True"):
                        print("merging email backend settings")
                        update_db_line.update(dict(email_to=new_db_line['email_to'],
                                                   email_subject_line=new_db_line['email_subject_line'],
                                                   id=line['id']))
                    old_folders_table.update(update_db_line, ['id'])

                else:
                    print("adding line")
                    del line['id']
                    print(line)
                    old_folders_table.insert(line)
            except Exception as error:
                print("import of folder failed with " + str(error))

            self.progress_of_folders += 1
            if progress_callback:
                progress_callback(self.progress_of_folders, self.number_of_folders)
