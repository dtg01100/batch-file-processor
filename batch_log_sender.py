import os
from pathlib import Path
from redmail import EmailSender

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

    attachment_dict = {}
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
        attachment_dict[attachmentname] = attachmentpath

        log['old_id'] = log.pop('id')
        if log['log'].endswith('.zip'):
            log['log'] = log['log'][:-4]
        sent_emails_removal_queue.insert(log)

    emailer = EmailSender(host=settings['email_smtp_server'], port=settings['smtp_port'])
    
    print("sending " + str(subject_line + " to " + str(to_address_list)))

    if settings['email_username'] == "" and settings['email_password'] == '':
        emailer.send(
            subject=subject_line,
            sender=settings['email_address'],
            receivers=to_address_list,
            text=email_body_text,
            attachments=attachment_dict
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
            text=email_body_text,
            attachments=attachment_dict
        )

    if not args.automatic:
        doingstuffoverlay.destroy_overlay()
