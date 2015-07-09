import ftplib
import os


def do(process_parameters):
    os.chdir(process_parameters['foldersname'])
    for filename in os.listdir(process_parameters['foldersname']):
        print ("fixme")
