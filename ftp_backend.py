import ftplib
import shutil

# this module sends the file specified in filename to the address specified in the dict process_parameters via ftp
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, filename):
    ftp = ftplib.FTP()
    ftp.connect(str(process_parameters['ftp_server']), 2121)
    ftp.login(process_parameters['ftp_username'], process_parameters['ftp_password'])
    ftp.storbinary("stor " + process_parameters['ftp_folder']+filename, open(filename,'rb'))
    ftp.close()
