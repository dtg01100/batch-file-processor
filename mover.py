import os
import threading
from tkinter import IntVar

import dataset

import backup_increment
import folders_database_migrator


class DbMigrationThing:
    def __init__(self, original_folder_path, new_folder_path):
        self.original_folder_path = original_folder_path
        self.new_folder_path = new_folder_path
        self.number_of_folders = IntVar()
        self.progress_of_folders = IntVar()

    def do_migrate(self, progress_bar, master, original_database_path):
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
        progress_bar.configure(mode='indeterminate', maximum=100)
        progress_bar.start()
        while preimport_operations_thread_object.isAlive():
            master.update()
        progress_bar.stop()
        progress_bar.configure(maximum=100, value=0, mode='determinate')
        new_database_connection = dataset.connect('sqlite:///' + modified_new_folder_path)
        new_folders_table = new_database_connection['folders']
        original_database_connection = dataset.connect('sqlite:///' + original_database_path)
        old_folders_table = original_database_connection['folders']
        # After migration, folder_is_active may be integer 1 or string "True"
        # Count both to handle pre- and post-v41 databases
        self.number_of_folders = (
            new_folders_table.count(folder_is_active="True") +
            new_folders_table.count(folder_is_active=1)
        )
        self.progress_of_folders = 0
        progress_bar.configure(maximum=self.number_of_folders, value=self.progress_of_folders)

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
            progress_bar.configure(value=self.progress_of_folders)
            master.update()
