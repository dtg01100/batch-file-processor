import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import doing_stuff_overlay

def do(reporting, emails_table, sent_emails_removal_queue, time, args, root, batch_number, emails_count, total_emails):
    fromaddr = reporting['report_email_address']
    toaddr = reporting['report_email_destination']
    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Logs from run at: " + time

    body = "See attached logs"

    msg.attach(MIMEText(body, 'plain'))

    for log in emails_table.all():

        if not args.automatic:
            doing_stuff_overlay.destroy_overlay()
            doing_stuff_overlay.make_overlay(root, "sending reports emails\r" + "email " + str(batch_number) +
                                             " attachment " + str(emails_count) + " of " + str(total_emails))

        filename = log['log']
        attachment = open(filename, "r")

        head, tail = os.path.split(filename)

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % tail)

        print("attaching " + filename)
        msg.attach(part)

        sent_emails_removal_queue.insert(log)

    server = smtplib.SMTP(reporting['report_email_smtp_server'], reporting['reporting_smtp_port'])
    server.starttls()
    server.login(fromaddr, reporting['report_email_password'])
    text = msg.as_string()
    print("sending " + str(msg['Subject'] + " to " + str(msg['To'])))
    server.sendmail(fromaddr, toaddr, text)
    server.quit()
