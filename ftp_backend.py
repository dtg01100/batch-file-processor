import ftplib
import os

from send_base import BaseSendBackend, create_send_wrapper


class FTPSendBackend(BaseSendBackend):
    """FTP send backend implementation with TLS support."""

    PLUGIN_ID = "ftp"
    PLUGIN_NAME = "FTP Transfer"
    PLUGIN_DESCRIPTION = "Send files via FTP with TLS fallback"

    CONFIG_FIELDS = [
        {
            "key": "ftp_server",
            "label": "FTP Server",
            "type": "string",
            "default": "",
            "required": True,
            "placeholder": "ftp.example.com",
            "help": "FTP server hostname or IP address",
        },
        {
            "key": "ftp_port",
            "label": "FTP Port",
            "type": "integer",
            "default": 21,
            "min_value": 1,
            "max_value": 65535,
            "help": "FTP server port (usually 21)",
        },
        {
            "key": "ftp_username",
            "label": "Username",
            "type": "string",
            "default": "",
            "required": True,
            "placeholder": "username",
            "help": "FTP login username",
        },
        {
            "key": "ftp_password",
            "label": "Password",
            "type": "string",
            "default": "",
            "required": True,
            "help": "FTP login password",
        },
        {
            "key": "ftp_folder",
            "label": "Remote Folder",
            "type": "string",
            "default": "/",
            "placeholder": "/path/to/folder/",
            "help": "Remote folder path (should end with /)",
        },
        {
            "key": "ftp_passive",
            "label": "Passive Mode",
            "type": "boolean",
            "default": True,
            "help": "Use passive mode for FTP connection",
        },
    ]

    def _send(self):
        with open(self.filename, "rb") as send_file:
            filename_no_path = os.path.basename(self.filename)
            ftp_providers = [ftplib.FTP_TLS, ftplib.FTP]

            for provider_index, provider in enumerate(ftp_providers):
                ftp = provider()
                try:
                    ftp_server = self.get_config_value("ftp_server", "")
                    ftp_port = self.get_config_value("ftp_port", 21)
                    ftp_username = self.get_config_value("ftp_username", "")
                    ftp_password = self.get_config_value("ftp_password", "")
                    ftp_folder = self.get_config_value("ftp_folder", "/")

                    print(f"Connecting to ftp server: {ftp_server}")
                    print(ftp.connect(str(ftp_server), ftp_port))
                    print(f"Logging in to {ftp_server}")
                    print(ftp.login(ftp_username, ftp_password))
                    print("Sending File...")
                    ftp.storbinary("stor " + ftp_folder + filename_no_path, send_file)
                    print("Success")
                    ftp.close()
                    break
                except Exception as error:
                    print(error)
                    if provider_index + 1 == len(ftp_providers):
                        raise
                    print("Falling back to non-TLS...")


do = create_send_wrapper(FTPSendBackend)
