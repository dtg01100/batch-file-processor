#!/usr/bin/env python3
"""Redact PII from the legacy v32 database fixture."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tests', 'fixtures', 'legacy_v32_folders.db')


def redact():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Redact folders table
    cursor.execute("""
        UPDATE folders SET
            email_origin_address = 'user' || id || '@example.com',
            email_origin_password = 'redacted_password',
            email_origin_username = 'user' || id || '@example.com',
            email_origin_smtp_server = 'smtp.example.com',
            email_to = CASE WHEN email_to IS NOT NULL AND email_to != ''
                       THEN 'recipient' || id || '@example.com' ELSE email_to END,
            email_subject_line = CASE WHEN email_subject_line IS NOT NULL AND email_subject_line != ''
                                 THEN 'Invoice' ELSE email_subject_line END,
            ftp_server = CASE WHEN ftp_server IS NOT NULL AND ftp_server != ''
                         THEN 'ftp.example.com' ELSE ftp_server END,
            ftp_username = CASE WHEN ftp_username IS NOT NULL AND ftp_username != ''
                           THEN 'ftp_user_' || id ELSE ftp_username END,
            ftp_password = CASE WHEN ftp_password IS NOT NULL AND ftp_password != ''
                           THEN 'redacted_password' ELSE ftp_password END,
            report_email_address = CASE WHEN report_email_address IS NOT NULL AND report_email_address != ''
                                   THEN 'report' || id || '@example.com' ELSE report_email_address END,
            report_email_username = CASE WHEN report_email_username IS NOT NULL AND report_email_username != ''
                                    THEN 'report' || id || '@example.com' ELSE report_email_username END,
            report_email_password = CASE WHEN report_email_password IS NOT NULL AND report_email_password != ''
                                    THEN 'redacted_password' ELSE report_email_password END,
            report_email_smtp_server = CASE WHEN report_email_smtp_server IS NOT NULL AND report_email_smtp_server != ''
                                       THEN 'smtp.example.com' ELSE report_email_smtp_server END,
            report_email_destination = CASE WHEN report_email_destination IS NOT NULL AND report_email_destination != ''
                                       THEN 'admin@example.com' ELSE report_email_destination END,
            reporting_email = CASE WHEN reporting_email IS NOT NULL AND reporting_email != ''
                              THEN 'report' || id || '@example.com' ELSE reporting_email END,
            copy_to_directory = CASE WHEN copy_to_directory IS NOT NULL AND copy_to_directory != ''
                                THEN 'D:/OUTPUT/' || alias ELSE copy_to_directory END,
            edi_converter_scratch_folder = CASE WHEN edi_converter_scratch_folder IS NOT NULL AND edi_converter_scratch_folder != ''
                                           THEN 'C:/ProgramData/BatchFileSender/scratch' ELSE edi_converter_scratch_folder END,
            folder_name = 'D:/DATA/OUT/' || alias
    """)
    print(f"Folders updated: {cursor.rowcount} rows")

    # Redact administrative table
    cursor.execute("""
        UPDATE administrative SET
            email_origin_address = 'admin@example.com',
            email_origin_password = 'redacted_password',
            email_origin_username = 'admin@example.com',
            email_origin_smtp_server = 'smtp.example.com',
            email_to = 'admin@example.com',
            email_subject_line = 'Invoice',
            ftp_server = 'ftp.example.com',
            ftp_username = 'ftp_admin',
            ftp_password = 'redacted_password',
            report_email_address = 'report@example.com',
            report_email_username = 'report@example.com',
            report_email_password = 'redacted_password',
            report_email_smtp_server = 'smtp.example.com',
            report_email_destination = 'admin@example.com',
            reporting_email = 'report@example.com',
            copy_to_directory = 'D:/OUTPUT/default',
            logs_directory = 'C:/ProgramData/BatchFileSender/Logs',
            edi_converter_scratch_folder = 'C:/ProgramData/BatchFileSender/scratch',
            errors_folder = 'C:/ProgramData/BatchFileSender/errors',
            folder_name = 'template'
    """)
    print(f"Administrative updated: {cursor.rowcount} rows")

    # Redact settings table
    cursor.execute("""
        UPDATE settings SET
            email_address = 'settings@example.com',
            email_username = '',
            email_password = '',
            email_smtp_server = 'smtp.example.com',
            as400_username = 'as400_user',
            as400_password = 'as400_pass',
            as400_address = '10.0.0.100'
    """)
    print(f"Settings updated: {cursor.rowcount} rows")

    # Redact processed_files table - replace path prefixes but keep structure
    # The file_name looks like "I:\MAILBOX\OUT\012258\012258.115"
    # Replace with "D:\DATA\OUT\{rest}"
    cursor.execute(r"""
        UPDATE processed_files SET
            file_name = REPLACE(file_name, 'I:\MAILBOX\OUT\', 'D:\DATA\OUT\'),
            copy_destination = CASE WHEN copy_destination = 'N/A' THEN copy_destination
                               ELSE 'D:/OUTPUT/redacted' END,
            ftp_destination = CASE WHEN ftp_destination = 'N/A' THEN ftp_destination
                              ELSE 'ftp.example.com/redacted' END,
            email_destination = CASE WHEN email_destination = 'N/A' THEN email_destination
                                ELSE 'redacted@example.com' END
    """)
    print(f"Processed files updated: {cursor.rowcount} rows")

    # Redact email tables
    cursor.execute("UPDATE emails_to_send SET log = 'redacted' WHERE log IS NOT NULL")
    print(f"emails_to_send updated: {cursor.rowcount} rows")
    cursor.execute("UPDATE working_batch_emails_to_send SET log = 'redacted' WHERE log IS NOT NULL")
    print(f"working_batch_emails_to_send updated: {cursor.rowcount} rows")
    cursor.execute("UPDATE sent_emails_removal_queue SET log = 'redacted' WHERE log IS NOT NULL")
    print(f"sent_emails_removal_queue updated: {cursor.rowcount} rows")

    conn.commit()

    # Verify counts are preserved
    cursor.execute("SELECT COUNT(*) FROM folders")
    print(f"Folders count: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM processed_files")
    print(f"Processed files count: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM administrative")
    print(f"Administrative count: {cursor.fetchone()[0]}")

    # VACUUM to reclaim space and remove old data from free pages
    cursor.execute("VACUUM")

    conn.close()
    print("Redaction complete!")


if __name__ == '__main__':
    redact()
