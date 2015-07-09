import os


def do(process_parameters):
    for foldername in os.listdir(process_parameters['foldersname']):
        print (foldername)
