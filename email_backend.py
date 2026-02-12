"""Email backend for sending files via email.

This module sends files as email attachments with
injectable client support for testing.
"""

import mimetypes
import os
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from backend.protocols import SMTPClientProtocol
from backend.smtp_client import RealSMTPClient, create_smtp_client


# this module sends the file specified in filename to the address specified in the dict process_parameters via email
# note: process_parameters is a dict from a row in the database, passed into this module


def do(
    process_parameters: dict,
    settings: dict,
    filename: str,
    smtp_client: Optional[SMTPClientProtocol] = None
) -> bool:
    """Send a file via email.
    
    Args:
        process_parameters: Dictionary containing email parameters:
            - email_to: Recipient email address(es), comma-separated
            - email_subject_line: Subject line template (supports %datetime% and %filename%)
        settings: Settings dictionary containing:
            - email_address: Sender email address
            - email_smtp_server: SMTP server hostname
            - smtp_port: SMTP server port
            - email_username: SMTP username (optional)
            - email_password: SMTP password (optional)
        filename: Local file path to send
        smtp_client: Optional injectable SMTP client for testing.
                    If None, creates real SMTP client.
    
    Returns:
        True if email was sent successfully
        
    Raises:
        Exception: If email cannot be sent after 10 retries
    """
    file_pass = False
    counter = 0
    
    while not file_pass:
        try:
            filename_no_path = os.path.basename(filename)
            filename_no_path_str = str(filename_no_path)
            
            # Build subject line
            if process_parameters['email_subject_line'] != "":
                date_time = str(time.ctime())
                subject_line_constructor = process_parameters['email_subject_line']
                subject_line = subject_line_constructor.replace(
                    "%datetime%", date_time
                ).replace("%filename%", filename_no_path)
            else:
                subject_line = str(filename_no_path) + " Attached"

            # Parse recipient addresses
            to_address = process_parameters['email_to']
            to_address_list = to_address.split(", ")

            # Build email message
            message = EmailMessage()
            message['Subject'] = subject_line
            message['From'] = settings['email_address']
            message['To'] = to_address_list
            message.set_content(filename_no_path_str + " Attached")

            # Determine content type and attach file
            ctype, encoding = mimetypes.guess_type(filename)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed), so
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            
            with open(filename, 'rb') as fp:
                message.add_attachment(
                    fp.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=filename_no_path_str
                )

            # Create or use provided SMTP client
            if smtp_client is not None:
                server = smtp_client
            else:
                server = create_smtp_client()
            
            # Connect and send
            server.connect(
                str(settings['email_smtp_server']),
                int(settings['smtp_port'])
            )
            server.ehlo()
            server.starttls()
            
            if settings.get('email_username', '') != "" and settings.get('email_password', '') != "":
                server.login(settings['email_username'], settings['email_password'])
            
            server.send_message(message)
            server.close()

            file_pass = True
            
        except Exception as email_error:
            if counter == 10:
                print("Retried 10 times, passing exception to dispatch")
                raise
            counter += 1
            time.sleep(counter * counter)
            print("Encountered an error. Retry number " + str(counter))
            print("Error is :" + str(email_error))
    
    return file_pass


class EmailBackend:
    """Email backend class for object-oriented usage.
    
    Provides an object-oriented interface to the email backend
    with injectable client support.
    
    Attributes:
        smtp_client: SMTP client instance (injectable for testing)
    """
    
    def __init__(self, smtp_client: Optional[SMTPClientProtocol] = None):
        """Initialize email backend.
        
        Args:
            smtp_client: Optional injectable SMTP client for testing.
        """
        self.smtp_client = smtp_client
    
    def send(
        self,
        process_parameters: dict,
        settings: dict,
        filename: str
    ) -> bool:
        """Send a file via email.
        
        Args:
            process_parameters: Email parameters
            settings: Settings dictionary
            filename: File to send
            
        Returns:
            True if successful
        """
        return do(process_parameters, settings, filename, self.smtp_client)
    
    @staticmethod
    def create_client(config: Optional[dict] = None) -> SMTPClientProtocol:
        """Create an SMTP client.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            SMTP client instance
        """
        return create_smtp_client(config=config)
