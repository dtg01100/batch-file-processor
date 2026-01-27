import ftplib
import os

from send_base import BaseSendBackend, create_send_wrapper


class FTPSendBackend(BaseSendBackend):
    """
    FTP send backend implementation.
    Sends files via FTP with TLS fallback.
    """
    
    def _send(self):
        with open(self.filename, 'rb') as send_file:
            filename_no_path = os.path.basename(self.filename)
            ftp_providers = [ftplib.FTP_TLS, ftplib.FTP]
            
            for provider_index, provider in enumerate(ftp_providers):
                ftp = provider()
                try:
                    print(f"Connecting to ftp server: {str(self.process_parameters['ftp_server'])}")
                    print(ftp.connect(str(self.process_parameters['ftp_server']), self.process_parameters['ftp_port']))
                    print(f"Logging in to {str(self.process_parameters['ftp_server'])}")
                    print(ftp.login(self.process_parameters['ftp_username'], self.process_parameters['ftp_password']))
                    print("Sending File...")
                    ftp.storbinary("stor " + self.process_parameters['ftp_folder'] + filename_no_path, send_file)
                    print("Success")
                    ftp.close()
                    break
                except Exception as error:
                    print(error)
                    if provider_index + 1 == len(ftp_providers):
                        raise
                    print("Falling back to non-TLS...")


do = create_send_wrapper(FTPSendBackend)
