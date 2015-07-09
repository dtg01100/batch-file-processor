import os
import shutil


def do(process_parameters):
    os.chdir(process_parameters['foldersname'])
    for filename in os.listdir(process_parameters['foldersname']):
        print (filename)
        shutil.copy(str(filename), process_parameters['copy_to_directory'])
