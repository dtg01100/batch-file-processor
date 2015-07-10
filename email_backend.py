import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def do(process_parameters):
    os.chdir(process_parameters['foldersname'])
    fromaddr = process_parameters['email_origin_address']
    toaddr = process_parameters['email_to']
    for filename in os.listdir(process_parameters['foldersname']):
        print (repr(filename))
        msg = MIMEMultipart()

        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = str(filename) + " Attached"

        body = str(filename) + " Attached"

        msg.attach(MIMEText(body, 'plain'))

        filename = filename
        attachment = open(process_parameters['foldersname'] + "/" + filename)

        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

        msg.attach(part)

        server = smtplib.SMTP(process_parameters['email_origin_smtp_server'], 587)
        server.starttls()
        server.login(fromaddr, process_parameters['email_origin_password'])
        text = msg.as_string()
        server.sendmail(fromaddr, toaddr, text)
    server.quit()
