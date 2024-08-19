import ftplib
import os


# this module sends the file specified in filename to the address specified in the dict process_parameters via ftp
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, settings_dict, filename):
    file_pass = False
    counter = 0
    ftp_providers = [ftplib.FTP_TLS, ftplib.FTP]
    while not file_pass:
        try:
            with open(filename, 'rb') as send_file:
                filename_no_path = os.path.basename(filename)
                for provider in ftp_providers:
                    ftp = provider()
                    try:
                        print(f"Connecting to ftp server: {str(process_parameters['ftp_server'])}")
                        ftp.connect(str(process_parameters['ftp_server']), process_parameters['ftp_port'])
                        print(f"Logging in to {str(process_parameters['ftp_server'])}")
                        ftp.login(process_parameters['ftp_username'], process_parameters['ftp_password'])
                        print("Sending File...")
                        ftp.storbinary("stor " + process_parameters['ftp_folder']+filename_no_path, send_file)
                        print("Success")
                        ftp.close()
                        file_pass = True
                        break
                    except Exception:
                        print("Falling back to non-TLS...")

        except Exception as ftp_error:
            if counter == 10:
                print("Retried 10 times, passing exception to dispatch")
                raise
            counter += 1
            print("Encountered an error. Retry number " + str(counter))
            print("Error is :" + str(ftp_error))
