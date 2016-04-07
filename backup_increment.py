import shutil
import os


def do_backup(input_file):
    counter = 0
    while os.path.exists(input_file + '.bak' + str(counter)):
        counter += 1
    backup_path = input_file + '.bak' + str(counter)
    shutil.copy(input_file, backup_path)
    return backup_path
