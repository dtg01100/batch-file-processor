import ftplib
import os


# this module sends the file specified in filename to the address specified in the dict process_parameters via ftp
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, filename):
    file_pass = False
    counter = 0
    while not file_pass:
        try:
            with open(filename, 'rb') as send_file:
                filename_no_path = os.path.basename(filename)
                ftp = ftplib.FTP()
                ftp.connect(str(process_parameters['ftp_server']), process_parameters['ftp_port'])
                ftp.login(process_parameters['ftp_username'], process_parameters['ftp_password'])
                ftp.storbinary("stor " + process_parameters['ftp_folder']+filename_no_path, send_file)
                ftp.close()
                file_pass = True

        except Exception as exception:
            if counter == 10:
                raise Exception(exception)
            counter += 1
