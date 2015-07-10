import ftplib
import os


def do(process_parameters):
    os.chdir(process_parameters['foldersname'])
    ftp = ftplib.FTP()
    print ("Connecting to: " + str(process_parameters['ftp_server']))
    ftp.connect(str(process_parameters['ftp_server']), 2121)
    ftp.login(process_parameters['ftp_username'], process_parameters['ftp_password'])
    for filename in os.listdir(process_parameters['foldersname']):
        print ("logging in with parameters: " + process_parameters['ftp_username'], process_parameters['ftp_password'])
        ftp.storbinary("stor " + process_parameters['ftp_folder']+filename, open(filename,'rb'))
    ftp.close()
