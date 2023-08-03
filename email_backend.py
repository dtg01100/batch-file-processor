from pathlib import Path
import smtplib
from email.message import EmailMessage
import mimetypes
import time
import os


# this module sends the file specified in filename to the address specified in the dict process_parameters via email
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, settings, filename):
    file_pass = False
    counter = 0
    while not file_pass:
        try:
            filename_no_path = os.path.basename(filename)
            filename_no_path_str = str(filename_no_path)
            if process_parameters['email_subject_line'] != "":
                date_time = str(time.ctime())
                subject_line_constructor = process_parameters['email_subject_line']
                subject_line = subject_line_constructor.replace("%datetime%", date_time).replace("%filename%",
                                                                                                   filename_no_path)
            else:
                subject_line = str(filename_no_path) + " Attached"

            to_address = process_parameters['email_to']
            to_address_list = to_address.split(", ")

            message = EmailMessage()
            message['Subject'] = subject_line
            message['From'] = settings['email_address']
            message['To'] = to_address_list
            message.set_content(filename_no_path_str + " Attached")

            ctype, encoding = mimetypes.guess_type(filename)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            with open(filename, 'rb') as fp:
                message.add_attachment(fp.read(),
                                maintype=maintype,
                                subtype=subtype,
                                filename=filename_no_path_str)

            server = smtplib.SMTP(str(settings['email_smtp_server']), str(settings['smtp_port']))
            server.ehlo()
            server.starttls()
            if settings['email_username'] != "" and settings['email_password'] != "":
                server.login(settings['email_username'], settings['email_password'])
            server.send_message(message)
            server.close()

            file_pass = True
        except Exception as email_error:
            if counter == 10:
                print("Retried 10 times, passing exception to dispatch")
                raise
            counter += 1
            time.sleep(counter * counter)
            print("Encountered an error. Retry number " + str(counter))
            print("Error is :" + str(email_error))
