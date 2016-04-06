import os
import shutil
from Tkinter import IntVar
import dataset
import folders_database_migrator


class DbMigrationThing:
    def __init__(self, original_folder_path, new_folder_path):
        self.original_folder_path = original_folder_path
        self.new_folder_path = new_folder_path
        self.number_of_folders = IntVar()
        self.progress_of_folders = IntVar()

    def do_migrate(self, progress_bar, master, original_database_connection):
        shutil.copy(os.path.abspath(self.original_folder_path), os.path.abspath(self.original_folder_path) + ".bak")
        shutil.copy(os.path.abspath(self.new_folder_path), os.path.abspath(self.new_folder_path) + ".bak")

        new_database_connection = dataset.connect('sqlite:///' + self.new_folder_path)
        folders_database_migrator.upgrade_database(new_database_connection)

        new_folders_table = new_database_connection['folders']
        old_folders_table = original_database_connection['folders']
        self.number_of_folders = old_folders_table.count(folder_is_active="True")
        self.progress_of_folders = 0
        progress_bar.configure(maximum=self.number_of_folders, value=self.progress_of_folders)

        def test_line_for_match(line):
            line_match = False
            new_db_line = None
            for db_line in new_folders_table.find(folder_is_active="True"):
                if os.path.abspath(db_line['folder_name']) == os.path.abspath(line['folder_name']):
                    new_db_line = db_line
                    line_match = True
                    break
            return line_match, new_db_line

        for line in old_folders_table.find(folder_is_active="True"):
            line_match, new_db_line = test_line_for_match(line)
            print(str(line_match))
            if line_match is True:
                update_db_line = new_db_line
                if new_db_line['process_backend_copy'] is True:
                    print("adding copy backend settings")
                    update_db_line.update(dict(process_backend_copy=new_db_line['process_backend_copy'],
                                               copy_to_directory=new_db_line['copy_to_directory'],
                                               id=line['id']))
                if new_db_line['process_backend_ftp'] is True:
                    print("adding ftp backend settings")
                    update_db_line.update(dict(ftp_server=new_db_line['ftp_server'],
                                               ftp_folder=new_db_line['ftp_folder'],
                                               ftp_username=new_db_line['ftp_username'],
                                               ftp_password=new_db_line['ftp_password'],
                                               ftp_port=new_db_line['ftp_port'],
                                               id=line['id']))
                if new_db_line['process_backend_email'] is True:
                    print("adding email backend settings")
                    update_db_line.update(dict(email_to=new_db_line['email_to'],
                                               email_origin_address=new_db_line['email_origin_address'],
                                               email_origin_username=new_db_line['email_origin_username'],
                                               email_origin_password=new_db_line['email_origin_password'],
                                               email_origin_smtp_server=new_db_line[
                                                   'email_origin_smtp_server'],
                                               email_smtp_port=new_db_line['email_smtp_port'],
                                               email_subject_line=new_db_line['email_subject_line'],
                                               id=line['id']))
                old_folders_table.update(update_db_line, ['id'])

            else:
                print("adding line")
                del line['id']
                print(line)
                old_folders_table.insert(line)
            self.progress_of_folders += 1
            progress_bar.configure(value=self.progress_of_folders)
            master.update()
