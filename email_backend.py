import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from binaryornot.check import is_binary
from email import encoders
import time
import os


# this module sends the file specified in filename to the address specified in the dict process_parameters via email
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, filename):
    from_address = process_parameters['email_origin_address']
    to_address = process_parameters['email_to']
    to_address_list = to_address.split(", ")
    msg = MIMEMultipart()

    filename_no_path = os.path.basename(filename)

    if process_parameters['email_subject_line'] != "":
        date_time = str(time.ctime())
        subject_line_constructor = process_parameters['email_subject_line']
        msg['Subject'] = subject_line_constructor.replace("%datetime%", date_time).replace("%filename%",
                                                                                           filename_no_path)
    else:
        msg['Subject'] = str(filename_no_path) + " Attached"

    msg['From'] = from_address
    msg['To'] = to_address

    body = str(filename_no_path) + " Attached"

    msg.attach(MIMEText(body, 'plain'))

    attachment = open(filename, 'rb')

    part = MIMEBase('application', 'octet-stream; name="%s"' % filename_no_path)
    part.set_payload(attachment.read())
    if is_binary(filename):
        encoders.encode_base64(part)
    part.add_header('X-Attachment-Id', '1')
    part.add_header('Content-Disposition', 'attachment; filename="%s"' % filename_no_path)

    msg.attach(part)
    server = smtplib.SMTP(process_parameters['email_origin_smtp_server'], process_parameters['email_smtp_port'])
    server.starttls()
    server.login(from_address, process_parameters['email_origin_password'])
    server.sendmail(from_address, to_address_list, msg.as_string())
    server.close()
