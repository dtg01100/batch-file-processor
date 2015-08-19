import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time

# this module sends the file specified in filename to the address specified in the dict process_parameters via email
# note: process_parameters is a dict from a row in the database, passed into this module


def do(process_parameters, filename):
    fromaddr = process_parameters['email_origin_address']
    toaddr = process_parameters['email_to']
    print (repr(filename))
    msg = MIMEMultipart()

    if process_parameters['email_subject_line'] != "":
        date_time = str(time.ctime())
        subject_line_constructor = process_parameters['email_subject_line']
        msg['Subject'] = subject_line_constructor.replace("%datetime%", date_time)
    else:
        msg['Subject'] = str(filename) + " Attached"


    msg['From'] = fromaddr
    msg['To'] = toaddr

    body = str(filename) + " Attached"

    msg.attach(MIMEText(body, 'plain'))

    filename = filename
    attachment = open(process_parameters['foldersname'] + "/" + filename)

    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    msg.attach(part)

    server = smtplib.SMTP(process_parameters['email_origin_smtp_server'], process_parameters['email_smtp_port'])
    server.starttls()
    server.login(fromaddr, process_parameters['email_origin_password'])
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.close()

