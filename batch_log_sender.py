import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import doingstuffoverlay


def do(settings, reporting, emails_table, sent_emails_removal_queue, time, args, root, batch_number, emails_count, total_emails):
    from_address = settings['email_address']
    to_address = reporting['report_email_destination']
    to_address_list = to_address.split(", ")
    msg = MIMEMultipart()

    msg['From'] = from_address
    msg['To'] = to_address

    if emails_table.count() != 1:
        msg['Subject'] = "Logs from run at: " + time
        body = "See attached logs"
    else:
        msg['Subject'] = "Log from run at: " + time
        body = "See attached log"

    msg.attach(MIMEText(body, 'plain'))

    for log in emails_table.all():

        if not args.automatic:
            doingstuffoverlay.destroy_overlay()
            doingstuffoverlay.make_overlay(root, "sending reports emails\r" + "email " + str(batch_number) +
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

    server = smtplib.SMTP(str(settings['email_smtp_server']), str(settings['email_smtp_port']))
    server.starttls()
    server.login(from_address, settings['email_password'])
    text = msg.as_string()
    print("sending " + str(msg['Subject'] + " to " + str(msg['To'])))
    server.sendmail(from_address, to_address_list, text)
    server.quit()
