import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import doingstuffoverlay


def do(settings, reporting, emails_table, sent_emails_removal_queue, time, args, root, batch_number, emails_count,
       total_emails, simple_output, run_summary_string):
    from_address = settings['email_address']
    email_username = settings['email_username']
    to_address = reporting['report_email_destination']
    to_address_list = to_address.split(", ")

    if emails_table.count() != 1:
        subject_line = "Logs from run at: " + time
        email_body_text = run_summary_string + ". See attached logs"
    else:
        subject_line = "Log from run at: " + time
        email_body_text = run_summary_string + ". See attached log"

    if not args.automatic:
        doingstuffoverlay.destroy_overlay()
        doingstuffoverlay.make_overlay(root, "sending reports emails\r" + "email " + str(batch_number) +
                                       " attachment " + str(emails_count) + " of " + str(total_emails))
    else:
        simple_output.configure(text="sending reports emails\r" + "email " + str(batch_number) +
                                     " attachment " + str(emails_count) + " of " + str(total_emails))

    message = EmailMessage()
    message['Subject'] = subject_line
    message['From'] = settings['email_address']
    message['To'] = to_address_list
    message.set_content(email_body_text)

    for log in emails_table.all():

        if not args.automatic:
            doingstuffoverlay.update_overlay(root, "sending reports emails\r" + "email " + str(batch_number) +
                                             " attachment " + str(emails_count) + " of " + str(total_emails))
        else:
            simple_output.configure(text="sending reports emails\r" + "email " + str(batch_number) +
                                         " attachment " + str(emails_count) + " of " + str(total_emails))
        root.update()

        filename = log['log']

        attachmentpath = Path(filename)
        attachmentname = os.path.basename(filename)
        ctype, encoding = mimetypes.guess_type(attachmentpath)
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        with open(attachmentpath, 'rb') as fp:
            message.add_attachment(fp.read(),
                            maintype=maintype,
                            subtype=subtype,
                            filename=attachmentname)

        log['old_id'] = log.pop('id')
        if log['log'].endswith('.zip'):
            log['log'] = log['log'][:-4]
        sent_emails_removal_queue.insert(log)

    print("sending " + str(subject_line + " to " + str(to_address_list)))

    server = smtplib.SMTP(str(settings['email_smtp_server']), str(settings['smtp_port']))
    server.ehlo()
    server.starttls()
    if settings['email_username'] != "" and settings['email_password'] != "":
        server.login(settings['email_username'], settings['email_password'])
    server.send_message(message)
    server.close()
    
    if not args.automatic:
        doingstuffoverlay.destroy_overlay()
