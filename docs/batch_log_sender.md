# batch_log_sender.py

## Purpose
Sends log files as email attachments, typically after a batch process run. Handles both single and multiple log scenarios, and updates UI overlays during sending.

## Main Function
- `do(settings, reporting, emails_table, sent_emails_removal_queue, time, args, root, batch_number, emails_count, total_emails, simple_output, run_summary_string)`: Sends logs as email attachments to the configured recipients.

## Usage
Call `do(...)` with the appropriate arguments after a batch run to email logs to recipients.
