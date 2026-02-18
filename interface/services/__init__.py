"""Services package for interface module.

This package contains service classes that provide business logic
separated from UI concerns.

Available services:
- FTPService: FTP connection testing and operations
- ReportingService: Email reporting and log file handling
- SMTPService: SMTP connection testing
- ResendService: File resend flag management
"""

from interface.services.ftp_service import FTPService, FTPConnectionResult, MockFTPService
from interface.services.reporting_service import ReportingService
from interface.services.resend_service import ResendService
from interface.services.smtp_service import SMTPService, SMTPServiceProtocol, MockSMTPService

__all__ = [
    "FTPService",
    "FTPConnectionResult",
    "MockFTPService",
    "ReportingService",
    "ResendService",
    "SMTPService",
    "SMTPServiceProtocol",
    "MockSMTPService",
]
