import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


def do(process_parameters, filename, reporting):
    fromaddr = reporting['report_email_address']
    toaddr = reporting['report_email_destination']
    print (repr(filename))
    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "error processing " + process_parameters['foldersname'] + "For " + process_parameters['alias']

    filename = filename

    with open (filename, "r") as myfile:
        data=myfile.read().replace('\n', '')

    body = data

    msg.attach(MIMEText(body, 'plain'))

    filename = filename
    attachment = open(filename)

    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

    msg.attach(part)

    server = smtplib.SMTP(reporting['report_email_smtp_server'], 587)
    server.starttls()
    server.login(fromaddr, reporting['report_email_password'])
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
