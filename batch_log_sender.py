import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os


def do(reporting, emails_table, time):
    fromaddr = reporting['report_email_address']
    toaddr = reporting['report_email_destination']
    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Logs from run at: " + time

    body = "See attached logs"

    msg.attach(MIMEText(body, 'plain'))

    for log in emails_table.all():
        print (log)

        filename = log['log']
        print str(filename)
        attachment = open(filename, "r")

        head, tail = os.path.split(filename)

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % tail)

        msg.attach(part)

    server = smtplib.SMTP(reporting['report_email_smtp_server'], 587)
    server.starttls()
    server.login(fromaddr, reporting['report_email_password'])
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
