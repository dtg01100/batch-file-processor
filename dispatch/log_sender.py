"""LogSender service for sending batch log emails.

This module provides a refactored, testable implementation of log email sending,
using Protocol interfaces for dependency injection.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Optional, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage
import mimetypes
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuration for email sending.
    
    Attributes:
        smtp_server: SMTP server hostname
        smtp_port: SMTP server port
        smtp_username: Username for SMTP authentication
        smtp_password: Password for SMTP authentication
        from_address: Email address to send from
        use_tls: Whether to use TLS encryption
    """
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_address: str
    use_tls: bool = True


@runtime_checkable
class EmailServiceProtocol(Protocol):
    """Protocol for email service implementations.
    
    Implementations should handle the actual sending of emails,
    abstracting away SMTP details for testing.
    """
    
    def send_email(self, to: list[str], subject: str, body: str, 
                   attachments: Optional[list[dict]] = None) -> bool:
        """Send an email.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            body: Email body text
            attachments: Optional list of attachment dicts with 'path' and 'name' keys
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        ...


@runtime_checkable  
class UIProtocol(Protocol):
    """Protocol for UI update implementations.
    
    Implementations should handle UI progress updates,
    abstracting away UI framework details for testing.
    """
    
    def update_progress(self, message: str) -> None:
        """Update the UI with a progress message.
        
        Args:
            message: Progress message to display
        """
        ...
    
    def update_email_progress(self, batch_number: int, email_count: int, 
                              total_emails: int) -> None:
        """Update the UI with email sending progress.
        
        Args:
            batch_number: Current batch number
            email_count: Current email/attachment count
            total_emails: Total number of emails to send
        """
        ...


class SMTPEmailService:
    """Real SMTP email service implementation.
    
    This class handles actual email sending via SMTP.
    """
    
    def __init__(self, config: EmailConfig):
        """Initialize the SMTP email service.
        
        Args:
            config: Email configuration containing SMTP settings
        """
        self.config = config
    
    def send_email(self, to: list[str], subject: str, body: str,
                   attachments: Optional[list[dict]] = None) -> bool:
        """Send an email via SMTP.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            body: Email body text
            attachments: Optional list of attachment dicts with 'path' and 'name' keys
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            message = EmailMessage()
            message['Subject'] = subject
            message['From'] = self.config.from_address
            message['To'] = to
            message.set_content(body)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    attachment_path = Path(attachment['path'])
                    attachment_name = attachment.get('name', os.path.basename(attachment['path']))
                    
                    ctype, encoding = mimetypes.guess_type(attachment_path)
                    if ctype is None or encoding is not None:
                        ctype = 'application/octet-stream'
                    maintype, subtype = ctype.split('/', 1)
                    
                    with open(attachment_path, 'rb') as fp:
                        message.add_attachment(
                            fp.read(),
                            maintype=maintype,
                            subtype=subtype,
                            filename=attachment_name
                        )
            
            # Connect and send
            server = smtplib.SMTP(str(self.config.smtp_server), str(self.config.smtp_port))
            try:
                server.ehlo()
                if self.config.use_tls:
                    server.starttls()
                    server.ehlo()
                if self.config.smtp_username and self.config.smtp_password:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(message)
            finally:
                server.close()
            
            logger.info(f"Email sent successfully to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class MockEmailService:
    """Mock email service for testing.
    
    Records all sent emails for verification in tests.
    """
    
    def __init__(self):
        """Initialize the mock email service."""
        self.sent_emails: list[dict] = []
        self.should_fail: bool = False
    
    def send_email(self, to: list[str], subject: str, body: str,
                   attachments: Optional[list[dict]] = None) -> bool:
        """Record an email send attempt.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            body: Email body text
            attachments: Optional list of attachment dicts
            
        Returns:
            False if should_fail is True, True otherwise
        """
        if self.should_fail:
            return False
            
        self.sent_emails.append({
            'to': to,
            'subject': subject,
            'body': body,
            'attachments': attachments or []
        })
        return True
    
    def reset(self) -> None:
        """Clear all recorded emails."""
        self.sent_emails.clear()
    
    def get_last_email(self) -> Optional[dict]:
        """Get the most recently sent email.
        
        Returns:
            The last sent email dict, or None if no emails sent
        """
        return self.sent_emails[-1] if self.sent_emails else None


class NullUIService:
    """Null UI service that does nothing.
    
    Useful for headless operation or when UI updates are not needed.
    """
    
    def update_progress(self, message: str) -> None:
        """Do nothing."""
        pass
    
    def update_email_progress(self, batch_number: int, email_count: int,
                              total_emails: int) -> None:
        """Do nothing."""
        pass


class MockUIService:
    """Mock UI service for testing.
    
    Records all progress updates for verification.
    """
    
    def __init__(self):
        """Initialize the mock UI service."""
        self.progress_messages: list[str] = []
        self.email_progress_updates: list[dict] = []
    
    def update_progress(self, message: str) -> None:
        """Record a progress update.
        
        Args:
            message: Progress message to record
        """
        self.progress_messages.append(message)
    
    def update_email_progress(self, batch_number: int, email_count: int,
                              total_emails: int) -> None:
        """Record an email progress update.
        
        Args:
            batch_number: Current batch number
            email_count: Current email/attachment count
            total_emails: Total number of emails to send
        """
        self.email_progress_updates.append({
            'batch_number': batch_number,
            'email_count': email_count,
            'total_emails': total_emails
        })
    
    def reset(self) -> None:
        """Clear all recorded updates."""
        self.progress_messages.clear()
        self.email_progress_updates.clear()
    
    def get_last_progress(self) -> Optional[str]:
        """Get the most recent progress message.
        
        Returns:
            The last progress message, or None if no messages
        """
        return self.progress_messages[-1] if self.progress_messages else None


@dataclass
class LogEntry:
    """Represents a log entry to be sent.
    
    Attributes:
        log_path: Path to the log file
        log_name: Display name for the log
        metadata: Additional metadata for the log
    """
    log_path: str
    log_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.log_name is None:
            self.log_name = os.path.basename(self.log_path)


class LogSender:
    """Service for sending batch log emails.
    
    This class coordinates the sending of log emails, using injected
    email and UI services for testability.
    """
    
    def __init__(self, email_service: EmailServiceProtocol, 
                 ui: Optional[UIProtocol] = None):
        """Initialize the log sender.
        
        Args:
            email_service: Service for sending emails
            ui: Optional UI service for progress updates
        """
        self.email_service = email_service
        self.ui = ui or NullUIService()
    
    def send_log(self, log_content: str, recipients: list[str], 
                 subject: str, log_name: Optional[str] = None) -> bool:
        """Send a log to recipients.
        
        Args:
            log_content: The content of the log to send
            recipients: List of email addresses to send to
            subject: Email subject line
            log_name: Optional name for the log attachment
            
        Returns:
            True if sent successfully, False otherwise
        """
        return self.email_service.send_email(
            to=recipients,
            subject=subject,
            body=log_content
        )
    
    def send_log_file(self, log_path: str, recipients: list[str],
                      subject: str) -> bool:
        """Send a log file as an attachment.
        
        Args:
            log_path: Path to the log file
            recipients: List of email addresses to send to
            subject: Email subject line
            
        Returns:
            True if sent successfully, False otherwise
        """
        attachment = {
            'path': log_path,
            'name': os.path.basename(log_path)
        }
        
        return self.email_service.send_email(
            to=recipients,
            subject=subject,
            body="Please see attached log file.",
            attachments=[attachment]
        )
    
    def send_batch_logs(self, logs: list[LogEntry], recipients: list[str],
                        subject: str, body: str = "Please see attached logs.",
                        batch_number: int = 1, total_batches: int = 1) -> dict[str, bool]:
        """Send multiple logs in a single email.
        
        Args:
            logs: List of LogEntry objects to send
            recipients: List of email addresses to send to
            subject: Email subject line
            body: Email body text
            batch_number: Current batch number for progress updates
            total_batches: Total number of batches for progress updates
            
        Returns:
            Dict mapping log paths to send success status
        """
        results: dict[str, bool] = {}
        
        # Build attachments list
        attachments = []
        for i, log in enumerate(logs):
            self.ui.update_email_progress(
                batch_number=batch_number,
                email_count=i + 1,
                total_emails=len(logs)
            )
            
            if os.path.exists(log.log_path):
                attachments.append({
                    'path': log.log_path,
                    'name': log.log_name or os.path.basename(log.log_path)
                })
                results[log.log_path] = True
            else:
                logger.warning(f"Log file not found: {log.log_path}")
                results[log.log_path] = False
        
        if attachments:
            success = self.email_service.send_email(
                to=recipients,
                subject=subject,
                body=body,
                attachments=attachments
            )
            # Update results based on actual send success
            for log_path in results:
                if results[log_path]:
                    results[log_path] = success
        
        return results
    
    def send_logs_from_table(self, logs_table: Any, recipients: list[str],
                             subject: str, body: str,
                             batch_number: int = 1, total_batches: int = 1,
                             removal_queue: Optional[Any] = None) -> dict[str, bool]:
        """Send logs from a table structure (for backward compatibility).
        
        This method provides compatibility with the existing batch_log_sender.py
        interface, which uses a table-like structure for logs.
        
        Args:
            logs_table: Table-like object with .all() method returning log records
            recipients: List of email addresses to send to
            subject: Email subject line
            body: Email body text
            batch_number: Current batch number for progress updates
            total_batches: Total number of batches for progress updates
            removal_queue: Optional queue to add sent logs to
            
        Returns:
            Dict mapping log paths to send success status
        """
        logs = []
        log_records = []
        
        for log_record in logs_table.all():
            log_path = log_record.get('log', '')
            logs.append(LogEntry(log_path=log_path))
            log_records.append(log_record)
        
        results = self.send_batch_logs(
            logs=logs,
            recipients=recipients,
            subject=subject,
            body=body,
            batch_number=batch_number,
            total_batches=total_batches
        )
        
        # Add to removal queue if provided
        if removal_queue:
            for log_record in log_records:
                log_path = log_record.get('log', '')
                if results.get(log_path, False):
                    # Prepare record for removal queue
                    record = dict(log_record)
                    if 'id' in record:
                        record['old_id'] = record.pop('id')
                    if record.get('log', '').endswith('.zip'):
                        record['log'] = record['log'][:-4]
                    removal_queue.insert(record)
        
        return results


def create_log_sender_from_settings(settings: dict, 
                                    ui: Optional[UIProtocol] = None) -> LogSender:
    """Factory function to create a LogSender from settings dict.
    
    Args:
        settings: Settings dictionary with email configuration
        ui: Optional UI service for progress updates
        
    Returns:
        Configured LogSender instance
    """
    config = EmailConfig(
        smtp_server=settings.get('email_smtp_server', ''),
        smtp_port=int(settings.get('smtp_port', 587)),
        smtp_username=settings.get('email_username', ''),
        smtp_password=settings.get('email_password', ''),
        from_address=settings.get('email_address', ''),
        use_tls=settings.get('use_tls', True)
    )
    
    email_service = SMTPEmailService(config)
    return LogSender(email_service=email_service, ui=ui)
