import mimetypes
import os
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from send_base import BaseSendBackend, create_send_wrapper


class EmailSendBackend(BaseSendBackend):
    """
    Email send backend implementation.
    Sends files via email using SMTP.
    """
    
    def __init__(self, process_parameters, settings_dict, filename):
        super().__init__(process_parameters, settings_dict, filename)
        self.exponential_backoff = True  # Use exponential backoff for email backend
    
    def _send(self):
        filename_no_path = os.path.basename(self.filename)
        filename_no_path_str = str(filename_no_path)
        
        if self.process_parameters['email_subject_line'] != "":
            date_time = str(time.ctime())
            subject_line_constructor = self.process_parameters['email_subject_line']
            subject_line = subject_line_constructor.replace("%datetime%", date_time).replace("%filename%", filename_no_path)
        else:
            subject_line = str(filename_no_path) + " Attached"

        to_address = self.process_parameters['email_to']
        to_address_list = to_address.split(", ")

        message = EmailMessage()
        message['Subject'] = subject_line
        message['From'] = self.settings_dict['email_address']
        message['To'] = to_address_list
        message.set_content(filename_no_path_str + " Attached")

        ctype, encoding = mimetypes.guess_type(self.filename)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        
        with open(self.filename, 'rb') as fp:
            message.add_attachment(fp.read(),
                            maintype=maintype,
                            subtype=subtype,
                            filename=filename_no_path_str)

        server = smtplib.SMTP(str(self.settings_dict['email_smtp_server']), str(self.settings_dict['smtp_port']))
        server.ehlo()
        server.starttls()
        
        if self.settings_dict['email_username'] != "" and self.settings_dict['email_password'] != "":
            server.login(self.settings_dict['email_username'], self.settings_dict['email_password'])
            
        server.send_message(message)
        server.close()


do = create_send_wrapper(EmailSendBackend)
