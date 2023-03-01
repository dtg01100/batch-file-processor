from redmail import EmailSender
from pathlib import Path
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
            emailer = EmailSender(host=settings['email_smtp_server'], port=settings['smtp_port'])
            if process_parameters['email_subject_line'] != "":
                date_time = str(time.ctime())
                subject_line_constructor = process_parameters['email_subject_line']
                subject_line = subject_line_constructor.replace("%datetime%", date_time).replace("%filename%",
                                                                                                   filename_no_path)
            else:
                subject_line = str(filename_no_path) + " Attached"

            to_address = process_parameters['email_to']
            to_address_list = to_address.split(", ")

            if settings['email_username'] == "" and settings['email_password'] == '':
                emailer.send(
                    subject=subject_line,
                    sender=settings['email_address'],
                    receivers=to_address_list,
                    text=filename_no_path_str + " Attached",
                    attachments={
                        filename_no_path_str: Path(filename),
                    }
                )
            else:
                send_username = settings['email_username']
                send_password = settings['email_password']
                emailer.send(
                    subject=subject_line,
                    username=send_username,
                    password=send_password,
                    sender=settings['email_address'],
                    receivers=to_address_list,
                    text=filename_no_path_str + " Attached",
                    attachments={
                        filename_no_path_str: Path(filename),
                    }
                )
            file_pass = True
        except Exception as email_error:
            if counter == 10:
                print("Retried 10 times, passing exception to dispatch")
                raise
            counter += 1
            time.sleep(counter * counter)
            print("Encountered an error. Retry number " + str(counter))
            print("Error is :" + str(email_error))
