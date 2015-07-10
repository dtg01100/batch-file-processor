import ftplib
import os


def do(process_parameters):
    os.chdir(process_parameters['foldersname'])
    ftp = ftplib.FTP()
    ftp.connect(process_parameters['ftp_server'], 21)
    ftp.login(process_parameters['ftp_username'], process_parameters['ftp_password'])
    for filename in os.listdir(process_parameters['foldersname']):
        ftp.storbinary(command="stor " + process_parameters['ftp_folder']+filename, file=open(filename,'rb'))
    ftp.close()
